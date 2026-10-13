//! The client: auth headers, conditional GETs, rate-limit exposure; retries via the error policy.

use std::collections::{BTreeMap, HashMap};
use std::future::Future;
use std::sync::{Mutex, MutexGuard, PoisonError};
use std::time::Duration;

use crate::{
    Error, ErrorPolicy, Halt, RateLimit, RawRequest, RawResponse, Token, Transport, parse_response,
    send_with_policy,
};

/// Lock, recovering the data if a panicking holder poisoned it.
fn relock<T>(m: &Mutex<T>) -> MutexGuard<'_, T> {
    m.lock().unwrap_or_else(PoisonError::into_inner)
}

/// The HTTP methods the client issues.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Method {
    /// Read.
    Get,
    /// Create or GraphQL.
    Post,
    /// Partial update.
    Patch,
    /// Replace.
    Put,
    /// Remove.
    Delete,
}

impl Method {
    /// The upper-case method token.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Get => "GET",
            Self::Post => "POST",
            Self::Patch => "PATCH",
            Self::Put => "PUT",
            Self::Delete => "DELETE",
        }
    }
}

/// Waiting, injected so tests record waits instead of sleeping.
pub trait Pause: Send + Sync {
    /// Wait for `duration`.
    fn pause(&self, duration: Duration) -> impl Future<Output = ()> + Send;
}

/// The real wait, on the tokio timer.
#[derive(Debug, Clone, Copy, Default)]
pub struct TokioPause;

impl Pause for TokioPause {
    async fn pause(&self, duration: Duration) {
        tokio::time::sleep(duration).await;
    }
}

/// A successful answer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reply {
    /// Final status (200 for a body replayed from the `ETag` cache after a `304`).
    pub status: u16,
    /// Body bytes.
    pub body: Vec<u8>,
    /// Rate-limit headers, or `None` when the response carried none.
    pub rate_limit: Option<RateLimit>,
    /// The response `etag`, when present.
    pub etag: Option<String>,
    /// True when GitHub answered 304 and the body came from the cache.
    pub from_cache: bool,
}

impl Reply {
    /// Decode the body as JSON.
    ///
    /// # Errors
    /// [`Error::Json`] when the body does not match `T`.
    pub fn json<T: serde::de::DeserializeOwned>(&self) -> Result<T, Error> {
        serde_json::from_slice(&self.body).map_err(|e| Error::Json(e.to_string()))
    }
}

/// A GitHub API client over any [`Transport`].
#[derive(Debug)]
pub struct Client<T, P = TokioPause> {
    transport: T,
    pause: P,
    token: Token,
    base: String,
    policy: ErrorPolicy,
    etags: Mutex<HashMap<String, (String, Vec<u8>)>>,
}

impl<T: Transport> Client<T, TokioPause> {
    /// A client for `https://api.github.com` with the default [`ErrorPolicy`].
    pub fn new(transport: T, token: Token) -> Self {
        Self {
            transport,
            pause: TokioPause,
            token,
            base: "https://api.github.com".to_string(),
            policy: ErrorPolicy::default(),
            etags: Mutex::new(HashMap::new()),
        }
    }
}

impl<T: Transport, P: Pause> Client<T, P> {
    /// Replace the waiting strategy.
    pub fn with_pause<Q: Pause>(self, pause: Q) -> Client<T, Q> {
        Client {
            transport: self.transport,
            pause,
            token: self.token,
            base: self.base,
            policy: self.policy,
            etags: self.etags,
        }
    }

    /// Replace the retry policy.
    #[must_use]
    pub fn with_policy(mut self, policy: ErrorPolicy) -> Self {
        self.policy = policy;
        self
    }

    /// Point at another API root (GitHub Enterprise); must be https.
    ///
    /// # Errors
    /// [`Error::InsecureBase`] when the URL is not https.
    pub fn with_base(mut self, base: &str) -> Result<Self, Error> {
        if !base.starts_with("https://") {
            return Err(Error::InsecureBase(base.to_string()));
        }
        self.base = base.trim_end_matches('/').to_string();
        Ok(self)
    }

    /// The transport, for inspection in tests.
    pub fn transport(&self) -> &T {
        &self.transport
    }

    /// Conditional REST GET: sends `If-None-Match` when the URL was seen before.
    ///
    /// # Errors
    /// Any [`Error`]; see [`Client::execute`].
    pub async fn get(&self, path: &str) -> Result<Reply, Error> {
        self.execute(Method::Get, path, None).await
    }

    /// REST call with a JSON body.
    ///
    /// # Errors
    /// Any [`Error`]; see [`Client::execute`].
    pub async fn send_json(
        &self,
        method: Method,
        path: &str,
        body: &serde_json::Value,
    ) -> Result<Reply, Error> {
        self.execute(method, path, Some(body.to_string().into_bytes()))
            .await
    }

    /// GraphQL call: POST `/graphql` with `query` and `variables`; any `errors` entry fails the
    /// whole scope via [`parse_response`].
    ///
    /// # Errors
    /// [`Error::Graphql`] for an errors array or bad envelope; else see [`Client::execute`].
    pub async fn graphql(
        &self,
        query: &str,
        variables: &serde_json::Value,
    ) -> Result<Reply, Error> {
        let body = serde_json::json!({ "query": query, "variables": variables });
        let reply = self.send_json(Method::Post, "/graphql", &body).await?;
        if let Err(failure) = parse_response(&reply.body, reply.rate_limit.as_ref()) {
            tracing::warn!(%failure, "graphql response failed the scope");
            return Err(Error::Graphql(failure));
        }
        Ok(reply)
    }

    /// Issue a request through [`send_with_policy`]: stop on no budget, else retry 5xx and
    /// Retry-After answers on the [`ErrorPolicy`] schedule.
    ///
    /// # Errors
    /// [`Error::RateLimited`], [`Error::RetriesExhausted`], [`Error::Status`] for other
    /// non-success statuses, [`Error::InsecureBase`] for a non-https URL, and transport errors.
    pub async fn execute(
        &self,
        method: Method,
        path: &str,
        body: Option<Vec<u8>>,
    ) -> Result<Reply, Error> {
        let url = if path.starts_with("https://") {
            path.to_string()
        } else {
            format!("{}{path}", self.base)
        };
        if !url.starts_with("https://") {
            return Err(Error::InsecureBase(url));
        }
        let cached = if method == Method::Get {
            relock(&self.etags).get(&url).cloned()
        } else {
            None
        };
        let request = self.build(method, &url, body, cached.as_ref().map(|(e, _)| e.as_str()));
        let response = send_with_policy(&self.transport, &self.pause, self.policy, request)
            .await
            .map_err(halt_to_error)?;
        let rate_limit = RateLimit::parse(&response.headers);
        match response.status {
            200..=299 => Ok(self.accept(method, &url, response, rate_limit)),
            304 => {
                let (etag, cached_body) = cached.ok_or(Error::Status {
                    status: 304,
                    url: url.clone(),
                })?;
                tracing::debug!(%url, "not modified; serving cached body");
                Ok(Reply {
                    status: 200,
                    body: cached_body,
                    rate_limit,
                    etag: Some(etag),
                    from_cache: true,
                })
            }
            status => {
                tracing::warn!(status, %url, "unsuccessful status");
                Err(Error::Status { status, url })
            }
        }
    }

    fn build(
        &self,
        method: Method,
        url: &str,
        body: Option<Vec<u8>>,
        etag: Option<&str>,
    ) -> RawRequest {
        let mut headers = BTreeMap::new();
        headers.insert("authorization".to_string(), self.token.bearer());
        headers.insert(
            "accept".to_string(),
            "application/vnd.github+json".to_string(),
        );
        headers.insert("x-github-api-version".to_string(), "2022-11-28".to_string());
        if body.is_some() {
            headers.insert("content-type".to_string(), "application/json".to_string());
        }
        if let Some(etag) = etag {
            headers.insert("if-none-match".to_string(), etag.to_string());
        }
        RawRequest {
            method,
            url: url.to_string(),
            headers,
            body,
        }
    }

    fn accept(
        &self,
        method: Method,
        url: &str,
        response: RawResponse,
        rate_limit: Option<RateLimit>,
    ) -> Reply {
        let etag = response.headers.get("etag").cloned();
        if let (Method::Get, Some(tag)) = (method, &etag) {
            relock(&self.etags).insert(url.to_string(), (tag.clone(), response.body.clone()));
        }
        Reply {
            status: response.status,
            body: response.body,
            rate_limit,
            etag,
            from_cache: false,
        }
    }
}

/// Map a policy halt onto the client's error type.
fn halt_to_error(halt: Halt) -> Error {
    match halt {
        Halt::RateLimited { reset } => Error::RateLimited { reset },
        Halt::RetriesExhausted { retries, .. } => Error::RetriesExhausted {
            attempts: retries + 1,
        },
        Halt::Transport(e) => e,
    }
}

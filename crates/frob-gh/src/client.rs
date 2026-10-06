//! The client: auth headers, conditional GETs, rate-limit exposure and Retry-After backoff.

use std::collections::{BTreeMap, HashMap};
use std::future::Future;
use std::sync::{Mutex, MutexGuard, PoisonError};
use std::time::Duration;

use crate::{Error, RateLimit, RawRequest, RawResponse, Token, Transport};

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

/// Retry bounds for rate-limited answers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Policy {
    /// Total attempts including the first.
    pub max_attempts: u32,
    /// The longest single wait the client will perform; a larger Retry-After is an error.
    pub max_wait: Duration,
    /// The first wait when no Retry-After is given; doubles per further attempt.
    pub base_backoff: Duration,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            max_attempts: 4,
            max_wait: Duration::from_secs(120),
            base_backoff: Duration::from_secs(1),
        }
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
    policy: Policy,
    etags: Mutex<HashMap<String, (String, Vec<u8>)>>,
}

impl<T: Transport> Client<T, TokioPause> {
    /// A client for `https://api.github.com` with the default [`Policy`].
    pub fn new(transport: T, token: Token) -> Self {
        Self {
            transport,
            pause: TokioPause,
            token,
            base: "https://api.github.com".to_string(),
            policy: Policy::default(),
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
    pub fn with_policy(mut self, policy: Policy) -> Self {
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

    /// GraphQL call: POST `/graphql` with `query` and `variables`; the `errors` array is the
    /// caller's to read (the error-policy ticket classifies it).
    ///
    /// # Errors
    /// Any [`Error`]; see [`Client::execute`].
    pub async fn graphql(
        &self,
        query: &str,
        variables: &serde_json::Value,
    ) -> Result<Reply, Error> {
        let body = serde_json::json!({ "query": query, "variables": variables });
        self.send_json(Method::Post, "/graphql", &body).await
    }

    /// Issue a request, retrying 429 and Retry-After-bearing 403/503 answers per the [`Policy`].
    ///
    /// # Errors
    /// [`Error::RetryAfterExceedsCap`], [`Error::RetriesExhausted`], [`Error::Status`] for other
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
        let mut attempt = 1u32;
        loop {
            let request = self.build(
                method,
                &url,
                body.clone(),
                cached.as_ref().map(|(e, _)| e.as_str()),
            );
            let response = self.transport.send(request).await?;
            let rate_limit = RateLimit::parse(&response.headers);
            match response.status {
                200..=299 => return Ok(self.accept(method, &url, response, rate_limit)),
                304 => {
                    let (etag, cached_body) = cached.ok_or(Error::Status {
                        status: 304,
                        url: url.clone(),
                    })?;
                    tracing::debug!(%url, "not modified; serving cached body");
                    return Ok(Reply {
                        status: 200,
                        body: cached_body,
                        rate_limit,
                        etag: Some(etag),
                        from_cache: true,
                    });
                }
                429 | 403 | 503 if is_retryable(&response) => {
                    let asked = retry_after(&response.headers);
                    let wait = asked.unwrap_or_else(|| self.backoff(attempt));
                    if wait > self.policy.max_wait {
                        tracing::warn!(?wait, cap = ?self.policy.max_wait, "retry-after exceeds the cap");
                        return Err(Error::RetryAfterExceedsCap {
                            wait,
                            cap: self.policy.max_wait,
                        });
                    }
                    if attempt >= self.policy.max_attempts {
                        tracing::warn!(attempt, "rate limited; attempts exhausted");
                        return Err(Error::RetriesExhausted { attempts: attempt });
                    }
                    tracing::info!(
                        attempt,
                        ?wait,
                        status = response.status,
                        "rate limited; waiting before retry"
                    );
                    self.pause.pause(wait).await;
                    attempt += 1;
                }
                status => {
                    tracing::warn!(status, %url, "unsuccessful status");
                    return Err(Error::Status { status, url });
                }
            }
        }
    }

    fn backoff(&self, attempt: u32) -> Duration {
        let factor = 1u32
            .checked_shl(attempt.saturating_sub(1))
            .unwrap_or(u32::MAX);
        self.policy
            .base_backoff
            .saturating_mul(factor)
            .min(self.policy.max_wait)
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

/// 429 always retries; 403 and 503 only when the server named a wait.
fn is_retryable(response: &RawResponse) -> bool {
    response.status == 429 || response.headers.contains_key("retry-after")
}

/// `Retry-After` in whole seconds; an HTTP-date form is treated as absent.
fn retry_after(headers: &BTreeMap<String, String>) -> Option<Duration> {
    headers
        .get("retry-after")?
        .trim()
        .parse::<u64>()
        .ok()
        .map(Duration::from_secs)
}

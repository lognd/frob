//! The live transport over reqwest: HTTPS only, redirects off, rustls with the ring provider.

use std::collections::BTreeMap;
use std::sync::Once;
use std::time::Duration;

use crate::{Error, Method, RawRequest, RawResponse, Transport};

static PROVIDER: Once = Once::new();

/// Production [`Transport`]; construction never touches the network.
#[derive(Debug, Clone)]
pub struct ReqwestTransport {
    http: reqwest::Client,
}

impl ReqwestTransport {
    /// Build the client (30 s request timeout, no redirects, https only).
    ///
    /// # Errors
    /// [`Error::Transport`] when the TLS stack cannot initialise.
    pub fn new() -> Result<Self, Error> {
        PROVIDER.call_once(|| {
            // Err means another provider is already installed, which is fine for us.
            let _ = rustls::crypto::ring::default_provider().install_default();
        });
        let http = reqwest::Client::builder()
            .redirect(reqwest::redirect::Policy::none())
            .https_only(true)
            .timeout(Duration::from_secs(30))
            .user_agent("frob-gh")
            .build()
            .map_err(|e| Error::Transport(e.to_string()))?;
        tracing::debug!("reqwest transport ready");
        Ok(Self { http })
    }
}

impl Transport for ReqwestTransport {
    async fn send(&self, request: RawRequest) -> Result<RawResponse, Error> {
        let method = match request.method {
            Method::Get => reqwest::Method::GET,
            Method::Post => reqwest::Method::POST,
            Method::Patch => reqwest::Method::PATCH,
            Method::Put => reqwest::Method::PUT,
            Method::Delete => reqwest::Method::DELETE,
        };
        tracing::debug!(?request, "sending request");
        let mut builder = self.http.request(method, &request.url);
        for (k, v) in &request.headers {
            builder = builder.header(k, v);
        }
        if let Some(body) = request.body {
            builder = builder.body(body);
        }
        let response = builder
            .send()
            .await
            .map_err(|e| Error::Transport(e.to_string()))?;
        let status = response.status().as_u16();
        let headers: BTreeMap<String, String> = response
            .headers()
            .iter()
            .filter_map(|(k, v)| {
                v.to_str()
                    .ok()
                    .map(|v| (k.as_str().to_ascii_lowercase(), v.to_string()))
            })
            .collect();
        let body = response
            .bytes()
            .await
            .map_err(|e| Error::Transport(e.to_string()))?
            .to_vec();
        tracing::debug!(status, bytes = body.len(), "response received");
        Ok(RawResponse {
            status,
            headers,
            body,
        })
    }
}

//! The seam between the client and the wire: a request and response as plain data.

use std::collections::BTreeMap;
use std::future::Future;

use crate::{Error, Method};

/// One outgoing request; `Debug` hides the `authorization` header.
#[derive(Clone, PartialEq, Eq)]
pub struct RawRequest {
    /// HTTP method.
    pub method: Method,
    /// Absolute https URL.
    pub url: String,
    /// Header names (lower case) to values.
    pub headers: BTreeMap<String, String>,
    /// JSON body bytes, if any.
    pub body: Option<Vec<u8>>,
}

impl std::fmt::Debug for RawRequest {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let headers: Vec<_> = self
            .headers
            .iter()
            .map(|(k, v)| {
                if k == "authorization" {
                    (k.as_str(), "<redacted>")
                } else {
                    (k.as_str(), v.as_str())
                }
            })
            .collect();
        f.debug_struct("RawRequest")
            .field("method", &self.method)
            .field("url", &self.url)
            .field("headers", &headers)
            .field("body_len", &self.body.as_ref().map(Vec::len))
            .finish()
    }
}

/// One response; header names are lower case.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawResponse {
    /// HTTP status code.
    pub status: u16,
    /// Header names (lower case) to values.
    pub headers: BTreeMap<String, String>,
    /// Body bytes.
    pub body: Vec<u8>,
}

/// Sends one request and returns one response; no retries, no caching, no policy.
pub trait Transport: Send + Sync {
    /// Perform the request.
    ///
    /// # Errors
    /// [`Error::Transport`] on connection or TLS failure; [`Error::Unrecorded`] from fixtures.
    fn send(&self, request: RawRequest) -> impl Future<Output = Result<RawResponse, Error>> + Send;
}

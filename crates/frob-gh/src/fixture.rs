//! Recorded exchanges replayed in order; anything unrecorded is an error, never a network call.

use std::collections::{BTreeMap, VecDeque};
use std::future::Future;
use std::sync::{Mutex, MutexGuard, PoisonError};

use crate::{Error, RawRequest, RawResponse, Transport};

/// Lock, recovering the data if a panicking test poisoned it.
fn relock<T>(m: &Mutex<T>) -> MutexGuard<'_, T> {
    m.lock().unwrap_or_else(PoisonError::into_inner)
}

/// What a recording expects to see: method and full URL (headers are not matched).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RecordedRequest {
    /// `GET`, `POST`, ...
    pub method: String,
    /// Absolute URL.
    pub url: String,
}

/// What a recording answers with; the body is UTF-8 text.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RecordedResponse {
    /// HTTP status.
    pub status: u16,
    /// Header names to values (matched case-insensitively by lower-casing on replay).
    #[serde(default)]
    pub headers: BTreeMap<String, String>,
    /// Body text.
    #[serde(default)]
    pub body: String,
}

/// One request/response pair of a recording (a JSON fixture file is an array of these).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Exchange {
    /// The expected request.
    pub request: RecordedRequest,
    /// The recorded answer.
    pub response: RecordedResponse,
}

/// A [`Transport`] that replays [`Exchange`]s in order and remembers what it was sent.
#[derive(Debug)]
pub struct FixtureTransport {
    queue: Mutex<VecDeque<Exchange>>,
    seen: Mutex<Vec<RawRequest>>,
}

impl FixtureTransport {
    /// Replay the given exchanges in order.
    pub fn new(exchanges: Vec<Exchange>) -> Self {
        Self {
            queue: Mutex::new(exchanges.into()),
            seen: Mutex::new(Vec::new()),
        }
    }

    /// Parse a JSON fixture (an array of exchanges).
    ///
    /// # Errors
    /// [`Error::Json`] when the text is not a valid recording.
    pub fn from_json(text: &str) -> Result<Self, Error> {
        let exchanges: Vec<Exchange> =
            serde_json::from_str(text).map_err(|e| Error::Json(e.to_string()))?;
        tracing::debug!(count = exchanges.len(), "loaded recorded exchanges");
        Ok(Self::new(exchanges))
    }

    /// Every request received so far, in order.
    pub fn requests(&self) -> Vec<RawRequest> {
        relock(&self.seen).clone()
    }

    /// Recorded exchanges not yet consumed.
    pub fn remaining(&self) -> usize {
        relock(&self.queue).len()
    }
}

impl Transport for FixtureTransport {
    fn send(&self, request: RawRequest) -> impl Future<Output = Result<RawResponse, Error>> + Send {
        let method = request.method.as_str().to_string();
        let url = request.url.clone();
        relock(&self.seen).push(request);
        let mut queue = relock(&self.queue);
        std::future::ready(match queue.front() {
            Some(next)
                if next.request.method.eq_ignore_ascii_case(&method) && next.request.url == url =>
            {
                let exchange = queue.pop_front().expect("front checked");
                let headers = exchange
                    .response
                    .headers
                    .into_iter()
                    .map(|(k, v)| (k.to_ascii_lowercase(), v))
                    .collect();
                Ok(RawResponse {
                    status: exchange.response.status,
                    headers,
                    body: exchange.response.body.into_bytes(),
                })
            }
            _ => {
                tracing::error!(%method, %url, "request has no recorded exchange");
                Err(Error::Unrecorded { method, url })
            }
        })
    }
}

//! Native HTTPS [`HttpTransport`] for the GitHub adapter (mirror.md 3.6): no subprocess, the
//! bearer token travels only in a request header held in this process.

// frob:ticket 01M5B07S0STANADP897P4A6YB2

use std::fmt::Write as _;
use std::time::Duration;

use tracing::{debug, warn};
use ureq::Agent;
use ureq::http::{Request, header};

use crate::github::adapter::{HttpRequest, HttpResponse, HttpTransport, Method, TransportError};

/// GitHub API root.
pub const API_ROOT: &str = "https://api.github.com";
/// Whole-call timeout.
const CALL_TIMEOUT: Duration = Duration::from_secs(30);

/// Percent-encode a query component (unreserved characters pass through).
fn enc(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'~') {
            out.push(char::from(b));
        } else {
            let _ = write!(out, "%{b:02X}");
        }
    }
    out
}

/// An [`HttpTransport`] over `ureq` (rustls); redirects are reported, never followed.
#[derive(Clone)]
pub struct NativeTransport {
    agent: Agent,
    root: String,
    token: String,
}

impl std::fmt::Debug for NativeTransport {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("NativeTransport")
            .field("root", &self.root)
            .field("token", &"<redacted>")
            .finish_non_exhaustive()
    }
}

impl NativeTransport {
    /// A transport against the public GitHub API authenticated with `token`.
    #[must_use]
    pub fn new(token: impl Into<String>) -> Self {
        Self::with_root(API_ROOT, token)
    }

    /// A transport against `root` (no trailing slash); used for GitHub Enterprise and tests.
    #[must_use]
    pub fn with_root(root: impl Into<String>, token: impl Into<String>) -> Self {
        let agent: Agent = Agent::config_builder()
            .timeout_global(Some(CALL_TIMEOUT))
            .http_status_as_error(false)
            .max_redirects(0)
            .build()
            .into();
        Self {
            agent,
            root: root.into(),
            token: token.into(),
        }
    }

    /// Full URL for `req`: root, path and encoded query.
    fn url(&self, req: &HttpRequest) -> String {
        let mut url = format!("{}{}", self.root, req.path);
        for (i, (k, v)) in req.query.iter().enumerate() {
            url.push(if i == 0 { '?' } else { '&' });
            let _ = write!(url, "{}={}", enc(k), enc(v));
        }
        url
    }
}

/// Map a `ureq` failure to the transport error it means.
fn map_error(e: &ureq::Error) -> TransportError {
    match e {
        ureq::Error::Timeout(_) => TransportError::Timeout,
        other => TransportError::Other(other.to_string()),
    }
}

impl HttpTransport for NativeTransport {
    fn send(&self, req: &HttpRequest) -> Result<HttpResponse, TransportError> {
        let method = match req.method {
            Method::Get => "GET",
            Method::Post => "POST",
            Method::Patch => "PATCH",
            Method::Delete => "DELETE",
        };
        let url = self.url(req);
        debug!(%method, path = %req.path, "mirror http: send");
        let body = req
            .body
            .as_ref()
            .map(ToString::to_string)
            .unwrap_or_default();
        let mut builder = Request::builder()
            .method(method)
            .uri(&url)
            .header(header::AUTHORIZATION, format!("Bearer {}", self.token))
            .header(header::ACCEPT, "application/vnd.github+json")
            .header("X-GitHub-Api-Version", "2022-11-28")
            .header(header::USER_AGENT, "frob-mirror");
        if req.body.is_some() {
            builder = builder.header(header::CONTENT_TYPE, "application/json");
        }
        let request = builder
            .body(body)
            .map_err(|e| TransportError::Other(format!("bad request: {e}")))?;
        let mut resp = self.agent.run(request).map_err(|e| {
            warn!(error = %e, path = %req.path, "mirror http: failed");
            map_error(&e)
        })?;
        let status = resp.status().as_u16();
        let location = resp
            .headers()
            .get(header::LOCATION)
            .and_then(|v| v.to_str().ok())
            .map(str::to_owned);
        let text = resp
            .body_mut()
            .read_to_string()
            .map_err(|e| map_error(&e))?;
        debug!(status, "mirror http: response");
        Ok(HttpResponse {
            status,
            location,
            body: text,
        })
    }
}

#[cfg(test)]
mod tests {
    use std::io::{Read, Write};
    use std::net::TcpListener;

    use serde_json::json;

    use super::*;

    /// Serve one canned response, returning the root URL and the raw request it saw.
    fn serve(response: &'static str) -> (String, std::thread::JoinHandle<String>) {
        let l = TcpListener::bind("127.0.0.1:0").expect("bind");
        let root = format!("http://{}", l.local_addr().expect("addr"));
        let h = std::thread::spawn(move || {
            let (mut s, _) = l.accept().expect("accept");
            let mut buf = Vec::new();
            let mut chunk = [0u8; 1024];
            loop {
                let n = s.read(&mut chunk).expect("read");
                buf.extend_from_slice(&chunk[..n]);
                let text = String::from_utf8_lossy(&buf).into_owned();
                if let Some((head, body)) = text.split_once("\r\n\r\n") {
                    let len = head
                        .lines()
                        .find_map(|l| {
                            l.to_ascii_lowercase()
                                .strip_prefix("content-length:")
                                .map(|v| v.trim().parse::<usize>().unwrap_or(0))
                        })
                        .unwrap_or(0);
                    if body.len() >= len {
                        break;
                    }
                }
                if n == 0 {
                    break;
                }
            }
            s.write_all(response.as_bytes()).expect("write");
            String::from_utf8_lossy(&buf).into_owned()
        });
        (root, h)
    }

    // frob:tests NativeTransport
    #[test]
    fn native_transport_posts_json_with_headers() {
        let (root, h) = serve(
            "HTTP/1.1 201 Created\r\nContent-Length: 11\r\nConnection: close\r\n\r\n{\"id\": 42}\n",
        );
        let t = NativeTransport::with_root(root, "tok");
        let resp = t
            .send(&HttpRequest {
                method: Method::Post,
                path: "/repos/o/r/issues".into(),
                query: vec![("a b".into(), "c".into())],
                body: Some(json!({"title": "x"})),
            })
            .expect("response");
        assert_eq!(resp.status, 201);
        assert_eq!(resp.body, "{\"id\": 42}\n");
        let seen = h.join().expect("join");
        assert!(seen.starts_with("POST /repos/o/r/issues?a%20b=c HTTP/1.1"));
        let lower = seen.to_ascii_lowercase();
        assert!(lower.contains("authorization: bearer tok"));
        assert!(lower.contains("content-type: application/json"));
        assert!(seen.ends_with("{\"title\":\"x\"}"));
    }

    // frob:tests NativeTransport
    #[test]
    fn native_transport_reports_redirect_without_following() {
        let (root, h) = serve(
            "HTTP/1.1 301 Moved\r\nLocation: https://api.github.com/repositories/9\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
        );
        let t = NativeTransport::with_root(root, "tok");
        let resp = t
            .send(&HttpRequest {
                method: Method::Get,
                path: "/repos/o/r".into(),
                query: vec![],
                body: None,
            })
            .expect("response");
        h.join().expect("join");
        assert_eq!(resp.status, 301);
        assert_eq!(
            resp.location.as_deref(),
            Some("https://api.github.com/repositories/9")
        );
    }

    // frob:tests NativeTransport
    #[test]
    fn native_transport_connection_refused_is_other() {
        let l = TcpListener::bind("127.0.0.1:0").expect("bind");
        let root = format!("http://{}", l.local_addr().expect("addr"));
        drop(l);
        let t = NativeTransport::with_root(root, "tok");
        let err = t
            .send(&HttpRequest {
                method: Method::Get,
                path: "/".into(),
                query: vec![],
                body: None,
            })
            .expect_err("refused");
        assert!(matches!(err, TransportError::Other(_)));
    }
}

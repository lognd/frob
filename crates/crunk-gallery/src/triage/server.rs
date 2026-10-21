//! The blocking loopback HTTP server behind `gallery triage`.

// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ

use std::fmt::Write as _;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::PathBuf;
use std::time::Duration;

use super::TriageError;
use super::page::{self, Tile};
use super::store::{self, Reviewer};
use crate::cells::Cell;
use crate::manifest::Manifest;

const MAX_REQUEST: usize = 64 * 1024;

/// Everything one triage session works on.
#[derive(Debug)]
pub struct Session {
    /// The cells under review, in display order.
    pub cells: Vec<Cell>,
    /// The manifest being edited.
    pub manifest: Manifest,
    /// Where the manifest is saved after every verdict.
    pub manifest_path: PathBuf,
    /// Directory the render paths are relative to.
    pub artifacts: PathBuf,
    /// Who the verdicts are attributed to.
    pub reviewer: Reviewer,
    /// Random per-run secret every request must carry.
    pub token: String,
    /// Set once the reviewer pressed Finish.
    pub done: bool,
}

/// A parsed request.
#[derive(Debug)]
pub struct Request {
    /// HTTP method.
    pub method: String,
    /// Request target including any query.
    pub target: String,
    /// Lower-cased header names with values.
    pub headers: Vec<(String, String)>,
    /// Request body.
    pub body: Vec<u8>,
}

/// A response to write back.
#[derive(Debug)]
pub struct Response {
    /// Status code.
    pub status: u16,
    /// Content type.
    pub content_type: &'static str,
    /// Body bytes.
    pub body: Vec<u8>,
}

impl Response {
    fn text(status: u16, msg: &str) -> Self {
        Self {
            status,
            content_type: "text/plain; charset=utf-8",
            body: msg.as_bytes().to_vec(),
        }
    }
}

impl Request {
    fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|(k, _)| k == name)
            .map(|(_, v)| v.as_str())
    }
    fn path(&self) -> &str {
        self.target.split('?').next().unwrap_or("")
    }
    fn query_token(&self) -> Option<&str> {
        self.target
            .split_once('?')?
            .1
            .split('&')
            .find_map(|kv| kv.strip_prefix("t="))
    }
}

fn tiles(s: &Session) -> Vec<Tile> {
    s.cells
        .iter()
        .map(|c| {
            let e = s.manifest.entries.iter().find(|e| {
                e.screen == c.screen
                    && e.platform == c.platform
                    && e.state.as_deref() == Some(c.state.as_str())
            });
            Tile {
                screen: c.screen.clone(),
                state: c.state.clone(),
                platform: c.platform.clone(),
                status: e.and_then(|e| e.verdict.as_ref()).map(|v| v.status),
                rendered: e.is_some_and(|e| e.render.is_some()),
            }
        })
        .collect()
}

fn host_ok(req: &Request) -> bool {
    req.header("host").is_some_and(|h| {
        let name = h.rsplit_once(':').map_or(h, |(n, _)| n);
        matches!(name, "127.0.0.1" | "localhost")
    })
}

fn token_ok(req: &Request, token: &str) -> bool {
    req.header("x-triage-token").or_else(|| req.query_token()) == Some(token)
}

/// Answer `req` against `session`; pure apart from saving the manifest on a verdict.
pub fn handle(session: &mut Session, req: &Request) -> Response {
    if !host_ok(req) {
        tracing::warn!("triage request refused: bad Host header");
        return Response::text(403, "bad host");
    }
    if req.method == "POST"
        && let Some(origin) = req.header("origin")
    {
        let local = origin.strip_prefix("http://").is_some_and(|o| {
            matches!(
                o.rsplit_once(':').map_or(o, |(n, _)| n),
                "127.0.0.1" | "localhost"
            )
        });
        if !local {
            tracing::warn!(origin, "triage request refused: cross-origin");
            return Response::text(403, "cross-origin");
        }
    }
    match (req.method.as_str(), req.path()) {
        ("GET", "/") => Response {
            status: 200,
            content_type: "text/html; charset=utf-8",
            body: page::render(&tiles(session), &session.token).into_bytes(),
        },
        ("GET", p) if p.starts_with("/img/") => {
            if !token_ok(req, &session.token) {
                return Response::text(403, "bad token");
            }
            image(session, &p["/img/".len()..])
        }
        ("POST", "/verdict") => {
            if !token_ok(req, &session.token) {
                return Response::text(403, "bad token");
            }
            verdict(session, &req.body)
        }
        ("POST", "/done") => {
            if !token_ok(req, &session.token) {
                return Response::text(403, "bad token");
            }
            session.done = true;
            Response::text(200, "saved")
        }
        _ => Response::text(404, "not found"),
    }
}

fn image(s: &Session, index: &str) -> Response {
    let Some(cell) = index.parse::<usize>().ok().and_then(|i| s.cells.get(i)) else {
        return Response::text(404, "no such cell");
    };
    let rel = s
        .manifest
        .entries
        .iter()
        .find(|e| {
            e.screen == cell.screen
                && e.platform == cell.platform
                && e.state.as_deref() == Some(cell.state.as_str())
        })
        .and_then(|e| e.render.as_ref())
        .map(|r| r.path.as_str());
    // Render paths are bare file names; anything with path syntax is never served.
    let Some(rel) = rel.filter(|r| !r.is_empty() && !r.contains(['/', '\\']) && *r != "..") else {
        return Response::text(404, "no render");
    };
    match std::fs::read(s.artifacts.join(rel)) {
        Ok(bytes) => Response {
            status: 200,
            content_type: "image/png",
            body: bytes,
        },
        Err(e) => {
            tracing::warn!(error = %e, "triage image unreadable");
            Response::text(404, "no render")
        }
    }
}

fn verdict(s: &mut Session, body: &[u8]) -> Response {
    let Ok(v) = serde_json::from_slice::<serde_json::Value>(body) else {
        return Response::text(400, "bad json");
    };
    let cell = v
        .get("index")
        .and_then(serde_json::Value::as_u64)
        .and_then(|i| s.cells.get(usize::try_from(i).ok()?))
        .cloned();
    let status = v
        .get("status")
        .and_then(serde_json::Value::as_str)
        .and_then(store::parse_status);
    let (Some(cell), Some(status)) = (cell, status) else {
        return Response::text(400, "bad verdict");
    };
    let result = store::set_verdict(&mut s.manifest, &cell, status, &s.reviewer)
        .and_then(|()| store::save(&s.manifest_path, &s.manifest));
    match result {
        Ok(()) => Response::text(200, "ok"),
        Err(e) => {
            tracing::warn!(error = %e, "verdict refused");
            Response::text(409, &e.to_string())
        }
    }
}

fn read_request(stream: &mut TcpStream) -> Option<Request> {
    let mut buf = Vec::new();
    let mut chunk = [0u8; 4096];
    let head_end = loop {
        if let Some(p) = buf.windows(4).position(|w| w == b"\r\n\r\n") {
            break p;
        }
        if buf.len() > MAX_REQUEST {
            return None;
        }
        let n = stream.read(&mut chunk).ok()?;
        if n == 0 {
            return None;
        }
        buf.extend_from_slice(&chunk[..n]);
    };
    let head = String::from_utf8_lossy(&buf[..head_end]).into_owned();
    let mut lines = head.split("\r\n");
    let mut first = lines.next()?.split(' ');
    let method = first.next()?.to_owned();
    let target = first.next()?.to_owned();
    let headers: Vec<(String, String)> = lines
        .filter_map(|l| l.split_once(':'))
        .map(|(k, v)| (k.trim().to_ascii_lowercase(), v.trim().to_owned()))
        .collect();
    let want = headers
        .iter()
        .find(|(k, _)| k == "content-length")
        .and_then(|(_, v)| v.parse::<usize>().ok())
        .unwrap_or(0);
    if want > MAX_REQUEST {
        return None;
    }
    let mut body = buf[head_end + 4..].to_vec();
    while body.len() < want {
        let n = stream.read(&mut chunk).ok()?;
        if n == 0 {
            return None;
        }
        body.extend_from_slice(&chunk[..n]);
    }
    body.truncate(want);
    Some(Request {
        method,
        target,
        headers,
        body,
    })
}

fn write_response(stream: &mut TcpStream, r: &Response) {
    let reason = match r.status {
        200 => "OK",
        400 => "Bad Request",
        403 => "Forbidden",
        404 => "Not Found",
        _ => "Conflict",
    };
    let head = format!(
        "HTTP/1.1 {} {reason}\r\nContent-Type: {}\r\nContent-Length: {}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n",
        r.status,
        r.content_type,
        r.body.len()
    );
    let _ = stream
        .write_all(head.as_bytes())
        .and_then(|()| stream.write_all(&r.body));
}

/// A fresh random token (32 hex digits) for one triage session.
///
/// # Errors
///
/// [`TriageError::Invalid`] when the system random source fails.
pub fn new_token() -> Result<String, TriageError> {
    let mut bytes = [0u8; 16];
    getrandom::fill(&mut bytes).map_err(|e| TriageError::Invalid(format!("no randomness: {e}")))?;
    Ok(bytes.iter().fold(String::new(), |mut acc, b| {
        let _ = write!(acc, "{b:02x}");
        acc
    }))
}

/// Bind `127.0.0.1:port` (0 picks a free port); the caller reads the address, then calls [`serve`].
///
/// # Errors
///
/// [`TriageError::Io`] when the port cannot be bound.
pub fn bind(port: u16) -> Result<TcpListener, TriageError> {
    let l = TcpListener::bind(SocketAddr::from(([127, 0, 0, 1], port)))?;
    tracing::info!(addr = ?l.local_addr().ok(), "triage server bound");
    Ok(l)
}

/// Serve requests one at a time until the reviewer finishes; returns the final session.
///
/// # Errors
///
/// [`TriageError::Io`] when accepting a connection fails.
pub fn serve(listener: &TcpListener, mut session: Session) -> Result<Session, TriageError> {
    while !session.done {
        let (mut stream, peer) = listener.accept()?;
        let _ = stream.set_read_timeout(Some(Duration::from_secs(5)));
        let Some(req) = read_request(&mut stream) else {
            tracing::debug!(peer = ?peer, "unreadable triage request dropped");
            continue;
        };
        tracing::debug!(method = %req.method, target = %req.target, "triage request");
        let resp = handle(&mut session, &req);
        write_response(&mut stream, &resp);
    }
    tracing::info!("triage finished");
    Ok(session)
}

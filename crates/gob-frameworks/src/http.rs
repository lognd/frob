//! The HTTP layer: server routes (`FastAPI`, Flask, Express, axum) and client call sites (`fetch`, axios, ky)
//! read from the folded terms of Python, Rust and TypeScript sources, and the cross-language edges that
//! match a call to a route by method and path template.

// frob:ticket 01M4GM5DE96WY2ZDRZP0ETTMMF

mod client;
mod read;
mod server;

use std::path::Path;

use gob_ir::{Model, Term};
use gob_symbols::fold_file;
use gob_walk::FileEntry;
use tracing::{debug, info, warn};

use crate::registry::in_node_modules;
use crate::types::{Method, Problem, Route, Status};

/// The HTTP client library a call site uses.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Library {
    /// The platform `fetch`.
    Fetch,
    /// axios.
    Axios,
    /// ky.
    Ky,
}

impl Library {
    /// The library's lower-case name.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Fetch => "fetch",
            Self::Axios => "axios",
            Self::Ky => "ky",
        }
    }
}

/// One HTTP client call site: where it is, which request it makes and how sure the reading is.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ClientCall {
    /// The client library.
    pub library: Library,
    /// The request method; `Any` when it is not statically known.
    pub method: Method,
    /// The path template (`/orders/:id`), or `None` when the URL is opaque.
    pub pattern: Option<String>,
    /// `Must` when method and path are spelled out, `May` when built dynamically, `Unknown` when opaque.
    pub status: Status,
    /// True when an unknown base URL precedes the path, so the path only has to match a route's tail.
    pub open_prefix: bool,
    /// The symref of the enclosing function or component, when there is one.
    pub caller: Option<String>,
    /// Repo-relative path of the file.
    pub file: String,
    /// One-based line of the call.
    pub line: u32,
}

/// A client call matched to a server route: one cross-language implementation hop.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct HttpEdge {
    /// The calling site.
    pub call: ClientCall,
    /// The route it reaches.
    pub route: Route,
    /// `Must` for an exact method and path match, `May` when either side is dynamic or open.
    pub status: Status,
}

/// One folded source file as the extractors see it.
pub(crate) struct File<'a> {
    pub path: &'a str,
    pub text: &'a str,
    pub term: &'a Term,
    pub model: &'a Model,
}

/// What the HTTP layer found.
#[derive(Debug, Default)]
pub(crate) struct Found {
    pub routes: Vec<Route>,
    pub calls: Vec<ClientCall>,
    pub problems: Vec<Problem>,
}

const TS_EXT: [&str; 6] = ["ts", "tsx", "js", "jsx", "mjs", "cjs"];

/// Reads every TypeScript, Python and Rust source under `root` and extracts server routes and client calls.
pub(crate) fn extract(root: &Path, files: &[FileEntry]) -> Found {
    let mut found = Found::default();
    for entry in files {
        let p = entry.path.as_str();
        let ext = p.rsplit_once('.').map_or("", |(_, e)| e);
        let (ts, py) = (TS_EXT.contains(&ext), ext == "py");
        if !(ts || py || ext == "rs") || in_node_modules(p) {
            continue;
        }
        let text = match std::fs::read_to_string(root.join(p)) {
            Ok(t) => t,
            Err(e) => {
                warn!(path = p, error = %e, "http layer could not read source");
                found.problems.push(Problem {
                    path: p.to_owned(),
                    reason: format!("unreadable source: {e}"),
                });
                continue;
            }
        };
        let relevant = if ts {
            ["fetch", "axios", "ky", "express"]
                .iter()
                .any(|k| text.contains(k))
        } else if py {
            text.contains("fastapi") || text.contains("flask")
        } else {
            text.contains("axum")
        };
        if !relevant {
            continue;
        }
        let folded = match fold_file(entry, &text) {
            Ok(f) => f,
            Err(e) => {
                warn!(path = p, error = %e, "http layer could not fold source");
                found.problems.push(Problem {
                    path: p.to_owned(),
                    reason: format!("unfoldable source: {e}"),
                });
                continue;
            }
        };
        let model = Model::new(folded.term, folded.scopes);
        let file = File {
            path: p,
            text: &text,
            term: model.term(),
            model: &model,
        };
        if ts {
            found.calls.extend(client::calls(&file));
            found.routes.extend(server::express_routes(&file));
        } else if py {
            found.routes.extend(server::python_routes(&file));
        } else {
            found.routes.extend(server::axum_routes(&file));
        }
    }
    info!(
        routes = found.routes.len(),
        calls = found.calls.len(),
        "http layer extracted"
    );
    found
}

/// The non-empty segments of a path template.
fn segments(pattern: &str) -> Vec<&str> {
    pattern.split('/').filter(|s| !s.is_empty()).collect()
}

/// Whether the call segments `c` match the route segments `r` in full.
fn match_segments(c: &[&str], r: &[&str]) -> bool {
    match (c.split_first(), r.split_first()) {
        (_, Some((rs, _))) if rs.starts_with(':') && (rs.ends_with('+') || rs.ends_with('*')) => {
            !(rs.ends_with('+') && c.is_empty())
        }
        (None, None) => true,
        (Some((cs, ctail)), Some((rs, rtail))) => {
            (cs.starts_with(':') || rs.starts_with(':') || cs == rs) && match_segments(ctail, rtail)
        }
        _ => false,
    }
}

/// Whether a call's path reaches the route's path.
fn paths_match(call: &ClientCall, route_pattern: &str) -> bool {
    let (Some(cp), r) = (call.pattern.as_deref(), segments(route_pattern)) else {
        return false;
    };
    let c = segments(cp);
    if call.open_prefix {
        (0..=r.len()).any(|i| match_segments(&c, &r[i..]))
    } else {
        match_segments(&c, &r)
    }
}

/// Matches client calls to server routes by method and path template, symbolically rather than by text.
///
/// Calls and routes whose path is opaque (`Unknown`, no pattern) produce no edge; a method of `Any` or an
/// open base-URL prefix on either side lowers the edge to `May`.
pub fn link(calls: &[ClientCall], routes: &[Route]) -> Vec<HttpEdge> {
    let mut edges = Vec::new();
    for call in calls {
        for route in routes {
            if route.client || route.component.is_some() {
                continue;
            }
            let Some(rp) = route.pattern.as_deref() else {
                continue;
            };
            let method_ok = call.method == route.method
                || call.method == Method::Any
                || route.method == Method::Any;
            if !method_ok || !paths_match(call, rp) {
                continue;
            }
            let mut status = call.status.meet(route.status);
            if call.method != route.method || call.open_prefix {
                status = status.meet(Status::May);
            }
            debug!(file = call.file, line = call.line, route = rp, "http edge");
            edges.push(HttpEdge {
                call: call.clone(),
                route: route.clone(),
                status,
            });
        }
    }
    edges.sort();
    edges.dedup();
    edges
}

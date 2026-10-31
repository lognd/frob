//! Client call sites in TypeScript: `fetch`, axios and ky, with the request method and URL template read
//! from the call's arguments.

// frob:ticket 01M4GM5DE96WY2ZDRZP0ETTMMF

use std::collections::BTreeMap;

use gob_ir::NodeId;
use tracing::trace;

use super::read::{
    Part, adapter, enclosing_symref, is_apply, leaves, line_of, lit, path_of, ref_name, ts_parts,
    unquote,
};
use super::{ClientCall, File, Library};
use crate::types::{Method, Status};

/// How an object literal relates to a property name.
enum Prop {
    Found(NodeId),
    Absent,
    Unknown,
}

/// Looks `key` up in the object literal `obj`; `Unknown` when it is not an object or has spreads.
fn prop(f: &File<'_>, obj: NodeId, key: &str) -> Prop {
    let term = f.term;
    if adapter(term, obj) != Some("object") {
        return Prop::Unknown;
    }
    let mut unknown = false;
    let mut found = None;
    for &c in term.node(obj).children() {
        if lit(term, c).is_some() {
            continue;
        }
        if adapter(term, c) == Some("pair") {
            let kids = term.node(c).children();
            let name = kids.first().and_then(|&k| lit(term, k)).map(|(kind, l)| {
                if kind == "string" {
                    unquote(l)
                } else {
                    l.to_owned()
                }
            });
            if name.as_deref() == Some(key) {
                found = kids.last().copied();
            }
        } else {
            unknown = true;
        }
    }
    match (found, unknown) {
        (Some(v), _) => Prop::Found(v),
        (None, true) => Prop::Unknown,
        (None, false) => Prop::Absent,
    }
}

/// The method and its status from the options/config argument `opts` (absent means GET).
fn method_of(f: &File<'_>, opts: Option<NodeId>) -> (Method, Status) {
    let Some(opts) = opts else {
        return (Method::Get, Status::Must);
    };
    match prop(f, opts, "method") {
        Prop::Absent => (Method::Get, Status::Must),
        Prop::Unknown => (Method::Any, Status::May),
        Prop::Found(v) => match ts_parts(f.term, v).as_deref() {
            Some([Part::Lit(s)]) => Method::from_export(&s.to_ascii_uppercase())
                .map_or((Method::Any, Status::May), |m| (m, Status::Must)),
            _ => (Method::Any, Status::May),
        },
    }
}

/// The module aliases for axios and ky imported by the file.
fn aliases(f: &File<'_>) -> BTreeMap<String, Library> {
    let term = f.term;
    let mut out = BTreeMap::new();
    for id in term.ids() {
        if adapter(term, id) != Some("import") {
            continue;
        }
        let toks = leaves(term, id);
        let Some(from) = toks.iter().position(|t| t.1 == "from") else {
            continue;
        };
        let source = toks[from..].iter().find(|t| t.0 == "string_fragment");
        let library = match source.map(|t| t.1.as_str()) {
            Some("axios") => Library::Axios,
            Some("ky") => Library::Ky,
            _ => continue,
        };
        let head = &toks[..from];
        if let Some(t) = head.get(1).filter(|t| t.0 == "identifier") {
            out.insert(t.1.clone(), library);
        }
        if let Some(t) = head
            .iter()
            .position(|t| t.1 == "*")
            .and_then(|i| head.get(i + 2))
        {
            out.insert(t.1.clone(), library);
        }
    }
    out
}

/// The client calls of a TypeScript file.
pub(super) fn calls(f: &File<'_>) -> Vec<ClientCall> {
    let term = f.term;
    let aliases = aliases(f);
    let mut out = Vec::new();
    for id in term.ids() {
        if !is_apply(term, id, "call") {
            continue;
        }
        let kids = term.node(id).children();
        let Some(&callee_id) = kids.first() else {
            continue;
        };
        let Some(callee) = ref_name(term, callee_id) else {
            continue;
        };
        let args = &kids[1..];
        let found = if matches!(
            callee,
            "fetch" | "window.fetch" | "globalThis.fetch" | "self.fetch"
        ) {
            let shadowed =
                callee == "fetch" && f.model.resolve_node(callee_id).status() == Status::Must;
            (!shadowed).then(|| {
                (
                    Library::Fetch,
                    args.first().copied(),
                    method_of(f, args.get(1).copied()),
                    None,
                )
            })
        } else {
            let (head, tail) = callee
                .split_once('.')
                .map_or((callee, None), |(h, t)| (h, Some(t)));
            aliases.get(head).and_then(|&lib| match tail {
                None => alias_call(f, lib, args),
                Some("request") => config_call(f, lib, args.first().copied()),
                Some(v) if !v.contains('.') => {
                    let m = Method::from_export(&v.to_ascii_uppercase())?;
                    let cfg = args
                        .iter()
                        .rev()
                        .find(|&&a| adapter(term, a) == Some("object"))
                        .copied();
                    let base = cfg.is_some_and(|c| has_base(f, c));
                    Some((
                        lib,
                        args.first().copied(),
                        (m, Status::Must),
                        base.then_some(()),
                    ))
                }
                Some(_) => None,
            })
        };
        let Some((library, url, (method, mstatus), open)) = found else {
            continue;
        };
        let Some(url) = url else {
            continue;
        };
        let mut path = path_of(ts_parts(term, url));
        path.open_prefix |= open.is_some();
        trace!(file = f.path, callee, "client call");
        out.push(ClientCall {
            library,
            method,
            pattern: path.pattern.clone(),
            status: path.status.meet(mstatus),
            open_prefix: path.open_prefix,
            caller: enclosing_symref(term, id),
            file: f.path.to_owned(),
            line: line_of(f.text, term, id),
        });
    }
    out
}

type Found = (Library, Option<NodeId>, (Method, Status), Option<()>);

/// Whether the config object sets a `baseURL`.
fn has_base(f: &File<'_>, cfg: NodeId) -> bool {
    matches!(prop(f, cfg, "baseURL"), Prop::Found(_))
        || matches!(prop(f, cfg, "prefixUrl"), Prop::Found(_))
}

/// `axios(url, cfg)` or `axios(config)`.
fn alias_call(f: &File<'_>, lib: Library, args: &[NodeId]) -> Option<Found> {
    let first = *args.first()?;
    if adapter(f.term, first) == Some("object") {
        return config_call(f, lib, Some(first));
    }
    let cfg = args.get(1).copied();
    let open = cfg.is_some_and(|c| has_base(f, c));
    Some((lib, Some(first), method_of(f, cfg), open.then_some(())))
}

/// A call whose request is one config object with `url`, `method` and `baseURL`.
fn config_call(f: &File<'_>, lib: Library, cfg: Option<NodeId>) -> Option<Found> {
    let cfg = cfg?;
    let Prop::Found(url) = prop(f, cfg, "url") else {
        return None;
    };
    Some((
        lib,
        Some(url),
        method_of(f, Some(cfg)),
        has_base(f, cfg).then_some(()),
    ))
}

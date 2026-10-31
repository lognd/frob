//! Readers over the folded terms of TypeScript, Python and Rust sources: string values with their dynamic
//! parts, the shapes of call nodes and the path patterns they spell.

// frob:ticket 01M4GM5DE96WY2ZDRZP0ETTMMF

use std::collections::BTreeMap;

use gob_ir::{Location, NodeId, Operator, Term, Universal};

use crate::types::Status;

/// One piece of a string value: text that is known, or an interpolated expression that is not.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Part {
    /// Literal text.
    Lit(String),
    /// An interpolation or an operand that is not a constant, with a name for the path parameter it becomes.
    Param(String),
}

/// A string value as parts; `None` where the whole value is opaque.
pub(super) type Parts = Option<Vec<Part>>;

/// A path pattern read from a string value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Path {
    /// The pattern (`/orders/:id`), or `None` when the value is opaque.
    pub pattern: Option<String>,
    /// `Must` when the path is spelled out, `May` when a part is dynamic, `Unknown` when it is opaque.
    pub status: Status,
    /// True when an unknown prefix (a base URL) precedes the known path.
    pub open_prefix: bool,
}

impl Path {
    /// The path of an opaque value.
    pub(super) fn opaque() -> Self {
        Self {
            pattern: None,
            status: Status::Unknown,
            open_prefix: false,
        }
    }
}

/// The operator of `id`.
pub(super) fn op(term: &Term, id: NodeId) -> &Operator {
    term.node(id).op()
}

/// The kind and lexeme of the literal `id`.
pub(super) fn lit(term: &Term, id: NodeId) -> Option<(&str, &str)> {
    match op(term, id) {
        Operator::Universal(Universal::Lit { kind, lexeme }) => Some((kind, lexeme)),
        _ => None,
    }
}

/// The adapter operator name of `id`.
pub(super) fn adapter(term: &Term, id: NodeId) -> Option<&str> {
    match op(term, id) {
        Operator::Adapter(a) => Some(&a.name),
        Operator::Universal(_) => None,
    }
}

/// The name of the `ref` node `id`.
pub(super) fn ref_name(term: &Term, id: NodeId) -> Option<&str> {
    match op(term, id) {
        Operator::Universal(Universal::Ref { name }) => Some(name),
        _ => None,
    }
}

/// True when `id` is an `apply` of `kind`.
pub(super) fn is_apply(term: &Term, id: NodeId, kind: &str) -> bool {
    matches!(op(term, id), Operator::Universal(Universal::Apply { kind: k }) if k == kind)
}

/// The last `.`- or `::`-separated segment of a name.
pub(super) fn last_segment(name: &str) -> &str {
    name.rsplit(['.', ':']).next().unwrap_or(name)
}

/// The one-based line of `id` in `text`.
pub(super) fn line_of(text: &str, term: &Term, id: NodeId) -> u32 {
    let Location::Text { range, .. } = term.node(id).location() else {
        return 1;
    };
    let start = usize::try_from(u32::from(range.start())).unwrap_or(0);
    let upto = text.as_bytes().get(..start).unwrap_or(text.as_bytes());
    u32::try_from(upto.split(|b| *b == b'\n').count()).unwrap_or(u32::MAX)
}

/// The nearest enclosing unit (or anonymous function) of `id` that has a symref.
pub(super) fn enclosing_symref(term: &Term, id: NodeId) -> Option<String> {
    let mut cur = term.node(id).parent();
    while let Some(p) = cur {
        if let Some(s) = term.symref_of(p) {
            return Some(s.to_string());
        }
        cur = term.node(p).parent();
    }
    None
}

/// Unit name to symref for the names that are unique in the file.
pub(super) fn unit_names(term: &Term) -> BTreeMap<String, String> {
    let mut seen: BTreeMap<String, Option<String>> = BTreeMap::new();
    for u in term.units() {
        let Some(name) = term.node(u.node).name() else {
            continue;
        };
        let sym = u.symref.to_string();
        seen.entry(name.to_owned())
            .and_modify(|v| {
                if v.as_deref() != Some(sym.as_str()) {
                    *v = None;
                }
            })
            .or_insert(Some(sym));
    }
    seen.into_iter()
        .filter_map(|(k, v)| v.map(|s| (k, s)))
        .collect()
}

/// The `(kind, lexeme)` of every literal under `id`, in source order.
pub(super) fn leaves(term: &Term, id: NodeId) -> Vec<(String, String)> {
    let mut out = Vec::new();
    collect_leaves(term, id, &mut out);
    out
}

fn collect_leaves(term: &Term, id: NodeId, out: &mut Vec<(String, String)>) {
    if let Some((k, l)) = lit(term, id) {
        out.push((k.to_owned(), l.to_owned()));
    }
    for &c in term.node(id).children() {
        collect_leaves(term, c, out);
    }
}

/// `s` without its surrounding quotes.
pub(super) fn unquote(s: &str) -> String {
    let b = s.as_bytes();
    match (b.first(), b.last()) {
        (Some(q @ (b'"' | b'\'' | b'`')), Some(e)) if q == e && b.len() >= 2 => {
            s[1..s.len() - 1].to_owned()
        }
        _ => s.to_owned(),
    }
}

/// The path parameter name an interpolated expression stands for.
fn param_name(term: &Term, expr: Option<&NodeId>) -> String {
    expr.and_then(|&e| ref_name(term, e))
        .map_or("param", last_segment)
        .to_owned()
}

/// The string value of a TypeScript expression: literals, template strings and `+` concatenations.
pub(super) fn ts_parts(term: &Term, id: NodeId) -> Parts {
    if let Some((kind, lexeme)) = lit(term, id) {
        return match kind {
            "string" => Some(vec![Part::Lit(unquote(lexeme))]),
            "str" => Some(vec![Part::Lit(lexeme.to_owned())]),
            _ => None,
        };
    }
    let kids = term.node(id).children();
    match adapter(term, id)? {
        "template_string" => {
            let mut out = Vec::new();
            for &c in kids {
                match (lit(term, c), adapter(term, c)) {
                    (Some(("string_fragment", s)), _) => out.push(Part::Lit(s.to_owned())),
                    (_, Some("template_substitution")) => {
                        let inner = term.node(c).children();
                        out.push(Part::Param(param_name(term, inner.get(1))));
                    }
                    _ => {}
                }
            }
            Some(out)
        }
        "binary_expression" => {
            let (&l, &r) = (kids.first()?, kids.get(2)?);
            if lit(term, *kids.get(1)?).map(|(_, s)| s) != Some("+") {
                return None;
            }
            let side = |n: NodeId| {
                ts_parts(term, n).unwrap_or_else(|| vec![Part::Param(param_name(term, Some(&n)))])
            };
            let mut out = side(l);
            out.extend(side(r));
            Some(out)
        }
        "parenthesized_expression" => ts_parts(term, *kids.get(1)?),
        "as_expression" | "satisfies_expression" | "non_null_expression" => {
            ts_parts(term, *kids.first()?)
        }
        _ => None,
    }
}

/// The string value spelled by Python tokens: strings (f-strings with their interpolations), concatenated.
pub(super) fn py_parts(tokens: &[(String, String)]) -> Parts {
    let mut out = Vec::new();
    let mut seen_string = false;
    let mut i = 0;
    while i < tokens.len() {
        let (kind, lexeme) = (&tokens[i].0, &tokens[i].1);
        match kind.as_str() {
            "string_start" => {
                seen_string = true;
                i += 1;
                while i < tokens.len() && tokens[i].0 != "string_end" {
                    match tokens[i].0.as_str() {
                        "string_content" => out.push(Part::Lit(tokens[i].1.clone())),
                        "{" => {
                            let mut name = None;
                            while i < tokens.len() && tokens[i].0 != "}" {
                                if name.is_none() && tokens[i].0 == "identifier" {
                                    name = Some(tokens[i].1.clone());
                                }
                                i += 1;
                            }
                            out.push(Part::Param(name.unwrap_or_else(|| "param".into())));
                        }
                        _ => {}
                    }
                    i += 1;
                }
            }
            "+" => {}
            "string" => {
                seen_string = true;
                out.push(Part::Lit(unquote(lexeme)));
            }
            _ => out.push(Part::Param(if kind == "identifier" {
                lexeme.clone()
            } else {
                "param".into()
            })),
        }
        i += 1;
    }
    seen_string.then_some(out)
}

/// The string value of a Rust string literal node without escapes.
pub(super) fn rs_parts(term: &Term, id: NodeId) -> Parts {
    if adapter(term, id)? != "string_literal" {
        return None;
    }
    let mut text = String::new();
    for (kind, lexeme) in leaves(term, id) {
        match kind.as_str() {
            "string_content" => text.push_str(&lexeme),
            "\"" => {}
            _ => return None,
        }
    }
    Some(vec![Part::Lit(text)])
}

/// The path pattern of a string value: scheme, host and query stripped, dynamic segments as `:name`.
pub(super) fn path_of(parts: Parts) -> Path {
    let Some(parts) = parts else {
        return Path::opaque();
    };
    let has_text = parts
        .iter()
        .any(|p| matches!(p, Part::Lit(s) if s.chars().any(|c| c != '/' && !c.is_whitespace())));
    if !has_text {
        return Path::opaque();
    }
    let (parts, mut dynamic) = strip_authority(parts);
    let mut open_prefix = false;
    let mut parts = parts;
    if matches!(parts.first(), Some(Part::Param(_)))
        && matches!(parts.get(1), Some(Part::Lit(s)) if s.starts_with('/'))
    {
        parts.remove(0);
        open_prefix = true;
        dynamic = true;
    }
    let mut segments: Vec<String> = Vec::new();
    let mut cur = String::new();
    let mut param: Option<String> = None;
    let flush = |cur: &mut String, param: &mut Option<String>, segments: &mut Vec<String>| {
        match param.take() {
            Some(p) => segments.push(format!(":{p}")),
            None if !cur.is_empty() => segments.push(cur.clone()),
            None => {}
        }
        cur.clear();
    };
    'parts: for part in &parts {
        match part {
            Part::Param(name) => {
                dynamic = true;
                param.get_or_insert_with(|| name.clone());
            }
            Part::Lit(s) => {
                let (s, cut) = match s.find(['?', '#']) {
                    Some(at) => (&s[..at], true),
                    None => (s.as_str(), false),
                };
                for (n, piece) in s.split('/').enumerate() {
                    if n > 0 {
                        flush(&mut cur, &mut param, &mut segments);
                    }
                    cur.push_str(piece);
                }
                if cut {
                    break 'parts;
                }
            }
        }
    }
    flush(&mut cur, &mut param, &mut segments);
    let pattern = format!("/{}", segments.join("/"));
    Path {
        pattern: Some(pattern),
        status: if dynamic { Status::May } else { Status::Must },
        open_prefix,
    }
}

/// Drops `scheme://authority` from the front of a value; true when the authority was dynamic.
fn strip_authority(parts: Vec<Part>) -> (Vec<Part>, bool) {
    let Some(Part::Lit(first)) = parts.first() else {
        return (parts, false);
    };
    let Some(rest) = first
        .strip_prefix("https://")
        .or_else(|| first.strip_prefix("http://"))
    else {
        return (parts, false);
    };
    let mut dynamic = false;
    let mut out = Vec::new();
    let mut found = false;
    let mut iter = std::iter::once(Part::Lit(rest.to_owned())).chain(parts.into_iter().skip(1));
    for part in iter.by_ref() {
        match part {
            Part::Param(_) if !found => dynamic = true,
            Part::Lit(s) if !found => {
                if let Some(at) = s.find('/') {
                    found = true;
                    out.push(Part::Lit(s[at..].to_owned()));
                }
            }
            other => out.push(other),
        }
    }
    if !found {
        out.insert(0, Part::Lit("/".into()));
    }
    (out, dynamic)
}

/// A server path template normalised to the pattern syntax: `{id}`, `<int:id>` and `:id` become `:id`;
/// catch-all segments (`{p:path}`, `<path:p>`, `*p`, `{*p}`) become `:p+`.
pub(super) fn normalize_server(pattern: &str) -> String {
    let segs: Vec<String> = pattern
        .split('/')
        .filter(|s| !s.is_empty())
        .map(normalize_segment)
        .collect();
    format!("/{}", segs.join("/"))
}

fn normalize_segment(seg: &str) -> String {
    if let Some(inner) = seg.strip_prefix('{').and_then(|s| s.strip_suffix('}')) {
        return match inner.split_once(':') {
            Some((name, "path")) => format!(":{name}+"),
            Some((name, _)) => format!(":{name}"),
            None => match inner.strip_prefix('*') {
                Some(name) => format!(":{name}+"),
                None => format!(":{inner}"),
            },
        };
    }
    if let Some(inner) = seg.strip_prefix('<').and_then(|s| s.strip_suffix('>')) {
        return match inner.split_once(':') {
            Some(("path", name)) => format!(":{name}+"),
            Some((_, name)) => format!(":{name}"),
            None => format!(":{inner}"),
        };
    }
    if let Some(name) = seg.strip_prefix('*') {
        let name = if name.is_empty() { "wildcard" } else { name };
        return format!(":{name}+");
    }
    match seg.strip_suffix('?') {
        Some(name) if name.starts_with(':') => format!("{name}*"),
        _ => seg.to_owned(),
    }
}

/// Joins path prefixes and a path into one pattern.
pub(super) fn join_paths(prefix: &str, path: &str) -> String {
    let segs: Vec<&str> = prefix
        .split('/')
        .chain(path.split('/'))
        .filter(|s| !s.is_empty())
        .collect();
    format!("/{}", segs.join("/"))
}

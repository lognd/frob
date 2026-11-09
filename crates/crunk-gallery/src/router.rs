//! Route discovery for GALLERY005: the route paths a React Router `router.tsx` declares.
//!
//! This is a small token scanner, not a TypeScript parser. It understands the two shapes React
//! Router apps use: route objects (`createBrowserRouter([{ path: "/", children: [...] }])`) and
//! JSX (`<Route path="/about" />`), including nesting, which joins a child's relative path onto its
//! parent's. Shapes it cannot resolve statically (a `path` that is not a string literal, a template
//! with `${}`) are a typed [`RouterError`], never a guess and never a panic.
//!
//! Dynamic segments (`:id`, `:id?`, `*`) are kept verbatim in the returned path, so a screen covers
//! `/users/:id` by declaring that same string as its `entry`.

// frob:ticket 01M4YZCC0PBYFW8CSBB8ERKFXE

use thiserror::Error;

/// Why a router source yielded no routes.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum RouterError {
    /// A route's `path` is not a plain string literal, so it cannot be resolved statically.
    #[error(
        "router.tsx line {line}: route path is not a string literal ({reason}); pass it with --route instead"
    )]
    UnsupportedPath {
        /// 1-based line of the offending `path`.
        line: usize,
        /// What was found instead of a literal.
        reason: String,
    },
    /// The source declares no route with a path.
    #[error("no route paths found in the router source; pass them with --route instead")]
    NoRoutes,
}

#[derive(Debug, Clone, PartialEq)]
enum Tok {
    Ident(String),
    /// A string literal; the flag is true when a template literal interpolates (`${`).
    Str(String, bool),
    Punct(char),
}

/// Split `src` into tokens with 1-based line numbers, dropping comments and whitespace.
fn tokenize(src: &str) -> Vec<(Tok, usize)> {
    let chars: Vec<char> = src.chars().collect();
    let mut out = Vec::new();
    let (mut i, mut line) = (0, 1);
    while i < chars.len() {
        let c = chars[i];
        match c {
            '\n' => {
                line += 1;
                i += 1;
            }
            c if c.is_whitespace() => i += 1,
            '/' if chars.get(i + 1) == Some(&'/') => {
                while i < chars.len() && chars[i] != '\n' {
                    i += 1;
                }
            }
            '/' if chars.get(i + 1) == Some(&'*') => {
                i += 2;
                while i < chars.len() && !(chars[i] == '*' && chars.get(i + 1) == Some(&'/')) {
                    if chars[i] == '\n' {
                        line += 1;
                    }
                    i += 1;
                }
                i += 2;
            }
            '"' | '\'' | '`' => {
                let start_line = line;
                let (mut text, mut interp) = (String::new(), false);
                i += 1;
                let mut closed = false;
                while i < chars.len() {
                    let d = chars[i];
                    if d == '\\' {
                        text.extend(chars.get(i + 1));
                        i += 2;
                        continue;
                    }
                    if d == c {
                        closed = true;
                        i += 1;
                        break;
                    }
                    if d == '\n' {
                        line += 1;
                        // An unterminated quote is JSX text (an apostrophe), not a string.
                        if c != '`' {
                            break;
                        }
                    }
                    if c == '`' && d == '$' && chars.get(i + 1) == Some(&'{') {
                        interp = true;
                    }
                    text.push(d);
                    i += 1;
                }
                if closed {
                    out.push((Tok::Str(text, interp), start_line));
                }
            }
            c if c.is_alphabetic() || c == '_' || c == '$' => {
                let start = i;
                while i < chars.len()
                    && (chars[i].is_alphanumeric() || chars[i] == '_' || chars[i] == '$')
                {
                    i += 1;
                }
                out.push((Tok::Ident(chars[start..i].iter().collect()), line));
            }
            c => {
                out.push((Tok::Punct(c), line));
                i += 1;
            }
        }
    }
    out
}

/// One route element or object, with the path it declared (if any).
#[derive(Debug, Default)]
struct Frame {
    parent: Option<usize>,
    path: Option<String>,
    bad: Option<(usize, String)>,
    /// An object with route-ish keys (`element`, `children`, ...); plain config objects are not routes.
    routey: bool,
    /// JSX `<Route>` elements are always routes.
    jsx: bool,
}

const ROUTE_KEYS: &[&str] = &[
    "element",
    "Component",
    "children",
    "lazy",
    "loader",
    "action",
    "errorElement",
    "ErrorBoundary",
    "index",
];

/// Index of the token after the balanced `{ ... }` starting at `i` (which must be a `{`).
fn skip_braces(toks: &[(Tok, usize)], mut i: usize) -> usize {
    let mut depth = 0usize;
    while i < toks.len() {
        match toks[i].0 {
            Tok::Punct('{') => depth += 1,
            Tok::Punct('}') => {
                depth = depth.saturating_sub(1);
                if depth == 0 {
                    return i + 1;
                }
            }
            _ => {}
        }
        i += 1;
    }
    i
}

/// Describe a non-literal token for the error message.
fn describe(t: Option<&(Tok, usize)>) -> String {
    match t.map(|t| &t.0) {
        Some(Tok::Ident(s)) => format!("identifier `{s}`"),
        Some(Tok::Str(_, true)) => "template literal with `${}`".to_owned(),
        Some(Tok::Punct(c)) => format!("`{c}`"),
        _ => "end of input".to_owned(),
    }
}

/// Parse a `<Route ...` opening tag whose `<` is at `i`; returns the next index, the frame and
/// whether the tag self-closes.
fn jsx_route(toks: &[(Tok, usize)], mut i: usize, parent: Option<usize>) -> (usize, Frame, bool) {
    let mut f = Frame {
        parent,
        jsx: true,
        ..Frame::default()
    };
    i += 2; // `<` `Route`
    while i < toks.len() {
        match &toks[i].0 {
            Tok::Punct('>') => {
                let selfclose = i > 0 && toks[i - 1].0 == Tok::Punct('/');
                return (i + 1, f, selfclose);
            }
            Tok::Punct('{') => i = skip_braces(toks, i),
            Tok::Ident(k)
                if k == "path" && toks.get(i + 1).map(|t| &t.0) == Some(&Tok::Punct('=')) =>
            {
                let line = toks[i].1;
                match toks.get(i + 2).map(|t| &t.0) {
                    Some(Tok::Str(s, false)) => {
                        f.path = Some(s.clone());
                        i += 3;
                    }
                    Some(Tok::Punct('{')) => match (toks.get(i + 3), toks.get(i + 4)) {
                        (Some((Tok::Str(s, false), _)), Some((Tok::Punct('}'), _))) => {
                            f.path = Some(s.clone());
                            i += 5;
                        }
                        (other, _) => {
                            f.bad = Some((line, describe(other)));
                            i = skip_braces(toks, i + 2);
                        }
                    },
                    other => {
                        f.bad = Some((line, describe(toks.get(i + 2))));
                        let _ = other;
                        i += 2;
                    }
                }
            }
            _ => i += 1,
        }
    }
    (i, f, true)
}

/// Join a child path onto its parent's absolute path; an absolute child replaces it, and a
/// top-level `*` stays `*` (the catch-all GALLERY005 skips).
fn join(parent: &str, child: &str) -> String {
    if child.starts_with('/') || (parent.is_empty() && child == "*") {
        child.to_owned()
    } else if parent.is_empty() || parent == "/" {
        format!("/{child}")
    } else {
        format!("{}/{}", parent.trim_end_matches('/'), child)
    }
}

/// The absolute route paths `src` (the text of a `router.tsx`) declares, in source order, deduplicated.
///
/// # Errors
///
/// [`RouterError::UnsupportedPath`] for a route `path` that is not a string literal, and
/// [`RouterError::NoRoutes`] when the source declares none.
pub fn parse_routes(src: &str) -> Result<Vec<String>, RouterError> {
    let toks = tokenize(src);
    let mut frames: Vec<Frame> = Vec::new();
    // Object stack holds (brace depth marker -> frame index or None for a plain brace).
    let mut objs: Vec<Option<usize>> = Vec::new();
    let mut jsx: Vec<usize> = Vec::new();
    let mut i = 0;
    while i < toks.len() {
        let (tok, line) = (&toks[i].0, toks[i].1);
        match tok {
            Tok::Punct('<')
                if toks.get(i + 1).map(|t| &t.0) == Some(&Tok::Ident("Route".into())) =>
            {
                let (next, f, selfclose) = jsx_route(&toks, i, jsx.last().copied());
                frames.push(f);
                if !selfclose {
                    jsx.push(frames.len() - 1);
                }
                i = next;
                continue;
            }
            Tok::Punct('<')
                if toks.get(i + 1).map(|t| &t.0) == Some(&Tok::Punct('/'))
                    && toks.get(i + 2).map(|t| &t.0) == Some(&Tok::Ident("Route".into())) =>
            {
                jsx.pop();
            }
            Tok::Punct('{') => {
                // A `{` right after `=` or `(` or `[` or `,` or `:` may open an object literal;
                // others (blocks, JSX expressions) are tracked but never become routes.
                let parent = objs.iter().rev().flatten().next().copied();
                frames.push(Frame {
                    parent,
                    ..Frame::default()
                });
                objs.push(Some(frames.len() - 1));
            }
            Tok::Punct('}') => {
                objs.pop();
            }
            Tok::Ident(k) | Tok::Str(k, false)
                if toks.get(i + 1).map(|t| &t.0) == Some(&Tok::Punct(':')) =>
            {
                if let Some(&Some(fi)) = objs.last() {
                    if k == "path" {
                        match toks.get(i + 2).map(|t| &t.0) {
                            Some(Tok::Str(s, false)) => frames[fi].path = Some(s.clone()),
                            _ => frames[fi].bad = Some((line, describe(toks.get(i + 2)))),
                        }
                    } else if ROUTE_KEYS.contains(&k.as_str()) {
                        frames[fi].routey = true;
                    }
                }
            }
            _ => {}
        }
        i += 1;
    }

    // Absolute path per frame, then collect routes.
    let mut abs: Vec<Option<String>> = vec![None; frames.len()];
    let mut routes: Vec<String> = Vec::new();
    for idx in 0..frames.len() {
        let f = &frames[idx];
        let is_route = f.jsx || f.routey;
        if is_route && let Some((line, reason)) = &f.bad {
            return Err(RouterError::UnsupportedPath {
                line: *line,
                reason: reason.clone(),
            });
        }
        // Inherit through parents that are not routes (plain objects) by walking up.
        let mut base = String::new();
        let mut p = f.parent;
        while let Some(pi) = p {
            if let Some(a) = &abs[pi] {
                base.clone_from(a);
                break;
            }
            p = frames[pi].parent;
        }
        let here = match (&f.path, is_route) {
            (Some(path), true) => Some(join(&base, path)),
            _ => None,
        };
        if let Some(h) = &here {
            let norm = if h.len() > 1 {
                h.trim_end_matches('/')
            } else {
                h
            };
            if !routes.iter().any(|r| r == norm) {
                routes.push(norm.to_owned());
            }
        }
        abs[idx] = here.or(if base.is_empty() { None } else { Some(base) });
    }
    tracing::debug!(routes = routes.len(), "router routes discovered");
    if routes.is_empty() {
        return Err(RouterError::NoRoutes);
    }
    Ok(routes)
}

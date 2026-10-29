//! Swallowed-error sites: `ERR001`, `ERR002` and `ERR003` (lint catalogue row K01).

// frob:ticket 01M4D956T20WN96P7A3K4B9CKF

use std::collections::BTreeMap;

use gob_languages::{
    Capture, Language, ParseLimits, ParseResult, ParsedTree, QueryError, captures, compiled_query,
    parse,
};
use gob_text::TextRange;

/// Which swallowed-error shape a site is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Kind {
    /// `ERR001`: a catch-all handler with an empty body.
    EmptyHandler,
    /// `ERR002`: the result of a fallible call is bound to `_` and dropped.
    DiscardedResult,
    /// `ERR003`: a catch-all handler with a body that neither rethrows nor logs.
    SilentCatchAll,
}

impl Kind {
    /// The rule id this kind belongs to.
    pub fn rule_id(self) -> &'static str {
        match self {
            Self::EmptyHandler => "ERR001",
            Self::DiscardedResult => "ERR002",
            Self::SilentCatchAll => "ERR003",
        }
    }
}

/// How sure the scan is that the site is a real swallowed error.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Certainty {
    /// The syntax decides it.
    Certain,
    /// The callee's fallibility is not visible in the file, so the site cannot be decided.
    Unknown,
}

/// One swallowed-error site.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The shape found.
    pub kind: Kind,
    /// The handler or statement, as byte offsets in the scanned text.
    pub range: TextRange,
    /// Whether the syntax alone decides it.
    pub certainty: Certainty,
}

/// Why a file could not be scanned.
#[derive(Debug, thiserror::Error)]
pub enum ScanError {
    /// The file did not parse within the limits, or its grammar is not built in.
    #[error("E-ERR-PARSE: {0}")]
    Parse(String),
    /// A built-in query failed to compile.
    #[error("E-ERR-QUERY: {0}")]
    Query(#[from] QueryError),
}

/// Handlers and `let` statements, one query per language.
fn query_for(language: Language) -> Option<&'static str> {
    match language {
        Language::Rust => Some(
            "(match_arm) @handler (if_expression) @handler (let_declaration) @let (function_item) @fn",
        ),
        Language::Python => Some("(except_clause) @handler"),
        Language::TypeScript | Language::CSharp => Some("(catch_clause) @handler"),
        _ => None,
    }
}

/// Every swallowed-error site of `text` parsed as `language`, in source order.
///
/// A language without a detector yields no sites. A tree with syntax errors is still scanned.
///
/// # Errors
///
/// [`ScanError`] when the file does not parse or a query does not compile.
pub fn scan(language: Language, text: &str) -> Result<Vec<Site>, ScanError> {
    let Some(source) = query_for(language) else {
        return Ok(Vec::new());
    };
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let query = compiled_query(language, source)?;
    let caps: Vec<Capture> = captures(query, &tree).collect();
    let mut sites = if language == Language::Rust {
        rust_sites(&tree, &caps)
    } else {
        caps.iter()
            .filter(|c| c.name == "handler")
            .filter_map(|c| handler_site(language, c))
            .collect()
    };
    sites.sort_by_key(|s| (s.range.start(), s.kind));
    sites.dedup();
    tracing::debug!(
        language = language.name(),
        sites = sites.len(),
        "error sites scanned"
    );
    Ok(sites)
}

fn site(kind: Kind, c: &Capture, certainty: Certainty) -> Site {
    Site {
        kind,
        range: c.node_range,
        certainty,
    }
}

/// The text with line and block comments removed and whitespace trimmed.
fn strip_comments(body: &str, hash: bool) -> String {
    let mut out = String::new();
    let mut rest = body;
    while !rest.is_empty() {
        if !hash && rest.starts_with("/*") {
            rest = rest.find("*/").map_or("", |i| &rest[i + 2..]);
        } else if (!hash && rest.starts_with("//")) || (hash && rest.starts_with('#')) {
            rest = rest.find('\n').map_or("", |i| &rest[i..]);
        } else {
            let mut chars = rest.chars();
            if let Some(c) = chars.next() {
                out.push(c);
            }
            rest = chars.as_str();
        }
    }
    out.trim().to_owned()
}

/// Split a handler into its header and body: braces for C-like syntax, the first top-level `:` for Python.
fn split(language: Language, text: &str) -> (&str, &str) {
    if language == Language::Python {
        let mut depth = 0_i32;
        for (i, ch) in text.char_indices() {
            match ch {
                '(' | '[' | '{' => depth += 1,
                ')' | ']' | '}' => depth -= 1,
                ':' if depth == 0 => return (&text[..i], &text[i + 1..]),
                _ => {}
            }
        }
        return (text, "");
    }
    match (text.find('{'), text.rfind('}')) {
        (Some(open), Some(close)) if close > open => (&text[..open], &text[open + 1..close]),
        _ => (text, ""),
    }
}

/// True when `body` rethrows or reports the error.
fn rethrows_or_logs(body: &str) -> bool {
    body.split(|c: char| !c.is_alphanumeric() && c != '_')
        .filter(|t| !t.is_empty())
        .any(|t| {
            let t = t.to_ascii_lowercase();
            t.starts_with("log")
                || matches!(
                    t.as_str(),
                    "raise"
                        | "throw"
                        | "console"
                        | "tracing"
                        | "eprintln"
                        | "eprint"
                        | "trace"
                        | "panic"
                )
        })
}

/// True when the handler header catches everything.
fn catch_all(language: Language, header: &str) -> bool {
    let h = header.trim();
    match language {
        Language::Python => {
            let rest = h
                .strip_prefix("except")
                .unwrap_or(h)
                .trim_start_matches('*')
                .trim();
            let first = rest.split_whitespace().next().unwrap_or("");
            first.is_empty() || matches!(first, "Exception" | "BaseException")
        }
        Language::TypeScript => true,
        Language::CSharp => {
            let rest = h.strip_prefix("catch").unwrap_or(h).trim();
            if rest.contains(" when ") || rest.starts_with("when") {
                return false;
            }
            let inner = rest.trim_start_matches('(').split(')').next().unwrap_or("");
            let ty = inner.split_whitespace().next().unwrap_or("");
            ty.is_empty() || ty == "Exception" || ty == "System.Exception"
        }
        _ => false,
    }
}

/// The site of one Python, TypeScript or C# handler, if it swallows the error.
fn handler_site(language: Language, c: &Capture) -> Option<Site> {
    let (header, body) = split(language, &c.text);
    if !catch_all(language, header) {
        return None;
    }
    let hash = language == Language::Python;
    let body = strip_comments(body, hash);
    let empty = body.is_empty()
        || (hash
            && body
                .lines()
                .all(|l| matches!(l.trim(), "pass" | "..." | "")));
    if empty {
        Some(site(Kind::EmptyHandler, c, Certainty::Certain))
    } else if !rethrows_or_logs(&body) {
        Some(site(Kind::SilentCatchAll, c, Certainty::Certain))
    } else {
        None
    }
}

/// Whether a function name is known to return a `Result` in this file.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Declared {
    Fallible,
    Infallible,
    Mixed,
}

/// Standard-library calls whose result is a `Result` whichever type they are called on.
const KNOWN_FALLIBLE: &[&str] = &[
    "write_all",
    "flush",
    "remove_file",
    "remove_dir",
    "remove_dir_all",
    "create_dir",
    "create_dir_all",
    "rename",
    "read_to_string",
    "send",
    "try_send",
    "write!",
    "writeln!",
];

fn declared_fns(caps: &[Capture]) -> BTreeMap<String, Declared> {
    let mut out: BTreeMap<String, Declared> = BTreeMap::new();
    for c in caps.iter().filter(|c| c.name == "fn") {
        let sig = c.text.split(['{', ';']).next().unwrap_or("");
        let Some(name) = sig.split("fn ").nth(1).and_then(|s| {
            s.split(|ch: char| !ch.is_alphanumeric() && ch != '_')
                .next()
        }) else {
            continue;
        };
        let fallible = sig.split("->").nth(1).is_some_and(|r| r.contains("Result"));
        let now = if fallible {
            Declared::Fallible
        } else {
            Declared::Infallible
        };
        out.entry(name.to_owned())
            .and_modify(|d| {
                if *d != now {
                    *d = Declared::Mixed;
                }
            })
            .or_insert(now);
    }
    out
}

/// The name called by the expression `expr` (ending in a call), `name!` for a macro.
fn callee(expr: &str) -> Option<String> {
    let expr = expr.trim().trim_end_matches(".await").trim();
    let body = expr.strip_suffix(')')?;
    let mut depth = 1_i32;
    let mut open = None;
    for (i, ch) in body.char_indices().rev() {
        match ch {
            ')' => depth += 1,
            '(' => {
                depth -= 1;
                if depth == 0 {
                    open = Some(i);
                    break;
                }
            }
            _ => {}
        }
    }
    let head = body[..open?].trim_end();
    let (head, bang) = head.strip_suffix('!').map_or((head, false), |h| (h, true));
    let name: String = head
        .chars()
        .rev()
        .take_while(|c| c.is_alphanumeric() || *c == '_')
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect();
    (!name.is_empty()).then(|| if bang { format!("{name}!") } else { name })
}

/// True for a Rust handler arm or `if let` whose `Err` body is empty.
fn rust_empty_err(text: &str) -> bool {
    let t = text.trim();
    if let Some(rest) = t.strip_prefix("if let Err(") {
        if t.contains("else") {
            return false;
        }
        let Some(after) = rest.split_once(" = ").map(|(_, r)| r) else {
            return false;
        };
        return match (after.find('{'), after.rfind('}')) {
            (Some(o), Some(c)) if c > o => strip_comments(&after[o + 1..c], false).is_empty(),
            _ => false,
        };
    }
    let Some(rest) = t.strip_prefix("Err(") else {
        return false;
    };
    let Some((_, arm)) = rest.split_once("=>") else {
        return false;
    };
    let arm = arm.trim().trim_end_matches(',').trim();
    let arm = strip_comments(arm, false);
    let inner = arm
        .strip_prefix('{')
        .and_then(|a| a.strip_suffix('}'))
        .map(str::trim);
    inner.is_some_and(str::is_empty) || arm == "()"
}

fn rust_sites(tree: &ParsedTree, caps: &[Capture]) -> Vec<Site> {
    let declared = declared_fns(caps);
    let mut out = Vec::new();
    for c in caps {
        match c.name.as_str() {
            "handler" if rust_empty_err(&c.text) => {
                out.push(site(Kind::EmptyHandler, c, Certainty::Certain));
            }
            "let" => {
                let Some(rest) = c.text.strip_prefix("let _") else {
                    continue;
                };
                if !rest.starts_with([' ', ':', '=']) {
                    continue;
                }
                let Some((_, expr)) = rest.split_once('=') else {
                    continue;
                };
                let expr = expr.trim().trim_end_matches(';').trim();
                let Some(name) = callee(expr) else { continue };
                let certainty = match declared.get(&name) {
                    Some(Declared::Fallible) => Certainty::Certain,
                    Some(Declared::Infallible) => continue,
                    None if KNOWN_FALLIBLE.contains(&name.as_str()) => Certainty::Certain,
                    Some(Declared::Mixed) | None => Certainty::Unknown,
                };
                out.push(site(Kind::DiscardedResult, c, certainty));
            }
            _ => {}
        }
    }
    tracing::trace!(bytes = tree.text.len(), found = out.len(), "rust sites");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn kinds(language: Language, text: &str) -> Vec<(Kind, Certainty)> {
        scan(language, text)
            .expect("scan")
            .into_iter()
            .map(|s| (s.kind, s.certainty))
            .collect()
    }

    const ONE_EMPTY: &[(Kind, Certainty)] = &[(Kind::EmptyHandler, Certainty::Certain)];

    // frob:tests crates/grimble-lints/src/err.rs::scan
    #[test]
    fn each_language_flags_an_empty_catch_all_once() {
        assert_eq!(
            kinds(Language::Python, "try:\n    f()\nexcept:\n    pass\n"),
            ONE_EMPTY
        );
        assert_eq!(
            kinds(
                Language::Python,
                "try:\n    f()\nexcept Exception as e:\n    ...\n"
            ),
            ONE_EMPTY
        );
        assert_eq!(
            kinds(Language::TypeScript, "try { f(); } catch (e) { }\n"),
            ONE_EMPTY
        );
        assert_eq!(
            kinds(
                Language::CSharp,
                "class A { void M() { try { F(); } catch (Exception) { } } }\n"
            ),
            ONE_EMPTY
        );
        assert_eq!(
            kinds(
                Language::CSharp,
                "class A { void M() { try { F(); } catch { } } }\n"
            ),
            ONE_EMPTY
        );
        assert_eq!(
            kinds(
                Language::Rust,
                "fn f(r: Result<u8, E>) { match r { Ok(_) => {}, Err(_) => {} } }\n"
            ),
            ONE_EMPTY
        );
    }

    #[test]
    fn a_silent_catch_all_with_a_body_is_err003() {
        let silent = &[(Kind::SilentCatchAll, Certainty::Certain)];
        assert_eq!(
            kinds(
                Language::Python,
                "try:\n    f()\nexcept Exception:\n    x = 1\n"
            ),
            silent
        );
        assert_eq!(
            kinds(Language::TypeScript, "try { f(); } catch (e) { x = 1; }\n"),
            silent
        );
        assert_eq!(
            kinds(
                Language::CSharp,
                "class A { void M() { try { F(); } catch (Exception e) { x = 1; } } }\n"
            ),
            silent
        );
    }

    #[test]
    fn handlers_that_log_rethrow_or_catch_a_specific_type_are_clean() {
        assert!(
            kinds(
                Language::Python,
                "try:\n    f()\nexcept Exception:\n    logger.exception('x')\n"
            )
            .is_empty()
        );
        assert!(kinds(Language::Python, "try:\n    f()\nexcept:\n    raise\n").is_empty());
        assert!(
            kinds(
                Language::Python,
                "try:\n    f()\nexcept KeyError:\n    pass\n"
            )
            .is_empty()
        );
        assert!(
            kinds(
                Language::TypeScript,
                "try { f(); } catch (e) { console.error(e); throw e; }\n"
            )
            .is_empty()
        );
        assert!(kinds(Language::CSharp, "class A { void M() { try { F(); } catch (IOException) { } catch (Exception e) { throw; } } }\n").is_empty());
        assert!(kinds(Language::Rust, "fn f(r: Result<u8, E>) { match r { Ok(_) => {}, Err(e) => { tracing::warn!(?e); } } }\n").is_empty());
    }

    #[test]
    fn a_discarded_result_is_certain_when_known_and_unknown_otherwise() {
        let known = "fn save() -> Result<(), E> { Ok(()) }\nfn f() { let _ = save(); }\n";
        assert_eq!(
            kinds(Language::Rust, known),
            [(Kind::DiscardedResult, Certainty::Certain)]
        );
        let std = "fn f(tx: Tx) { let _ = tx.send(1); }\n";
        assert_eq!(
            kinds(Language::Rust, std),
            [(Kind::DiscardedResult, Certainty::Certain)]
        );
        let unknown = "fn f() { let _ = mystery(); }\n";
        assert_eq!(
            kinds(Language::Rust, unknown),
            [(Kind::DiscardedResult, Certainty::Unknown)]
        );
        let plain = "fn count() -> u8 { 1 }\nfn f() { let _ = count(); let _ = value; }\n";
        assert!(kinds(Language::Rust, plain).is_empty());
    }

    #[test]
    fn an_unsupported_language_has_no_sites() {
        assert!(kinds(Language::Markdown, "# x\n").is_empty());
    }

    // frob:tests crates/grimble-lints/src/err.rs::Kind.rule_id
    #[test]
    fn rule_ids_follow_kinds() {
        assert_eq!(Kind::EmptyHandler.rule_id(), "ERR001");
        assert_eq!(Kind::DiscardedResult.rule_id(), "ERR002");
        assert_eq!(Kind::SilentCatchAll.rule_id(), "ERR003");
    }
}

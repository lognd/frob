//! Swallowed-error sites: `ERR001`, `ERR002` and `ERR003` (lint catalogue row K01).
//!
//! Discovery runs through the universal model (`gob_symbols::model_of_source_at`): handlers are
//! the `except_clause` / `catch_clause` nodes, a Rust `Err(..) => ..` arm is a `bind(pattern)`,
//! an `if let Err(..)` is an `if_expression`, a `let _ = ..` is a `bind(let)` whose rhs is an
//! `apply`, and the functions that declare fallibility are `unit(function|method)` nodes. The
//! judgements the model cannot express yet stay on the text of the node's span (see
//! docs/design/grimble/lint-classification.md section 3): whether a handler header catches
//! everything, whether a body is empty, rethrows or logs, and whether a signature returns a
//! `Result`.

// frob:ticket 01M4D956T20WN96P7A3K4B9CKF

use std::collections::BTreeMap;

use gob_ir::{Location, NodeId, Operator, Term, Universal};
use gob_languages::Language;
use gob_symbols::model_of_source_at;
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
    /// The universal model of the file could not be built (an adapter bug).
    #[error("E-ERR-MODEL: {0}")]
    Model(String),
}

/// The adapter path whose extension selects the fold for `language`, if a detector exists.
fn model_path(language: Language) -> Option<&'static str> {
    match language {
        Language::Rust => Some("err.rs"),
        Language::Python => Some("err.py"),
        Language::TypeScript => Some("err.ts"),
        Language::CSharp => Some("err.cs"),
        _ => None,
    }
}

/// A node of the universal term with the text its span covers.
#[derive(Clone, Copy)]
struct Span<'t> {
    range: TextRange,
    text: &'t str,
}

/// The span of node `id` in `text`, if it carries a text location that slices `text`.
fn span_of<'t>(term: &Term, id: NodeId, text: &'t str) -> Option<Span<'t>> {
    let Location::Text { range, .. } = term.node(id).location() else {
        return None;
    };
    let slice = text.get(u32::from(range.start()) as usize..u32::from(range.end()) as usize)?;
    Some(Span {
        range: *range,
        text: slice,
    })
}

/// Every swallowed-error site of `text` parsed as `language`, in source order.
///
/// A language without a detector yields no sites. Source with syntax errors is still scanned.
///
/// # Errors
///
/// [`ScanError`] when the universal model cannot be built.
pub fn scan(language: Language, text: &str) -> Result<Vec<Site>, ScanError> {
    let Some(path) = model_path(language) else {
        return Ok(Vec::new());
    };
    let model = model_of_source_at(path, text).map_err(|e| ScanError::Model(e.to_string()))?;
    let term = model.term();
    let mut sites = if language == Language::Rust {
        rust_sites(term, text)
    } else {
        handler_sites(language, term, text)
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

/// The Python, TypeScript or C# handlers of the model that swallow the error.
fn handler_sites(language: Language, term: &Term, text: &str) -> Vec<Site> {
    term.ids()
        .filter(|id| {
            matches!(
                term.node(*id).op(),
                Operator::Adapter(a) if matches!(a.name.as_str(), "except_clause" | "catch_clause")
            )
        })
        .filter_map(|id| span_of(term, id, text))
        .filter_map(|sp| handler_site(language, sp))
        .collect()
}

fn site(kind: Kind, sp: Span<'_>, certainty: Certainty) -> Site {
    Site {
        kind,
        range: sp.range,
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
fn handler_site(language: Language, sp: Span<'_>) -> Option<Site> {
    let (header, body) = split(language, sp.text);
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
        Some(site(Kind::EmptyHandler, sp, Certainty::Certain))
    } else if !rethrows_or_logs(&body) {
        Some(site(Kind::SilentCatchAll, sp, Certainty::Certain))
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

/// The declared fallibility of every function and method unit of the model, by name.
fn declared_fns(term: &Term, text: &str) -> BTreeMap<String, Declared> {
    let mut out: BTreeMap<String, Declared> = BTreeMap::new();
    for id in term.ids() {
        let Operator::Universal(Universal::Unit { kind, .. }) = term.node(id).op() else {
            continue;
        };
        if !matches!(kind.as_str(), "function" | "method") {
            continue;
        }
        let Some(sp) = span_of(term, id, text) else {
            continue;
        };
        let sig = sp.text.split(['{', ';']).next().unwrap_or("");
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

/// The last path segment of a callee head name (`a::b` and `.send` both end in their member).
fn last_segment(head: &str) -> &str {
    head.rsplit(['.', ':']).next().unwrap_or(head)
}

/// The name the right-hand side `id` of a `let` calls: a call or method head from the model, or
/// `name!` for a macro (read from the macro's text, which the model keeps as a `phase`).
fn rhs_callee(term: &Term, id: NodeId, text: &str) -> Option<String> {
    match term.node(id).op() {
        Operator::Universal(Universal::Apply { kind }) if kind != "new" => {
            let head = *term.node(id).children().first()?;
            match term.node(head).op() {
                Operator::Universal(Universal::Ref { name }) => Some(last_segment(name).to_owned()),
                _ => None,
            }
        }
        Operator::Universal(Universal::Phase { kind }) if kind == "macro" => {
            callee(span_of(term, id, text)?.text)
        }
        Operator::Adapter(a) if a.name == "await_expression" => {
            rhs_callee(term, *term.node(id).children().first()?, text)
        }
        _ => None,
    }
}

/// The `ERR002` site of the `bind(let)` node `id`, if it discards a call's result.
fn discarded_let(
    term: &Term,
    id: NodeId,
    text: &str,
    declared: &BTreeMap<String, Declared>,
) -> Option<Site> {
    let sp = span_of(term, id, text)?;
    let rest = sp.text.strip_prefix("let _")?;
    if !rest.starts_with([' ', ':', '=']) {
        return None;
    }
    let rhs_group = *term.node(id).children().get(1)?;
    let rhs = *term.node(rhs_group).children().last()?;
    let name = rhs_callee(term, rhs, text)?;
    let certainty = match declared.get(&name) {
        Some(Declared::Fallible) => Certainty::Certain,
        Some(Declared::Infallible) => return None,
        None if KNOWN_FALLIBLE.contains(&name.as_str()) => Certainty::Certain,
        Some(Declared::Mixed) | None => Certainty::Unknown,
    };
    Some(site(Kind::DiscardedResult, sp, certainty))
}

/// The Rust sites of the model: empty `Err` arms and `if let Err`, and discarded results.
fn rust_sites(term: &Term, text: &str) -> Vec<Site> {
    let declared = declared_fns(term, text);
    let mut out = Vec::new();
    for id in term.ids() {
        match term.node(id).op() {
            Operator::Universal(Universal::Bind { kind, .. }) if kind == "pattern" => {
                if let Some(sp) = span_of(term, id, text).filter(|sp| rust_empty_err(sp.text)) {
                    out.push(site(Kind::EmptyHandler, sp, Certainty::Certain));
                }
            }
            Operator::Adapter(a) if a.name == "if_expression" => {
                if let Some(sp) = span_of(term, id, text).filter(|sp| rust_empty_err(sp.text)) {
                    out.push(site(Kind::EmptyHandler, sp, Certainty::Certain));
                }
            }
            Operator::Universal(Universal::Bind { kind, .. }) if kind == "let" => {
                out.extend(discarded_let(term, id, text, &declared));
            }
            _ => {}
        }
    }
    tracing::trace!(bytes = text.len(), found = out.len(), "rust sites");
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
    }

    #[test]
    fn a_discarded_result_is_certain_when_known_and_unknown_otherwise_part_2() {
        let std = "fn f(tx: Tx) { let _ = tx.send(1); }\n";
        assert_eq!(
            kinds(Language::Rust, std),
            [(Kind::DiscardedResult, Certainty::Certain)]
        );
    }

    #[test]
    fn a_discarded_result_is_certain_when_known_and_unknown_otherwise_part_3() {
        let unknown = "fn f() { let _ = mystery(); }\n";
        assert_eq!(
            kinds(Language::Rust, unknown),
            [(Kind::DiscardedResult, Certainty::Unknown)]
        );
    }

    #[test]
    fn a_discarded_result_is_certain_when_known_and_unknown_otherwise_part_4() {
        let plain = "fn count() -> u8 { 1 }\nfn f() { let _ = count(); let _ = value; }\n";
        assert!(kinds(Language::Rust, plain).is_empty());
    }

    // frob:tests crates/grimble-lints/src/err.rs::scan
    #[test]
    fn a_discarded_method_and_macro_call_are_certain() {
        let certain = [(Kind::DiscardedResult, Certainty::Certain)];
        let method = "struct S;\nimpl S { fn save(&self) -> Result<(), E> { Ok(()) } }\nfn f(s: S) { let _ = s.save(); }\n";
        assert_eq!(kinds(Language::Rust, method), certain);
        let mac = "fn f(w: W) { let _ = writeln!(w, \"x\"); }\n";
        assert_eq!(kinds(Language::Rust, mac), certain);
    }

    // frob:tests crates/grimble-lints/src/err.rs::scan
    #[test]
    fn a_discarded_awaited_call_is_unknown() {
        let unknown = [(Kind::DiscardedResult, Certainty::Unknown)];
        let awaited = "async fn f() { let _ = mystery().await; }\n";
        assert_eq!(kinds(Language::Rust, awaited), unknown);
    }

    // frob:tests crates/grimble-lints/src/err.rs::scan
    #[test]
    fn a_qualified_call_is_certain_and_a_propagated_one_is_not_flagged() {
        let qualified = "fn f() { let _ = std::fs::remove_file(p); }\n";
        assert_eq!(
            kinds(Language::Rust, qualified),
            [(Kind::DiscardedResult, Certainty::Certain)]
        );
        let propagated = "fn f() -> Result<(), E> { let _ = mystery()?; Ok(()) }\n";
        assert!(kinds(Language::Rust, propagated).is_empty());
    }

    // frob:tests crates/grimble-lints/src/err.rs::scan
    #[test]
    fn an_empty_if_let_err_is_flagged_and_one_with_an_else_is_not() {
        assert_eq!(
            kinds(Language::Rust, "fn f(r: R) { if let Err(_) = r { } }\n"),
            ONE_EMPTY
        );
        assert!(
            kinds(
                Language::Rust,
                "fn f(r: R) { if let Err(_) = r { } else { g(); } }\n"
            )
            .is_empty()
        );
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

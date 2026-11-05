//! A snippet taken `as roles`: lifted to language-neutral roles (grl-spec.md 7.3).
//!
//! The snippet text cannot be matched against a target in another language, so only its shape
//! is read: the root word names a role (`if`, `match`, `switch` a branch; `for`, `while`,
//! `loop` a loop) and the body is either empty or exactly one call. The lift is a plain
//! condition, `x is branch` plus, for a call body, `some k: call where k directly inside x`.
//! Any other shape (an `else`, several statements, a nested block, a body that is not a call)
//! is refused with [`LowerError::Unsupported`], the stand-in for GRL007.

// frob:ticket 01M5ETB7Y10SZTEWWKBR3AHZ1T
// frob:ticket 01M4XJ9HA1C3KVG78XF5YAFTXP
use gob_text::Span;

use super::LowerError;
use super::convert::{Cond, Opd};
use crate::grl::Snippet;
use crate::plan::CmpOp;
use crate::plan::Quant;

/// What the body of a roles snippet requires of the matched node.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Body {
    /// No statements: the root role alone.
    Empty,
    /// Exactly one call statement.
    OneCall,
}

fn refuse<T>(what: &'static str, span: Span) -> Result<T, LowerError> {
    Err(LowerError::Unsupported { what, span })
}

/// The role word a snippet's first token names.
fn root_role(text: &str) -> Option<&'static str> {
    let word: String = text
        .trim_start()
        .chars()
        .take_while(|c| c.is_ascii_alphanumeric() || *c == '_')
        .collect();
    match word.as_str() {
        "if" | "match" | "switch" => Some("branch"),
        "for" | "while" | "loop" => Some("loop"),
        _ => None,
    }
}

/// The text of the snippet's block: between the outer braces, or after the first `:`.
fn block(text: &str) -> Option<&str> {
    if let (Some(open), Some(close)) = (text.find('{'), text.rfind('}')) {
        let inner = text.get(open + 1..close)?;
        // A nested block is a statement this lift does not read.
        return (!inner.contains(['{', '}'])).then_some(inner);
    }
    text.find(':').map(|i| &text[i + 1..])
}

/// Whether one statement is a call: a callee made of names, `$` metavariables, `.` and `::`.
fn is_call(stmt: &str) -> bool {
    let Some(open) = stmt.find('(') else {
        return false;
    };
    let callee = &stmt[..open];
    stmt.ends_with(')')
        && !callee.is_empty()
        && callee
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '$' | '.' | ':'))
}

/// The body shape of a snippet's block, or `None` for any shape this lift refuses.
fn body_of(text: &str) -> Option<Body> {
    let block = block(text)?;
    let stmts: Vec<&str> = block
        .split([';', '\n'])
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect();
    match stmts.as_slice() {
        [] => Some(Body::Empty),
        [one] if is_call(one) => Some(Body::OneCall),
        _ => None,
    }
}

/// The callee's last name segment when it is a plain word (no metavariable), e.g. `unwrap`.
fn callee_name(stmt: &str) -> Option<&str> {
    let callee = &stmt[..stmt.find('(')?];
    let last = callee.rsplit(['.', ':']).next()?;
    (!last.is_empty() && !last.contains('$')).then_some(last)
}

/// Lift a snippet that is one call: `x is call`, plus the callee's last name when it is plain.
fn call_cond(var: &str, text: &str, span: Span) -> Result<Cond, LowerError> {
    let stmt = text.trim();
    if !is_call(stmt) {
        return refuse(
            "a roles snippet whose root is not a branch, loop or call",
            span,
        );
    }
    tracing::debug!(var, "lowering a call roles snippet");
    let root = Cond::Is {
        subject: Opd::Var(var.to_owned()),
        test: "call".to_owned(),
    };
    Ok(match callee_name(stmt) {
        Some(name) => Cond::And(vec![
            root,
            Cond::Cmp {
                lhs: Opd::Field(var.to_owned(), "callee.name".to_owned()),
                op: CmpOp::Eq,
                rhs: Opd::Str(name.to_owned()),
            },
        ]),
        None => root,
    })
}

/// The role a metavariable plays in a roles snippet, by where it is written.
///
/// A name in the head before the block (`if $C {`) is the branch `condition`; in a call, a
/// name before the `(` is the `callee` and one inside the parentheses an `arg`.
fn role_at(text: &str, at: usize) -> &'static str {
    let head_end = if root_role(text).is_some() {
        text.find(['{', ':']).unwrap_or(text.len())
    } else {
        0
    };
    if at < head_end {
        return "condition";
    }
    let rest = &text[head_end..at];
    if rest.rfind('(').is_some_and(|o| !rest[o..].contains(')')) {
        "arg"
    } else {
        "callee"
    }
}

/// The named metavariables of a roles snippet with the role each fills, in text order.
///
/// `$_`, sequences (`$$$XS`) and a name written twice (an equality test, not a new node) bind nothing new.
/// GRL variables are lowercase, so `$C` binds the variable `c`.
pub(super) fn role_bindings(snippet: &Snippet) -> Vec<(String, &'static str)> {
    let text = snippet.text.as_str();
    let mut out: Vec<(String, &'static str)> = Vec::new();
    let mut i = 0;
    while let Some(off) = text[i..].find('$') {
        let at = i + off;
        let rest = text[at..].trim_start_matches('$');
        let dollars = text.len() - at - rest.len();
        i = at + dollars;
        if dollars == 2 || dollars == 3 {
            // `$$` is a literal dollar; `$$$XS` is a sequence of nodes, not one node.
            continue;
        }
        let name: String = rest
            .chars()
            .take_while(|c| c.is_ascii_alphanumeric() || *c == '_')
            .collect();
        if name.is_empty()
            || name == "_"
            || out.iter().any(|(n, _)| *n == name.to_ascii_lowercase())
        {
            continue;
        }
        let role = role_at(text, at);
        tracing::debug!(name, role, "binding a snippet metavariable as a role node");
        out.push((name.to_ascii_lowercase(), role));
    }
    out
}

/// The condition that `var` is the `role` node of `base`.
pub(super) fn role_cond(var: &str, base: &str, role: &'static str) -> Cond {
    Cond::Role {
        var: var.to_owned(),
        base: base.to_owned(),
        role: role.to_owned(),
    }
}

/// Lift `var is <snippet> as roles` to a condition; `fresh` numbers the call variable.
///
/// # Errors
///
/// [`LowerError::Unsupported`] when the snippet's root is not a branch or loop, or its body is
/// anything but empty or one call.
pub(super) fn roles_cond(
    var: &str,
    snippet: &Snippet,
    fresh: &mut u32,
    span: Span,
) -> Result<Cond, LowerError> {
    let text = snippet.text.as_str();
    let Some(role) = root_role(text) else {
        return call_cond(var, text, span);
    };
    if text
        .split(|c: char| !c.is_ascii_alphanumeric() && c != '_')
        .any(|w| w == "else" || w == "elif")
    {
        return refuse("a roles snippet with an else branch", span);
    }
    let Some(body) = body_of(text) else {
        return refuse("a roles snippet body that is not exactly one call", span);
    };
    tracing::debug!(var, role, ?body, "lowering a roles snippet");
    let root = Cond::Is {
        subject: Opd::Var(var.to_owned()),
        test: role.to_owned(),
    };
    Ok(match body {
        Body::Empty => root,
        Body::OneCall => {
            let call = format!("_{fresh}");
            *fresh += 1;
            Cond::And(vec![
                root,
                Cond::Quant {
                    quant: Quant::Some,
                    var: call.clone(),
                    kind: "call".to_owned(),
                    cond: Box::new(Cond::Inside {
                        sub: call,
                        sup: var.to_owned(),
                        direct: true,
                    }),
                },
            ])
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-plan/src/lower/roles.rs::body_of
    #[test]
    fn body_shapes() {
        assert_eq!(body_of("if $C { $F($$$A) }"), Some(Body::OneCall));
        assert_eq!(body_of("if $C: $F($$$A)"), Some(Body::OneCall));
        assert_eq!(body_of("if $C { $F(); }"), Some(Body::OneCall));
        assert_eq!(body_of("if $C { }"), Some(Body::Empty));
        assert_eq!(body_of("if $C { a(); b() }"), None);
        assert_eq!(body_of("if $C { x = 1 }"), None);
        assert_eq!(body_of("if $C { if $D { f() } }"), None);
        assert_eq!(body_of("loop"), None);
    }

    // frob:tests crates/gob-plan/src/lower/roles.rs::role_bindings
    #[test]
    fn metavariables_take_roles_by_position() {
        let snip = |t: &str| Snippet {
            lang: None,
            ticks: 1,
            text: t.to_owned(),
            body: Span::new(
                gob_text::FileInterner::new().intern("t.grl"),
                gob_text::TextRange::default(),
            ),
            metavars: Vec::new(),
            dollars: Vec::new(),
        };
        assert_eq!(
            role_bindings(&snip("if $C { $F($$$A, $C) }")),
            vec![("c".to_owned(), "condition"), ("f".to_owned(), "callee")]
        );
        assert_eq!(
            role_bindings(&snip("$X.f($_, $Y)")),
            vec![("x".to_owned(), "callee"), ("y".to_owned(), "arg")]
        );
    }

    // frob:tests crates/gob-plan/src/lower/roles.rs::root_role
    #[test]
    fn root_words() {
        assert_eq!(root_role("  if $C {}"), Some("branch"));
        assert_eq!(root_role("while $C {}"), Some("loop"));
        assert_eq!(root_role("iffy $C {}"), None);
        assert_eq!(root_role("$X.f()"), None);
    }
}

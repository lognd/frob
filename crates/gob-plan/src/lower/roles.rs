//! A snippet taken `as roles`: lifted to language-neutral roles (grl-spec.md 7.3).
//!
//! The snippet text cannot be matched against a target in another language, so only its shape
//! is read: the root word names a role (`if`, `match`, `switch` a branch; `for`, `while`,
//! `loop` a loop) and the body is either empty or exactly one call. The lift is a plain
//! condition, `x is branch` plus, for a call body, `some k: call where k directly inside x`.
//! Any other shape (an `else`, several statements, a nested block, a body that is not a call)
//! is refused with [`LowerError::Unsupported`], the stand-in for GRL007.

// frob:ticket 01M5ETB7Y10SZTEWWKBR3AHZ1T
use gob_text::Span;

use super::LowerError;
use super::convert::{Cond, Opd};
use crate::grl::Snippet;
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
        return refuse("a roles snippet whose root is not a branch or loop", span);
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

    // frob:tests crates/gob-plan/src/lower/roles.rs::root_role
    #[test]
    fn root_words() {
        assert_eq!(root_role("  if $C {}"), Some("branch"));
        assert_eq!(root_role("while $C {}"), Some("loop"));
        assert_eq!(root_role("iffy $C {}"), None);
        assert_eq!(root_role("$X.f()"), None);
    }
}

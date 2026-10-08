//! Value facts: the colors, lengths and `var()` references of one declaration value, each with
//! its own span. Judgment-free; rules decide what they mean.

// frob:ticket 01M43ARY91XZ35DN9SCHRHS033

use crunk_values::{Color, Length};

use crate::lex::{Kind, Tok, inner_tokens, tokenize, unescape};
use crate::model::{LocatedColor, LocatedLength, LocatedVarRef, Span};

/// The facts of one value.
#[derive(Debug, Default, Clone, PartialEq)]
pub struct ValueFacts {
    /// Colors found.
    pub colors: Vec<LocatedColor>,
    /// Lengths found.
    pub lengths: Vec<LocatedLength>,
    /// `var()` references found.
    pub var_refs: Vec<LocatedVarRef>,
}

/// The first identifier among the top-level arguments of the `var(` function token `tok`.
fn var_name(src: &str, tok: &Tok) -> Option<String> {
    inner_tokens(src, tok)
        .iter()
        .find(|t| t.kind == Kind::Ident)
        .map(|t| unescape(t.text(src)))
}

/// Every `var(--name)` nested in the arguments of `tok`, at any function depth.
fn nested_var_refs(src: &str, tok: &Tok, out: &mut Vec<LocatedVarRef>) {
    for arg in inner_tokens(src, tok) {
        if arg.kind != Kind::Function {
            continue;
        }
        if is_var(src, &arg) {
            if let Some(name) = var_name(src, &arg) {
                out.push(LocatedVarRef {
                    name,
                    span: (arg.start, arg.end),
                });
            }
        } else {
            nested_var_refs(src, &arg, out);
        }
    }
}

fn is_var(src: &str, tok: &Tok) -> bool {
    tok.kind == Kind::Function
        && src
            .get(tok.start..tok.start + 4)
            .is_some_and(|p| p.eq_ignore_ascii_case("var("))
}

/// Extract the colors, lengths and `var()` references of the value `src`, spans shifted by
/// `base` so they address the owning source file.
///
/// A `var()` at the top level is a reference and nothing else; a color function is a color; any
/// other function contributes only its nested `var()` references (its literals are the host
/// function's business).
pub fn value_facts(src: &str, base: usize, root_font_size: f64) -> ValueFacts {
    let mut facts = ValueFacts::default();
    let shift = |t: &Tok| -> Span { (t.start + base, t.end + base) };
    for tok in tokenize(src) {
        if is_var(src, &tok) {
            if let Some(name) = var_name(src, &tok) {
                facts.var_refs.push(LocatedVarRef {
                    name,
                    span: shift(&tok),
                });
            }
            continue;
        }
        if matches!(tok.kind, Kind::Hash | Kind::Function | Kind::Ident)
            && let Ok(color) = Color::parse(tok.text(src))
        {
            facts.colors.push(LocatedColor {
                color,
                span: shift(&tok),
            });
            continue;
        }
        if tok.kind == Kind::Function {
            let mut nested = Vec::new();
            nested_var_refs(src, &tok, &mut nested);
            facts.var_refs.extend(nested.into_iter().map(|mut r| {
                r.span = (r.span.0 + base, r.span.1 + base);
                r
            }));
            continue;
        }
        if matches!(tok.kind, Kind::Dimension | Kind::Number | Kind::Percentage)
            && let Ok(length) = Length::parse(tok.text(src), root_font_size)
        {
            facts.lengths.push(LocatedLength {
                length,
                span: shift(&tok),
            });
        }
    }
    facts
}

/// A custom property whose value is exactly three bare integers 0-255 reads as an opaque color
/// (the `--x-rgb: 230 232 239` channel-triplet convention).
pub fn channel_triplet(src: &str, value_span: Span) -> Option<LocatedColor> {
    let significant: Vec<Tok> = tokenize(src)
        .into_iter()
        .filter(|t| !t.is_trivia())
        .collect();
    if significant.len() != 3 {
        return None;
    }
    let mut channels = [0.0f64; 3];
    for (slot, tok) in channels.iter_mut().zip(&significant) {
        if tok.kind != Kind::Number {
            return None;
        }
        let text = tok.text(src);
        if text.contains(['.', 'e', 'E']) {
            return None;
        }
        let n: i64 = text.parse().ok()?;
        if !(0..=255).contains(&n) {
            return None;
        }
        #[allow(clippy::cast_precision_loss, reason = "n is 0..=255")]
        {
            *slot = n as f64 / 255.0;
        }
    }
    Some(LocatedColor {
        color: Color {
            r: channels[0],
            g: channels[1],
            b: channels[2],
            a: 1.0,
        },
        span: value_span,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-ingest/src/facts.rs::value_facts
    #[test]
    fn colors_lengths_and_vars_with_spans() {
        let src = "1px solid var(--line, #ccc) #fff";
        let f = value_facts(src, 10, 16.0);
        assert_eq!(f.var_refs.len(), 1);
        assert_eq!(f.var_refs[0].name, "--line");
        assert_eq!(f.var_refs[0].span, (10 + 10, 10 + 27));
        assert_eq!(
            f.colors.len(),
            1,
            "the #ccc inside var() is not a color of its own"
        );
        assert_eq!(f.colors[0].span, (10 + 28, 10 + 32));
        assert_eq!(f.lengths.len(), 1);
        assert_eq!(f.lengths[0].length.px, Some(1.0));
    }

    // frob:tests crates/crunk-ingest/src/facts.rs::value_facts
    #[test]
    fn nested_function_vars_and_slash_split_lengths() {
        let f = value_facts("calc(var(--a) * 2) 1px/2px", 0, 16.0);
        assert_eq!(f.var_refs.len(), 1);
        assert_eq!(f.lengths.len(), 2);
    }

    // frob:tests crates/crunk-ingest/src/facts.rs::channel_triplet
    #[test]
    fn channel_triplet_needs_three_bare_bytes() {
        assert!(channel_triplet("230 232 239", (0, 11)).is_some());
        assert!(channel_triplet("230 232", (0, 7)).is_none());
        assert!(channel_triplet("256 0 0", (0, 7)).is_none());
        assert!(channel_triplet("1.5 0 0", (0, 7)).is_none());
    }
}

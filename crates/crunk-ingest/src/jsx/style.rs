//! `style={{...}}` inline-style objects to [`Declaration`]s (the Python `jsx._style`).
//!
//! The TS adapter lowers each statically named entry of a `style` object to a `style.declaration`
//! (name in CSS spelling, entry located). Whether the value is a literal, and where exactly it
//! sits, is read from the entry's source text: a string, a template without substitutions or a
//! bare number is a declaration; anything computed is exempt, as `var()` values are in CSS.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

use crunk_values::{Length, LengthKind};
use gob_ir::style;

use super::cx::Cx;
use crate::facts::value_facts;
use crate::model::{Declaration, LocatedLength};

/// Properties React leaves unitless when the value is a bare number; every other numeric style
/// value is `px` (React's own list, which is a superset of the Python crunk's seven).
const UNITLESS: [&str; 22] = [
    "animation-iteration-count",
    "aspect-ratio",
    "column-count",
    "flex",
    "flex-grow",
    "flex-shrink",
    "flex-order",
    "font-weight",
    "grid-area",
    "grid-column",
    "grid-row",
    "line-height",
    "opacity",
    "order",
    "orphans",
    "scale",
    "tab-size",
    "widows",
    "z-index",
    "zoom",
    "fill-opacity",
    "stroke-opacity",
];

/// What the value of an entry is, with its byte offset in the source.
#[derive(Debug, PartialEq)]
enum Value<'a> {
    /// A bare number (`44`, `-4`, `0.5`).
    Number(&'a str),
    /// The inner text of a string or a template literal without substitutions.
    Text(&'a str),
}

/// The `(offset in entry, value)` of an object entry `key: value`, `None` for a shorthand entry
/// or a value that is computed.
fn entry_value(entry: &str) -> Option<(usize, Value<'_>)> {
    let key_end = match entry.chars().next()? {
        q @ ('"' | '\'') => 1 + entry[1..].find(q)? + 1,
        _ => entry
            .find(|c: char| !(c.is_alphanumeric() || matches!(c, '_' | '$' | '-')))
            .unwrap_or(entry.len()),
    };
    let after_key = entry[key_end..].trim_start();
    let colon = entry.len() - after_key.len();
    let value_text = after_key.strip_prefix(':')?;
    let lead = value_text.len() - value_text.trim_start().len();
    let start = colon + 1 + lead;
    let value = entry[start..].trim_end();
    if is_number(value) {
        return Some((start, Value::Number(value)));
    }
    if let Some(inner) = quoted_inner(value) {
        return Some((start + 1, Value::Text(inner)));
    }
    None
}

/// The text between the quotes when `value` is exactly one string or substitution-free template.
fn quoted_inner(value: &str) -> Option<&str> {
    let quote = value
        .chars()
        .next()
        .filter(|c| matches!(c, '"' | '\'' | '`'))?;
    if value.len() < 2 || !value.ends_with(quote) {
        return None;
    }
    let inner = &value[1..value.len() - 1];
    let mut chars = inner.char_indices();
    while let Some((i, c)) = chars.next() {
        match c {
            '\\' => {
                chars.next();
            }
            c if c == quote => return None,
            '$' if quote == '`' && inner[i + 1..].starts_with('{') => return None,
            _ => {}
        }
    }
    Some(inner)
}

/// True for a decimal number literal with an optional sign (`_` separators allowed).
fn is_number(value: &str) -> bool {
    let body = value.strip_prefix(['+', '-']).unwrap_or(value);
    let digits_ok = body
        .bytes()
        .all(|b| b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'e' | b'E' | b'+' | b'-'));
    digits_ok
        && body
            .bytes()
            .next()
            .is_some_and(|b| b.is_ascii_digit() || b == b'.')
        && parse_number(value).is_some()
}

fn parse_number(value: &str) -> Option<f64> {
    value
        .replace('_', "")
        .parse::<f64>()
        .ok()
        .filter(|n| n.is_finite())
}

/// Every literal entry of every inline style object of the file, in source order.
pub(super) fn declarations(cx: &Cx<'_>, root_font_size: f64) -> Vec<Declaration> {
    let mut found: Vec<(usize, Declaration)> = Vec::new();
    let mut skipped = 0usize;
    for d in style::declarations(cx.model) {
        let Some((start, end)) = cx.range(d.node) else {
            continue;
        };
        let Some((offset, value)) = entry_value(&cx.src[start..end]) else {
            skipped += 1;
            tracing::debug!(property = %d.property, "jsx style: computed value skipped");
            continue;
        };
        let at = start + offset;
        let declaration = match value {
            Value::Number(text) => number(&d.property, text, at, cx),
            Value::Text("") => continue,
            Value::Text(text) => {
                let facts = value_facts(text, at, root_font_size);
                Declaration {
                    prop: d.property.clone(),
                    value: text.to_owned(),
                    line: cx.lines.line_of(at),
                    span: (at, at + text.len()),
                    waivers: Vec::new(),
                    colors: facts.colors,
                    lengths: facts.lengths,
                    var_refs: facts.var_refs,
                }
            }
        };
        found.push((at, declaration));
    }
    found.sort_by_key(|(at, _)| *at);
    tracing::debug!(
        declarations = found.len(),
        skipped,
        "jsx style: inline styles read"
    );
    found.into_iter().map(|(_, d)| d).collect()
}

/// A numeric style value: `px` unless the property is unitless.
fn number(property: &str, text: &str, at: usize, cx: &Cx<'_>) -> Declaration {
    let span = (at, at + text.len());
    let lengths = match parse_number(text) {
        Some(px) if !UNITLESS.contains(&property) => vec![LocatedLength {
            length: Length {
                raw: format!("{text}px"),
                px: Some(px),
                kind: LengthKind::Px,
            },
            span,
        }],
        _ => Vec::new(),
    };
    Declaration {
        prop: property.to_owned(),
        value: text.to_owned(),
        line: cx.lines.line_of(at),
        span,
        waivers: Vec::new(),
        colors: Vec::new(),
        lengths,
        var_refs: Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-ingest/src/jsx/style.rs::declarations
    #[test]
    fn entry_values_are_literals_or_nothing() {
        assert_eq!(entry_value("width: 44"), Some((7, Value::Number("44"))));
        assert_eq!(
            entry_value("margin: '4px 13px'"),
            Some((9, Value::Text("4px 13px")))
        );
        assert_eq!(
            entry_value("'z-index': -1"),
            Some((11, Value::Number("-1")))
        );
        assert_eq!(entry_value("a: `x y`"), Some((4, Value::Text("x y"))));
        assert_eq!(entry_value("label: `${p}-x`"), None);
        assert_eq!(entry_value("color: pick()"), None);
        assert_eq!(entry_value("color: \"red\" as const"), None);
        assert_eq!(entry_value("color"), None);
        assert_eq!(entry_value("gap: 'a' + b"), None);
    }
}

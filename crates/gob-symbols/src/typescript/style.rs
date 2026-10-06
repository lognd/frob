//! Pure text helpers for lowering inline `style={{..}}` objects: property names and CSS value tokens.
//!
//! The tokens follow the component-value classes of `gob_ir::style` (`ident`, `number`, `dimension`,
//! `string`, `color`, `function`, and `var(--x)` as a reference).

// frob:ticket 01M47QKSBYX7YFQHV3VVGKB025

/// Properties React leaves unitless when the value is a number.
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

/// One component value of a style declaration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Token {
    /// A plain token of the given class.
    Lit(&'static str, String),
    /// A `var(--x)` reference to the custom property `--x`.
    Var(String),
}

/// The CSS property for a style-object key: `backgroundColor` is `background-color`, `WebkitX` is `-webkit-x`.
pub(super) fn css_property(key: &str) -> String {
    if key.starts_with("--") {
        return key.to_owned();
    }
    let mut out = String::with_capacity(key.len() + 4);
    if key.starts_with("ms") && key[2..].starts_with(|c: char| c.is_ascii_uppercase()) {
        out.push('-');
    }
    for c in key.chars() {
        if c.is_ascii_uppercase() {
            out.push('-');
            out.push(c.to_ascii_lowercase());
        } else {
            out.push(c);
        }
    }
    out
}

/// The raw CSS text of a numeric style value: React appends `px` unless the property is unitless or the value is 0.
pub(super) fn numeric_raw(property: &str, number: &str) -> String {
    let zero = number.parse::<f64>().is_ok_and(|v| v == 0.0);
    if zero || UNITLESS.contains(&property) || property.starts_with("--") {
        number.to_owned()
    } else {
        format!("{number}px")
    }
}

/// The component values of a raw declaration value, split at top-level whitespace and commas.
pub(super) fn tokens(raw: &str) -> Vec<Token> {
    let mut out = Vec::new();
    for word in split_top(raw) {
        out.extend(token(&word));
    }
    out
}

fn split_top(raw: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut cur = String::new();
    let mut depth = 0usize;
    let mut quote: Option<char> = None;
    for c in raw.chars() {
        match (quote, c) {
            (Some(q), _) => {
                cur.push(c);
                if c == q {
                    quote = None;
                }
            }
            (None, '"' | '\'') => {
                quote = Some(c);
                cur.push(c);
            }
            (None, '(') => {
                depth += 1;
                cur.push(c);
            }
            (None, ')') => {
                depth = depth.saturating_sub(1);
                cur.push(c);
            }
            (None, c) if depth == 0 && (c.is_whitespace() || c == ',') => {
                if !cur.is_empty() {
                    words.push(std::mem::take(&mut cur));
                }
            }
            (None, _) => cur.push(c),
        }
    }
    if !cur.is_empty() {
        words.push(cur);
    }
    words
}

fn token(word: &str) -> Vec<Token> {
    if word.starts_with('"') || word.starts_with('\'') {
        return vec![Token::Lit("string", word.to_owned())];
    }
    if word.starts_with('#') {
        return vec![Token::Lit("color", word.to_owned())];
    }
    if let Some(open) = word.find('(').filter(|_| word.ends_with(')')) {
        if &word[..open] == "var" {
            let inner = &word[open + 1..word.len() - 1];
            let name = inner.split(',').next().unwrap_or_default().trim();
            return vec![Token::Var(name.to_owned())];
        }
        let mut out = vec![Token::Lit("function", word.to_owned())];
        out.extend(vars_in(&word[open + 1..]));
        return out;
    }
    let digits = word
        .trim_start_matches(['-', '+'])
        .chars()
        .take_while(|c| c.is_ascii_digit() || *c == '.')
        .count();
    if digits > 0 {
        let rest = &word.trim_start_matches(['-', '+'])[digits..];
        let class = if rest.is_empty() {
            "number"
        } else {
            "dimension"
        };
        return vec![Token::Lit(class, word.to_owned())];
    }
    vec![Token::Lit("ident", word.to_owned())]
}

/// The `var(--x)` references nested in the text of a function value.
fn vars_in(text: &str) -> Vec<Token> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(i) = rest.find("var(") {
        let after = &rest[i + 4..];
        let end = after.find([',', ')']).unwrap_or(after.len());
        out.push(Token::Var(after[..end].trim().to_owned()));
        rest = &after[end..];
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-symbols/src/typescript/style.rs::css_property
    #[test]
    fn keys_become_css_properties() {
        assert_eq!(css_property("backgroundColor"), "background-color");
        assert_eq!(css_property("WebkitMask"), "-webkit-mask");
        assert_eq!(css_property("msTransform"), "-ms-transform");
        assert_eq!(css_property("--gap"), "--gap");
        assert_eq!(css_property("color"), "color");
    }

    // frob:tests crates/gob-symbols/src/typescript/style.rs::numeric_raw
    #[test]
    fn numbers_get_px_unless_unitless() {
        assert_eq!(numeric_raw("margin-top", "16"), "16px");
        assert_eq!(numeric_raw("opacity", "0.5"), "0.5");
        assert_eq!(numeric_raw("margin", "0"), "0");
    }

    // frob:tests crates/gob-symbols/src/typescript/style.rs::tokens
    #[test]
    fn values_split_into_component_tokens() {
        assert_eq!(
            tokens("1px solid var(--line, #ccc)"),
            [
                Token::Lit("dimension", "1px".into()),
                Token::Lit("ident", "solid".into()),
                Token::Var("--line".into()),
            ]
        );
        assert_eq!(
            tokens("calc(var(--a) * 2)"),
            [
                Token::Lit("function", "calc(var(--a) * 2)".into()),
                Token::Var("--a".into())
            ]
        );
        assert_eq!(tokens("#fff"), [Token::Lit("color", "#fff".into())]);
    }
}

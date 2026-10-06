//! Component-value tokens of a raw CSS declaration value, shared by the CSS adapter and the TypeScript
//! inline-style lowering.
//!
//! The tokens follow the component-value classes of `gob_ir::style` (`ident`, `number`, `dimension`,
//! `string`, `color`, `function`, and `var(--x)` as a reference).

// frob:ticket 01M47QKSBYX7YFQHV3VVGKB025
// frob:ticket 01M43ARY26XF7A4MSRAZ8V73JM

/// One component value of a style declaration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Token {
    /// A plain token of the given class.
    Lit(&'static str, String),
    /// A `var(--x)` reference to the custom property `--x`.
    Var(String),
}

/// The component values of a raw declaration value, split at top-level whitespace and commas.
pub(crate) fn tokens(raw: &str) -> Vec<Token> {
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

    // frob:tests crates/gob-symbols/src/css/tokens.rs::tokens
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

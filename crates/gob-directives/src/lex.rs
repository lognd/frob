//! Tokenizer for the argument tail of one directive line.

use gob_text::{TextRange, TextSize};

use crate::args::{ArgList, Keyed, Token};

/// A malformed tail: what is wrong and where.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct LexError {
    pub(crate) range: TextRange,
    pub(crate) message: String,
}

/// Byte range `[start, end)` shifted by `base`.
pub(crate) fn range_at(base: usize, start: usize, end: usize) -> TextRange {
    let clamp = |n: usize| TextSize::new(u32::try_from(base + n).unwrap_or(u32::MAX));
    TextRange::new(clamp(start), clamp(end))
}

/// True for lowercase words (`frob`, `my-key`); dashes only when `dash`.
pub(crate) fn is_word(s: &str, dash: bool) -> bool {
    let mut chars = s.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || (dash && c == '-'))
}

/// Foreign-tool pragma openers that end a directive's argument list.
const HASH_PRAGMAS: &[&str] = &[
    "noqa", "type:", "pragma", "pylint:", "fmt:", "isort:", "ruff:", "nosec", "mypy:", "pyright:",
    "flake8:", "yapf:", "nolint", "pytype:",
];

/// Foreign-tool pragma openers after `//`.
const SLASH_PRAGMAS: &[&str] = &[
    "eslint-",
    "@ts-",
    "prettier-ignore",
    "noinspection",
    "nolint",
    "NOLINT",
    "tslint:",
    "jshint",
    "istanbul",
    "biome-ignore",
    "rustfmt",
    "lint:",
];

/// True when `rest` starts a trailing foreign pragma such as `# noqa: E501`.
fn is_foreign_pragma(rest: &str) -> bool {
    let (marker, openers) = if let Some(r) = rest.strip_prefix('#') {
        (r, HASH_PRAGMAS)
    } else if let Some(r) = rest.strip_prefix("//") {
        (r, SLASH_PRAGMAS)
    } else {
        return false;
    };
    let body = marker.trim_start();
    openers.iter().any(|o| body.starts_with(o))
}

/// Reads a double-quoted value starting at the opening quote at `open`.
///
/// Returns the unescaped value and the index just past the closing quote.
fn quoted(text: &str, open: usize, base: usize) -> Result<(String, usize), LexError> {
    let mut value = String::new();
    let mut chars = text[open + 1..].char_indices();
    while let Some((i, c)) = chars.next() {
        match c {
            '"' => return Ok((value, open + 1 + i + 1)),
            '\\' => match chars.next() {
                Some((_, e @ ('"' | '\\'))) => value.push(e),
                Some((_, other)) => {
                    value.push('\\');
                    value.push(other);
                }
                None => break,
            },
            c => value.push(c),
        }
    }
    Err(LexError {
        range: range_at(base, open, open + 1),
        message: "unterminated quoted value".to_owned(),
    })
}

/// Split `text` (the tail after the verb, starting at file offset `base`) into arguments.
pub(crate) fn tokenize(text: &str, base: usize) -> Result<ArgList, LexError> {
    let mut out = ArgList::default();
    let mut i = 0;
    while i < text.len() {
        let rest = &text[i..];
        let Some(c) = rest.chars().next() else { break };
        if c.is_whitespace() {
            i += c.len_utf8();
            continue;
        }
        if is_foreign_pragma(rest) {
            tracing::debug!(at = base + i, "trailing foreign pragma ends the arguments");
            break;
        }
        let start = i;
        let stop = rest
            .find(|ch: char| ch.is_whitespace() || ch == '=' || ch == '"')
            .map_or(text.len(), |p| start + p);
        let at = text[stop..].chars().next();
        match at {
            Some('"') if stop == start => {
                let (value, end) = quoted(text, start, base)?;
                check_boundary(text, end, base)?;
                out.positional.push(Token {
                    value,
                    range: range_at(base, start, end),
                    quoted: true,
                });
                i = end;
            }
            Some('"') => {
                return Err(LexError {
                    range: range_at(base, stop, stop + 1),
                    message: "unexpected quote inside a bare argument".to_owned(),
                });
            }
            Some('=') => {
                let key = &text[start..stop];
                if !is_word(key, true) {
                    return Err(LexError {
                        range: range_at(base, start, stop + 1),
                        message: format!("invalid argument key `{key}`"),
                    });
                }
                let vstart = stop + 1;
                let (value, end, was_quoted) = if text[vstart..].starts_with('"') {
                    let (v, end) = quoted(text, vstart, base)?;
                    (v, end, true)
                } else {
                    let end = text[vstart..]
                        .find(char::is_whitespace)
                        .map_or(text.len(), |p| vstart + p);
                    let v = &text[vstart..end];
                    if let Some(q) = v.find('"') {
                        return Err(LexError {
                            range: range_at(base, vstart + q, vstart + q + 1),
                            message: "unexpected quote inside a bare argument".to_owned(),
                        });
                    }
                    (v.to_owned(), end, false)
                };
                if value.is_empty() && !was_quoted {
                    return Err(LexError {
                        range: range_at(base, start, stop + 1),
                        message: format!("`{key}=` has no value"),
                    });
                }
                check_boundary(text, end, base)?;
                out.keyed.push(Keyed {
                    key: key.to_owned(),
                    key_range: range_at(base, start, stop),
                    value: Token {
                        value,
                        range: range_at(base, vstart, end),
                        quoted: was_quoted,
                    },
                });
                i = end;
            }
            _ => {
                out.positional.push(Token {
                    value: text[start..stop].to_owned(),
                    range: range_at(base, start, stop),
                    quoted: false,
                });
                i = stop;
            }
        }
    }
    Ok(out)
}

/// A closing quote must be followed by whitespace or the end.
fn check_boundary(text: &str, end: usize, base: usize) -> Result<(), LexError> {
    match text[end..].chars().next() {
        Some(c) if !c.is_whitespace() => Err(LexError {
            range: range_at(base, end, end + c.len_utf8()),
            message: "text directly after a closing quote".to_owned(),
        }),
        _ => Ok(()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn vals(a: &ArgList) -> Vec<&str> {
        a.positional.iter().map(|t| t.value.as_str()).collect()
    }

    #[test]
    fn positionals_and_keys() {
        let a = tokenize("COV006 because=\"a b\" ticket=X \"q r\"", 100).unwrap();
        assert_eq!(vals(&a), ["COV006", "q r"]);
        assert_eq!(a.get("because").unwrap().value, "a b");
        assert_eq!(a.get("ticket").unwrap().value, "X");
        assert_eq!(u32::from(a.positional[0].range.start()), 100);
    }

    #[test]
    fn escapes() {
        let a = tokenize(r#"k="a \"b\" \\ c""#, 0).unwrap();
        assert_eq!(a.get("k").unwrap().value, r#"a "b" \ c"#);
    }

    #[test]
    fn trailing_foreign_pragmas_end_the_arguments() {
        for tail in [
            "p::t kind=\"unit\"  # noqa: E501",
            "p::t kind=\"unit\" //eslint-disable-line",
            "p::t kind=\"unit\" # type: ignore[arg-type]",
        ] {
            let a = tokenize(tail, 0).unwrap();
            assert_eq!(vals(&a), ["p::t"], "{tail}");
            assert_eq!(a.get("kind").unwrap().value, "unit", "{tail}");
        }
        let q = tokenize("k=\"a # noqa b\"", 0).unwrap();
        assert_eq!(q.get("k").unwrap().value, "a # noqa b");
        assert_eq!(
            vals(&tokenize("a # note b", 0).unwrap()),
            ["a", "#", "note", "b"]
        );
    }

    #[test]
    fn errors_have_positions() {
        let e = tokenize("ok k=\"open", 10).unwrap_err();
        assert_eq!(u32::from(e.range.start()), 15);
        assert!(tokenize("a\"b", 0).is_err());
        assert!(tokenize("k=", 0).is_err());
        assert!(tokenize("=v", 0).is_err());
        assert!(tokenize("K=v", 0).is_err());
        assert!(tokenize("k=\"v\"x", 0).is_err());
    }
}

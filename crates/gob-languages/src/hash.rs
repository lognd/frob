//! String-aware discovery of `#` comments for TOML, YAML and fallback Python.

/// Lexer state carried across lines by [`hash_comments`].
#[derive(Clone, Copy, PartialEq, Eq)]
enum Str {
    /// Outside any string.
    None,
    /// Inside a quoted string (`"` or `'`); `multi` strings span lines.
    Quoted { quote: u8, multi: bool },
    /// Inside a YAML block scalar whose content is indented deeper than `parent`.
    Block { parent: usize },
}

/// True when `rest` (text after a block-scalar indicator) is only header modifiers and a comment.
fn block_header_tail(rest: &str) -> bool {
    let t = rest.trim_start_matches(|c: char| c == '+' || c == '-' || c.is_ascii_digit());
    let t = t.trim_start();
    t.is_empty() || t.starts_with('#')
}

// frob:ticket 01M43HGBQ9YS0Z8YPKQ41MBK6Q
/// Byte offsets of the `#` that starts each comment of a TOML, YAML or fallback-Python file.
///
/// A comment runs from the returned offset to the end of its line. Strings are lexed so a quoted `#` is text.
///
/// TOML: basic, literal, multi-line basic and multi-line literal strings (escapes honoured).
/// YAML: quoted scalars (also multi-line), block scalars (`|`, `>`), and `#` only after whitespace.
pub fn hash_comment_starts(text: &str, yaml: bool) -> Vec<usize> {
    let mut out = Vec::new();
    let mut offset = 0;
    let mut state = Str::None;
    for line in text.split_inclusive('\n') {
        let b = line.as_bytes();
        let indent = line.len() - line.trim_start().len();
        if let Str::Block { parent } = state {
            if line.trim().is_empty() || indent > parent {
                offset += line.len();
                continue;
            }
            state = Str::None;
        }
        let mut i = 0;
        while i < b.len() {
            match state {
                Str::Block { .. } => {
                    // Rest of the header line: only modifiers and an optional comment.
                    if let Some(h) = line[i..].find('#') {
                        let at = i + h;
                        out.push(offset + at);
                    }
                    break;
                }
                Str::None => match b[i] {
                    q @ (b'"' | b'\'') => {
                        let value_start = !yaml
                            || i == 0
                            || matches!(b[i - 1], b' ' | b'\t' | b'[' | b'{' | b',' | b':');
                        if value_start {
                            let triple = !yaml && b[i..].starts_with(&[q, q, q]);
                            state = Str::Quoted {
                                quote: q,
                                multi: triple,
                            };
                            i += if triple { 3 } else { 1 };
                            continue;
                        }
                    }
                    b'|' | b'>'
                        if yaml
                            && (i == 0 || matches!(b[i - 1], b' ' | b'\t'))
                            && block_header_tail(&line[i + 1..]) =>
                    {
                        state = Str::Block { parent: indent };
                    }
                    b'#' if !yaml || i == 0 || matches!(b[i - 1], b' ' | b'\t') => {
                        out.push(offset + i);
                        break;
                    }
                    _ => {}
                },
                Str::Quoted { quote, multi } => {
                    let escapes = quote == b'"';
                    if b[i] == b'\\' && escapes {
                        i += 2;
                        continue;
                    }
                    if b[i] == quote {
                        if multi {
                            if b[i..].starts_with(&[quote, quote, quote]) {
                                // A run of 3..=5 quotes closes; extras are content.
                                let run = b[i..].iter().take_while(|&&c| c == quote).count();
                                state = Str::None;
                                i += run;
                                continue;
                            }
                        } else if yaml && quote == b'\'' && b.get(i + 1) == Some(&quote) {
                            // YAML `''` is an escaped quote, not a close.
                            i += 2;
                            continue;
                        } else {
                            state = Str::None;
                        }
                    }
                }
            }
            i += 1;
        }
        // Single-line TOML strings end at the newline; YAML quoted scalars may continue.
        if !yaml && matches!(state, Str::Quoted { multi: false, .. }) {
            state = Str::None;
        }
        offset += line.len();
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Comment texts (from `#` to end of line) found in `src`.
    fn texts(src: &str, yaml: bool) -> Vec<String> {
        hash_comment_starts(src, yaml)
            .into_iter()
            .map(|at| {
                src[at..]
                    .lines()
                    .next()
                    .unwrap_or_default()
                    .trim_start_matches('#')
                    .trim()
                    .to_owned()
            })
            .collect()
    }
    #[test]
    // frob:tests crates/gob-languages/src/hash.rs::hash_comment_starts
    fn toml_strings_hide_hash_in_every_form() {
        let cases: &[(&str, &[&str])] = &[
            ("a = \"# no\" # yes\n", &["yes"]),
            ("a = '# no' # yes\n", &["yes"]),
            ("a = \"x \\\" # no\" # yes\n", &["yes"]),
            (
                "a = \"\"\"\n# frob:doc no\n  # frob:doc no\n\"\"\" # yes\n# after\n",
                &["yes", "after"],
            ),
            ("a = '''\n# frob:doc no\n''' # yes\n", &["yes"]),
            ("a = \"\"\"\nesc \\\"\"\" # no\n\"\"\"\n# real\n", &["real"]),
            ("a = \"\"\"\nx\"\"\"\"\n# real\n", &["real"]),
            ("a = '''\nx''''\n# real\n", &["real"]),
            ("a = \"\"\"\nline \\\n# no\n\"\"\"\n# real\n", &["real"]),
            ("a = ''\n# real\n", &["real"]),
            ("a = \"\"\n# real\n", &["real"]),
            ("a = \"unterminated\n# real\n", &["real"]),
        ];
        for (src, want) in cases {
            assert_eq!(texts(src, false), *want, "{src:?}");
        }
    }

    #[test]
    // frob:tests crates/gob-languages/src/hash.rs::hash_comment_starts
    fn yaml_strings_and_block_scalars_hide_hash() {
        let cases: &[(&str, &[&str])] = &[
            ("a: \"# no\" # yes\n", &["yes"]),
            ("a: 'it''s # no' # yes\n", &["yes"]),
            ("a: x#no # yes\n", &["yes"]),
            ("a: |\n  # no\n  # no\n# real\n", &["real"]),
            ("a: >-  # yes\n  # no\nb: 1\n", &["yes"]),
            ("a: \"two\n  # no\n  lines\" # yes\n", &["yes"]),
            ("- it's fine # yes\n", &["yes"]),
        ];
        for (src, want) in cases {
            assert_eq!(texts(src, true), *want, "{src:?}");
        }
    }
}

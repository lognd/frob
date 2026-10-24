//! `PATH001`: string literals that are absolute host paths.

// frob:ticket 01M41RV691XZQ5W2EW821PHK3V

use tree_sitter::Node;

use gob_languages::Language;

/// The string-literal node kinds of a language.
fn literal_kinds(language: Language) -> &'static [&'static str] {
    match language {
        Language::Rust => &["string_literal", "raw_string_literal"],
        Language::Python => &["string"],
        Language::TypeScript => &["string", "template_string"],
        Language::CSharp => &[
            "string_literal",
            "verbatim_string_literal",
            "raw_string_literal",
            "interpolated_string_expression",
        ],
        _ => &[],
    }
}

/// True when `node` is a string literal of `language` that is not a docstring.
pub(super) fn is_string_literal(language: Language, node: Node<'_>) -> bool {
    literal_kinds(language).contains(&node.kind())
        && !(language == Language::Python
            && node
                .parent()
                .is_some_and(|p| p.kind() == "expression_statement"))
}

/// The value of a string literal's source text: quotes and prefix removed, escapes decoded
/// (`\\` becomes `\`, `\n` a newline so a line break is never mistaken for a separator; raw
/// and verbatim literals are taken as written).
pub(super) fn decode(source: &str) -> Option<String> {
    let open = source.find(['"', '\'', '`'])?;
    let quote = source[open..].chars().next()?;
    let (prefix, rest) = source.split_at(open);
    let raw = prefix.contains(['r', 'R', '@']);
    let triple: String = std::iter::repeat_n(quote, 3).collect();
    let (skip, close) = if rest.starts_with(&triple) && rest.len() >= 6 {
        (3, rest.rfind(&triple).filter(|i| *i >= 3)?)
    } else {
        (1, rest.rfind(quote).filter(|i| *i >= 1)?)
    };
    let body = &rest[skip..close];
    if raw {
        return Some(body.to_owned());
    }
    let mut out = String::with_capacity(body.len());
    let mut chars = body.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match chars.next() {
            Some(e @ ('\\' | '"' | '\'' | '/')) => out.push(e),
            Some('n') => out.push('\n'),
            Some('t') => out.push('\t'),
            Some('r') => out.push('\r'),
            Some('0') => out.push('\0'),
            Some(other) => {
                out.push('\\');
                out.push(other);
            }
            None => out.push('\\'),
        }
    }
    Some(out)
}

/// Directories whose absolute form is a host path.
const HOST_PREFIXES: &[&str] = &["/home/", "/Users/", "/root/", "/tmp/"];

/// True when the decoded literal `value` is an absolute host path not exempted by `allowed`.
pub(super) fn is_absolute_host_path(value: &str, allowed: &[String]) -> bool {
    if value == "/" || value.contains("://") || value.starts_with("#!") {
        return false;
    }
    if allowed.iter().any(|a| a == value) {
        return false;
    }
    if HOST_PREFIXES.iter().any(|p| {
        (value.starts_with(p) && value.len() > p.len()) || value == p.trim_end_matches('/')
    }) {
        return true;
    }
    let mut chars = value.chars();
    match (chars.next(), chars.next(), chars.next()) {
        (Some(d), Some(':'), Some('\\' | '/')) if d.is_ascii_alphabetic() => true,
        (Some('\\'), Some('\\'), Some(c)) => c != '\\',
        (Some('~'), Some(n), _) if n != '/' => {
            let name: &str = value[1..].split('/').next().unwrap_or("");
            value[1..].contains('/')
                && name
                    .chars()
                    .all(|c| c.is_alphanumeric() || "_-.".contains(c))
        }
        _ => false,
    }
}

//! Static reader of Tailwind v4 CSS-first config: `@theme` blocks and their `--name` variables.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use super::text::{line_of, mask_comments};

/// Theme variable namespaces, longest prefix first, mapped to their v3-style names.
const NAMESPACES: [(&str, &str); 15] = [
    ("--color-", "colors"),
    ("--spacing-", "spacing"),
    ("--radius-", "borderRadius"),
    ("--breakpoint-", "screens"),
    ("--font-", "fontFamily"),
    ("--text-", "fontSize"),
    ("--shadow-", "boxShadow"),
    ("--inset-shadow-", "insetShadow"),
    ("--drop-shadow-", "dropShadow"),
    ("--blur-", "blur"),
    ("--ease-", "transitionTimingFunction"),
    ("--animate-", "animation"),
    ("--z-", "zIndex"),
    ("--tracking-", "letterSpacing"),
    ("--leading-", "lineHeight"),
];

/// One `--name: value;` declared in an `@theme` block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Var {
    pub name: String,
    pub value: String,
    pub line: u32,
}

/// Whether `src` carries v4 signals: `@import "tailwindcss"` or an `@theme` block.
pub(crate) fn looks_like_v4(src: &str) -> bool {
    let masked = mask_comments(src, false);
    masked.contains("@theme")
        || masked.contains("@import \"tailwindcss")
        || masked.contains("@import 'tailwindcss")
        || masked.contains("@import url(\"tailwindcss")
}

/// Every variable declared in an `@theme` block of `src`, in source order.
pub(crate) fn theme_vars(src: &str) -> Vec<Var> {
    let masked = mask_comments(src, false);
    let b = masked.as_bytes();
    let mut out = Vec::new();
    let mut from = 0;
    while let Some(p) = masked[from..].find("@theme") {
        let at = from + p;
        let Some(open) = masked[at..].find('{').map(|o| at + o) else {
            break;
        };
        let mut depth = 0usize;
        let mut end = b.len();
        for (i, &c) in b.iter().enumerate().skip(open) {
            match c {
                b'{' => depth += 1,
                b'}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = i;
                        break;
                    }
                }
                _ => {}
            }
        }
        let mut start = open + 1;
        for decl in masked[open + 1..end].split(';') {
            let lead = decl.len() - decl.trim_start().len();
            if let Some((name, value)) = decl.trim().split_once(':')
                && name.trim().starts_with("--")
            {
                out.push(Var {
                    name: name.trim().to_owned(),
                    value: value.trim().to_owned(),
                    line: line_of(&masked, start + lead),
                });
            }
            start += decl.len() + 1;
        }
        from = end.max(at + 1);
    }
    out
}

/// Split `--color-primary` into (`colors`, `primary`); `("", "--name")` when no namespace
/// matches. `--spacing` alone is the base multiplier: (`spacing`, `DEFAULT`).
pub(crate) fn split_name(name: &str) -> (&'static str, String) {
    if name == "--spacing" {
        return ("spacing", "DEFAULT".to_owned());
    }
    for (prefix, ns) in NAMESPACES {
        if let Some(rest) = name.strip_prefix(prefix) {
            return (ns, rest.to_owned());
        }
    }
    ("", name.to_owned())
}

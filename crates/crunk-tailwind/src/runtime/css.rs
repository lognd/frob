//! Compiled Tailwind CSS to per-candidate declarations, through the shared CSS adapter.
//!
//! A declaration belongs to the candidate named by the leading class of its outermost style
//! rule's selector (`.p-\[13px\]` is candidate `p-[13px]`; escapes are resolved, never matched
//! by text). The at-rules it sits in are kept outermost first.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::collections::{BTreeMap, HashMap};

use gob_ir::{Model, NodeId, style};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};

use super::model::{AtRuleWrap, ClassDeclaration};

/// Why compiled CSS could not be read.
#[derive(Debug, thiserror::Error)]
#[error("cannot fold the compiled CSS: {0}")]
pub struct CssError(String);

/// Declarations of `css` grouped by the candidate class their rule names.
///
/// # Errors
///
/// [`CssError`] when the CSS adapter builds an ill-formed term (an adapter bug); malformed CSS
/// never fails, it just yields fewer declarations.
pub fn parse_declarations_by_candidate(
    css: &str,
) -> Result<BTreeMap<String, Vec<ClassDeclaration>>, CssError> {
    let entry = FileEntry {
        path: "tailwind.css".to_owned(),
        size: css.len() as u64,
        digest: Digest::of(css.as_bytes()),
        language: LanguageHint::Other("css".to_owned()),
    };
    let folded = fold_file(&entry, css).map_err(|e| CssError(e.to_string()))?;
    let model = Model::new(folded.term, folded.scopes);
    let rules: HashMap<NodeId, style::StyleRule> = style::style_rules(&model)
        .into_iter()
        .map(|r| (r.node, r))
        .collect();
    let ats: HashMap<NodeId, style::AtRule> = style::at_rules(&model)
        .into_iter()
        .map(|a| (a.node, a))
        .collect();
    let mut out: BTreeMap<String, Vec<ClassDeclaration>> = BTreeMap::new();
    for decl in style::declarations(&model) {
        // `ancestors` is nearest first.
        let chain = model.term().ancestors(decl.node);
        let Some(nearest) = chain.iter().find_map(|a| rules.get(a)) else {
            continue;
        };
        let Some(outermost) = chain.iter().rev().find_map(|a| rules.get(a)) else {
            continue;
        };
        let Some(candidate) = leading_class(&outermost.selector) else {
            continue;
        };
        let at_rules = chain
            .iter()
            .rev()
            .filter_map(|a| ats.get(a))
            .map(|a| AtRuleWrap {
                name: a.name.clone(),
                params: a.prelude.trim().to_owned(),
            })
            .collect();
        out.entry(candidate).or_default().push(ClassDeclaration {
            property: decl.property.to_ascii_lowercase(),
            value: decl.raw.trim().to_owned(),
            selector: nearest.selector.trim().to_owned(),
            at_rules,
        });
    }
    tracing::debug!(candidates = out.len(), "compiled css parsed");
    Ok(out)
}

/// The class name a selector starts with (`.a\:b:hover` is `a:b`), or `None`.
pub fn leading_class(selector: &str) -> Option<String> {
    let rest = selector.trim_start().strip_prefix('.')?;
    let mut name = String::new();
    let mut chars = rest.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '\\' {
            push_escape(&mut chars, &mut name);
        } else if c.is_alphanumeric() || c == '-' || c == '_' || !c.is_ascii() {
            name.push(c);
        } else {
            break;
        }
    }
    (!name.is_empty()).then_some(name)
}

/// Resolve one CSS escape after a backslash: up to six hex digits (and one trailing space), else
/// the next character literally.
fn push_escape(chars: &mut std::iter::Peekable<std::str::Chars<'_>>, name: &mut String) {
    let mut hex = String::new();
    while hex.len() < 6 && chars.peek().is_some_and(char::is_ascii_hexdigit) {
        hex.extend(chars.next());
    }
    if hex.is_empty() {
        name.extend(chars.next());
        return;
    }
    if chars.peek().is_some_and(|c| c.is_whitespace()) {
        chars.next();
    }
    let code = u32::from_str_radix(&hex, 16).unwrap_or(0xFFFD);
    name.push(
        char::from_u32(code)
            .filter(|&c| c != '\0')
            .unwrap_or('\u{FFFD}'),
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-tailwind/src/runtime/css.rs::leading_class
    #[test]
    fn leading_class_resolves_escapes_and_stops_at_selector_syntax() {
        assert_eq!(leading_class(r".p-\[13px\]").as_deref(), Some("p-[13px]"));
        assert_eq!(
            leading_class(r".md\:hover\:p-4:hover").as_deref(),
            Some("md:hover:p-4")
        );
        assert_eq!(leading_class(r".\31 0").as_deref(), Some("10"));
        assert_eq!(leading_class(".a > .b").as_deref(), Some("a"));
        assert_eq!(leading_class("div.a"), None);
        assert_eq!(leading_class("&:hover"), None);
    }

    // frob:tests crates/crunk-tailwind/src/runtime/css.rs::parse_declarations_by_candidate
    #[test]
    fn declarations_group_by_candidate_with_their_at_rule_stack() {
        let css = ".flex { display: flex; }\n@media (min-width: 768px) {\n  .md\\:p-4 { padding: 1rem; }\n}\n@layer utilities { @media (hover: hover) { .a:hover { color: red; } } }\n";
        let got = parse_declarations_by_candidate(css).unwrap();
        assert_eq!(got["flex"][0].property, "display");
        assert_eq!(got["flex"][0].value, "flex");
        assert!(got["flex"][0].at_rules.is_empty());
        let md = &got["md:p-4"][0];
        assert_eq!(md.at_rules.len(), 1);
        assert_eq!(md.at_rules[0].name, "media");
        assert_eq!(md.at_rules[0].params, "(min-width: 768px)");
        let hover = &got["a"][0];
        let names: Vec<&str> = hover.at_rules.iter().map(|a| a.name.as_str()).collect();
        assert_eq!(names, ["layer", "media"]);
        assert_eq!(hover.selector, ".a:hover");
    }
}

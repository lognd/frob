//! Test titles of a JavaScript or TypeScript file: the `describe`/`it`/`test` ids a runner reports.

use tree_sitter::Node;

use crate::{Language, ParseLimits, ParseResult, parse};

// frob:ticket 01M4FGZ4KY03QKSWXACP7APFVH
/// The separator a vitest/jest runner puts between a describe chain and a test title.
pub const TITLE_SEP: &str = " > ";

/// Suite wrappers whose title opens a describe level.
const SUITES: [&str; 2] = ["describe", "suite"];
/// Test wrappers whose title ends an id.
const TESTS: [&str; 2] = ["it", "test"];
/// Modifier properties that keep the wrapper's meaning (`it.only`, `describe.skip`).
const MODIFIERS: [&str; 5] = ["only", "skip", "todo", "concurrent", "sequential"];

/// Every test id of a TS/JS source, as `describe > ... > title`; empty for other languages.
#[must_use]
pub fn js_test_ids(language: Language, text: &str) -> Vec<String> {
    if !matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    ) {
        return Vec::new();
    }
    let ParseResult::Parsed(tree) = parse(language, text, &ParseLimits::default()) else {
        tracing::debug!(language = language.name(), "test titles: no tree");
        return Vec::new();
    };
    let mut out = Vec::new();
    walk(tree.root(), text, &mut Vec::new(), &mut out);
    tracing::debug!(
        language = language.name(),
        found = out.len(),
        "test titles scanned"
    );
    out
}

fn walk(node: Node<'_>, text: &str, chain: &mut Vec<String>, out: &mut Vec<String>) {
    let mut pushed = false;
    if node.kind() == "call_expression"
        && let Some((is_suite, title)) = wrapper(node, text)
    {
        if is_suite {
            chain.push(title);
            pushed = true;
        } else {
            let mut parts = chain.clone();
            parts.push(title);
            out.push(parts.join(TITLE_SEP));
        }
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        walk(child, text, chain, out);
    }
    if pushed {
        chain.pop();
    }
}

/// `(is_suite, title)` when the call is `describe("t", ..)`/`it.only("t", ..)`/`test("t", ..)`.
fn wrapper(call: Node<'_>, text: &str) -> Option<(bool, String)> {
    let func = call.child_by_field_name("function")?;
    let name = match func.kind() {
        "identifier" => node_text(func, text),
        "member_expression" => {
            let prop = node_text(func.child_by_field_name("property")?, text);
            let obj = func.child_by_field_name("object")?;
            if obj.kind() != "identifier" || !MODIFIERS.contains(&prop) {
                return None;
            }
            node_text(obj, text)
        }
        _ => return None,
    };
    let is_suite = SUITES.contains(&name);
    if !is_suite && !TESTS.contains(&name) {
        return None;
    }
    let args = call.child_by_field_name("arguments")?;
    let first = args.named_child(0)?;
    let title = match first.kind() {
        "string" => unquote(node_text(first, text)),
        "template_string" if !node_text(first, text).contains("${") => {
            unquote(node_text(first, text))
        }
        _ => return None,
    };
    Some((is_suite, title))
}

fn node_text<'a>(node: Node<'_>, text: &'a str) -> &'a str {
    text.get(node.start_byte()..node.end_byte()).unwrap_or("")
}

fn unquote(raw: &str) -> String {
    raw.get(1..raw.len().saturating_sub(1))
        .unwrap_or("")
        .to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests testnames.rs::js_test_ids
    #[test]
    fn describe_chain_joins_with_separator() {
        let src = "describe('gate', () => { describe(\"inner\", () => { it('runs', () => {}); }); it.only(`solo`, () => {}); });\ntest('top', () => {});\n";
        assert_eq!(
            js_test_ids(Language::TypeScript, src),
            vec!["gate > inner > runs", "gate > solo", "top"]
        );
    }

    // frob:tests testnames.rs::js_test_ids
    #[test]
    fn other_languages_and_dynamic_titles_yield_nothing() {
        assert!(js_test_ids(Language::Python, "def test_a(): pass").is_empty());
        assert!(
            js_test_ids(Language::JavaScript, "it(name, () => {}); it(`a${b}`, f);").is_empty()
        );
    }
}

//! PROC002: no print macro in verb code outside the configured presenter crates.
//!
//! A repository-local policy (`[check] output_presenters`): human output goes
//! through logging, and only the listed presenter crates may write to
//! stdout/stderr directly. Macro invocations are found in the syntax tree
//! (`macro_invocation` nodes), never by a text search, so strings, comments
//! and look-alike identifiers cannot fire it. Test code (`#[cfg(test)]`,
//! `#[test]`), `src/bin/`, `build.rs` and integration tests are not verb code.

// frob:ticket 01M5XMN90BZAYHQSK214270F1C
use std::path::{Path, PathBuf};

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tracing::debug;

/// Macros that write straight to stdout or stderr.
const PRINT_MACROS: [&str; 4] = ["println", "eprintln", "print", "eprint"];

/// One forbidden macro invocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Proc002Hit {
    /// File containing the invocation.
    pub path: PathBuf,
    /// 1-based line.
    pub line: usize,
    /// 1-based column of the invocation.
    pub col: usize,
    /// Byte offset of the invocation start.
    pub start: usize,
    /// Byte offset one past the end of the invocation.
    pub end: usize,
    /// The macro name, without the `!`.
    pub name: String,
}

/// Whether `rel` (repo-relative, forward slashes) is verb code the rule checks.
///
/// That is `crates/<crate>/src/**/*.rs` of a crate not in `presenters`, minus
/// `src/main.rs` and `src/bin/`. An empty `presenters` means no policy.
pub fn is_checked_path(rel: &str, presenters: &[String]) -> bool {
    if presenters.is_empty() {
        return false;
    }
    let parts: Vec<&str> = rel.split('/').collect();
    let ["crates", krate, "src", rest @ ..] = parts.as_slice() else {
        return false;
    };
    let is_bin = rest.first() == Some(&"bin") || rest == ["main.rs"];
    let checked = Path::new(rel).extension().is_some_and(|x| x == "rs")
        && !is_bin
        && !presenters.iter().any(|p| p == krate);
    debug!(rel, checked, "out-of-presenter path classified");
    checked
}

/// Whether an attribute marks the next item as test-only code.
fn is_test_attr(text: &str) -> bool {
    let t: String = text.split_whitespace().collect();
    t == "#[test]" || t.starts_with("#[cfg(test)") || t.contains("cfg(test)]")
}

/// Collect print-macro invocations under `node`, skipping test-only items.
fn walk(node: tree_sitter::Node<'_>, text: &str, path: &Path, out: &mut Vec<Proc002Hit>) {
    let mut skip_next = false;
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        match child.kind() {
            "attribute_item" => {
                if is_test_attr(&text[child.byte_range()]) {
                    skip_next = true;
                }
                continue;
            }
            "line_comment" | "block_comment" => continue,
            _ => {}
        }
        if std::mem::take(&mut skip_next) {
            continue;
        }
        if child.kind() == "macro_invocation" {
            let name = child
                .child_by_field_name("macro")
                .map(|m| &text[m.byte_range()])
                .and_then(|m| m.rsplit("::").next())
                .unwrap_or("");
            if PRINT_MACROS.contains(&name) {
                let pos = child.start_position();
                out.push(Proc002Hit {
                    path: path.to_path_buf(),
                    line: pos.row + 1,
                    col: pos.column + 1,
                    start: child.start_byte(),
                    end: child.end_byte(),
                    name: name.to_owned(),
                });
            }
        }
        walk(child, text, path, out);
    }
}

/// Scan one file's text; only print-macro invocations in non-test code match.
pub fn scan_text(path: &Path, text: &str) -> Vec<Proc002Hit> {
    let ParseResult::Parsed(tree) = parse(Language::Rust, text, &ParseLimits::default()) else {
        debug!(path = ?path, "proc002 skipped: file did not parse");
        return Vec::new();
    };
    let mut hits = Vec::new();
    walk(tree.root(), text, path, &mut hits);
    hits
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-check/src/proc002.rs::scan_text
    #[test]
    fn flags_macro_invocations_not_text() {
        let src = "// println!(\"a\")\nfn f() {\n    let s = \"println!\";\n    println!(\"x\");\n    std::eprintln!(\"y\");\n    my_println(1);\n    format!(\"z\");\n}\n";
        let hits = scan_text(Path::new("x.rs"), src);
        let seen: Vec<_> = hits.iter().map(|h| (h.line, h.name.as_str())).collect();
        assert_eq!(seen, vec![(4, "println"), (5, "eprintln")]);
        assert_eq!(hits[0].col, 5);
    }

    // frob:tests crates/gob-check/src/proc002.rs::scan_text
    #[test]
    fn test_code_is_exempt() {
        let src = "#[cfg(test)]\nmod tests {\n    fn t() { println!(\"a\"); }\n}\n#[test]\nfn u() { print!(\"b\"); }\nfn real() { eprint!(\"c\"); }\n";
        let hits = scan_text(Path::new("x.rs"), src);
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].line, 7);
    }

    // frob:tests crates/gob-check/src/proc002.rs::is_checked_path
    #[test]
    fn only_non_presenter_crate_sources_are_checked() {
        let p = ["frob-present".to_owned()];
        assert!(is_checked_path("crates/other/src/lib.rs", &p));
        assert!(is_checked_path("crates/other/src/a/b.rs", &p));
        assert!(!is_checked_path("crates/frob-present/src/lib.rs", &p));
        assert!(!is_checked_path("crates/other/src/bin/tool.rs", &p));
        assert!(!is_checked_path("crates/other/src/main.rs", &p));
        assert!(!is_checked_path("crates/other/tests/it.rs", &p));
        assert!(!is_checked_path("crates/other/build.rs", &p));
        assert!(!is_checked_path("crates/other/src/lib.rs", &[]));
    }
}

//! The `rule fmt` engine over the whole-rule examples of grl-spec.md section 12.

// frob:ticket 01M3ZX7DG5711ZSC4R0Y64C78A

use gob_plan::grl::ast::File;
use gob_plan::grl::{FormatError, format_source, parse};
use gob_text::{FileId, FileInterner};

fn file_id() -> FileId {
    FileInterner::new().intern("rules/T.grl")
}

/// The whole-rule `grl` blocks of grl-spec.md (excerpts with a bare `...` line are skipped).
fn spec_rules() -> Vec<String> {
    let path = format!(
        "{}/../../docs/design/grl-spec.md",
        env!("CARGO_MANIFEST_DIR")
    );
    let text = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"));
    let mut blocks = Vec::new();
    let mut cur: Option<String> = None;
    for line in text.lines() {
        match (&mut cur, line.trim_end()) {
            (None, "```grl") => cur = Some(String::new()),
            (Some(b), "```") => {
                blocks.push(std::mem::take(b));
                cur = None;
            }
            (Some(b), l) => {
                b.push_str(l);
                b.push('\n');
            }
            (None, _) => {}
        }
    }
    blocks
        .into_iter()
        .filter(|b| b.trim_start().starts_with("rule ") && !b.lines().any(|l| l.trim() == "..."))
        .collect()
}

/// Every spec rule the formatter accepts; those carrying `#` comments are refused, not mangled.
fn formatted_spec_rules() -> Vec<(String, String)> {
    spec_rules()
        .into_iter()
        .filter_map(|src| match format_source(file_id(), &src) {
            Ok(out) => Some((src, out)),
            Err(FormatError::CommentsWouldBeLost(_)) => None,
            Err(e) => panic!("{src}: {e}"),
        })
        .collect()
}

/// The tree of `src` with source ranges removed from its `Debug` text.
fn shape(file: &File) -> String {
    let raw = format!("{file:?}");
    let mut out = String::new();
    let mut rest = raw.as_str();
    while let Some(at) = rest.find("Span {") {
        out.push_str(&rest[..at]);
        let tail = &rest[at..];
        let end = tail.find('}').map_or(tail.len(), |i| i + 1);
        rest = &tail[end..];
    }
    out.push_str(rest);
    out
}

// frob:tests crates/gob-plan/src/grl/fmt.rs::format_source
#[test]
fn spec_rules_format_one_clause_per_line_examples_last_and_reparse_to_the_same_tree() {
    let all = formatted_spec_rules();
    assert!(all.len() >= 6, "only {} spec rules formatted", all.len());
    for (src, out) in &all {
        let before = parse(file_id(), src);
        let after = parse(file_id(), out);
        assert!(after.is_ok(), "formatted text does not parse:\n{out}");
        assert_eq!(shape(&before.file), shape(&after.file), "{src}");
        for rule in &after.file.rules {
            let clause_lines: Vec<u32> = rule
                .clauses
                .iter()
                .map(|c| line_of(out, start_of(c.span)))
                .collect();
            let mut sorted = clause_lines.clone();
            sorted.dedup();
            assert_eq!(sorted, clause_lines, "two clauses share a line in\n{out}");
            let last_clause = clause_lines.iter().max();
            for ex in &rule.examples {
                let l = line_of(out, start_of(ex.span));
                assert!(
                    last_clause.is_none_or(|c| l > *c),
                    "example before clause in\n{out}"
                );
            }
        }
    }
}

fn line_of(text: &str, offset: usize) -> u32 {
    u32::try_from(text[..offset].matches('\n').count()).expect("small file")
}

// frob:tests crates/gob-plan/src/grl/fmt.rs::format_source
#[test]
fn formatting_formatted_source_returns_the_same_bytes() {
    let all = formatted_spec_rules();
    assert!(!all.is_empty());
    for (_, once) in &all {
        let twice = format_source(file_id(), once).expect("formatted text formats");
        assert_eq!(once, &twice);
    }
}

// frob:tests crates/gob-plan/src/grl/fmt.rs::format_source
#[test]
fn syntax_errors_and_comments_are_refused_not_mangled() {
    assert!(matches!(
        format_source(file_id(), "rule NOPE999 \"t\" {"),
        Err(FormatError::Syntax(_))
    ));
    let spec = spec_rules()
        .into_iter()
        .find(|s| format_source(file_id(), s).is_err())
        .expect("a spec rule with a comment");
    assert!(matches!(
        format_source(file_id(), &spec),
        Err(FormatError::CommentsWouldBeLost(n)) if n > 0
    ));
}

fn start_of(span: gob_text::Span) -> usize {
    u32::from(span.range.start()) as usize
}

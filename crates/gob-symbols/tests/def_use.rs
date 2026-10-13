//! `def_use` golden tests: Must and May edges over Rust, Python and TypeScript fixtures.

// frob:ticket 01M4CXSPADQCCZ40KNYPAFVSV6

use gob_ir::{NodeId, Operator, Status, Universal};
use gob_symbols::{def_use_of, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// Renders the edges of function `f` in `text` as sorted `var Ldef -> Luse strength` lines.
fn render(path: &str, lang: &str, text: &str) -> String {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    let folded = fold_file(&entry, text).expect("fold");
    let unit = folded
        .term
        .ids()
        .find(|&i| {
            matches!(folded.term.node(i).op(), Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
                && folded.term.node(i).name() == Some("f")
        })
        .expect("function f");
    let line = |n: NodeId| -> String {
        if n == unit {
            return "param".to_owned();
        }
        let span = folded.term.node(n).location().span().expect("text span");
        let off = u32::from(span.range.start()) as usize;
        format!("L{}", text[..off].matches('\n').count() + 1)
    };
    let edges = def_use_of(&folded, lang, unit).expect("supported language");
    let mut lines: Vec<String> = edges
        .iter()
        .map(|e| {
            let how = match (e.strength, e.cause) {
                (Status::Must, _) => "must".to_owned(),
                (_, Some(c)) => format!("may({})", c.as_str()),
                (_, None) => "may".to_owned(),
            };
            format!(
                "{:<8} {:>5} -> {:<4} {how}",
                e.var,
                line(e.def),
                line(e.use_site)
            )
        })
        .collect();
    lines.sort();
    lines.dedup();
    lines.join("\n") + "\n"
}

// frob:tests crates/gob-ir/src/defuse.rs::def_use
#[test]
fn def_use_rust_golden() {
    insta::assert_snapshot!(render(
        "flow.rs",
        "rust",
        include_str!("fixtures/def_use/flow.rs")
    ));
}

// frob:tests crates/gob-ir/src/defuse.rs::def_use
#[test]
fn def_use_python_golden() {
    insta::assert_snapshot!(render(
        "flow.py",
        "python",
        include_str!("fixtures/def_use/flow.py")
    ));
}

// frob:tests crates/gob-ir/src/defuse.rs::def_use
#[test]
fn def_use_typescript_golden() {
    insta::assert_snapshot!(render(
        "flow.ts",
        "typescript",
        include_str!("fixtures/def_use/flow.ts")
    ));
}

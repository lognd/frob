//! Opaque and partial-parse files are Unresolved or `NotApplicable`, never silently skipped.

use std::path::Path;

use frob_check::{CheckOptions, run};
use gob_rules::{Finding, Severity};

/// The upper-case work marker, assembled so this file does not carry one.
fn marker() -> String {
    ["TO", "DO"].concat()
}

fn write(root: &Path, path: &str, bytes: &[u8]) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, bytes).expect("write");
}

/// A `.rs` with a parse hole, a `.png`, an adapter-less `.json` and a markdown file.
fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    write(
        root,
        "src/broken.rs",
        b"/// Fine.\npub fn fine() {}\n\n/// Broken.\npub fn broken() {\n    let = ;\n    call(;\n}\n",
    );
    write(root, "logo.png", &[0x89, b'P', b'N', b'G', 0, 1, 2, 3]);
    write(
        root,
        "tool.json",
        format!("# {} fix this\nprint(1)\n", marker()).as_bytes(),
    );
    write(root, "README.md", b"# Title\n\nSome text.\n");
    dir
}

fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

fn of<'a>(findings: &'a [Finding], rule: &str) -> Vec<&'a Finding> {
    findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .collect()
}

// frob:tests crates/gob-check/src/status.rs::subject_status_for
#[test]
fn a_p_plus_rule_over_an_opaque_text_file_is_unresolved_not_silent() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    // The bare marker in the adapter-less .json is invisible to TODO001: Unresolved, never Warn or Error.
    // frob:ticket 01M4FG5RCDA668CK81QT54E67N
    // The notice is emitted once per run, naming every rule that could not read the file.
    let notices: Vec<_> = report
        .findings
        .iter()
        .filter(|f| f.message.contains("opaque text file(s)"))
        .collect();
    assert_eq!(notices.len(), 1, "one opaque notice per run: {notices:?}");
    let todo = notices[0];
    assert_eq!(todo.severity, Severity::Unresolved);
    assert!(todo.message.contains("tool.json"), "{}", todo.message);
    for rule in ["TODO001", "REF001"] {
        assert!(
            todo.message.contains(rule),
            "names {rule}: {}",
            todo.message
        );
    }
    assert!(
        !todo.message.contains("logo.png"),
        "binary is NotApplicable"
    );
}

// frob:tests crates/gob-check/src/status.rs::hole_caveat
#[test]
fn a_partial_parse_is_examined_and_unresolved_for_its_symbol_rules() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    let doc = of(&report.findings, "DOC001");
    assert_eq!(doc.len(), 1, "only the hole caveat: {doc:?}");
    assert_eq!(doc[0].severity, Severity::Unresolved);
    assert!(doc[0].message.contains("src/broken.rs"));
    assert!(doc[0].span.is_some(), "anchored at the file");
    let cov = of(&report.findings, "COV001");
    assert!(
        cov.iter()
            .any(|f| f.severity == Severity::Unresolved && f.message.contains("parsed partially")),
        "{cov:?}"
    );
}

#[test]
fn not_applicable_is_counted_never_a_finding() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    assert!(
        report
            .findings
            .iter()
            .all(|f| !f.message.contains("logo.png")),
        "the PNG yields no finding at all: {:?}",
        report.findings
    );
    let opaque = &report.fidelity.languages["opaque"];
    assert_eq!(opaque.files, 2);
    assert_eq!(opaque.not_applicable["DOC"], 1, "only the PNG");
    assert_eq!(opaque.not_applicable["TODO"], 1, "only the PNG");
    assert_eq!(opaque.not_applicable["REF"], 1, "only the PNG");
    assert_eq!(opaque.unresolved["TODO001"], 1);
    // D106: a capability rule over adapter-less text is one rolled-up Unresolved, not a silent pass.
    for rule in ["DOC001", "INV002"] {
        assert_eq!(opaque.unresolved[rule], 1, "{rule}");
    }
    // DOC002 is markdown-only: adapter-less text is NotApplicable to it, never Unresolved.
    assert!(!opaque.unresolved.contains_key("DOC002"));
    assert_eq!(opaque.unresolved["REF001"], 1);
    assert_eq!(opaque.files_examined, 0);
}

#[test]
fn every_walked_file_appears_in_the_fidelity_counts() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    let counted: usize = report.fidelity.languages.values().map(|l| l.files).sum();
    assert_eq!(counted, report.stats.files, "{:?}", report.fidelity);
    assert_eq!(report.fidelity.languages["rust"].partial_parse, 1);
    assert_eq!(report.fidelity.languages["markdown"].files, 1);
    assert_eq!(report.fidelity.languages["markdown"].files_examined, 1);
    assert!(!report.fidelity.lines().is_empty());
}

// frob:ticket 01M4GKD8WNG2NW2VAR1MBP382J
// frob:tests crates/gob-check/src/status.rs::locate_hole
#[test]
fn a_partial_markdown_parse_points_at_the_table_row_and_names_the_cause() {
    let dir = fixture();
    write(
        dir.path(),
        "docs/table.md",
        b"# Table\n\n| Name | Use |\n|---|---|\n| `x|y` | fine |\n| `a||b` | broken |\n\nAfter.\n",
    );
    let report = run(dir.path(), &options()).expect("run");
    let hits: Vec<&Finding> = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved && f.message.contains("docs/table.md"))
        .filter(|f| f.message.contains("unescaped `|`"))
        .collect();
    assert!(!hits.is_empty(), "{:?}", report.findings);
    let span = hits[0].span.expect("anchored");
    assert_ne!(span.range, gob_text::TextRange::default(), "not 1:1");
    assert!(hits[0].message.contains("line 6"), "{}", hits[0].message);
}

// frob:ticket 01M48R03CM670YGJ6V3P8VPKKP
// frob:tests crates/frob-pm/src/rules/pm001.rs::Pm001
#[test]
fn pm_rules_inapplicable_reasons_appear_in_the_not_applicable_list() {
    let dir = fixture();
    let report = run(dir.path(), &options()).expect("run");
    for rule in ["PM001", "PM002", "PM034"] {
        let why =
            report.fidelity.inapplicable.get(rule).unwrap_or_else(|| {
                panic!("{rule} missing from {:?}", report.fidelity.inapplicable)
            });
        assert!(!why.is_empty(), "{rule} carries a reason");
    }
    assert!(
        report
            .fidelity
            .lines()
            .iter()
            .any(|l| l.starts_with("inapplicable PM001: ")),
        "{:?}",
        report.fidelity.lines()
    );
}

// frob:tests crates/frob-check/src/product.rs::is_frob_owned
#[test]
fn a_fresh_repository_with_only_frob_owned_files_has_no_unresolved_finding() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    write(root, "frob.toml", b"# frob config\n");
    write(
        root,
        ".gitattributes",
        b"tickets/**/ticket.md merge=frob-ledger\n",
    );
    write(root, ".gitignore", b".frob/\n");
    let report = run(root, &options()).expect("run");
    let unresolved: Vec<_> = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved)
        .collect();
    assert!(unresolved.is_empty(), "{unresolved:?}");
}

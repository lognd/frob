//! WAIVE001, `crunk:waive` suppression, `[lint]` severities and report order through `crunk check`;
//! plus the registry page under `docs/crunk/rules/`.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use std::path::Path;

use crunk_check::{CheckOptions, CrunkRun, run};
use gob_rules::Severity;

fn spec() -> &'static str {
    crunk_spec::presets::preset("default").expect("default preset")
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// Run crunk over a fresh repository; the directory lives as long as the returned guard.
fn run_in(spec_text: &str, files: &[(&str, &str)]) -> (tempfile::TempDir, CrunkRun) {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", spec_text);
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let run = run(dir.path(), &CheckOptions::default()).expect("run");
    (dir, run)
}

fn run_over(spec_text: &str, files: &[(&str, &str)]) -> CrunkRun {
    run_in(spec_text, files).1
}

/// The rule ids found, ORG001 and TOKENS001 left out: the fixture sheets sit directly under `css_root` and
/// no tokens file is generated.
fn ids(run: &CrunkRun) -> Vec<String> {
    run.report
        .findings
        .iter()
        .map(|f| f.rule.to_string())
        .filter(|id| id != "ORG001" && id != "TOKENS001")
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/waive001.rs::Waive001
#[test]
fn a_waiver_without_a_reason_fires_waive001_and_does_not_suppress() {
    let r = run_over(
        spec(),
        &[(
            "styles/a.css",
            ".a { color: #ff0000; /* crunk:waive COLOR001 */ }\n",
        )],
    );
    let got = ids(&r);
    assert!(got.contains(&"WAIVE001".to_owned()), "{got:?}");
    assert!(got.contains(&"COLOR001".to_owned()), "{got:?}");
    assert!(r.report.suppressed.is_empty());
    let w = r
        .report
        .findings
        .iter()
        .find(|f| f.rule.as_str() == "WAIVE001")
        .expect("WAIVE001");
    assert_eq!(w.message, "waiver for COLOR001 has no reason");
    assert_eq!(w.severity, Severity::Error);
}

// frob:tests crates/crunk-rules/src/waiver.rs::exceptions
#[test]
fn a_waiver_with_a_reason_suppresses_its_rule_only() {
    let css = ".a {\n  color: #ff0000; /* crunk:waive COLOR001 reason=\"brand red\" */\n  background: #00ff00;\n}\n";
    let r = run_over(spec(), &[("styles/a.css", css)]);
    let live = ids(&r);
    assert_eq!(live, ["COLOR001"], "the second colour stays: {live:?}");
    assert_eq!(r.report.suppressed.len(), 1);
    let (f, ex) = &r.report.suppressed[0];
    assert_eq!(f.rule.as_str(), "COLOR001");
    assert_eq!(ex.reason, "brand red");
}

// frob:tests crates/crunk-rules/src/waiver.rs::exceptions
#[test]
fn a_leading_waiver_suppresses_the_next_declaration() {
    let css = ".a {\n  /* crunk:waive COLOR001 reason=\"brand red\" */\n  color: #ff0000;\n}\n";
    let r = run_over(spec(), &[("styles/a.css", css)]);
    assert!(ids(&r).is_empty(), "{:?}", ids(&r));
    assert_eq!(r.report.suppressed.len(), 1);
}

// frob:tests crates/crunk-rules/src/lint.rs::apply
#[test]
fn lint_warn_changes_the_severity_and_off_drops_the_finding() {
    let css = ".a { color: #ff0000; /* crunk:waive COLOR001 */ }\n";
    let warn = spec().replace("[lint]", "[lint]\nWAIVE001 = \"warn\"");
    let r = run_over(&warn, &[("styles/a.css", css)]);
    let w = r
        .report
        .findings
        .iter()
        .find(|f| f.rule.as_str() == "WAIVE001")
        .expect("WAIVE001");
    assert_eq!(w.severity, Severity::Warn);
    let off = spec().replace("[lint]", "[lint]\nWAIVE001 = \"off\"");
    let r = run_over(&off, &[("styles/a.css", css)]);
    assert!(!ids(&r).contains(&"WAIVE001".to_owned()));
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn findings_from_several_files_are_ordered_by_path_line_rule() {
    let (_dir, r) = run_in(
        spec(),
        &[
            ("styles/z.css", ".z {\n  color: #ff0000;\n}\n"),
            (
                "styles/a.css",
                ".a {\n  color: #00ff00; /* crunk:waive COLOR001 */\n}\n",
            ),
            (
                "styles/m.css",
                "/* crunk:waive COLOR001 */\n.m {\n  color: #0000ff;\n}\n",
            ),
        ],
    );
    let doc = crunk_check::sibling_document(&r);
    let rows: Vec<(String, u64, String)> = doc["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] != "TOKENS001")
        .map(|f| {
            (
                f["file"].as_str().unwrap_or_default().to_owned(),
                f["line"].as_u64().unwrap_or_default(),
                f["rule"].as_str().unwrap_or_default().to_owned(),
            )
        })
        .collect();
    let mut sorted = rows.clone();
    sorted.sort();
    assert_eq!(rows, sorted, "document order is (path, line, rule)");
    assert!(rows.len() >= 5, "{rows:?}");
    assert_eq!(rows[0].0, "styles/a.css");
}

// frob:tests crates/crunk-rules/src/registry.rs::render_markdown
#[test]
fn the_committed_registry_page_is_fresh() {
    let page = crunk_rules::registry::render_markdown(crunk_check::product_rules::RULE_INDEXES);
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/crunk/rules/README.md");
    if std::env::var_os("UPDATE_CRUNK_RULES_DOC").is_some() {
        std::fs::write(&path, &page).expect("write page");
    }
    let committed = std::fs::read_to_string(&path).unwrap_or_default();
    assert_eq!(
        committed, page,
        "docs/crunk/rules/README.md is stale; rerun with UPDATE_CRUNK_RULES_DOC=1"
    );
}

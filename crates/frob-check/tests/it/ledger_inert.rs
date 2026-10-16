//! The ledger tree is data: directive and obligation scans skip it (D91, ~JTV288R).

use std::path::Path;

use frob_check::{CheckOptions, run};

/// The upper-case work marker, assembled so this file does not carry one.
fn marker() -> String {
    ["TO", "DO"].concat()
}

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn quiet() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

fn rules_of(findings: &[gob_rules::Finding]) -> Vec<String> {
    findings.iter().map(|f| f.rule.to_string()).collect()
}

// frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
// frob:tests crates/frob-check/src/snapshot.rs::scan_one
#[test]
fn text_in_the_ledger_tree_is_never_a_live_directive() {
    let quoted = "+++\nbody = \"- <!-- frob:waive DOC006 reason=\\\"x\\\" -->\"\n+++\n\n- <!-- frob:waive DOC006 reason=\"x\" -->\n";
    let dsl001 = |root: &Path| {
        let r = run(root, &quiet()).expect("run");
        rules_of(&r.findings)
            .iter()
            .filter(|id| *id == "DSL001")
            .count()
    };
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "tickets/ABC/ticket.md", quoted);
    write(
        dir.path(),
        "tickets/ABC/events/1.toml",
        "# frob:waive DOC006 reason=\"x\"\n",
    );
    assert_eq!(dsl001(dir.path()), 0, "ledger text is inert");
    write(
        dir.path(),
        "docs/live.md",
        "<!-- frob:waive DOC006 reason=\"x\" -->\n",
    );
    assert_eq!(
        dsl001(dir.path()),
        1,
        "the same text outside the ledger is live"
    );
}

// frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
// frob:tests crates/frob-check/src/filecheck.rs::ObligationFileCheck
#[test]
fn bare_markers_in_ledger_files_are_not_examined() {
    let dir = tempfile::tempdir().expect("tempdir");
    let line = format!("# {}: quoted from v1\n", marker());
    write(dir.path(), "tickets/ABC/events/1.toml", &line);
    write(dir.path(), "src/live.toml", &line);
    let r = run(dir.path(), &quiet()).expect("run");
    let todo = rules_of(&r.findings)
        .iter()
        .filter(|id| *id == "TODO001")
        .count();
    assert_eq!(todo, 1, "only the file outside the ledger is examined");
}

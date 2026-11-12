//! The nightly DUP005 scan workflow stays off the land path, is SHA-pinned and is documented.
// frob:ticket 01M4P0SXJRVQ0ADAAH3FMYPAR6

use std::path::PathBuf;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn workflow() -> String {
    std::fs::read_to_string(root().join(".github/workflows/dup-scan.yml")).unwrap()
}

/// The text of the workflow's `on:` block (up to the next top-level key).
fn triggers(text: &str) -> String {
    let mut out = String::new();
    let mut inside = false;
    for line in text.lines() {
        if line.starts_with("on:") {
            inside = true;
            continue;
        }
        if inside && !line.starts_with(' ') && !line.trim().is_empty() {
            break;
        }
        if inside {
            out.push_str(line);
            out.push('\n');
        }
    }
    out
}

// Acceptance 1: the job runs off the critical path and never blocks land.
#[test]
fn the_scan_runs_only_on_a_schedule_so_it_cannot_block_a_land() {
    let on = triggers(&workflow());
    assert!(on.contains("schedule:"), "{on}");
    assert!(on.contains("workflow_dispatch:"), "{on}");
    assert!(!on.contains("push:"), "{on}");
    assert!(!on.contains("pull_request"), "{on}");
    let ci = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    assert!(!ci.contains("DUP005"), "ci.yml must not run the scan");
}

#[test]
fn the_scan_enables_dup005_and_fails_only_through_the_baseline() {
    let text = workflow();
    assert!(text.contains("GRIMBLE_DUP_SCAN: \"1\""));
    assert!(text.contains("grimble check --only DUP005"));
    assert!(text.contains("timeout-minutes:"));
}

#[test]
fn every_action_in_the_scan_workflow_is_pinned_by_full_sha() {
    let text = workflow();
    let mut remote = 0;
    for line in text.lines().filter(|l| !l.trim_start().starts_with('#')) {
        let Some((_, spec)) = line.split_once("uses:") else {
            continue;
        };
        let spec = spec.trim();
        if spec.starts_with("./") {
            continue;
        }
        let (_, sha) = spec.split_once('@').expect("uses: has a ref");
        let sha: String = sha.chars().take_while(|c| !c.is_whitespace()).collect();
        assert!(
            sha.len() == 40 && sha.chars().all(|c| c.is_ascii_hexdigit()),
            "not SHA pinned: {line}"
        );
        remote += 1;
    }
    assert!(remote >= 3, "expected the pinned actions to be found");
}

// Acceptance 3: the runtime budget is documented.
#[test]
fn the_runtime_budget_is_documented() {
    let doc = std::fs::read_to_string(root().join("docs/design/dup.md")).unwrap();
    assert!(doc.contains("Runtime budget"));
    assert!(doc.contains("dup-scan.yml"));
}

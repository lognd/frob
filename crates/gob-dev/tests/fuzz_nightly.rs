//! The nightly fuzz workflow is pinned by SHA, documented, and reuses the `fuzz-build` step.
// frob:ticket 01M47QV3BRRZZSMJ5Q79N8G5S2

use std::path::PathBuf;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn nightly() -> String {
    std::fs::read_to_string(root().join(".github/workflows/fuzz-nightly.yml")).unwrap()
}

#[test]
fn every_action_in_the_nightly_fuzz_workflow_is_pinned_by_full_sha() {
    let text = nightly();
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

#[test]
fn the_nightly_fuzz_workflow_runs_the_fuzz_build_step_longer_and_is_documented() {
    let text = nightly();
    assert!(text.contains("cargo dev ci --step fuzz-build"));
    assert!(text.contains("FROB_FUZZ_SECONDS: \"900\""));
    assert!(text.contains("schedule:"));
    let doc = std::fs::read_to_string(root().join("docs/design/build-test-ci.md")).unwrap();
    assert!(doc.contains("fuzz-nightly.yml"));
    assert!(doc.contains("pinned by SHA"));
}

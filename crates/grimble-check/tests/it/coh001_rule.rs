//! COH001 as a registered rule: the `[coh]` knobs through `grimble check`.

// frob:ticket 01M4TVEKR73CP9A5RGGPPK3AWW


use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

/// Two independent two-statement jobs.
const TWO_JOBS: &str =
    "def f(a, b):\n    x = a + 1\n    y = x * 2\n    z = b - 1\n    w = z * 3\n    return y, w\n";
/// A second job that is one statement plus a call to `audit`: two jobs only while `audit` counts.
const LOGGED: &str =
    "def f(a, b):\n    x = a + 1\n    y = x * 2\n    t = b + 1\n    audit(t)\n    return y\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// The COH001 findings of a repo holding `grimble.toml` and `app/a.py`.
fn coh001_findings(config: &str, source: &str) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", config);
    write(dir.path(), "app/a.py", source);
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "COH001")
        .cloned()
        .collect()
}

// frob:tests crates/grimble-check/src/rules/coh001.rs::Coh001
// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
// frob:tests crates/grimble-check/src/host.rs::CohHost.coh_subjects_of
#[test]
fn coh001_fires_through_the_product_without_a_coh_table() {
    let found = coh001_findings("[check]\n", TWO_JOBS);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "error", "{found:?}");
}

// frob:tests crates/grimble-check/src/config.rs::CohTable
// frob:tests crates/grimble-check/src/coh001.rs::DEFAULT_MIN_SLICE_STATEMENTS
#[test]
fn min_slice_statements_raises_the_floor_for_a_job() {
    let quiet = coh001_findings("[coh]\nmin_slice_statements = 3\n", TWO_JOBS);
    assert!(quiet.is_empty(), "{quiet:?}");
    let loud = coh001_findings("[coh]\nmin_slice_statements = 2\n", TWO_JOBS);
    assert_eq!(loud.len(), 1, "{loud:?}");
}

// frob:tests crates/grimble-check/src/coh001.rs::CohOptions
#[test]
fn coh_trivial_adds_to_the_builtin_vocabulary() {
    let plain = coh001_findings("[check]\n", LOGGED);
    assert_eq!(plain.len(), 1, "{plain:?}");
    let found = coh001_findings("[coh]\ntrivial = [\"audit\"]\n", LOGGED);
    assert!(found.is_empty(), "{found:?}");
}

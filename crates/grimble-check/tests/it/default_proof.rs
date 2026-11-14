//! `[grimble] default_proof` reaches CLAIM003 for claims that write no `proof` clause.

// frob:ticket 01M5A56QNQJE7PP75H8F90AJQS

use std::path::Path;

use grimble_check::{CheckOptions, run};

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n}\nnode b : trusted {\n}\nflow f : a -> b {\n  label Public;\n}\nclaim k {\n  noflow b -> a;\n}\n";

/// Write `text` to the repo-relative `rel` under `root`, creating parents.
fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// How many CLAIM003 findings a run over a repo configured with `config` reports.
fn claim003(config: &str) -> usize {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "design/model.grmb", MODEL);
    write(dir.path(), "grimble.toml", config);
    let done = run(dir.path(), &CheckOptions::default()).expect("run");
    done.report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "CLAIM003")
        .count()
}

// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn default_proof_above_l1_makes_an_unlabelled_claim_unresolved() {
    assert!(claim003("[grimble]\ndefault_proof = \"L2\"\n") > 0);
}

// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn default_proof_defaults_to_l1_and_leaves_the_claim_decided() {
    assert_eq!(claim003("[grimble]\n"), 0);
}

//! `CFG001` markdown corpus: each block is the `frob.toml` of a fresh repository.

// frob:ticket 01M4YBK7YTVNC16GHFFK4JKY97

mod common;

use gob_config::check;
use gob_mdtest::Case;
use gob_rules::Finding;

/// Write the block as `frob.toml` and return the missing-knob findings.
fn runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("frob.toml"), &case.text).expect("write block");
    let (t, l) = common::tables();
    tracing::debug!("CFG001 corpus block");
    check(dir.path(), "frob", &[&t, &l]).expect("check reads the block")
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

//! `GRL016` markdown corpus: each block is one `.grl` file checked in a fresh repository.

// frob:ticket 01M3ZX7H37B9GKN45MPD6ZNBTY

use frob_check::{CheckOptions, run};
use gob_mdtest::Case;
use gob_rules::Finding;

/// Check the block as a repository holding only its file and return the findings.
fn runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join(&case.file_name);
    std::fs::create_dir_all(path.parent().expect("file has a parent")).expect("mkdir");
    std::fs::write(&path, &case.text).expect("write block");
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    tracing::debug!(file = %case.file_name, "GRL016 corpus block");
    run(dir.path(), &opts).expect("check runs").findings
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

#![allow(dead_code, reason = "the tables are described, never loaded")]
//! `CFG001` markdown corpus: each block is the `frob.toml` of a fresh repository.

// frob:ticket 01M4YBK7YTVNC16GHFFK4JKY97

use gob_config::{ConfigTable, TableDescription, check};
use gob_mdtest::Case;
use gob_rules::Finding;

/// Ticket settings with two enforcement knobs.
#[derive(Debug, ConfigTable)]
#[config(table = "tickets", materialize)]
struct Tickets {
    /// Compare-and-swap retries when updating the ledger.
    #[config(default = 5, enforcement)]
    cas_retries: u32,
    /// Where tickets live: `trunk` or `branch`.
    #[config(default = "trunk".to_owned(), enforcement)]
    r#ref: String,
}

/// Lease settings with one enforcement knob.
#[derive(Debug, ConfigTable)]
#[config(table = "tickets.lease", materialize)]
struct Lease {
    /// Minutes before a lease expires.
    #[config(default = 120, enforcement)]
    ttl_minutes: u64,
}

/// Write the block as `frob.toml` and return the missing-knob findings.
fn runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("frob.toml"), &case.text).expect("write block");
    let (t, l): (TableDescription, TableDescription) = (Tickets::describe(), Lease::describe());
    tracing::debug!("CFG001 corpus block");
    check(dir.path(), "frob", &[&t, &l]).expect("check reads the block")
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

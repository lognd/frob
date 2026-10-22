//! Shared materialized tables for the CFG001 integration tests.
#![allow(dead_code, reason = "the tables are described, never loaded")]

// frob:ticket 01M5G2WH1J8G8WR3PGF5N3TAQD

use gob_config::{ConfigTable, TableDescription};

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

/// Descriptions of both materialized tables.
pub fn tables() -> (TableDescription, TableDescription) {
    (Tickets::describe(), Lease::describe())
}

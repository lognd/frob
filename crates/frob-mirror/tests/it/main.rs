//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
#![allow(dead_code)]
mod create;
mod dups;
mod fake_github;
mod fake_github_selftest;
mod host;
mod ledger_source;
mod prop_budget;
mod prop_dups;
mod prop_liveness;
mod prop_safety;

//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod ci_parity;
mod ci_plan;
mod config_products;
mod dup_scan_workflow;
mod fuzz_nightly;
mod inline;
mod layering;
mod rule_pages;
mod small_api;

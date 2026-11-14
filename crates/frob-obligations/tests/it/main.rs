//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod common;
mod corpus;
mod coverage_threshold;
mod csharp;
mod doc002_moved;
mod doc_citation;
mod doc_orphan;
mod doc_status;
mod dsl002_alias;
mod fix_harness;
mod polarity_conformance;
mod repo;
mod small_api;
mod unity;
mod unity_dynamic;
mod unity_fields;
mod unity_meta;

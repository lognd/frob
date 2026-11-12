//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M4CTE9W9QH6SBZSJ3E0E8M28
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod autocrlf;
mod check;
mod corpus;
mod csharp;
mod equivalence;
mod evaluation;
mod fidelity;
mod ledger_inert;
mod ledger_missing;
mod opaque;
mod opens_once;
mod perf;
mod proc001;
mod proc002;
mod python;
mod ramp;
mod rule_matrix;
mod sibling;
mod tool_bind;
mod unreadable;
mod warm_cache;

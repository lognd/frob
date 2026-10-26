//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M4CTE9W9QH6SBZSJ3E0E8M28
mod autocrlf;
mod check;
mod csharp;
mod equivalence;
mod evaluation;
mod fidelity;
mod ledger_inert;
mod ledger_missing;
mod perf;
mod proc001;
mod python;
mod ramp;
mod sibling;
mod tool_bind;
mod unreadable;
mod warm_cache;

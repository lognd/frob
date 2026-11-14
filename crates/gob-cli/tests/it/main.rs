//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod envelope_ok;
mod flags_declared_once;
mod presenter;
mod root;
mod serve;
mod usage_missing_args;

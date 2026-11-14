//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod claim;
mod claim_evict;
mod claim_hold;
mod claim_notice;
mod claim_observe;
mod claim_restore;
mod claim_wip;
mod evict;
mod gc;
mod next;
mod python_env;
mod work;

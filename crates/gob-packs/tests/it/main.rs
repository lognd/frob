//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod core_effects;
mod hooks;
mod loader;
mod lock;
mod manifest;
mod plan_cache;
mod std_pack;
mod sysdesign_pack;
mod tier1;

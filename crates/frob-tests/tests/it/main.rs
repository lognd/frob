//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod bump_mtimes;
mod cargo_env;
mod common;
mod csharp;
mod dotnet;
mod graph_cache;
mod lease_worktree;
mod poison_bounds;
mod rule;
mod rust_root;
mod selection;
mod small_api;
mod test002;
mod typescript;
mod warm_median;

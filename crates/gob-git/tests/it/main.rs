//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M5AH5JNAB2APDDP317HGFM86
mod discover_scope;
mod ledger;
mod read_blobs;
mod shallow_overlay;
mod shared_reader;
mod surface;
mod symlinks;
mod tag;
mod walk_content;
mod walk_paths;

//! The crunk binary must link gob-git: its `SourceProvider` is registered at link time, and
//! without it digests silently fall back to raw reads instead of git-normalized content.

// frob:ticket 01M55VA1V2RX832AYQ5AG4YATH

use gob_walk::SourceProvider;

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn crunk_links_a_gob_walk_source_provider() {
    // Referencing the lib forces the same link set the `crunk` binary has.
    let _ = crunk::cli();
    let providers = inventory::iter::<SourceProvider>.into_iter().count();
    assert!(
        providers >= 1,
        "no gob_walk::SourceProvider registered: crunk does not link gob-git"
    );
}

//! A warm artifact cache spares every parse: facts come from the cache and terms fold on demand.

// frob:ticket 01M4D6NGJANPW3T3DKM77B0T1W

use gob_cache::Cache;
use gob_walk::{WalkConfig, walk};
use grimble_bind::code::Code;

#[test]
// frob:tests crates/grimble-bind/src/code.rs::Code.build_with
// frob:tests crates/grimble-bind/src/code.rs::CodeFile.folded
fn second_build_parses_nothing_and_folds_terms_only_on_demand() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().join("repo");
    std::fs::create_dir_all(&root).expect("mkdir");
    std::fs::write(root.join("a.rs"), "pub fn a() -> u32 { 1 }\n").expect("write");
    std::fs::write(root.join("b.rs"), "// grimble:binds a\npub fn b() {}\n").expect("write");
    std::fs::write(root.join("c.bin"), [0u8, 1, 2]).expect("write");
    let cache = Cache::open(&dir.path().join("cache"));
    let entries = walk(&root, &WalkConfig::default()).expect("walk").files;

    let cold = Code::build_with(&root, &entries, &cache);
    assert_eq!(cold.stats.cached, 0);

    let warm = Code::build_with(&root, &entries, &cache);
    assert_eq!(warm.stats.cached, 2, "both Rust files come from the cache");
    assert_eq!(warm.stats.folded, 1, "only the adapter-less file is folded");
    for path in ["a.rs", "b.rs"] {
        let (c, w) = (cold.file(path).unwrap(), warm.file(path).unwrap());
        assert_eq!(c.symbols(), w.symbols());
        assert_eq!(c.has_unseen(), w.has_unseen());
        assert_eq!(c.units().len(), w.units().len(), "on-demand fold agrees");
    }
    assert!(
        warm.file("b.rs").unwrap().text.is_some(),
        "binds text is kept"
    );
    assert!(warm.file("a.rs").unwrap().text.is_none());
}

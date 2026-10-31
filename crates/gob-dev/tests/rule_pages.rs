//! Rule pages are generated from each rule's own declaration and fail loudly when stale.

// frob:ticket 01M48R067DQ5C408CN4B00MAQ3

use std::path::PathBuf;

use gob_dev::products::OTHER_PRODUCTS;
use gob_dev::render::rules::pages_for_products;
use gob_dev::{GenFile, Mode, apply, workspace_root};

/// The workspace root of the repository under test.
fn root() -> PathBuf {
    workspace_root().expect("workspace root")
}

/// Paths of `pages` whose committed file is missing or differs.
fn stale_paths(root: &std::path::Path, pages: &[GenFile]) -> Vec<String> {
    pages
        .iter()
        .filter(|p| std::fs::read_to_string(root.join(&p.path)).ok().as_deref() != Some(&p.content))
        .map(|p| p.path.clone())
        .collect()
}

// frob:tests pages_for_products
#[test]
fn every_grimble_and_crunk_rule_has_a_fresh_page() {
    let root = root();
    let pages = pages_for_products(OTHER_PRODUCTS, &root.join("crates"));
    let want: usize = OTHER_PRODUCTS
        .iter()
        .map(|(_, ix)| ix.iter().map(|i| i.metas.len()).sum::<usize>())
        .sum();
    assert!(want > 0, "no rules found in the product lists");
    assert_eq!(pages.len(), want, "one page per rule");
    let stale = stale_paths(&root, &pages);
    assert!(
        stale.is_empty(),
        "stale or missing rule pages (run `cargo dev gen rules`): {stale:?}"
    );
}

// frob:tests apply
#[test]
fn a_stale_page_fails_the_check_naming_its_path() {
    let root = root();
    let pages = pages_for_products(OTHER_PRODUCTS, &root.join("crates"));
    let tmp = tempfile::tempdir().expect("tempdir");
    let victim = pages.first().expect("at least one page").path.clone();
    for p in &pages {
        let target = tmp.path().join(&p.path);
        std::fs::create_dir_all(target.parent().expect("parent")).expect("mkdir");
        std::fs::write(&target, &p.content).expect("write");
    }
    assert!(stale_paths(tmp.path(), &pages).is_empty());
    std::fs::write(tmp.path().join(&victim), "edited by hand\n").expect("tamper");
    assert_eq!(stale_paths(tmp.path(), &pages), vec![victim]);
    let applied = apply(tmp.path(), &pages, Mode::Check).expect("check");
    assert_eq!(applied.differing, 1);
}

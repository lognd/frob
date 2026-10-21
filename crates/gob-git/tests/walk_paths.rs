//! `walk_paths` lists without reading; `walk` hashes through the installed git content backend.

use std::fs;
use std::path::Path;

use gob_walk::{WalkConfig, walk, walk_paths};

fn write(root: &Path, rel: &str, text: &str) {
    fs::write(root.join(rel), text).unwrap();
}

// frob:ticket 01M4DPJR7RFS40YTGVT80A3EXX
// frob:tests crates/gob-walk/src/lib.rs::walk_paths
#[test]
fn walk_paths_lists_without_reading_any_file() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let marker = root.join("clean-ran");
    gob_git::Repo::init(root).unwrap();
    gob_git::install_content_backend();
    // A clean filter that leaves a marker proves the file went through the content source.
    let config = root.join(".git/config");
    let mut text = fs::read_to_string(&config).unwrap();
    text = format!(
        "{text}[filter \"spy\"]\n\tclean = touch {}; cat\n",
        // Forward slashes: git runs the filter through sh, which eats Windows backslashes.
        gob_path::Shown::with_home(&marker, None)
            .to_string()
            .replace('\\', "/")
    );
    fs::write(&config, text).unwrap();
    write(root, ".gitattributes", "*.css filter=spy\n");
    write(root, "a.css", "a{}");
    write(root, "big.css", "0123456789");
    let cfg = WalkConfig {
        size_cap: 5,
        ..WalkConfig::default()
    };

    let listed = walk_paths(root, &cfg).unwrap();
    assert!(!marker.exists(), "walk_paths must not read or filter files");
    let names: Vec<&str> = listed.files.iter().map(|f| f.path.as_str()).collect();
    assert!(names.contains(&"a.css"));
    assert_eq!(
        listed
            .files
            .iter()
            .find(|f| f.path == "a.css")
            .unwrap()
            .size,
        3
    );
    assert!(listed.oversized.iter().any(|o| o.path == "big.css"));

    let hashed = walk(root, &cfg).unwrap();
    assert!(marker.exists(), "walk hashes through the clean filter");
    assert!(hashed.files.iter().any(|f| f.path == "a.css"));
}

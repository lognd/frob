//! `.scene.html` discovery and loading through `crunk_scene::parse_scene_bytes`.

// frob:ticket 01M5H30AT7FM2BAXCTTDEGWV6J

use std::path::Path;

use crunk_ingest::scene::{SceneDocProblemKind, is_scene_doc_path, load_scene_docs};

const DIR: &str = "design/scenes";
const GOOD: &str = "<div data-id=\"a\"></div>\n";

fn write(root: &Path, rel: &str, bytes: &[u8]) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, bytes).expect("write");
}

fn paths(load: &crunk_ingest::scene::SceneDocLoad) -> Vec<&str> {
    load.docs.iter().map(|d| d.path.as_str()).collect()
}

// frob:tests load_scene_docs
#[test]
fn discovers_and_parses_scene_html_files_recursively_in_path_order() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "design/scenes/b.scene.html", GOOD.as_bytes());
    write(
        dir.path(),
        "design/scenes/nested/deep/a.scene.html",
        GOOD.as_bytes(),
    );
    write(
        dir.path(),
        "design/scenes/Z.scene.HTML",
        b"<p data-id=\"x\"></p>",
    );
    write(dir.path(), "design/scenes/card.scene.json", b"{}");
    write(dir.path(), "design/scenes/notes.html", GOOD.as_bytes());
    let load = load_scene_docs(dir.path(), DIR);
    assert_eq!(
        paths(&load),
        [
            "design/scenes/b.scene.html",
            "design/scenes/nested/deep/a.scene.html",
            "design/scenes/Z.scene.HTML",
        ]
    );
    assert!(load.problems.is_empty(), "{:?}", load.problems);
    assert_eq!(load.docs[2].doc.elements.len(), 1);
    assert_eq!(load.docs[0].text, GOOD);
}

// frob:tests load_scene_docs
#[test]
fn a_non_utf8_file_is_a_problem_not_a_panic() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "design/scenes/bad.scene.html",
        &[0x3c, 0xff, 0xfe, 0x3e],
    );
    write(dir.path(), "design/scenes/ok.scene.html", GOOD.as_bytes());
    let load = load_scene_docs(dir.path(), DIR);
    assert_eq!(paths(&load), ["design/scenes/ok.scene.html"]);
    assert_eq!(load.problems.len(), 1);
    assert_eq!(load.problems[0].kind, SceneDocProblemKind::NotUtf8);
    assert_eq!(load.problems[0].path, "design/scenes/bad.scene.html");
}

// frob:tests load_scene_docs
#[test]
fn empty_files_load_but_are_reported_and_duplicate_names_are_flagged() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "design/scenes/empty.scene.html", b"");
    write(dir.path(), "design/scenes/home.scene.html", GOOD.as_bytes());
    write(
        dir.path(),
        "design/scenes/sub/Home.scene.html",
        GOOD.as_bytes(),
    );
    let load = load_scene_docs(dir.path(), DIR);
    assert_eq!(load.docs.len(), 3);
    let kinds: Vec<_> = load
        .problems
        .iter()
        .map(|p| (p.path.as_str(), p.kind))
        .collect();
    assert_eq!(
        kinds,
        [
            ("design/scenes/empty.scene.html", SceneDocProblemKind::Empty),
            (
                "design/scenes/sub/Home.scene.html",
                SceneDocProblemKind::DuplicateName
            )
        ]
    );
}

// frob:tests load_scene_docs
#[test]
fn a_missing_directory_and_ignored_files_yield_nothing() {
    let dir = tempfile::tempdir().expect("tempdir");
    let none = load_scene_docs(dir.path(), DIR);
    assert!(none.docs.is_empty() && none.problems.is_empty());
    write(dir.path(), ".gitignore", b"design/scenes/skip.scene.html\n");
    write(dir.path(), "design/scenes/skip.scene.html", GOOD.as_bytes());
    write(dir.path(), "design/scenes/keep.scene.html", GOOD.as_bytes());
    let load = load_scene_docs(dir.path(), DIR);
    assert_eq!(paths(&load), ["design/scenes/keep.scene.html"]);
}

// frob:tests is_scene_doc_path
#[test]
fn suffix_match_is_case_insensitive_and_needs_a_stem() {
    assert!(is_scene_doc_path("a/home.scene.html"));
    assert!(is_scene_doc_path("HOME.SCENE.HTML"));
    assert!(!is_scene_doc_path(".scene.html"));
    assert!(!is_scene_doc_path("home.html"));
    assert!(!is_scene_doc_path("home.scene.json"));
}

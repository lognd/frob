//! Route a11y gaps: pages that change the route without a title or a focus move or announcement.

// frob:ticket 01M4D95TNEY7MCTS3A4F9HC26C

use std::path::{Path, PathBuf};

use gob_frameworks::{Repo, RouteGap, analyze, route_gaps};
use gob_symbols::{SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

/// The a11y fixture directory.
fn fixture() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/a11y")
}

/// The fixture files the routes are read from.
const FILES: [&str; 5] = [
    "package.json",
    "app/routes.ts",
    "app/routes/good.tsx",
    "app/routes/silent.tsx",
    "app/routes/untitled.tsx",
];

/// One fixture file as a [`FileEntry`].
fn entry(root: &Path, rel: &str) -> FileEntry {
    let bytes = std::fs::read(root.join(rel)).expect("read");
    FileEntry {
        language: LanguageHint::from_path(rel),
        path: rel.to_owned(),
        size: bytes.len() as u64,
        digest: Digest::of(&bytes),
    }
}

/// The gaps found in the fixture.
fn gaps() -> Vec<RouteGap> {
    let root = fixture();
    let files: Vec<FileEntry> = FILES.iter().map(|rel| entry(&root, rel)).collect();
    let symbols = files
        .iter()
        .map(|f| {
            let text = std::fs::read_to_string(root.join(&f.path)).expect("read");
            extract_file(f, &text)
        })
        .collect();
    let graph = SymbolGraph::from_files(symbols);
    let analysis = analyze(&root, &files, &graph);
    route_gaps(&Repo::load(&root, &files, &graph), &analysis.routes)
}

#[test]
fn silent_routes_get_one_gap_each() {
    // frob:tests crates/gob-frameworks/src/route_a11y.rs::route_gaps
    let gaps = gaps();
    let seen: Vec<(Option<&str>, bool, bool)> = gaps
        .iter()
        .map(|g| (g.pattern.as_deref(), g.missing_title, g.missing_focus))
        .collect();
    assert_eq!(
        seen,
        vec![
            (Some("/silent"), true, true),
            (Some("/untitled"), true, false),
        ]
    );
}

#[test]
fn titled_and_focused_route_is_clean() {
    // frob:tests crates/gob-frameworks/src/route_a11y.rs::route_gaps
    assert!(gaps().iter().all(|g| g.pattern.as_deref() != Some("/")));
}

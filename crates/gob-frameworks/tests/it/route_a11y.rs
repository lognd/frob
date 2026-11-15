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

/// Every file under `dir` as a [`FileEntry`] relative to `root`, sorted.
fn entries(root: &Path, dir: &Path, out: &mut Vec<FileEntry>) {
    let mut found: Vec<_> = std::fs::read_dir(dir)
        .expect("read dir")
        .flatten()
        .collect();
    found.sort_by_key(std::fs::DirEntry::path);
    for e in found {
        let p = e.path();
        if p.is_dir() {
            entries(root, &p, out);
            continue;
        }
        let rel = p
            .strip_prefix(root)
            .expect("under root")
            .to_string_lossy()
            .replace('\\', "/");
        let bytes = std::fs::read(&p).expect("read");
        out.push(FileEntry {
            language: LanguageHint::from_path(&rel),
            path: rel,
            size: bytes.len() as u64,
            digest: Digest::of(&bytes),
        });
    }
}

/// The gaps found in the fixture.
fn gaps() -> Vec<RouteGap> {
    let root = fixture();
    let mut files = Vec::new();
    entries(&root, &root, &mut files);
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

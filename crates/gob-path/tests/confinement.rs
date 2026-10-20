//! The path-to-text confinement allow list (docs/design/paths.md section 3): it can only shrink.
// frob:ticket 01M41S1KX3ZVF51H8KPJ3YXZF9

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

/// Marker carried by the crate-level `#![expect(clippy::disallowed_methods, ..)]` of an allow-listed target.
const MARKER: &str = "confinement allow list:";

/// Crates that still convert paths to text. Remove an entry when its migration ticket lands; never add one.
const ALLOW: &[&str] = &[
    "crunk",
    "crunk-ingest",
    "crunk-rules",
    "crunk-spec",
    "crunk-tailwind",
    "crunk-tokens",
    "frob",
    "frob-ack",
    "frob-evidence",
    "frob-land",
    "frob-lease",
    "frob-ledger",
    "frob-obligations",
    "frob-pm",
    "frob-release",
    "frob-tests",
    "frob-worktree",
    "gob-cache",
    "gob-cli",
    "gob-config",
    "gob-dev",
    "gob-exec",
    "gob-frameworks",
    "gob-fs",
    "gob-git",
    "gob-languages",
    "gob-lock",
    "gob-macros",
    "gob-mdtest",
    "gob-packs",
    "gob-plan",
    "gob-product",
    "gob-symbols",
    "gob-time",
    "gob-trust",
    "gob-walk",
];

/// Every `.rs` file under `dir`, recursively.
fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if p.is_dir() {
            rust_files(&p, out);
        } else if p.extension().is_some_and(|e| e == "rs") {
            out.push(p);
        }
    }
}

/// Crates (other than gob-path) whose sources carry the allow-list marker.
#[expect(
    clippy::disallowed_methods,
    reason = "gob-path is the one crate that converts paths to text"
)]
fn marked_crates() -> BTreeSet<String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");
    let mut found = BTreeSet::new();
    for entry in fs::read_dir(&root).unwrap().flatten() {
        let name = entry.file_name().to_string_lossy().into_owned();
        if name == "gob-path" || !entry.path().is_dir() {
            continue;
        }
        let mut files = Vec::new();
        rust_files(&entry.path(), &mut files);
        if files
            .iter()
            .any(|f| fs::read_to_string(f).is_ok_and(|s| s.contains(MARKER)))
        {
            found.insert(name);
        }
    }
    found
}

// frob:tests allow_list_matches_markers
#[test]
fn allow_list_matches_markers() {
    let marked = marked_crates();
    let listed: BTreeSet<String> = ALLOW.iter().map(|s| (*s).to_owned()).collect();
    let unlisted: Vec<_> = marked.difference(&listed).collect();
    assert!(
        unlisted.is_empty(),
        "crates carry the confinement marker but are not on ALLOW (the list may only shrink; \
         use gob_path::Shown, RelPath or Arg instead): {unlisted:?}"
    );
    let stale: Vec<_> = listed.difference(&marked).collect();
    assert!(
        stale.is_empty(),
        "crates on ALLOW no longer convert paths to text; remove them from ALLOW: {stale:?}"
    );
}

// frob:tests allow_list_is_sorted
#[test]
fn allow_list_is_sorted() {
    assert!(
        ALLOW.windows(2).all(|w| w[0] < w[1]),
        "ALLOW must be sorted and unique"
    );
}

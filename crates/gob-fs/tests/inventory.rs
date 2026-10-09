//! Inventory: every temp-and-rename write goes through `gob_fs`; a new hand-rolled copy fails here.

// frob:ticket 01M43JETBHW7FYNMR6SGVWFAEV

use std::fs;
use std::path::{Path, PathBuf};

/// Files allowed to call `fs::rename` / `fs::hard_link` directly, with the reason.
const ALLOWED: &[(&str, &str)] = &[
    ("gob-fs/src/lib.rs", "the shared helper itself"),
    (
        "frob-lease/src/store.rs",
        "quarantines a corrupt lease file; moves, never writes",
    ),
    (
        "frob-land/src/land.rs",
        "renames a merged worktree directory aside for background deletion; moves, never writes",
    ),
    (
        "gob-trust/src/key.rs",
        "no-clobber hard-link publish so one creator wins",
    ),
];

/// Collect every `.rs` file under `dir`.
fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            rust_files(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

// frob:tests crates/gob-fs/src/lib.rs::write_atomic
#[test]
fn no_hand_rolled_temp_and_rename_outside_the_helper() {
    let crates = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let mut offenders = Vec::new();
    for member in fs::read_dir(crates).unwrap() {
        let src = member.unwrap().path().join("src");
        if !src.is_dir() {
            continue;
        }
        let mut files = Vec::new();
        rust_files(&src, &mut files);
        for file in files {
            let rel = file
                .strip_prefix(crates)
                .unwrap()
                .to_string_lossy()
                .replace('\\', "/");
            if ALLOWED.iter().any(|(a, _)| *a == rel) {
                continue;
            }
            // Only production code: stop at the unit-test module.
            let text = fs::read_to_string(&file).unwrap();
            let prod = text.split("#[cfg(test)]").next().unwrap_or("");
            for (n, line) in prod.lines().enumerate() {
                let code = line.trim_start();
                if code.starts_with("//") {
                    continue;
                }
                if code.contains("fs::rename(") || code.contains("fs::hard_link(") {
                    offenders.push(format!("{rel}:{}: {code}", n + 1));
                }
            }
        }
    }
    assert!(
        offenders.is_empty(),
        "hand-rolled temp-and-rename; use gob_fs::write_atomic:\n{}",
        offenders.join("\n")
    );
}

//! Lint: no verb reads a flag by string name; flags are declared once on a `clap::Args` struct.
//!
//! Scans the verb sources of frob, grimble, crunk and the `frob-*` verb crates. The shared
//! root in `gob-cli/src/cli.rs` (global flags) and the `gob-*` plumbing crates are out of scope.

use std::path::{Path, PathBuf};

/// Textual patterns that look a flag up (or declare it) by string name.
const FORBIDDEN: &[&str] = &[
    "Arg::new(",
    ".get_one",
    ".try_get_one",
    ".get_many",
    ".try_get_many",
    ".get_flag",
    ".get_count",
    ".contains_id(",
    ".value_of(",
    ".get_raw(",
];

/// The `crates/` directory of the workspace.
fn crates_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("gob-cli lives under crates/")
        .to_path_buf()
}

/// Every `.rs` file under `dir`.
fn rust_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(read) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in read.flatten() {
        let path = entry.path();
        if path.is_dir() {
            rust_files(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// The verb crates the lint covers (each crate's `src/` tree).
fn verb_crates() -> Vec<PathBuf> {
    let mut crates = Vec::new();
    for entry in std::fs::read_dir(crates_dir())
        .expect("crates/ is readable")
        .flatten()
    {
        let name =
            gob_path::Shown::with_home(std::path::Path::new(&entry.file_name()), None).to_string();
        let covered =
            matches!(name.as_str(), "frob" | "grimble" | "crunk") || name.starts_with("frob-");
        if covered && entry.path().join("src").is_dir() {
            crates.push(entry.path().join("src"));
        }
    }
    crates.sort();
    crates
}

// frob:tests crates/gob-cli/src/command.rs::augment
// frob:tests crates/gob-cli/src/command.rs::parse
#[test]
fn no_verb_reads_a_flag_by_string_name() {
    let mut files = Vec::new();
    for src in verb_crates() {
        rust_files(&src, &mut files);
    }
    assert!(!files.is_empty(), "the lint found no verb sources to scan");
    let mut hits = Vec::new();
    for file in &files {
        let text = std::fs::read_to_string(file).expect("source is readable");
        for (n, line) in text.lines().enumerate() {
            let code = line.split("//").next().unwrap_or("");
            if let Some(p) = FORBIDDEN.iter().find(|p| code.contains(**p)) {
                hits.push(format!(
                    "{}:{}: {p}",
                    gob_path::Shown::with_home(file, None),
                    n + 1
                ));
            }
        }
    }
    assert!(
        hits.is_empty(),
        "flags looked up by string name:\n{}",
        hits.join("\n")
    );
}

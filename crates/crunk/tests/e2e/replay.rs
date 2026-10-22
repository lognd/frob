//! Replay one captured Python scenario through the Rust crunk, step by step.
//!
//! A scenario is a directory of `NN.step.json` files (argv, cwd) with optional `NN.setup/` trees
//! written before the step. The golden side is `NN.result.json` (exit code) and `NN.effects/`
//! (the files the Python step left behind). stdout is not compared here: the output formats
//! differ by design and the parity harness already judges the shared verbs' output.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use gob_cli::run_for_test;
use serde_json::Value;

/// What a step can differ in: the exit code, or the files it was expected to leave behind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Field {
    /// The process exit code.
    Exit,
    /// A file the Python step wrote that the Rust step did not.
    Effects,
}

impl Field {
    /// The lowercase name used in messages.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Exit => "exit",
            Self::Effects => "effects",
        }
    }
}

/// The `tests/crunk-parity` directory.
pub fn parity_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/crunk-parity")
}

fn read_json(path: &Path) -> Value {
    let text = std::fs::read_to_string(path).unwrap_or_else(|e| panic!("read corpus file: {e}"));
    serde_json::from_str(&text).unwrap_or_else(|e| panic!("corpus json: {e}"))
}

/// Overlay the tree `from` onto `to`, creating directories as needed.
fn overlay(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).expect("mkdir");
    for entry in std::fs::read_dir(from).expect("read_dir").flatten() {
        let (src, dst) = (entry.path(), to.join(entry.file_name()));
        if src.is_dir() {
            overlay(&src, &dst);
        } else {
            std::fs::copy(&src, &dst).expect("copy");
        }
    }
}

/// Every file under `dir`, relative to it, with `/` separators.
fn files_under(dir: &Path) -> BTreeSet<String> {
    fn walk(dir: &Path, prefix: &str, out: &mut BTreeSet<String>) {
        for entry in std::fs::read_dir(dir).into_iter().flatten().flatten() {
            #[expect(
                clippy::disallowed_methods,
                reason = "test-only: corpus file names are ASCII"
            )]
            let name = entry.file_name().to_string_lossy().into_owned();
            let rel = if prefix.is_empty() {
                name
            } else {
                format!("{prefix}{}{name}", '/')
            };
            if entry.path().is_dir() {
                walk(&entry.path(), &rel, out);
            } else {
                out.insert(rel);
            }
        }
    }
    let mut out = BTreeSet::new();
    walk(dir, "", &mut out);
    out
}

/// The Rust argv for a Python argv: `tokens --format X` is `--target X` (`--format` is global).
fn translate(argv: &[String]) -> Vec<String> {
    let tokens = argv.first().is_some_and(|a| a == "tokens");
    argv.iter()
        .map(|a| {
            if tokens && a == "--format" {
                "--target".to_owned()
            } else {
                a.clone()
            }
        })
        .collect()
}

/// One step's observable difference from the Python golden.
#[derive(Debug, Clone)]
pub struct Diff {
    /// `<group>/<scenario>#<NN>`: the id divergences refer to.
    pub id: String,
    /// The differing field.
    pub field: Field,
    /// A short account of the difference.
    pub what: String,
}

/// The file name of a directory entry as text.
#[expect(
    clippy::disallowed_methods,
    reason = "test-only: corpus file names are ASCII"
)]
pub fn entry_name(entry: &std::fs::DirEntry) -> String {
    entry.file_name().to_string_lossy().into_owned()
}

/// The step numbers of a scenario, ascending.
fn step_numbers(fixture: &Path) -> Vec<String> {
    let mut nums: Vec<String> = std::fs::read_dir(fixture)
        .expect("scenario dir")
        .flatten()
        .map(|e| entry_name(&e))
        .filter_map(|n| n.strip_suffix(".step.json").map(str::to_owned))
        .collect();
    nums.sort();
    nums
}

#[expect(
    clippy::disallowed_methods,
    reason = "the work dir is substituted into captured argv text"
)]
fn quoted(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

/// Replay `scenario` (`<group>/<name>`) and return every difference from the golden.
pub fn replay(scenario: &str) -> Vec<Diff> {
    let root = parity_root();
    let fixture = root.join("fixtures/e2e").join(scenario);
    let expected = root.join("expected/e2e").join(scenario);
    let tmp = tempfile::tempdir().expect("tempdir");
    let work = tmp.path().join("root");
    std::fs::create_dir_all(&work).expect("work dir");
    let placeholder = quoted(&work);
    let mut diffs = Vec::new();
    for num in step_numbers(&fixture) {
        let id = format!("{scenario}#{num}");
        let setup = fixture.join(format!("{num}.setup"));
        if setup.is_dir() {
            overlay(&setup, &work);
        }
        let step = read_json(&fixture.join(format!("{num}.step.json")));
        for gone in step["setup_deleted"].as_array().into_iter().flatten() {
            let _ = std::fs::remove_file(work.join(gone.as_str().expect("path")));
        }
        let argv: Vec<String> = step["argv"]
            .as_array()
            .expect("argv")
            .iter()
            .map(|a| {
                a.as_str()
                    .expect("argv item")
                    .replace("<ROOT>", &placeholder)
                    .replace("<TMP>", &quoted(tmp.path()))
            })
            .collect();
        let cwd = work.join(step["cwd"].as_str().expect("cwd"));
        std::fs::create_dir_all(&cwd).expect("cwd");
        let full = translate(&argv);
        let call: Vec<&str> = full.iter().map(String::as_str).collect();
        let (code, _out, _err) = run_for_test(&crunk::cli(), &call, &cwd);
        let want = read_json(&expected.join(format!("{num}.result.json")))["exit"]
            .as_i64()
            .expect("exit");
        if i64::from(code) != want {
            diffs.push(Diff {
                id: id.clone(),
                field: Field::Exit,
                what: format!("python {want} rust {code}"),
            });
        }
        let effects = expected.join(format!("{num}.effects"));
        if effects.is_dir() {
            let missing: Vec<String> = files_under(&effects)
                .into_iter()
                .filter(|f| !work.join(f).is_file())
                .collect();
            if !missing.is_empty() {
                diffs.push(Diff {
                    id,
                    field: Field::Effects,
                    what: format!("missing {}", missing.join(", ")),
                });
            }
        }
    }
    diffs
}

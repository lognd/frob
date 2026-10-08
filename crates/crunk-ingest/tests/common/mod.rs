#![allow(
    dead_code,
    reason = "each test binary uses a different subset of the helpers"
)]

//! Shared helpers for the crunk-ingest integration tests.

use std::fs;
use std::path::{Path, PathBuf};

use crunk_spec::{DesignSpec, load_spec};
use tempfile::TempDir;

/// The committed fixture project `name`.
pub fn project(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/projects")
        .join(name)
}

/// Copy the directory `from` into `to`, creating parents.
pub fn copy_tree(from: &Path, to: &Path) {
    fs::create_dir_all(to).unwrap();
    for entry in fs::read_dir(from).unwrap() {
        let entry = entry.unwrap();
        let target = to.join(entry.file_name());
        if entry.file_type().unwrap().is_dir() {
            copy_tree(&entry.path(), &target);
        } else {
            fs::copy(entry.path(), target).unwrap();
        }
    }
}

/// Write `text` to `root/rel`, creating parents.
pub fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, text).unwrap();
}

/// A temp copy of fixture project `name` and its loaded spec.
///
/// The copy lives outside the repository so the repository's own ignore files do not apply.
pub fn scratch(name: &str) -> (TempDir, DesignSpec) {
    let dir = tempfile::tempdir().unwrap();
    copy_tree(&project(name), dir.path());
    let spec = load_spec(dir.path()).unwrap_or_else(|e| panic!("{name}: {e}"));
    (dir, spec)
}

/// A temp project with `crunk.toml` = the shared synthetic config and `files` written.
pub fn synthetic(files: &[(&str, &str)]) -> (TempDir, DesignSpec) {
    let dir = tempfile::tempdir().unwrap();
    copy_tree(&project("rules"), dir.path());
    fs::remove_dir_all(dir.path().join("styles")).unwrap();
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let spec = load_spec(dir.path()).unwrap();
    (dir, spec)
}

/// Like [`synthetic`], with `[jsx] globs` set to `globs`.
pub fn synthetic_jsx(globs: &[&str], files: &[(&str, &str)]) -> (TempDir, DesignSpec) {
    let dir = tempfile::tempdir().unwrap();
    copy_tree(&project("rules"), dir.path());
    fs::remove_dir_all(dir.path().join("styles")).unwrap();
    let toml = fs::read_to_string(dir.path().join("crunk.toml")).unwrap();
    let globs: Vec<String> = globs.iter().map(|g| format!("{g:?}")).collect();
    write(
        dir.path(),
        "crunk.toml",
        &format!("{toml}\n[jsx]\nglobs = [{}]\n", globs.join(", ")),
    );
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let spec = load_spec(dir.path()).unwrap();
    (dir, spec)
}

/// Compare two JSON values, numbers by value with a tolerance; every difference is pushed to
/// `diffs` as `path: what`.
pub fn same_json(
    path: &str,
    rust: &serde_json::Value,
    python: &serde_json::Value,
    diffs: &mut Vec<String>,
) {
    use serde_json::Value;
    match (rust, python) {
        (Value::Number(a), Value::Number(b)) => {
            let (a, b) = (a.as_f64().unwrap(), b.as_f64().unwrap());
            if (a - b).abs() > 1e-9 * a.abs().max(1.0) {
                diffs.push(format!("{path}: rust {a} != python {b}"));
            }
        }
        (Value::Object(a), Value::Object(b)) => {
            for key in a.keys().chain(b.keys()) {
                match (a.get(key), b.get(key)) {
                    (Some(x), Some(y)) => same_json(&format!("{path}.{key}"), x, y, diffs),
                    (Some(x), None) => diffs.push(format!("{path}.{key}: only in rust: {x}")),
                    (None, Some(y)) => diffs.push(format!("{path}.{key}: only in python: {y}")),
                    (None, None) => {}
                }
            }
        }
        (Value::Array(a), Value::Array(b)) => {
            if a.len() != b.len() {
                diffs.push(format!(
                    "{path}: rust len {} != python len {}",
                    a.len(),
                    b.len()
                ));
                return;
            }
            for (i, (x, y)) in a.iter().zip(b).enumerate() {
                same_json(&format!("{path}[{i}]"), x, y, diffs);
            }
        }
        (a, b) if a == b => {}
        (a, b) => diffs.push(format!("{path}: rust {a} != python {b}")),
    }
}

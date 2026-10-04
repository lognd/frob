//! Corpus parity: every valid fixture config loads to the `DesignSpec` the Python crunk dumps.
//!
//! The reference files are `<name>.spec.json` next to each `<name>.toml` under
//! `tests/fixtures/valid`, produced by `tests/fixtures/dump_spec.py` from the Python spec
//! (`DesignSpec.model_dump(mode="json")` without `root`).

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

mod common;

use std::path::{Path, PathBuf};

use common::ok;
use crunk_spec::DesignSpec;
use serde_json::Value;

fn fixtures() -> Vec<PathBuf> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/valid");
    let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
        .expect("fixtures dir")
        .map(|e| e.expect("entry").path())
        .filter(|p| p.extension().is_some_and(|e| e == "toml"))
        .collect();
    files.sort();
    files
}

/// Compare two JSON values, numbers by value with a tolerance, objects ignoring key order.
fn same(path: &str, rust: &Value, python: &Value, diffs: &mut Vec<String>) {
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
                    (Some(x), Some(y)) => same(&format!("{path}.{key}"), x, y, diffs),
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
                same(&format!("{path}[{i}]"), x, y, diffs);
            }
        }
        (a, b) if a == b => {}
        (a, b) => diffs.push(format!("{path}: rust {a} != python {b}")),
    }
}

/// Declaration order of every user-keyed map of `spec`, named as in the `.order.json` files.
fn rust_order(spec: &DesignSpec) -> Value {
    let keys = |it: Vec<&String>| Value::from(it.into_iter().cloned().collect::<Vec<_>>());
    serde_json::json!({
        "palette": keys(spec.palette.keys().collect()),
        "roles": keys(spec.roles.keys().collect()),
        "layers": keys(spec.layers.keys().collect()),
        "stacks": keys(spec.typography.stacks.keys().collect()),
        "lint_rules": keys(spec.lint.rules.keys().collect()),
        "breakpoints": keys(spec.breakpoints.points.keys().collect()),
        "platforms": keys(spec.platforms.keys().collect()),
        "screens": keys(spec.screens.keys().collect()),
        "sessions": keys(spec.sessions.keys().collect()),
        "mock_sets": keys(spec.mock_sets.keys().collect()),
    })
}

// frob:tests crates/crunk-spec/src/model.rs::DesignSpec
#[test]
fn every_fixture_equals_the_python_spec_dump() {
    let files = fixtures();
    assert!(files.len() >= 7, "corpus shrank: {files:?}");
    for toml in files {
        let name = toml.file_stem().unwrap().to_string_lossy().into_owned();
        let spec = ok(&std::fs::read_to_string(&toml).unwrap());
        let mut rust = serde_json::to_value(&spec).unwrap();
        rust.as_object_mut().unwrap().remove("root");
        let python: Value = serde_json::from_str(
            &std::fs::read_to_string(toml.with_extension("spec.json")).unwrap_or_else(|e| {
                panic!("{name}: missing reference dump (run dump_spec.py): {e}")
            }),
        )
        .unwrap();
        let mut diffs = Vec::new();
        same("$", &rust, &python, &mut diffs);
        assert!(
            diffs.is_empty(),
            "{name} differs from the Python spec:\n{}",
            diffs.join("\n")
        );
        // Declaration order is part of the contract for the maps tokens are emitted from.
        let order: Value = serde_json::from_str(
            &std::fs::read_to_string(toml.with_extension("order.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(rust_order(&spec), order, "{name}: declaration order");
    }
}

#[test]
fn corpus_covers_every_section() {
    let all: String = fixtures()
        .iter()
        .map(|p| std::fs::read_to_string(p).unwrap())
        .collect::<Vec<_>>()
        .join("\n");
    for table in crunk_spec::OWN_TABLES {
        assert!(
            all.contains(&format!("[{table}]")) || all.contains(&format!("[[{table}]]")),
            "no fixture exercises [{table}]"
        );
    }
}

//! `crunk query`, `map` and `explain` against the captured Python goldens.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use std::path::{Path, PathBuf};

#[path = "common/mod.rs"]
mod common;

use common::RUST_ONLY_RULES;
use gob_cli::run_for_test;
use serde_json::Value;

fn parity_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/crunk-parity")
}

fn golden(path: &Path) -> Value {
    let text = std::fs::read_to_string(path).expect("read golden");
    serde_json::from_str(&text).expect("golden is json")
}

/// Opt the `crunk.toml` in `dir` out of the severity ramp; a no-op when absent or already set.
fn disable_ramp(dir: &Path) {
    let path = dir.join("crunk.toml");
    let Ok(text) = std::fs::read_to_string(&path) else {
        return;
    };
    std::fs::write(&path, with_ramp_off(&text)).expect("write crunk.toml");
}

/// `text` with the severity ramp turned off; unchanged when it already has a `[rules]` table.
fn with_ramp_off(text: &str) -> String {
    if text.contains("[rules]") {
        text.to_owned()
    } else {
        format!("{text}\n[rules]\nramp = false\n")
    }
}

fn copy_tree(from: &Path, to: &Path) {
    gob_fs::copy_tree(from, to).expect("copy tree");
}

/// Run `args` in the fixture of `project` and return the envelope `data`.
fn data_for(project: &str, args: &[&str]) -> Value {
    let tmp = tempfile::tempdir().expect("tempdir");
    let dir = tmp.path().join(project);
    copy_tree(&parity_root().join("fixtures/static").join(project), &dir);
    disable_ramp(&dir);
    let (code, out, err) = run_for_test(&crunk::cli(), args, &dir);
    assert_eq!(code, 0, "{project} {args:?}: {out} {err}");
    let env: Value = serde_json::from_str(&out).expect("envelope");
    env["data"].clone()
}

#[expect(
    clippy::disallowed_methods,
    reason = "test-only: matrix directory names are ASCII fixture ids"
)]
fn projects() -> Vec<String> {
    let mut names: Vec<String> = std::fs::read_dir(parity_root().join("expected/matrix"))
        .expect("matrix dir")
        .flatten()
        .filter_map(|e| e.file_name().into_string().ok())
        .collect();
    names.sort();
    names
}

fn assert_query(project: &str, name: &str, argv: &[&str]) {
    let path = parity_root()
        .join("expected/matrix")
        .join(project)
        .join(format!("{name}.stdout"));
    let want = golden(&path);
    let got = data_for(project, argv);
    assert_eq!(got["results"], want["results"], "{project} {name}");
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn unused_matches_python_for_every_project() {
    for p in projects() {
        assert_query(&p, "query_unused_--json", &["query", "unused", "--json"]);
    }
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn uses_matches_python_for_every_project() {
    for p in projects() {
        assert_query(
            &p,
            "query_uses_color-ink_--json",
            &["query", "uses", "color-ink", "--json"],
        );
    }
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn color_matches_python_for_every_project() {
    for p in projects() {
        assert_query(
            &p,
            "query_color_1a1a1a_--json",
            &["query", "color", "1a1a1a", "--json"],
        );
    }
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn find_matches_python_for_every_project() {
    for p in projects() {
        assert_query(
            &p,
            "query_find_card_--json",
            &["query", "find", "card", "--json"],
        );
    }
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn dupes_matches_python_for_every_project() {
    for p in projects() {
        assert_query(&p, "query_dupes_--json", &["query", "dupes", "--json"]);
    }
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn violations_match_python_for_every_project() {
    for p in projects() {
        // Messages are worded by the Rust rules (double quotes where Python used single), so
        // compare everything but the message text.
        let name = "query_violations_--json";
        let want = golden(
            &parity_root()
                .join("expected/matrix")
                .join(&p)
                .join(format!("{name}.stdout")),
        );
        let got = data_for(&p, &["query", "violations", "--json"]);
        let strip = |v: &Value| -> Vec<Value> {
            v["results"]
                .as_array()
                .expect("rows")
                .iter()
                // Rules the Python tool never had are not parity subjects; EXPORT001 restates
                // TOKENS001 per export target, so it reports the same files a second time.
                .filter(|row| {
                    !row["rule"]
                        .as_str()
                        .is_some_and(|r| RUST_ONLY_RULES.contains(&r))
                })
                .map(|row| {
                    let mut row = row.clone();
                    row.as_object_mut().expect("row").remove("message");
                    row
                })
                .collect()
        };
        assert_eq!(strip(&got), strip(&want), "{p} {name}");
    }
}

// frob:tests crates/crunk/src/map.rs::Map
#[test]
fn map_matches_python_for_every_project() {
    for p in projects() {
        let want = golden(
            &parity_root()
                .join("expected/matrix")
                .join(&p)
                .join("map_--json.stdout"),
        );
        let got = data_for(&p, &["map", "--json"]);
        assert_eq!(got["buckets"], want["buckets"], "{p} buckets");
        assert_eq!(got["strays"], want["strays"], "{p} strays");
    }
}

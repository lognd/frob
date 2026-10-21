//! Path-filtered CI (monorepo.md 4): `.github/scripts/plan-jobs.py` maps a diff to job sets and
//! `ci.yml` gates the workspace job, the crunk job and the optional node job on its outputs.
// frob:ticket 01M43ARWT173GKANZ322H41VF1
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

use serde_yaml_ng::Value;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The job-set flags the planner prints for `paths` (`key=value` lines), as sorted pairs.
fn plan(paths: &[&str]) -> Vec<(String, bool)> {
    let script = root().join(".github/scripts/plan-jobs.py");
    let child = |python: &str| {
        Command::new(python)
            .arg(&script)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
    };
    let mut child = child("python3")
        .or_else(|_| child("python"))
        .expect("a python on PATH");
    child
        .stdin
        .take()
        .unwrap()
        .write_all(paths.join("\n").as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    assert!(out.status.success(), "planner failed");
    let mut flags: Vec<(String, bool)> = String::from_utf8(out.stdout)
        .unwrap()
        .lines()
        .map(|l| {
            let (k, v) = l.split_once('=').unwrap();
            (k.to_owned(), v == "true")
        })
        .collect();
    flags.sort();
    flags
}

fn flag(flags: &[(String, bool)], key: &str) -> bool {
    flags.iter().find(|(k, _)| k == key).unwrap().1
}

fn workflow() -> Value {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    serde_yaml_ng::from_str(&text).unwrap()
}

/// What the workflow runs for a plan: the `if` conditions are matched on the exact outputs they
/// read, so a gate that stops reading `full` or `crunk` fails these tests.
fn runs(doc: &Value, job: &str, flags: &[(String, bool)]) -> bool {
    let cond = doc["jobs"][job]["if"].as_str().unwrap();
    let mut cond = cond
        .trim_start_matches("${{")
        .trim_end_matches("}}")
        .to_owned();
    for (k, v) in flags {
        cond = cond.replace(
            &format!("needs.changes.outputs.{k} == 'true'"),
            &v.to_string(),
        );
        cond = cond.replace(
            &format!("needs.changes.outputs.{k} != 'true'"),
            &(!v).to_string(),
        );
    }
    let cond = cond.replace("&&", " ");
    cond.split_whitespace().all(|t| t == "true")
}

// frob:tests crates/gob-dev/tests/ci_plan.rs::a_crunk_values_change_runs_crunk_tests_and_not_the_workspace_job
#[test]
fn a_crunk_values_change_runs_crunk_tests_and_not_the_workspace_job() {
    let flags = plan(&["crates/crunk-values/src/color.rs", "tickets/x/ticket.md"]);
    let doc = workflow();
    assert!(runs(&doc, "crunk", &flags), "{flags:?}");
    // The workspace job is the one that runs the frob and grimble tests.
    assert!(!runs(&doc, "rust", &flags), "{flags:?}");
    assert!(!flag(&flags, "full"));
}

// frob:tests crates/gob-dev/tests/ci_plan.rs::a_gob_change_runs_all_three_products
#[test]
fn a_gob_change_runs_all_three_products() {
    let doc = workflow();
    for path in [
        "crates/gob-fix/src/lib.rs",
        "crates/gob-dev/src/ci.rs",
        "Cargo.lock",
        ".github/workflows/ci.yml",
    ] {
        let flags = plan(&[path]);
        assert!(runs(&doc, "rust", &flags), "{path}: {flags:?}");
        assert!(!runs(&doc, "crunk", &flags), "{path}: {flags:?}");
    }
    // Mixed with crunk files the workspace job still runs (and covers crunk).
    let flags = plan(&[
        "crates/crunk-values/src/lib.rs",
        "crates/gob-fix/src/lib.rs",
    ]);
    assert!(runs(&doc, "rust", &flags) && !runs(&doc, "crunk", &flags));
}

// frob:tests crates/gob-dev/tests/ci_plan.rs::prose_only_changes_run_no_rust_job
#[test]
fn prose_only_changes_run_no_rust_job() {
    let flags = plan(&["notes/a.md", "docs/design/x.md", "changelog.d/a.added.md"]);
    let doc = workflow();
    assert!(
        !runs(&doc, "rust", &flags) && !runs(&doc, "crunk", &flags),
        "{flags:?}"
    );
    // docs/crunk is read by the generated-file check, so it is not prose.
    assert!(flag(&plan(&["docs/crunk/ci.md"]), "crunk"));
}

// frob:tests crates/gob-dev/tests/ci_plan.rs::the_optional_node_job_never_gates_anything
#[test]
fn the_optional_node_job_never_gates_anything() {
    let doc = workflow();
    let job = &doc["jobs"]["crunk-node"];
    assert_eq!(job["continue-on-error"].as_bool(), Some(true));
    assert_eq!(job["env"]["CRUNK_REQUIRE_NODE"].as_str(), Some("1"));
    let needs_node = |needs: &Value| match needs {
        Value::String(s) => s == "crunk-node",
        Value::Sequence(v) => v.iter().any(|n| n.as_str() == Some("crunk-node")),
        _ => false,
    };
    for (name, j) in doc["jobs"].as_mapping().unwrap() {
        assert!(
            !needs_node(&j["needs"]),
            "job {name:?} waits for the optional crunk-node job"
        );
    }
    // It is planned from the node runtime paths alone.
    assert!(flag(
        &plan(&["crates/crunk-tailwind/node/helper.mjs"]),
        "node"
    ));
    assert!(!flag(&plan(&["crates/crunk-values/src/lib.rs"]), "node"));
}

// frob:tests crates/gob-dev/tests/ci_plan.rs::the_crunk_job_lists_every_crunk_package
#[test]
fn the_crunk_job_lists_every_crunk_package() {
    let doc = workflow();
    let listed = doc["jobs"]["crunk"]["env"]["CRUNK_PACKAGES"]
        .as_str()
        .unwrap();
    let mut listed: Vec<&str> = listed.split_whitespace().filter(|t| *t != "-p").collect();
    listed.sort_unstable();
    let mut on_disk: Vec<String> = std::fs::read_dir(root().join("crates"))
        .unwrap()
        .filter_map(|e| e.ok()?.file_name().into_string().ok())
        .filter(|n| n == "crunk" || n.starts_with("crunk-"))
        .collect();
    on_disk.sort_unstable();
    assert_eq!(listed, on_disk);
}

// frob:ticket 01M47QVD03PGCAZ301WHC5Q4MF
// frob:tests crates/gob-dev/tests/ci_plan.rs::the_script_and_the_rust_mapping_agree_and_docs_only_runs_its_own_job
#[test]
fn the_script_and_the_rust_mapping_agree_and_docs_only_runs_its_own_job() {
    let map = gob_dev::changes::ChangeMap::builtin().unwrap();
    let doc = workflow();
    for paths in [
        vec!["notes/a.md", "tickets/x/ticket.md"],
        vec!["crates/gob-fix/src/lib.rs"],
        vec!["crates/crunk-values/src/lib.rs"],
        vec!["crates/crunk-tailwind/node/h.mjs"],
        vec![".github/workflows/ci.yml", "notes/a.md"],
        vec!["docs/crunk/ci.md"],
    ] {
        let script = plan(&paths);
        let mut rust = map.plan(&paths).render();
        rust.sort();
        let mut rendered: Vec<String> = script.iter().map(|(k, v)| format!("{k}={v}")).collect();
        rendered.sort();
        assert_eq!(rendered, rust, "{paths:?}");
    }
    // Only a docs-only diff runs the docs-only job; it never runs the workspace job.
    let docs = plan(&["notes/a.md", "docs/design/x.md"]);
    assert!(runs(&doc, "docs-only", &docs) && !runs(&doc, "rust", &docs));
    let code = plan(&["crates/gob-fix/src/lib.rs"]);
    assert!(!runs(&doc, "docs-only", &code) && runs(&doc, "rust", &code));
}

//! Invariants of `.github/workflows/dev.yml`, the dev channel: triggered only by a green ci run
//! on the base branch, sha-pinned actions, timeouts and minimal permissions, add-then-prune asset
//! replacement, and no registry publishing.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036

use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use serde_yaml_ng::Value;

fn read(rel: &str) -> String {
    fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .join(rel),
    )
    .unwrap()
}

fn load(rel: &str) -> Value {
    serde_yaml_ng::from_str(&read(rel)).unwrap()
}

fn dev() -> Value {
    load(".github/workflows/dev.yml")
}

fn jobs(wf: &Value) -> Vec<(&str, &Value)> {
    wf["jobs"]
        .as_mapping()
        .unwrap()
        .iter()
        .map(|(k, v)| (k.as_str().unwrap(), v))
        .collect()
}

fn step_text(job: &Value) -> String {
    serde_yaml_ng::to_string(&job["steps"]).unwrap()
}

/// Binds acceptance criterion 2: the trigger is ci completing, and every job is gated on success.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn triggers_only_after_ci_succeeds_on_the_base_branch() {
    let wf = dev();
    let on = wf["on"].as_mapping().unwrap();
    assert_eq!(on.len(), 1, "only the workflow_run trigger");
    let run = on["workflow_run"].as_mapping().unwrap();
    assert_eq!(
        run["workflows"].as_sequence().unwrap(),
        &[Value::from("ci")]
    );
    assert_eq!(
        run["types"].as_sequence().unwrap(),
        &[Value::from("completed")]
    );
    // The ci workflow it follows is named `ci` and runs on push.
    assert_eq!(
        load(".github/workflows/ci.yml")["name"].as_str(),
        Some("ci")
    );

    let plan = wf["jobs"]["plan"]["if"].as_str().unwrap();
    for needle in [
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.event == 'push'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
    ] {
        assert!(plan.contains(needle), "plan job `if` lacks {needle}");
    }
    // The base-branch knob lives in the env and the gate step reads it.
    let knob = wf["env"]["DEV_BRANCHES"].as_str().unwrap();
    assert!(knob.split_whitespace().any(|b| b == "experimental"));
    let gate = step_text(&wf["jobs"]["plan"]);
    assert!(gate.contains("$DEV_BRANCHES") && gate.contains("workflow_run.head_branch"));
    // Every other job needs plan and its go output.
    for (name, job) in jobs(&wf) {
        if name == "plan" {
            continue;
        }
        let gated = job["if"]
            .as_str()
            .is_some_and(|i| i.contains("needs.plan.outputs.go == 'true'"));
        let downstream = job["needs"]
            .as_sequence()
            .is_some_and(|n| n.iter().any(|v| v.as_str() == Some("build")));
        assert!(gated || downstream, "job {name:?} is not gated on the plan");
    }
    // Builds check out the tested sha, never a branch name or a fork ref.
    let build = step_text(&wf["jobs"]["build"]);
    assert!(build.contains("needs.plan.outputs.sha"));
}

/// Binds acceptance criterion 1: the build is the release matrix and the assets name the sha.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn the_build_matrix_is_the_release_matrix_and_assets_name_the_sha() {
    let release = load(".github/workflows/release.yml");
    let wf = dev();
    assert_eq!(
        wf["jobs"]["build"]["strategy"], release["jobs"]["build"]["strategy"],
        "dev build matrix drifted from release.yml"
    );
    assert_eq!(wf["env"]["DIST_VERSION"], release["env"]["DIST_VERSION"]);
    let smoke = step_text(&wf["jobs"]["build"]);
    assert!(smoke.contains("packaging/smoke/archive-smoke.sh"));
    let publish = step_text(&wf["jobs"]["publish"]);
    assert!(
        publish.contains("${stem}-${SHORT}."),
        "assets must name the sha"
    );
    assert!(publish.contains("gh release upload dev"));
    assert!(
        wf["jobs"]["publish"]["needs"]
            .as_sequence()
            .unwrap()
            .contains(&Value::from("build"))
    );
}

/// Binds the hardening rules: SHA pins, timeouts, minimal permissions, no persisted credentials.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn every_action_is_sha_pinned_and_every_job_has_a_timeout_and_minimal_permissions() {
    let wf = dev();
    assert!(
        wf["permissions"].as_mapping().unwrap().is_empty(),
        "workflow default permissions must be empty"
    );
    let mut writers = BTreeSet::new();
    for (name, job) in jobs(&wf) {
        assert!(
            job["timeout-minutes"].as_u64().is_some_and(|m| m > 0),
            "job {name:?} lacks timeout-minutes"
        );
        let perms = job["permissions"]
            .as_mapping()
            .unwrap_or_else(|| panic!("job {name:?} lacks explicit permissions"));
        for (k, v) in perms {
            match v.as_str().unwrap() {
                "read" => {}
                "write" => {
                    assert_eq!(k.as_str(), Some("contents"), "job {name:?}: only contents");
                    writers.insert(name);
                }
                other => panic!("job {name:?}: permission {k:?} is {other}"),
            }
        }
        for s in job["steps"].as_sequence().unwrap() {
            if let Some(u) = s["uses"].as_str() {
                let sha = u.split('@').nth(1).unwrap_or_default();
                assert!(
                    sha.len() == 40 && sha.chars().all(|c| c.is_ascii_hexdigit()),
                    "job {name:?}: action {u} is not pinned to a commit SHA"
                );
                if u.starts_with("actions/checkout") {
                    assert_eq!(s["with"]["persist-credentials"].as_bool(), Some(false));
                }
            }
        }
    }
    assert_eq!(writers, BTreeSet::from(["publish"]), "only publish writes");
    // No secrets at all: the token is the job's own, and nothing reads `secrets.`.
    assert!(!read(".github/workflows/dev.yml").contains("secrets."));
}

/// Binds the atomic-replacement rule: add, move the tag, and prune the previous assets last.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn assets_are_replaced_add_then_prune_so_a_failed_run_keeps_the_previous_ones() {
    let wf = dev();
    let steps = wf["jobs"]["publish"]["steps"].as_sequence().unwrap();
    let pos = |needle: &str| {
        steps
            .iter()
            .position(|s| s["run"].as_str().is_some_and(|r| r.contains(needle)))
            .unwrap_or_else(|| panic!("no publish step runs {needle:?}"))
    };
    let upload = pos("gh release upload dev");
    let tag = pos("git/refs/tags/dev");
    let notes = pos("gh release edit dev");
    let prune = pos("gh release delete-asset");
    assert!(
        upload < tag && tag < notes && notes < prune,
        "prune must be last"
    );
    assert_eq!(steps[prune]["id"].as_str(), Some("prune"));
    // Deleting is the only destructive call before the cleanup step and it spares the new sha.
    let prune_run = steps[prune]["run"].as_str().unwrap();
    assert!(
        prune_run.contains("*\"-${SHORT}.\"*) ;;"),
        "prune must spare new assets"
    );
    // The upload never deletes a whole release, and the release is never recreated.
    let text = step_text(&wf["jobs"]["publish"]);
    assert!(!text.contains("gh release delete dev") && !text.contains("release delete dev "));
    // A failure before the prune removes only this run's partial uploads.
    let cleanup = steps.last().unwrap();
    let cond = cleanup["if"].as_str().unwrap();
    assert!(cond.contains("failure()") && cond.contains("steps.prune.outcome == 'skipped'"));
    // Runs queue; a half-published release is never cancelled.
    assert_eq!(
        wf["concurrency"]["cancel-in-progress"].as_bool(),
        Some(false)
    );
}

/// Binds the registry rule: nothing in dev.yml publishes to a package index.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn nothing_is_published_to_pypi_or_crates_io() {
    let text = read(".github/workflows/dev.yml");
    for banned in [
        "uv publish",
        "cargo publish",
        "cargo dev publish",
        "pypi-publish",
        "twine",
        "maturin publish",
        "crates-io-auth-action",
        "id-token",
        "CARGO_REGISTRY_TOKEN",
        "environment:",
    ] {
        assert!(
            !text.contains(banned),
            "dev.yml must not contain {banned:?}"
        );
    }
    // The dev workflow stays out of the tag-triggered release workflow's territory.
    assert!(!text.contains("frob-v*"));
}

//! Invariants of `.github/workflows/dev.yml`, the dev channel: triggered only by a green ci run
//! on the base branch, build and smoke through the reusable `build-smoke.yml` shared with
//! `release.yml`, sha-pinned actions, timeouts and minimal permissions, add-then-prune asset
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

/// The text without comment-only lines, for "never appears" checks that prose may mention.
fn code_only(text: &str) -> String {
    text.lines()
        .filter(|l| !l.trim_start().starts_with('#'))
        .collect::<Vec<_>>()
        .join("\n")
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
            .is_some_and(|n| n.iter().any(|v| v.as_str() == Some("artifacts")));
        assert!(gated || downstream, "job {name:?} is not gated on the plan");
    }
    // The build checks out the tested sha (the shared workflow's `ref` input), never a branch
    // name or a fork ref.
    assert_eq!(
        wf["jobs"]["artifacts"]["with"]["ref"].as_str(),
        Some("${{ needs.plan.outputs.sha }}")
    );
    assert_eq!(
        wf["jobs"]["artifacts"]["needs"].as_str(),
        Some("plan"),
        "the build waits for the gate"
    );
}

/// Binds acceptance criterion 1: build and smoke are the shared reusable workflow that release.yml
/// also calls (one matrix, one dist pin), without wheels or secrets, and the assets name the sha.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
// frob:ticket 01M418CX3WCN4WPW7XTZ2QPBZ2
#[test]
fn both_workflows_call_the_shared_build_workflow_and_assets_name_the_sha() {
    let release = load(".github/workflows/release.yml");
    let wf = dev();
    let shared_uses = "./.github/workflows/build-smoke.yml";
    for (file, w) in [("release.yml", &release), ("dev.yml", &wf)] {
        let call = &w["jobs"]["artifacts"];
        assert_eq!(
            call["uses"].as_str(),
            Some(shared_uses),
            "{file} must call it"
        );
        // No secrets cross the call (neither a map nor `inherit`), no duplicated pins.
        assert!(
            call["secrets"].is_null(),
            "{file}: the build needs no secrets"
        );
        let text = code_only(&read(&format!(".github/workflows/{file}")));
        assert!(
            !text.contains("inherit"),
            "{file}: secrets: inherit is forbidden"
        );
        assert!(
            !text.contains("DIST_VERSION"),
            "{file} must not carry its own dist pin"
        );
        // The called workflow's permissions are capped by the caller: read-only.
        let perms = call["permissions"].as_mapping().unwrap();
        assert_eq!(perms.len(), 1, "{file}");
        assert_eq!(
            call["permissions"]["contents"].as_str(),
            Some("read"),
            "{file}"
        );
        // Only the shared workflow owns a matrix.
        assert!(
            !text.contains("matrix:"),
            "{file} must not duplicate the matrix"
        );
    }
    // dev.yml builds archives only: no wheels.
    assert_eq!(
        wf["jobs"]["artifacts"]["with"]["wheels"].as_bool(),
        Some(false)
    );
    // The shared workflow offers exactly the inputs the callers use and builds the archives.
    let shared = load(".github/workflows/build-smoke.yml");
    let inputs = shared["on"]["workflow_call"]["inputs"]
        .as_mapping()
        .unwrap();
    let names: BTreeSet<&str> = inputs.keys().map(|k| k.as_str().unwrap()).collect();
    assert_eq!(names, BTreeSet::from(["ref", "tag", "wheels"]));
    let smoke = step_text(&shared["jobs"]["build"]);
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
            .contains(&Value::from("artifacts"))
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
        // A job-level `uses` is the shared workflow; its jobs carry their own timeouts, pins and
        // permissions (pinned in release_workflow.rs) and a called job takes no timeout key.
        let is_call = job["uses"].is_string();
        assert!(
            is_call || job["timeout-minutes"].as_u64().is_some_and(|m| m > 0),
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
        for s in job["steps"].as_sequence().into_iter().flatten() {
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
    // The cleanup deletes only names this run recorded, never by sha pattern, listing or clobber.
    let cleanup_run = cleanup["run"].as_str().unwrap();
    assert!(
        cleanup_run.contains("uploaded.txt"),
        "cleanup must read the recorded list"
    );
    for banned in ["${SHORT}", "--json assets", "release view", "staged/"] {
        assert!(
            !cleanup_run.contains(banned),
            "cleanup must not select assets by {banned}"
        );
    }
    // The upload records each name before uploading, skips existing names, and never clobbers.
    let upload_run = steps[upload]["run"].as_str().unwrap();
    assert!(upload_run.contains(">> \"$RUNNER_TEMP/uploaded.txt\""));
    assert!(upload_run.contains("grep -Fxq") && upload_run.contains("continue"));
    assert!(
        !upload_run.contains("--clobber"),
        "an existing asset is skipped, never overwritten"
    );
    assert!(
        upload_run.find("uploaded.txt\"\n").unwrap_or(0)
            < upload_run.find("gh release upload").unwrap(),
        "record before upload"
    );
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

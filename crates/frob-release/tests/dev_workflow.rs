//! Invariants of the dev channel, the `dev-artifacts` and `dev-publish` jobs of
//! `.github/workflows/ci.yml`: gated on a push to a dev branch of this repository after every
//! test job passed (no `workflow_run` anywhere), build and smoke through the reusable
//! `build-smoke.yml` shared with `release.yml`, sha-pinned actions, timeouts and minimal
//! permissions, add-then-prune asset replacement, and no registry publishing.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
// frob:ticket 01M41ZJGQ1GKF6NJ1JV25QHMNX

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
    load(".github/workflows/ci.yml")
}

const CI: &str = ".github/workflows/ci.yml";

/// The dev jobs of ci.yml: the shared-workflow call and the publisher.
const DEV_JOBS: [&str; 2] = ["dev-artifacts", "dev-publish"];

/// The gate every dev job carries: a push event, this repository, a configured dev branch.
fn assert_dev_gate(job: &Value, name: &str) {
    let cond = job["if"].as_str().unwrap_or_default();
    for needle in [
        "github.event_name == 'push'",
        "github.repository == 'lognd/frob'",
        "refs/heads/experimental",
        "github.ref",
    ] {
        assert!(cond.contains(needle), "job {name:?} `if` lacks {needle}");
    }
    assert!(
        !cond.contains("pull_request"),
        "job {name:?} must not admit pull requests"
    );
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

/// Binds the gate: ci.yml carries no `workflow_run`, the dev jobs wait for the test jobs, and
/// only a push to a dev branch of this repository runs them (pull requests skip them).
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
// frob:ticket 01M41ZJGQ1GKF6NJ1JV25QHMNX
#[test]
fn dev_jobs_run_only_on_a_push_to_a_dev_branch_after_every_test_job() {
    let wf = dev();
    // No workflow_run trigger in any workflow file (GitHub fires it from the default branch only).
    for entry in
        fs::read_dir(Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.github/workflows")).unwrap()
    {
        let path = entry.unwrap().path();
        let text = code_only(&fs::read_to_string(&path).unwrap());
        assert!(
            !text.contains("workflow_run"),
            "{} must not use workflow_run",
            path.display()
        );
    }
    let on = wf["on"].as_mapping().unwrap();
    assert!(on.contains_key("push") && on.contains_key("pull_request"));
    assert!(
        on["push"]["branches"]
            .as_sequence()
            .unwrap()
            .contains(&Value::from("experimental"))
    );
    // Both dev jobs carry the gate; a skipped dev-artifacts also skips dev-publish.
    for name in DEV_JOBS {
        assert_dev_gate(&wf["jobs"][name], name);
    }
    // Every test job (all jobs but the dev ones) is awaited by the publisher, directly or
    // through dev-artifacts, which itself needs them.
    let tests: Vec<&str> = jobs(&wf)
        .into_iter()
        .map(|(n, _)| n)
        .filter(|n| !DEV_JOBS.contains(n))
        .collect();
    assert!(tests.contains(&"rust"));
    let needs = |name: &str| -> Vec<String> {
        match &wf["jobs"][name]["needs"] {
            Value::String(s) => vec![s.clone()],
            Value::Sequence(q) => q.iter().map(|v| v.as_str().unwrap().to_owned()).collect(),
            _ => vec![],
        }
    };
    for t in &tests {
        assert!(
            needs("dev-artifacts").iter().any(|n| n == t),
            "dev-artifacts must need {t}"
        );
        assert!(
            needs("dev-publish").iter().any(|n| n == t),
            "dev-publish must need {t}"
        );
    }
    assert!(needs("dev-publish").iter().any(|n| n == "dev-artifacts"));
    // The build checks out the tested sha (the shared workflow's `ref` input), never a branch
    // name or a fork ref.
    assert_eq!(
        wf["jobs"]["dev-artifacts"]["with"]["ref"].as_str(),
        Some("${{ github.sha }}")
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
    for (file, w, job) in [
        ("release.yml", &release, "artifacts"),
        ("ci.yml", &wf, "dev-artifacts"),
    ] {
        let call = &w["jobs"][job];
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
        // Only the shared workflow owns the release matrix: the call carries no strategy.
        assert!(
            call["strategy"].is_null() && (file == "ci.yml" || !text.contains("matrix:")),
            "{file} must not duplicate the matrix"
        );
    }
    // The dev jobs build archives only: no wheels.
    assert_eq!(
        wf["jobs"]["dev-artifacts"]["with"]["wheels"].as_bool(),
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
    let publish = step_text(&wf["jobs"]["dev-publish"]);
    assert!(
        publish.contains("${stem}-${SHORT}."),
        "assets must name the sha"
    );
    assert!(publish.contains("gh release upload dev"));
    assert!(
        wf["jobs"]["dev-publish"]["needs"]
            .as_sequence()
            .unwrap()
            .contains(&Value::from("dev-artifacts"))
    );
}

/// Binds the hardening rules: SHA pins, timeouts, minimal permissions, no persisted credentials.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn every_action_is_sha_pinned_and_every_job_has_a_timeout_and_minimal_permissions() {
    let wf = dev();
    // The workflow default is read-only; the dev jobs spell out their own permissions.
    let default = wf["permissions"].as_mapping().unwrap();
    assert_eq!(
        default.len(),
        1,
        "workflow default permissions: contents only"
    );
    assert_eq!(wf["permissions"]["contents"].as_str(), Some("read"));
    let mut writers = BTreeSet::new();
    for (name, job) in jobs(&wf) {
        let dev_job = DEV_JOBS.contains(&name);
        // A job-level `uses` is the shared workflow; its jobs carry their own timeouts, pins and
        // permissions (pinned in release_workflow.rs) and a called job takes no timeout key.
        let is_call = job["uses"].is_string();
        assert!(
            is_call || !dev_job || job["timeout-minutes"].as_u64().is_some_and(|m| m > 0),
            "job {name:?} lacks timeout-minutes"
        );
        if dev_job {
            assert!(
                job["permissions"].is_mapping(),
                "job {name:?} lacks explicit permissions"
            );
        }
        for (k, v) in job["permissions"].as_mapping().into_iter().flatten() {
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
                if u == "./.github/actions/install-linker" {
                    continue; // the repository's own composite action: same ref, no pin
                }
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
    assert_eq!(
        writers,
        BTreeSet::from(["dev-publish"]),
        "only dev-publish writes"
    );
    // No secrets at all: the token is the job's own, and nothing reads `secrets.`.
    assert!(!read(CI).contains("secrets."));
}

/// Binds the atomic-replacement rule: add, move the tag, and prune the previous assets last.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn assets_are_replaced_add_then_prune_so_a_failed_run_keeps_the_previous_ones() {
    let wf = dev();
    let steps = wf["jobs"]["dev-publish"]["steps"].as_sequence().unwrap();
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
    let text = step_text(&wf["jobs"]["dev-publish"]);
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
        wf["jobs"]["dev-publish"]["concurrency"]["cancel-in-progress"].as_bool(),
        Some(false)
    );
}

/// Binds the registry rule: nothing in the dev jobs of ci.yml publishes to a package index.
// frob:ticket 01M4069YQHN3EMTKR3RNE8Z036
#[test]
fn nothing_is_published_to_pypi_or_crates_io() {
    let wf = dev();
    let text: String = DEV_JOBS
        .iter()
        .map(|j| serde_yaml_ng::to_string(&wf["jobs"][*j]).unwrap())
        .collect();
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
            "the dev jobs must not contain {banned:?}"
        );
    }
    // The dev jobs stay out of the tag-triggered release workflow's territory.
    assert!(!text.contains("frob-v*"));
}

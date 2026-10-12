//! Invariants of the release pipeline. The plan, build, wheel and smoke jobs live in the
//! reusable `.github/workflows/build-smoke.yml` (five targets, pinned images, dist and maturin,
//! timeouts, minimal permissions, the explicit smoke exemption, no secrets); `release.yml`
//! calls it as `artifacts` and its publishing jobs (tag-only trigger, SHA pins, crates token or
//! OIDC order, notes source) each need that call.
// frob:ticket 01M4069XRXTR0P7BE595Y75MX7
// frob:ticket 01M4069XXM8A47Y1F88NWXQPMM

use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use serde_yaml_ng::Value;

/// Targets whose wheel cannot be executed on its build runner (cross-built); never faked.
const SMOKE_EXEMPT_TARGETS: [&str; 1] = ["x86_64-apple-darwin"];
const WHEEL_TARGETS: [&str; 5] = [
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "aarch64-apple-darwin",
    "x86_64-apple-darwin",
    "x86_64-pc-windows-msvc",
];

fn workflow_text() -> String {
    fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.github/workflows/release.yml"),
    )
    .unwrap()
}

fn workflow() -> Value {
    serde_yaml_ng::from_str(&workflow_text()).unwrap()
}

/// Text of the reusable workflow that now holds plan, build, wheel and smoke.
fn shared_text() -> String {
    fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.github/workflows/build-smoke.yml"),
    )
    .unwrap()
}

fn shared() -> Value {
    serde_yaml_ng::from_str(&shared_text()).unwrap()
}

/// The text without comment-only lines, for "never appears" checks that prose may mention.
fn code_only(text: &str) -> String {
    text.lines()
        .filter(|l| !l.trim_start().starts_with('#'))
        .collect::<Vec<_>>()
        .join("\n")
}

/// The local composite action that installs the Linux linker (clang and mold) once, for every workflow.
const LINKER_ACTION: &str = "./.github/actions/install-linker";

/// The `uses:` path both callers must use: local, so caller and callee are the same ref.
const SHARED_USES: &str = "./.github/workflows/build-smoke.yml";

fn matrix(wf: &Value) -> Vec<&Value> {
    wf["jobs"]["wheel"]["strategy"]["matrix"]["include"]
        .as_sequence()
        .unwrap()
        .iter()
        .collect()
}

fn str_of<'a>(v: &'a Value, key: &str) -> &'a str {
    v[key]
        .as_str()
        .unwrap_or_else(|| panic!("matrix entry lacks string `{key}`: {v:?}"))
}

#[test]
fn the_matrix_is_exactly_the_five_wheel_targets() {
    let wf = shared();
    let got: BTreeSet<&str> = matrix(&wf)
        .into_iter()
        .map(|e| str_of(e, "target"))
        .collect();
    assert_eq!(got, BTreeSet::from(WHEEL_TARGETS));
}

#[test]
fn only_the_exempt_targets_skip_the_smoke_and_the_exemption_is_explicit() {
    let wf = shared();
    let exempt: BTreeSet<&str> = matrix(&wf)
        .into_iter()
        .filter(|e| e["smoke"].as_bool() == Some(false))
        .map(|e| str_of(e, "target"))
        .collect();
    assert_eq!(exempt, BTreeSet::from(SMOKE_EXEMPT_TARGETS));
    for e in matrix(&wf) {
        assert!(
            e["smoke"].is_bool(),
            "smoke must be an explicit boolean: {e:?}"
        );
        if e["smoke"].as_bool() == Some(false) {
            assert_eq!(
                e["cross"].as_bool(),
                Some(true),
                "an exempt wheel must be a cross build"
            );
        }
    }
    let steps = wf["jobs"]["wheel"]["steps"].as_sequence().unwrap();
    let smoke_ifs: Vec<&str> = steps
        .iter()
        .filter(|s| {
            s["run"]
                .as_str()
                .is_some_and(|r| r.contains("cargo dev wheel-smoke"))
        })
        .map(|s| s["if"].as_str().unwrap_or_default())
        .collect();
    assert_eq!(
        smoke_ifs,
        ["matrix.smoke"],
        "exactly one smoke step, gated only on matrix.smoke"
    );
}

#[test]
fn linux_wheels_build_in_digest_pinned_manylinux_2_28_images_and_others_natively() {
    let wf = shared();
    for e in matrix(&wf) {
        let (target, image) = (str_of(e, "target"), str_of(e, "image"));
        if target.contains("linux") {
            let arch = target.split('-').next().unwrap();
            let prefix = format!("quay.io/pypa/manylinux_2_28_{arch}@sha256:");
            let digest = image.strip_prefix(&prefix).unwrap_or_else(|| {
                panic!("{target}: image {image} is not pinned {prefix}<digest>")
            });
            assert!(
                digest.len() == 64 && digest.chars().all(|c| c.is_ascii_hexdigit()),
                "{target}: bad digest"
            );
            let var = format!(
                "CARGO_TARGET_{}_LINKER",
                target.to_uppercase().replace('-', "_")
            );
            assert_eq!(str_of(e, "linker_var"), var);
        } else {
            assert_eq!(image, "", "{target}: only Linux builds in a container");
        }
    }
}

#[test]
fn macos_x86_64_is_cross_built_on_macos_latest_and_nothing_else_is_cross() {
    let wf = shared();
    for e in matrix(&wf) {
        let target = str_of(e, "target");
        let cross = e["cross"].as_bool().unwrap();
        assert_eq!(cross, target == "x86_64-apple-darwin", "{target}");
        if cross {
            assert_eq!(str_of(e, "os"), "macos-latest");
        }
    }
}

/// Text of the hash-pinned maturin requirements file `cargo dev wheel` installs from.
fn maturin_requirements() -> String {
    fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../packaging/pypi/maturin-requirements.txt"),
    )
    .unwrap()
}

/// The `X.Y.Z` of the `maturin==X.Y.Z` line of the requirements file.
fn maturin_pin() -> String {
    let text = maturin_requirements();
    let line = code_only(&text)
        .lines()
        .find_map(|l| l.trim().strip_prefix("maturin=="))
        .expect("maturin-requirements.txt must pin `maturin==X.Y.Z`")
        .to_string();
    line.trim_end_matches('\\').trim().to_string()
}

fn is_sha256(h: &str) -> bool {
    h.len() == 64 && h.chars().all(|c| c.is_ascii_hexdigit())
}

/// Violations of "maturin is installed only from the hashed requirements file".
fn maturin_unhashed(requirements: &str, build_wheel: &str, shared_code: &str) -> Vec<String> {
    let mut bad = Vec::new();
    let code = code_only(requirements);
    let hashes: Vec<&str> = code
        .split_whitespace()
        .filter_map(|w| w.strip_prefix("--hash=sha256:"))
        .collect();
    if hashes.is_empty() || !hashes.iter().all(|h| is_sha256(h)) {
        bad.push("maturin-requirements.txt lacks valid --hash=sha256: entries".to_string());
    }
    // `cargo dev wheel` (crates/gob-dev/src/wheel.rs) builds the uv argv; it must install only
    // from the hashed requirements file, with hash checking on.
    if !build_wheel.contains("maturin-requirements.txt") {
        bad.push("wheel.rs no longer installs maturin from maturin-requirements.txt".to_string());
    }
    if !build_wheel.contains("\"--require-hashes\"") {
        bad.push("wheel.rs installs maturin without --require-hashes".to_string());
    }
    // The workflow must never install maturin itself, nor pass a version around.
    for l in shared_code.lines() {
        if l.contains("maturin") && (l.contains("pip install") || l.contains("MATURIN_VERSION")) {
            bad.push(format!("build-smoke.yml installs maturin unhashed: {l}"));
        }
    }
    bad
}

/// Violations of "rustup-init is downloaded versioned and checked before it runs".
fn rustup_unhashed(shared_code: &str) -> Vec<String> {
    let mut bad = Vec::new();
    if shared_code.contains("sh.rustup.rs") {
        bad.push("rustup is piped from sh.rustup.rs".to_string());
    }
    let lines: Vec<&str> = shared_code.lines().collect();
    let fetch = lines
        .iter()
        .position(|l| l.contains("rustup-init") && l.contains("static.rust-lang.org"));
    let check = lines
        .iter()
        .position(|l| l.contains("sha256sum -c") && l.contains("RUSTUP_INIT_SHA"));
    let run = lines.iter().position(|l| {
        l.trim_start().starts_with("/tmp/rustup-init") || l.contains("; /tmp/rustup-init")
    });
    match (fetch, check, run) {
        (Some(f), Some(c), Some(r)) if f <= c && c < r => {}
        // The url is on the continuation line of the curl; accept fetch just before the check.
        (None, ..) => {
            if !lines.iter().any(|l| {
                l.contains(
                    "static.rust-lang.org/rustup/archive/$RUSTUP_INIT_VERSION/$TARGET/rustup-init",
                )
            }) {
                bad.push("rustup-init is not fetched from the versioned static URL".to_string());
            }
        }
        _ => bad.push("rustup-init is not sha256-checked before it runs".to_string()),
    }
    bad
}

#[test]
fn maturin_is_installed_only_from_a_hash_pinned_requirements_file() {
    let _ = maturin_pin();
    let bad = maturin_unhashed(
        &maturin_requirements(),
        &fs::read_to_string(
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../crates/gob-dev/src/wheel.rs"),
        )
        .unwrap(),
        &code_only(&shared_text()),
    );
    assert!(bad.is_empty(), "{bad:#?}");
}

#[test]
fn rustup_init_is_a_versioned_download_verified_by_sha256_before_it_runs() {
    let wf = shared();
    let text = code_only(&shared_text());
    let bad = rustup_unhashed(&text);
    assert!(bad.is_empty(), "{bad:#?}");
    let ver = wf["env"]["RUSTUP_INIT_VERSION"].as_str().unwrap();
    assert!(ver.split('.').all(|p| p.parse::<u32>().is_ok()), "{ver}");
    for e in matrix(&wf) {
        let (target, sha) = (str_of(e, "target"), str_of(e, "rustup_sha"));
        if target.contains("linux") {
            assert!(is_sha256(sha), "{target}: rustup_sha is not a sha256");
        } else {
            assert_eq!(sha, "", "{target}: only containers fetch rustup-init");
        }
    }
}

#[test]
fn the_unhashed_install_checks_reject_a_stripped_pin() {
    let reqs = "maturin==1.0.0 \\\n    --hash=sha256:0000000000000000000000000000000000000000000000000000000000000000\n";
    let good_sh = "vec![\"--require-hashes\".into(), \"maturin-requirements.txt\"]\n";
    assert!(maturin_unhashed(reqs, good_sh, "").is_empty());
    assert!(!maturin_unhashed("maturin==1.0.0\n", good_sh, "").is_empty());
    assert!(!maturin_unhashed(reqs, "vec![\"pip\", \"install\", \"maturin\"]\n", "").is_empty());
    assert!(!maturin_unhashed(reqs, good_sh, "run: pip install maturin==1\n").is_empty());
    let ok = "curl -o /tmp/rustup-init \\\n  \"https://static.rust-lang.org/rustup/archive/$RUSTUP_INIT_VERSION/$TARGET/rustup-init\"\necho \"$RUSTUP_INIT_SHA  /tmp/rustup-init\" | sha256sum -c -\n/tmp/rustup-init -y\n";
    assert!(rustup_unhashed(ok).is_empty());
    assert!(!rustup_unhashed(&ok.replace("sha256sum -c -", "cat")).is_empty());
    assert!(!rustup_unhashed("curl https://sh.rustup.rs | sh\n").is_empty());
}

#[test]
fn maturin_and_uv_are_pinned_exactly_and_every_job_has_a_timeout_and_permissions() {
    let wf = shared();
    let ver = maturin_pin();
    assert_eq!(ver.split('.').count(), 3);
    assert!(ver.split('.').all(|p| p.parse::<u32>().is_ok()), "{ver}");
    assert!(
        wf["env"]["UV_VERSION"]
            .as_str()
            .unwrap()
            .split('.')
            .all(|p| p.parse::<u32>().is_ok())
    );
    for (name, job) in wf["jobs"].as_mapping().unwrap() {
        assert!(
            job["timeout-minutes"].as_u64().is_some(),
            "job {name:?} lacks timeout-minutes"
        );
        assert!(
            job["permissions"].is_mapping(),
            "job {name:?} lacks its own permissions"
        );
    }
    // release.yml's own jobs: a timeout, or a call of the shared workflow (a call job takes
    // no timeout; the shared jobs carry theirs above) that still states its permissions.
    let release = workflow();
    for (name, job) in jobs(&release) {
        assert!(job["permissions"].is_mapping(), "release job {name:?}");
        assert!(
            job["timeout-minutes"].as_u64().is_some() || job["uses"].as_str() == Some(SHARED_USES),
            "release job {name:?} lacks timeout-minutes"
        );
    }
    assert_eq!(
        wf["jobs"]["wheel"]["permissions"]["contents"].as_str(),
        Some("read")
    );
    assert_eq!(
        wf["jobs"]["wheel"]["permissions"]
            .as_mapping()
            .unwrap()
            .len(),
        1
    );
}

#[test]
fn wheels_are_uploaded_as_artifacts_and_the_wheel_job_never_publishes() {
    let wf = shared();
    let steps = wf["jobs"]["wheel"]["steps"].as_sequence().unwrap();
    let upload = steps
        .iter()
        .find(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("actions/upload-artifact@"))
        })
        .expect("wheel job uploads an artifact");
    assert_eq!(upload["with"]["if-no-files-found"].as_str(), Some("error"));
    let text = format!("{}{}", shared_text(), workflow_text());
    // The wheel job itself never publishes; only the `pypi` job does.
    let wheel_text = serde_yaml_ng::to_string(&wf["jobs"]["wheel"]).unwrap();
    for banned in [
        "uv publish",
        "twine",
        "maturin publish",
        "gh-action-pypi-publish",
        "cargo publish",
    ] {
        assert!(
            !wheel_text.contains(banned),
            "wheel job must not publish: {banned}"
        );
    }
    for banned in ["uv publish", "twine", "maturin publish", "cargo publish"] {
        assert!(!text.contains(banned), "unexpected publisher: {banned}");
    }
}

#[test]
fn retired_runner_and_manylinux_auto_never_appear() {
    let text = format!("{}{}", shared_text(), workflow_text());
    assert!(!text.contains("macos-13"));
    assert!(
        !text.contains("manylinux auto")
            && !text.contains("manylinux: auto")
            && !text.contains("manylinux_auto")
    );
}

fn repo_file(rel: &str) -> String {
    fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .join(rel),
    )
    .unwrap_or_else(|e| panic!("{rel}: {e}"))
}

fn smoke_steps<'a>(wf: &'a Value, job: &str, script: &str) -> Vec<&'a Value> {
    wf["jobs"][job]["steps"]
        .as_sequence()
        .unwrap()
        .iter()
        .filter(|s| s["run"].as_str().is_some_and(|r| r.contains(script)))
        .collect()
}

/// Binds acceptance criterion 2 of ~NWXQPMM: an exempt target reports an explicit skip, never a fake run.
// frob:ticket 01M4069XXM8A47Y1F88NWXQPMM
#[test]
fn every_non_exempt_target_runs_the_fixture_repository_loop_for_wheel_and_archive() {
    let wf = shared();
    // Wheel jobs: `cargo dev wheel-smoke` delegates to the shared loop; archive jobs call archive-smoke.sh, which does too.
    assert!(repo_file("crates/gob-dev/src/wheel_smoke.rs").contains("smoke/fixture-loop.sh"));
    assert!(repo_file("packaging/smoke/archive-smoke.sh").contains("fixture-loop.sh"));
    let loop_script = repo_file("packaging/smoke/fixture-loop.sh");
    for verb in [
        "init",
        "doctor",
        "check",
        "ticket new",
        "work \"$handle\"",
        "evidence add",
        "--provider command",
        "land",
        "ticket show",
        "ticket doctor",
    ] {
        assert!(loop_script.contains(verb), "fixture loop lacks `{verb}`");
    }
    assert!(
        loop_script.contains("changelog.d/$id."),
        "fragment is named by the ticket id"
    );
    assert!(loop_script.is_ascii(), "fixture loop must be ASCII");

    let wheel = smoke_steps(&wf, "wheel", "cargo dev wheel-smoke");
    assert_eq!(wheel.len(), 1);
    let archive = smoke_steps(&wf, "build", "packaging/smoke/archive-smoke.sh");
    assert_eq!(archive.len(), 1, "exactly one archive smoke step");
    assert_eq!(archive[0]["if"].as_str(), Some("matrix.smoke"));

    let build_matrix = wf["jobs"]["build"]["strategy"]["matrix"]["include"]
        .as_sequence()
        .unwrap();
    let targets: BTreeSet<&str> = build_matrix.iter().map(|e| str_of(e, "target")).collect();
    assert_eq!(targets, BTreeSet::from(WHEEL_TARGETS));
    let exempt: BTreeSet<&str> = build_matrix
        .iter()
        .filter(|e| {
            assert!(
                e["smoke"].is_bool(),
                "smoke must be an explicit boolean: {e:?}"
            );
            e["smoke"].as_bool() == Some(false)
        })
        .map(|e| str_of(e, "target"))
        .collect();
    assert_eq!(exempt, BTreeSet::from(SMOKE_EXEMPT_TARGETS));
    // The exemption reports skipped with its reason (a notice), gated on the negation.
    let notices: Vec<&Value> = wf["jobs"]["build"]["steps"]
        .as_sequence()
        .unwrap()
        .iter()
        .filter(|s| {
            s["run"]
                .as_str()
                .is_some_and(|r| r.contains("smoke exempt for"))
        })
        .collect();
    assert_eq!(notices.len(), 1);
    assert_eq!(notices[0]["if"].as_str(), Some("${{ !matrix.smoke }}"));
}

fn jobs(wf: &Value) -> Vec<(&str, &Value)> {
    wf["jobs"]
        .as_mapping()
        .unwrap()
        .iter()
        .map(|(k, v)| (k.as_str().unwrap(), v))
        .collect()
}

fn needs_of(job: &Value) -> BTreeSet<&str> {
    match &job["needs"] {
        Value::String(s) => BTreeSet::from([s.as_str()]),
        Value::Sequence(seq) => seq.iter().map(|v| v.as_str().unwrap()).collect(),
        _ => BTreeSet::new(),
    }
}

/// A job publishes when it can write the repository or mint an OIDC token, or runs a publish command.
fn publishes(job: &Value) -> bool {
    let perms = job["permissions"].as_mapping().unwrap();
    let writes = perms.iter().any(|(_, v)| v.as_str() == Some("write"));
    let text = serde_yaml_ng::to_string(&job["steps"]).unwrap();
    writes
        || [
            "gh release create",
            "uv publish",
            "cargo publish",
            "cargo dev publish",
            "gh-action-pypi-publish",
        ]
        .iter()
        .any(|c| text.contains(c))
}

/// Binds acceptance criterion 1 of ~DH63PV1: a job without timeout-minutes fails the test, naming the job.
// frob:ticket 01M4069Y1YR0XCN4BKDDH63PV1
#[test]
fn every_job_has_a_timeout_and_the_failure_names_the_job() {
    let wf = shared();
    let missing: Vec<&str> = jobs(&wf)
        .into_iter()
        .filter(|(_, j)| j["timeout-minutes"].as_u64().is_none())
        .map(|(n, _)| n)
        .collect();
    assert!(
        missing.is_empty(),
        "jobs lacking timeout-minutes: {missing:?}"
    );
    // The same check against a mutated workflow must name the offender.
    let mut broken = wf.clone();
    broken["jobs"]["smoke"]
        .as_mapping_mut()
        .unwrap()
        .remove("timeout-minutes");
    let names: Vec<&str> = jobs(&broken)
        .into_iter()
        .filter(|(_, j)| j["timeout-minutes"].as_u64().is_none())
        .map(|(n, _)| n)
        .collect();
    assert_eq!(names, ["smoke"]);
}

/// Binds acceptance criterion 2 of ~DH63PV1: every publishing job needs the artifact smoke job,
/// now the `artifacts` call of the shared workflow whose `smoke` job follows build and wheel.
// frob:ticket 01M4069Y1YR0XCN4BKDDH63PV1
#[test]
fn every_publishing_job_needs_smoke() {
    let wf = workflow();
    // The call is unconditional and is the shared workflow, so passing it means smoke passed.
    let call = &wf["jobs"]["artifacts"];
    assert_eq!(call["uses"].as_str(), Some(SHARED_USES));
    assert!(
        call["if"].is_null(),
        "the artifacts call must not be skippable"
    );
    let sh = shared();
    assert_eq!(
        needs_of(&sh["jobs"]["smoke"]),
        BTreeSet::from(["plan", "build", "wheel"])
    );
    let mut publishers = 0;
    for (name, job) in jobs(&wf) {
        if publishes(job) {
            publishers += 1;
            assert!(
                needs_of(job).contains("artifacts"),
                "publishing job {name:?} must list the `artifacts` call (plan, build, smoke) in needs"
            );
        }
    }
    assert!(
        publishers >= 1,
        "the GitHub release job must be detected as publishing"
    );
    // A publishing job without the need is detected.
    let mut broken = wf.clone();
    broken["jobs"]["release"]["needs"] = Value::Sequence(vec![]);
    assert!(!needs_of(&broken["jobs"]["release"]).contains("artifacts"));
    assert!(publishes(&broken["jobs"]["release"]));
}

#[test]
fn smoke_job_runs_on_fresh_runners_from_downloaded_artifacts_with_the_same_exemption() {
    let wf = shared();
    let job = &wf["jobs"]["smoke"];
    assert_eq!(
        needs_of(job),
        BTreeSet::from(["plan", "build", "wheel"]),
        "smoke runs after every artifact exists"
    );
    // Wheels are optional (the dev jobs build none), so `wheel` may be skipped; a failed or
    // cancelled need must still stop the smoke.
    let cond = job["if"].as_str().unwrap();
    for needle in [
        "!cancelled()",
        "!contains(needs.*.result, 'failure')",
        "!contains(needs.*.result, 'cancelled')",
    ] {
        assert!(cond.contains(needle), "smoke `if` lacks {needle}: {cond}");
    }
    assert_eq!(wf["jobs"]["wheel"]["if"].as_str(), Some("inputs.wheels"));
    assert_eq!(job["permissions"].as_mapping().unwrap().len(), 1);
    assert_eq!(job["permissions"]["contents"].as_str(), Some("read"));
    let entries = job["strategy"]["matrix"]["include"].as_sequence().unwrap();
    let targets: BTreeSet<&str> = entries.iter().map(|e| str_of(e, "target")).collect();
    assert_eq!(targets, BTreeSet::from(WHEEL_TARGETS));
    let exempt: BTreeSet<&str> = entries
        .iter()
        .filter(|e| {
            assert!(e["smoke"].is_bool(), "smoke must be explicit: {e:?}");
            e["smoke"].as_bool() == Some(false)
        })
        .map(|e| str_of(e, "target"))
        .collect();
    assert_eq!(exempt, BTreeSet::from(SMOKE_EXEMPT_TARGETS));
    let steps = job["steps"].as_sequence().unwrap();
    // No building here: the job only consumes the uploaded artifacts.
    let text = serde_yaml_ng::to_string(steps).unwrap();
    for banned in [
        "cargo build",
        "maturin",
        "dist build",
        "cargo dev wheel ", // the trailing space allows `cargo dev wheel-smoke` (the smoke itself)
        "rustup",
    ] {
        assert!(!text.contains(banned), "smoke must not build: {banned}");
    }
    let downloads: Vec<&str> = steps
        .iter()
        .filter(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("actions/download-artifact@"))
        })
        .map(|s| s["with"]["name"].as_str().unwrap())
        .collect();
    assert_eq!(
        downloads,
        [
            "wheel-${{ matrix.target }}",
            "archives-${{ matrix.target }}"
        ]
    );
    // Every runnable step is gated on matrix.smoke; the only other step is the exemption notice.
    // The wheel steps are additionally gated on the `wheels` input, and only they.
    for s in steps {
        let cond = s["if"].as_str().unwrap_or_default();
        assert!(
            cond == "matrix.smoke"
                || cond == "${{ !matrix.smoke }}"
                || cond == "matrix.smoke && inputs.wheels",
            "smoke step must be gated on the exemption flag: {s:?}"
        );
        let about_wheels = serde_yaml_ng::to_string(s).unwrap().contains("wheel");
        assert_eq!(
            cond.contains("inputs.wheels"),
            about_wheels,
            "exactly the wheel steps are gated on the wheels input: {s:?}"
        );
    }
    assert_eq!(smoke_steps(&wf, "smoke", "cargo dev wheel-smoke").len(), 1);
    assert_eq!(
        smoke_steps(&wf, "smoke", "packaging/smoke/archive-smoke.sh").len(),
        1
    );
}

#[test]
fn triggers_are_tag_only_and_every_action_is_sha_pinned() {
    let wf = workflow();
    let on = wf["on"].as_mapping().unwrap();
    assert_eq!(
        on.len(),
        2,
        "the push trigger and the publish-nothing dry-run dispatch"
    );
    assert!(on.contains_key("workflow_dispatch"));
    let push = on["push"].as_mapping().unwrap();
    assert_eq!(
        push.len(),
        1,
        "push is filtered by tags alone (no branches)"
    );
    assert_eq!(
        push["tags"].as_sequence().unwrap(),
        &[Value::from("frob-v*")]
    );
    // Jobs of both files; a job-level `uses` is the local shared workflow (same ref, no pin).
    let sh = shared();
    for (name, job) in jobs(&wf).into_iter().chain(jobs(&sh)) {
        if let Some(u) = job["uses"].as_str() {
            assert_eq!(
                u, SHARED_USES,
                "job {name:?}: reusable workflow must be local"
            );
            continue;
        }
        for s in job["steps"].as_sequence().unwrap() {
            if let Some(u) = s["uses"].as_str() {
                if u == LINKER_ACTION {
                    continue; // local composite action: same ref as the caller, no pin
                }
                let sha = u.split('@').nth(1).unwrap_or_default();
                assert!(
                    sha.len() == 40 && sha.chars().all(|c| c.is_ascii_hexdigit()),
                    "job {name:?}: action {u} is not pinned to a commit SHA"
                );
            }
        }
    }
    // The shared workflow is only ever called; it has no trigger of its own.
    let sh_on = sh["on"].as_mapping().unwrap();
    assert_eq!(sh_on.len(), 1);
    assert!(sh_on.contains_key("workflow_call"));
}

/// Binds the `crates` job design of ~6N2KET1 and ~AZS0RRT: the `crates-io` environment after smoke, a registry token when the environment has one, OIDC otherwise.
// frob:ticket 01M4069Y65FA7GGXG2F6N2KET1
// frob:ticket 01M4172YE3SZDG17J1CAZS0RRT
#[test]
fn crates_job_uses_the_environment_token_when_set_and_oidc_otherwise_after_smoke() {
    let wf = workflow();
    let job = &wf["jobs"]["crates"];
    assert!(
        publishes(job),
        "the crates job must be detected as publishing"
    );
    assert!(needs_of(job).contains("artifacts"));
    assert_eq!(job["environment"].as_str(), Some("crates-io"));
    let perms = job["permissions"].as_mapping().unwrap();
    assert_eq!(perms.len(), 2, "only contents and id-token: {perms:?}");
    assert_eq!(job["permissions"]["contents"].as_str(), Some("read"));
    assert_eq!(job["permissions"]["id-token"].as_str(), Some("write"));
    let steps = job["steps"].as_sequence().unwrap();
    let auth = steps
        .iter()
        .position(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("rust-lang/crates-io-auth-action@"))
        })
        .expect("the OIDC exchange step");
    let publish = steps
        .iter()
        .position(|s| s["run"].as_str() == Some("cargo dev publish"))
        .expect("the publish step");
    assert!(auth < publish, "token is minted before the publish");
    // The OIDC exchange runs only when no first-publish token is stored.
    let mode = steps
        .iter()
        .find(|s| s["id"].as_str() == Some("mode"))
        .expect("the token detection step");
    assert_eq!(
        mode["env"]["FIRST_PUBLISH_TOKEN"].as_str(),
        Some("${{ secrets.CARGO_REGISTRY_TOKEN }}"),
        "the detection step reads the environment secret"
    );
    assert!(
        steps[auth]["if"]
            .as_str()
            .is_some_and(|c| c.contains("steps.mode.outputs.token != 'true'")),
        "OIDC is the fallback, skipped when a token is set"
    );
    let token = steps[publish]["env"]["CARGO_REGISTRY_TOKEN"]
        .as_str()
        .expect("the publish token env");
    let secret_at = token.find("secrets.CARGO_REGISTRY_TOKEN");
    let oidc_at = token.find("steps.auth.outputs.token");
    assert!(
        secret_at.is_some() && oidc_at.is_some() && secret_at < oidc_at,
        "the stored token wins, the OIDC token is the fallback: {token}"
    );
    // The only secret the workflow names is that one environment secret.
    let text = workflow_text();
    assert_eq!(
        text.matches("secrets.").count(),
        text.matches("secrets.CARGO_REGISTRY_TOKEN").count(),
        "no secret other than CARGO_REGISTRY_TOKEN"
    );
    assert!(
        !wf["jobs"]
            .as_mapping()
            .unwrap()
            .iter()
            .filter(|(k, _)| k.as_str() != Some("crates"))
            .any(|(_, j)| serde_yaml_ng::to_string(j).unwrap().contains("secrets.")),
        "the token is exposed to the crates job only"
    );
}

/// Binds both criteria of ~DR38G0G: the `pypi` job follows smoke, and only it and `crates` mint OIDC tokens.
// frob:ticket 01M4069YA9PXDNNCV86DR38G0G
#[test]
fn pypi_job_publishes_smoked_wheels_through_trusted_publishing_and_holds_the_only_other_id_token() {
    let wf = workflow();
    let job = &wf["jobs"]["pypi"];
    assert!(
        publishes(job),
        "the pypi job must be detected as publishing"
    );
    // PyPI and crates.io publish independently after smoke (~0JTYGH0): a slow crates.io
    // publish behind the new-crate rate limit must not hold the wheels back.
    assert_eq!(needs_of(job), BTreeSet::from(["artifacts"]));
    assert!(needs_of(&wf["jobs"]["crates"]).contains("artifacts"));
    assert_eq!(job["environment"].as_str(), Some("pypi"));
    let perms = job["permissions"].as_mapping().unwrap();
    assert_eq!(perms.len(), 1, "id-token only: {perms:?}");
    assert_eq!(job["permissions"]["id-token"].as_str(), Some("write"));
    // id-token: write is granted to no job other than crates and pypi.
    let minters: BTreeSet<&str> = jobs(&wf)
        .into_iter()
        .filter(|(_, j)| j["permissions"]["id-token"].as_str() == Some("write"))
        .map(|(n, _)| n)
        .collect();
    assert_eq!(minters, BTreeSet::from(["crates", "pypi"]));
    // No build, no checkout: it downloads the wheel artifacts and publishes them.
    let steps = job["steps"].as_sequence().unwrap();
    let text = serde_yaml_ng::to_string(steps).unwrap();
    for banned in [
        "cargo build",
        "maturin",
        "dist build",
        "cargo dev wheel",
        "rustup",
        "actions/checkout",
        "secrets.",
        "password",
    ] {
        assert!(!text.contains(banned), "pypi job must not use {banned}");
    }
    let downloads: Vec<&Value> = steps
        .iter()
        .filter(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("actions/download-artifact@"))
        })
        .collect();
    assert_eq!(downloads.len(), 1);
    assert_eq!(downloads[0]["with"]["pattern"].as_str(), Some("wheel-*"));
    let publish = steps
        .iter()
        .find(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("pypa/gh-action-pypi-publish@"))
        })
        .expect("the publish step");
    assert_eq!(publish["with"]["packages-dir"].as_str(), Some("dist"));
    assert_eq!(publish["with"]["skip-existing"].as_bool(), Some(true));
    assert_eq!(downloads[0]["with"]["path"].as_str(), Some("dist"));
}

/// Binds the upload criterion of ~TPHS84G: the pypi job uploads both products' wheels, and each set's count is checked.
// frob:ticket 01M421FB3B2P9EMNKPDTPHS84G
#[test]
fn the_pypi_job_checks_each_products_wheel_count_before_uploading_both() {
    let wf = workflow();
    let steps = wf["jobs"]["pypi"]["steps"].as_sequence().unwrap();
    let guard = steps
        .iter()
        .filter_map(|s| s["run"].as_str())
        .find(|r| r.contains("-name \"$product-*.whl\""))
        .expect("a step counts each product's wheels");
    assert!(
        guard.contains("for product in frob grimble crunk; do"),
        "{guard}"
    );
    assert!(guard.contains("-ne 5"), "five targets per product: {guard}");
    assert!(guard.contains("exit 1"));
    // The guard precedes the publish; the single download holds both products' artifacts.
    let at = |pred: &dyn Fn(&Value) -> bool| steps.iter().position(pred).unwrap();
    let guard_at = at(&|s| {
        s["run"]
            .as_str()
            .is_some_and(|r| r.contains("$product-*.whl"))
    });
    let publish_at = at(&|s| {
        s["uses"]
            .as_str()
            .is_some_and(|u| u.starts_with("pypa/gh-action-pypi-publish@"))
    });
    assert!(guard_at < publish_at);
    // Each wheel job artifact carries both products' wheels (the glob is not product-specific).
    let shared = shared();
    let upload = shared["jobs"]["wheel"]["steps"]
        .as_sequence()
        .unwrap()
        .iter()
        .find(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("actions/upload-artifact@"))
        })
        .unwrap();
    assert_eq!(upload["with"]["path"].as_str(), Some("target/wheels/*.whl"));
    // The wheel job checks one wheel per product, and the smoke runs on the whole directory.
    let text = serde_yaml_ng::to_string(&shared["jobs"]["wheel"]["steps"]).unwrap();
    assert!(text.contains("for product in frob grimble crunk; do"));
    assert!(text.contains("cargo dev wheel-smoke target/wheels"));
    // The container leaves a root-owned target/: the host-side tool build must go elsewhere.
    assert!(
        text.contains("CARGO_TARGET_DIR=\"$RUNNER_TEMP/gob-dev-tool\""),
        "the host smoke must build gob-dev outside the root-owned target/"
    );
    let fresh = serde_yaml_ng::to_string(&shared["jobs"]["smoke"]["steps"]).unwrap();
    assert!(fresh.contains("cargo dev wheel-smoke wheels"));
}

#[test]
fn release_notes_come_from_the_verb_output_not_generated_or_inline_text() {
    // frob:ticket 01M41B4KPWQVBT234N2DY20758
    let wf = workflow();
    let steps = wf["jobs"]["release"]["steps"].as_sequence().unwrap();
    assert!(
        steps.iter().any(|s| s["uses"]
            .as_str()
            .is_some_and(|u| u.starts_with("actions/checkout@"))),
        "the release job needs the checkout for CHANGELOG.md"
    );
    let run = steps
        .iter()
        .filter_map(|s| s["run"].as_str())
        .find(|r| r.contains("gh release create"))
        .expect("a step creates the release");
    let notes = run
        .find("release notes --version")
        .expect("the verb is run");
    let create = run.find("gh release create").unwrap();
    assert!(notes < create, "the notes are produced before the release");
    assert!(run.contains("--notes-file"), "{run}");
    assert!(
        run.contains("release notes --version \"$VERSION\" --text > notes.md"),
        "the raw text view is the notes file: {run}"
    );
    assert!(
        !run.contains("jq"),
        "no JSON post-processing in shell: {run}"
    );
    assert!(!run.contains("--generate-notes"), "{run}");
    assert!(!run.contains("--notes \""), "{run}");
}

/// Binds the shared-workflow rules: no secrets in or through it, least privilege, one dist pin.
// frob:ticket 01M418CX3WCN4WPW7XTZ2QPBZ2
#[test]
fn the_shared_workflow_takes_no_secrets_asks_for_read_only_and_is_the_only_dist_pin() {
    let sh = shared();
    let text = shared_text();
    // The build needs no secrets: none declared on workflow_call, none read, none inherited.
    let call = sh["on"]["workflow_call"].as_mapping().unwrap();
    assert!(
        !call.contains_key("secrets"),
        "workflow_call declares secrets"
    );
    assert!(
        !code_only(&text).contains("secrets"),
        "the shared workflow must not mention secrets"
    );
    assert!(sh["permissions"].as_mapping().unwrap().is_empty());
    for (name, job) in jobs(&sh) {
        let perms = job["permissions"].as_mapping().unwrap();
        assert_eq!(perms.len(), 1, "job {name:?}: contents only");
        assert_eq!(
            job["permissions"]["contents"].as_str(),
            Some("read"),
            "{name}"
        );
        assert!(
            job["environment"].is_null(),
            "job {name:?} must not use an environment"
        );
        for s in job["steps"].as_sequence().unwrap() {
            if s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("actions/checkout@"))
            {
                assert_eq!(
                    s["with"]["persist-credentials"].as_bool(),
                    Some(false),
                    "{name}"
                );
            }
        }
    }
    // The caller passes nothing but plain inputs and holds only contents: read (the cap).
    let release = workflow();
    let call = &release["jobs"]["artifacts"];
    assert!(
        call["secrets"].is_null(),
        "release.yml must not pass secrets"
    );
    assert!(
        !code_only(&workflow_text()).contains("inherit"),
        "secrets: inherit is forbidden"
    );
    assert_eq!(call["permissions"].as_mapping().unwrap().len(), 1);
    assert_eq!(call["permissions"]["contents"].as_str(), Some("read"));
    assert_eq!(call["with"]["wheels"].as_bool(), Some(true));
    assert_eq!(
        call["with"]["tag"].as_str(),
        Some("${{ github.event_name == 'push' && github.ref_name || '' }}")
    );
    // The dist version is pinned in the shared workflow alone.
    assert!(sh["env"]["DIST_VERSION"].as_str().is_some());
    assert!(!code_only(&workflow_text()).contains("DIST_VERSION"));
    assert!(!code_only(&repo_file(".github/workflows/ci.yml")).contains("DIST_VERSION"));
    // Inputs reach shell only through env, never interpolated into a `run`.
    for (name, job) in jobs(&sh) {
        for s in job["steps"].as_sequence().unwrap() {
            if let Some(run) = s["run"].as_str() {
                assert!(
                    !run.contains("${{"),
                    "job {name:?}: expression in run: {run}"
                );
            }
        }
    }
}

/// Binds acceptance criterion 1 of ~Y3S3WBF: a `workflow_dispatch` dry run reaches no publishing job.
// frob:ticket 01M4069Z4MQBBH3Q938Y3S3WBF
#[test]
fn every_publishing_job_runs_only_on_a_tag_push_so_a_dispatch_publishes_nowhere() {
    let wf = workflow();
    let mut publishers = 0;
    for (name, job) in jobs(&wf) {
        if publishes(job) {
            publishers += 1;
            assert_eq!(
                job["if"].as_str(),
                Some("github.event_name == 'push'"),
                "publishing job {name:?} must be guarded to the tag push"
            );
        }
    }
    assert_eq!(publishers, 3, "release, crates and pypi");
    // The dispatch builds the ref as is: the tag input of the shared call is empty off a push.
    let tag = wf["jobs"]["artifacts"]["with"]["tag"].as_str().unwrap();
    assert!(tag.contains("github.event_name == 'push'") && tag.ends_with("|| '' }}"));
}

/// Cargo invocations that compile and link Rust (`cargo metadata` and friends do not link).
const LINKING_CARGO: [&str; 9] = [
    "cargo dev",
    "cargo build",
    "cargo run",
    "cargo test",
    "cargo nextest",
    "cargo clippy",
    "cargo doc",
    "cargo install",
    "cargo publish",
];

/// Jobs that may run on Linux and compile Rust on the host before installing the linker.
///
/// The repository config links Linux with clang and mold, which a stock runner lacks, so such a
/// job needs the `LINKER_ACTION` step before its first host compile; a job-level
/// `CARGO_TARGET_*_LINKER` override (the `crates` job's stock linker) is the other accepted setup.
/// A step that only runs `docker run` compiles inside the container and is exempt.
fn unlinked_rust_jobs(wf: &Value) -> Vec<String> {
    let mut bad = Vec::new();
    for (name, job) in jobs(wf) {
        let runs_on = serde_yaml_ng::to_string(&job["runs-on"]).unwrap();
        let linux_capable = runs_on.contains("ubuntu") || runs_on.contains("matrix.os");
        let Some(steps) = job["steps"].as_sequence() else {
            continue;
        };
        let overridden = job["env"].as_mapping().is_some_and(|m| {
            m.keys()
                .filter_map(Value::as_str)
                .any(|k| k.starts_with("CARGO_TARGET_") && k.ends_with("_LINKER"))
        });
        let mut linker = false;
        for step in steps {
            if step["uses"].as_str() == Some(LINKER_ACTION) {
                linker = true;
            }
            let run = step["run"].as_str().unwrap_or_default();
            let compiles =
                LINKING_CARGO.iter().any(|c| run.contains(c)) && !run.contains("docker run");
            if linux_capable && compiles && !linker && !overridden {
                bad.push(format!(
                    "job {name:?} step {:?} compiles Rust before the linker setup",
                    step["name"].as_str().unwrap_or("(unnamed)")
                ));
                break;
            }
        }
    }
    bad
}

/// Binds ~H2CEBV3: a job that compiles Rust on a Linux host installs clang and mold first, through the one shared action.
// frob:ticket 01M454HXEWGJM5MXTA2H2CEBV3
#[test]
fn every_job_that_compiles_rust_on_linux_installs_the_linker_first() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.github");
    for file in ["ci.yml", "release.yml", "build-smoke.yml"] {
        let text = fs::read_to_string(root.join("workflows").join(file)).unwrap();
        let wf: Value = serde_yaml_ng::from_str(&text).unwrap();
        let bad = unlinked_rust_jobs(&wf);
        assert!(bad.is_empty(), "{file}: {bad:#?}");
    }
    // One definition: the install command lives only in the action.
    let action = fs::read_to_string(root.join("actions/install-linker/action.yml")).unwrap();
    assert!(action.contains("apt-get install -y mold clang"));
    for file in ["ci.yml", "release.yml", "build-smoke.yml"] {
        let text = fs::read_to_string(root.join("workflows").join(file)).unwrap();
        assert!(
            !text.contains("install -y mold"),
            "{file} copies the linker install"
        );
    }
}

// frob:tests crates/frob-release/tests/release_workflow.rs::unlinked_rust_jobs
#[test]
fn the_linker_check_rejects_a_linux_job_that_compiles_without_it() {
    let bad = "jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n      - name: build\n        run: cargo dev wheel-smoke x\n";
    let wf: Value = serde_yaml_ng::from_str(bad).unwrap();
    assert_eq!(unlinked_rust_jobs(&wf).len(), 1);
    let good = format!(
        "jobs:\n  j:\n    runs-on: ${{{{ matrix.os }}}}\n    steps:\n      - uses: {LINKER_ACTION}\n      - run: cargo dev wheel-smoke x\n"
    );
    assert!(unlinked_rust_jobs(&serde_yaml_ng::from_str(&good).unwrap()).is_empty());
    let mac =
        "jobs:\n  j:\n    runs-on: macos-latest\n    steps:\n      - run: cargo dev wheel x\n";
    assert!(unlinked_rust_jobs(&serde_yaml_ng::from_str(mac).unwrap()).is_empty());
}

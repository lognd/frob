//! Invariants of the `wheel` job in `.github/workflows/release.yml`: five targets, pinned
//! images and maturin, timeouts, minimal permissions, and the explicit smoke exemption.
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
    let wf = workflow();
    let got: BTreeSet<&str> = matrix(&wf)
        .into_iter()
        .map(|e| str_of(e, "target"))
        .collect();
    assert_eq!(got, BTreeSet::from(WHEEL_TARGETS));
}

#[test]
fn only_the_exempt_targets_skip_the_smoke_and_the_exemption_is_explicit() {
    let wf = workflow();
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
                .is_some_and(|r| r.contains("packaging/pypi/smoke.sh"))
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
    let wf = workflow();
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
    let wf = workflow();
    for e in matrix(&wf) {
        let target = str_of(e, "target");
        let cross = e["cross"].as_bool().unwrap();
        assert_eq!(cross, target == "x86_64-apple-darwin", "{target}");
        if cross {
            assert_eq!(str_of(e, "os"), "macos-latest");
        }
    }
}

#[test]
fn maturin_and_uv_are_pinned_exactly_and_every_job_has_a_timeout_and_permissions() {
    let wf = workflow();
    let pin = wf["env"]["MATURIN_VERSION"].as_str().unwrap();
    let ver = pin
        .strip_prefix("==")
        .expect("MATURIN_VERSION must be `==X.Y.Z`");
    assert_eq!(ver.split('.').count(), 3);
    assert!(ver.split('.').all(|p| p.parse::<u32>().is_ok()), "{pin}");
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
    let wf = workflow();
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
    let text = workflow_text();
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
    let text = workflow_text();
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
    let wf = workflow();
    // Wheel jobs: smoke.sh delegates to the shared loop; archive jobs call archive-smoke.sh, which does too.
    assert!(repo_file("packaging/pypi/smoke.sh").contains("smoke/fixture-loop.sh"));
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

    let wheel = smoke_steps(&wf, "wheel", "packaging/pypi/smoke.sh");
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
    let wf = workflow();
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

/// Binds acceptance criterion 2 of ~DH63PV1: every publishing job needs the artifact smoke job.
// frob:ticket 01M4069Y1YR0XCN4BKDDH63PV1
#[test]
fn every_publishing_job_needs_smoke() {
    let wf = workflow();
    let mut publishers = 0;
    for (name, job) in jobs(&wf) {
        if publishes(job) {
            publishers += 1;
            assert!(
                needs_of(job).contains("smoke"),
                "publishing job {name:?} must list `smoke` in needs"
            );
        }
    }
    assert!(
        publishers >= 1,
        "the GitHub release job must be detected as publishing"
    );
    // A publishing job without the need is detected.
    let mut broken = wf.clone();
    broken["jobs"]["release"]["needs"] = Value::Sequence(vec!["plan".into(), "build".into()]);
    assert!(!needs_of(&broken["jobs"]["release"]).contains("smoke"));
    assert!(publishes(&broken["jobs"]["release"]));
}

#[test]
fn smoke_job_runs_on_fresh_runners_from_downloaded_artifacts_with_the_same_exemption() {
    let wf = workflow();
    let job = &wf["jobs"]["smoke"];
    assert_eq!(
        needs_of(job),
        BTreeSet::from(["plan", "build", "wheel"]),
        "smoke runs after every artifact exists"
    );
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
        "build-wheel.sh",
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
    for s in steps {
        let cond = s["if"].as_str().unwrap_or_default();
        assert!(
            cond == "matrix.smoke" || cond == "${{ !matrix.smoke }}",
            "smoke step must be gated on the exemption flag: {s:?}"
        );
    }
    assert_eq!(
        smoke_steps(&wf, "smoke", "packaging/pypi/smoke.sh").len(),
        1
    );
    assert_eq!(
        smoke_steps(&wf, "smoke", "packaging/smoke/archive-smoke.sh").len(),
        1
    );
}

#[test]
fn triggers_are_tag_only_and_every_action_is_sha_pinned() {
    let wf = workflow();
    let on = wf["on"].as_mapping().unwrap();
    assert_eq!(on.len(), 1, "only the push trigger");
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
    for (name, job) in jobs(&wf) {
        for s in job["steps"].as_sequence().unwrap() {
            if let Some(u) = s["uses"].as_str() {
                let sha = u.split('@').nth(1).unwrap_or_default();
                assert!(
                    sha.len() == 40 && sha.chars().all(|c| c.is_ascii_hexdigit()),
                    "job {name:?}: action {u} is not pinned to a commit SHA"
                );
            }
        }
    }
}

/// Binds the `crates` job design of ~6N2KET1: OIDC in the `crates-io` environment, gated on smoke, no stored token.
// frob:ticket 01M4069Y65FA7GGXG2F6N2KET1
#[test]
fn crates_job_publishes_through_trusted_publishing_in_the_crates_io_environment_after_smoke() {
    let wf = workflow();
    let job = &wf["jobs"]["crates"];
    assert!(
        publishes(job),
        "the crates job must be detected as publishing"
    );
    assert!(needs_of(job).is_superset(&BTreeSet::from(["plan", "smoke"])));
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
    assert!(
        steps[publish]["env"]["CARGO_REGISTRY_TOKEN"]
            .as_str()
            .is_some_and(|t| t.contains("steps.auth.outputs.token")),
        "the registry token comes from the OIDC exchange"
    );
    let text = workflow_text();
    assert!(
        !text.contains("secrets."),
        "no stored secret: crates.io uses trusted publishing"
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
    assert!(needs_of(job).is_superset(&BTreeSet::from(["plan", "wheel", "smoke", "crates"])));
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
        "build-wheel.sh",
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
    assert_eq!(downloads[0]["with"]["path"].as_str(), Some("dist"));
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
    assert!(!run.contains("--generate-notes"), "{run}");
    assert!(!run.contains("--notes \""), "{run}");
}

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
fn wheels_are_uploaded_as_artifacts_and_nothing_publishes_to_an_index() {
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
    for banned in [
        "uv publish",
        "twine",
        "maturin publish",
        "pypa/gh-action-pypi-publish",
        "cargo publish",
    ] {
        assert!(
            !text.contains(banned),
            "release.yml must not publish yet: {banned}"
        );
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

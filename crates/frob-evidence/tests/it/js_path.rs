//! The vitest provider puts the project's `node_modules/.bin` on the runner's `PATH`.

#![cfg(unix)]

use std::os::unix::fs::PermissionsExt;
use std::time::Duration;

use frob_evidence::Provider;
use frob_evidence::provider::{JsRun, js_bin_path, run_js_tests};
use gob_exec::{Limits, Runner};

#[test]
fn the_vitest_runner_starts_with_node_modules_bin_on_path() {
    // frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
    // frob:tests crates/frob-evidence/src/provider.rs::run_js_tests
    let dir = tempfile::tempdir().expect("tempdir");
    let bin = dir.path().join("node_modules/.bin");
    std::fs::create_dir_all(&bin).expect("bin dir");
    let script = bin.join("vitest");
    std::fs::write(&script, "#!/bin/sh\necho \"PATH=$PATH\"\n").expect("script");
    std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    let allowed = ["vitest".to_owned()];
    let cap = run_js_tests(
        &Runner::new(Limits { jobs: 1 }),
        &JsRun {
            provider: Provider::Vitest,
            allowed: &allowed,
            node: "sh",
            root: dir.path(),
            member: "",
            args: &[],
            timeout: Duration::from_secs(30),
        },
    )
    .expect("run");
    let path_line = cap
        .transcript
        .lines()
        .find_map(|l| l.strip_prefix("PATH="))
        .expect("PATH line");
    let first = std::env::split_paths(path_line).next().expect("an entry");
    assert_eq!(first, bin, "{path_line}");
}

#[test]
fn bin_directories_lead_path_nearest_first_and_a_bare_project_adds_nothing() {
    // frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
    // frob:tests crates/frob-evidence/src/provider.rs::js_bin_path
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let member = root.join("apps/a");
    assert_eq!(js_bin_path(root, &member, Some("/usr/bin".into())), None);
    std::fs::create_dir_all(root.join("node_modules/.bin")).expect("root bin");
    std::fs::create_dir_all(member.join("node_modules/.bin")).expect("member bin");
    let joined = js_bin_path(root, &member, Some("/usr/bin".into())).expect("path");
    let parts: Vec<_> = std::env::split_paths(&joined).collect();
    assert_eq!(parts[0], member.join("node_modules/.bin"));
    assert_eq!(parts[1], root.join("node_modules/.bin"));
    assert_eq!(parts[2], std::path::Path::new("/usr/bin"));
}

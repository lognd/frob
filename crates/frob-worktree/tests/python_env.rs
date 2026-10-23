//! A new worktree of a uv project gets its own `.venv` instead of sharing the primary's editable install.
// frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
#![cfg(unix)]

use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

use frob_worktree::python_env::{VenvOutcome, ensure_worktree_venv};
use gob_exec::{Limits, Program, Runner};
use gob_path::Shown;

struct Case {
    _tmp: tempfile::TempDir,
    primary: PathBuf,
    checkout: PathBuf,
    uv: Program,
    log: PathBuf,
}

/// A primary checkout (optionally a uv project with a `.venv`), a bare checkout, and a fake `uv`
/// that records its arguments and environment pin, fails when `fail_offline`, and creates the venv.
#[allow(
    clippy::fn_params_excessive_bools,
    reason = "a fixture switchboard read at its few call sites"
)]
fn case(pyproject: bool, primary_venv: bool, fail_offline: bool, fail_all: bool) -> Case {
    let tmp = tempfile::tempdir().expect("tempdir");
    let primary = tmp.path().join("primary");
    let checkout = tmp.path().join("checkout");
    std::fs::create_dir_all(primary.join(".venv")).expect("primary");
    std::fs::create_dir_all(&checkout).expect("checkout");
    if primary_venv {
        std::fs::write(primary.join(".venv").join("pyvenv.cfg"), "home = x\n").expect("cfg");
    }
    if pyproject {
        std::fs::write(checkout.join("pyproject.toml"), "[project]\nname = \"p\"\n").expect("pp");
    }
    let log = tmp.path().join("uv.log");
    let script = tmp.path().join("fake-uv");
    let body = format!(
        "#!/bin/sh\necho \"$UV_PROJECT_ENVIRONMENT|$*\" >> '{log}'\n{fail_all}\n{offline}\nmkdir -p \"$UV_PROJECT_ENVIRONMENT\"\necho 'home = y' > \"$UV_PROJECT_ENVIRONMENT/pyvenv.cfg\"\n",
        log = Shown::of(&log),
        fail_all = if fail_all { "exit 1" } else { "true" },
        offline = if fail_offline {
            "case \"$*\" in *--offline*) exit 1;; esac"
        } else {
            "true"
        },
    );
    std::fs::write(&script, body).expect("script");
    std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    Case {
        _tmp: tmp,
        primary,
        checkout,
        uv: Program::Hook { path: script },
        log,
    }
}

fn run(c: &Case) -> VenvOutcome {
    ensure_worktree_venv(
        &Runner::new(Limits { jobs: 1 }),
        &c.uv,
        &c.primary,
        &c.checkout,
    )
}

fn calls(c: &Case) -> Vec<String> {
    std::fs::read_to_string(&c.log)
        .unwrap_or_default()
        .lines()
        .map(str::to_owned)
        .collect()
}

fn has_venv(dir: &Path) -> bool {
    dir.join(".venv").join("pyvenv.cfg").is_file()
}

// frob:tests crates/frob-worktree/src/python_env.rs::ensure_worktree_venv
#[test]
fn a_new_worktree_gets_its_own_venv_pinned_to_the_worktree() {
    let c = case(true, true, false, false);
    assert_eq!(run(&c), VenvOutcome::Created { offline: true });
    assert!(has_venv(&c.checkout));
    let seen = calls(&c);
    assert_eq!(seen.len(), 1, "{seen:?}");
    let pin = format!("{}|", Shown::of(&c.checkout.join(".venv")));
    assert!(seen[0].starts_with(&pin), "{seen:?}");
    assert!(seen[0].contains("sync"), "{seen:?}");
    // The primary's environment is never the target.
    assert!(
        !seen[0].starts_with(&Shown::of(&c.primary).to_string()),
        "{seen:?}"
    );
}

// frob:tests crates/frob-worktree/src/python_env.rs::ensure_worktree_venv
#[test]
fn an_offline_miss_retries_online_and_a_failing_sync_never_aborts() {
    let c = case(true, true, true, false);
    assert_eq!(run(&c), VenvOutcome::Created { offline: false });
    let seen = calls(&c);
    assert_eq!(seen.len(), 2, "{seen:?}");
    assert!(
        seen[0].contains("--offline") && !seen[1].contains("--offline"),
        "{seen:?}"
    );

    let broken = case(true, true, false, true);
    assert_eq!(run(&broken), VenvOutcome::Failed);
    assert!(!has_venv(&broken.checkout));

    let mut gone = case(true, true, false, false);
    gone.uv = Program::Hook {
        path: gone.checkout.join("no-such-uv"),
    };
    assert_eq!(run(&gone), VenvOutcome::Failed);
}

// frob:tests crates/frob-worktree/src/python_env.rs::ensure_worktree_venv
#[test]
fn only_a_uv_project_with_a_primary_venv_and_no_venv_of_its_own_is_touched() {
    let plain = case(false, true, false, false);
    assert_eq!(run(&plain), VenvOutcome::NotApplicable);
    let no_primary = case(true, false, false, false);
    assert_eq!(run(&no_primary), VenvOutcome::NotApplicable);
    let owned = case(true, true, false, false);
    std::fs::create_dir_all(owned.checkout.join(".venv")).expect("venv");
    assert_eq!(run(&owned), VenvOutcome::Present);
    for c in [&plain, &no_primary, &owned] {
        assert!(calls(c).is_empty(), "uv must not run");
    }
}

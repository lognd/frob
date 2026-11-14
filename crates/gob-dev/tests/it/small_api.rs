//! Small public entry points of gob-dev: argument resolution and fail-fast error paths.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::path::Path;
use std::process::Command;

use gob_dev::Kind;
use gob_dev::changes::{ChangesError, diff_paths};
use gob_dev::ci::RemoteOs;
#[cfg(unix)]
use gob_dev::genrun::delegate_to_docgen;
use gob_dev::genrun::generate_files;
use gob_dev::render::inline::Outcome;
use gob_dev::wheel::{HostOs, WheelError, build_from_env};
use gob_dev::wheel_smoke::smoke_from_env;

fn git(dir: &Path, args: &[&str]) {
    let status = Command::new("git")
        .current_dir(dir)
        .args(["-c", "user.name=t", "-c", "user.email=t@example.invalid"])
        .args(["-c", "commit.gpgsign=false"])
        .args(args)
        .status()
        .unwrap();
    assert!(status.success(), "git {args:?}");
}

// frob:tests crates/gob-dev/src/changes.rs::diff_paths
#[test]
fn diff_paths_lists_files_changed_since_the_base() {
    let dir = tempfile::tempdir().unwrap();
    git(dir.path(), &["init", "--quiet"]);
    std::fs::write(dir.path().join("a.txt"), "1\n").unwrap();
    git(dir.path(), &["add", "."]);
    git(dir.path(), &["commit", "--quiet", "-m", "one"]);
    std::fs::write(dir.path().join("b.txt"), "2\n").unwrap();
    git(dir.path(), &["add", "."]);
    git(dir.path(), &["commit", "--quiet", "-m", "two"]);
    assert_eq!(diff_paths(dir.path(), "HEAD~1").unwrap(), ["b.txt"]);
}

// frob:tests crates/gob-dev/src/changes.rs::diff_paths
#[test]
fn diff_paths_reports_an_unknown_base() {
    let dir = tempfile::tempdir().unwrap();
    let err = diff_paths(dir.path(), "no-such-base").unwrap_err();
    assert!(matches!(err, ChangesError::Diff { ref base, .. } if base == "no-such-base"));
}

// frob:tests crates/gob-dev/src/wheel.rs::HostOs.current
#[test]
fn the_current_host_os_matches_the_build_target() {
    let want = if cfg!(windows) {
        HostOs::Windows
    } else if cfg!(target_os = "macos") {
        HostOs::Macos
    } else {
        HostOs::Linux
    };
    assert_eq!(HostOs::current(), want);
}

// frob:tests crates/gob-dev/src/wheel.rs::build_from_env
#[test]
fn build_from_env_fails_on_a_root_without_products() {
    let root = tempfile::tempdir().unwrap();
    let err = build_from_env(root.path(), None, None, Vec::new()).unwrap_err();
    assert!(matches!(err, WheelError::Products { .. }), "{err}");
}

// frob:tests crates/gob-dev/src/wheel_smoke.rs::smoke_from_env
#[test]
fn smoke_from_env_fails_on_a_root_without_products() {
    let root = tempfile::tempdir().unwrap();
    let err = smoke_from_env(root.path(), Path::new("wheels"), None).unwrap_err();
    assert!(matches!(err, WheelError::Products { .. }), "{err}");
}

// frob:tests crates/gob-dev/src/genrun.rs::generate_files
#[test]
fn generate_files_refuses_when_frob_is_not_registered() {
    // This test binary never calls register_frob.
    let err = generate_files(Kind::Schemas, true, None).unwrap_err();
    assert!(err.starts_with("error:"), "{err}");
}

// frob:tests crates/gob-dev/src/genrun.rs::delegate_to_docgen
#[cfg(unix)]
#[test]
fn delegate_to_docgen_rejects_a_root_that_is_not_unicode() {
    use std::os::unix::ffi::OsStrExt;
    let root = Path::new(std::ffi::OsStr::from_bytes(b"bad-\xff"));
    let err = delegate_to_docgen(Kind::All, true, Some(root)).unwrap_err();
    assert_eq!(err, "error: --root is not valid unicode");
}

// frob:tests crates/gob-dev/src/ci.rs::RemoteOs.needs_term
#[test]
fn a_linux_helper_is_selected_with_the_os_needs_term() {
    assert_eq!(RemoteOs::Linux.needs_term(), "os=linux");
}

// frob:tests crates/gob-dev/src/render/inline.rs::Outcome.dir
#[test]
fn outcomes_name_their_resource_directories() {
    assert_eq!(Outcome::Ok.dir(), "ok");
    assert_eq!(Outcome::Err.dir(), "err");
}

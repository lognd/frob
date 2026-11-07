//! `frob agent heavy`: shared build lock, target dir, test-executable cleanup.
// frob:ticket 01M4P2N1TAV3MPF9G2CC274E3G

use std::path::Path;
use std::process::{Child, Stdio};
use std::time::{Duration, Instant};

use crate::common;

/// A git repo that `frob init` has set up.
fn repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let init = common::frob_command()
        .current_dir(dir.path())
        .env_remove("FROB_LOG")
        .arg("init")
        .output()
        .expect("init");
    assert_eq!(init.status.code(), Some(0));
    dir
}

/// A frob command running `agent heavy` in `cwd` with the trailing `cmd`.
fn heavy(cwd: &Path, target: &Path, cmd: &[&str]) -> std::process::Command {
    let mut c = std::process::Command::new(env!("CARGO_BIN_EXE_frob"));
    c.current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(["agent", "heavy", "--target-dir"])
        .arg(target)
        .arg("--");
    c.args(cmd);
    c
}

/// Plant an executable `name` in `<target>/debug/deps`.
fn plant(target: &Path, name: &str) -> std::path::PathBuf {
    use std::os::unix::fs::PermissionsExt;
    let deps = target.join("debug").join("deps");
    std::fs::create_dir_all(&deps).expect("deps");
    let p = deps.join(name);
    std::fs::write(&p, "bin").expect("write");
    std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    p
}

// frob:tests crates/frob/src/agent_heavy_cmd.rs::AgentHeavy
#[test]
fn heavy_locks_sets_target_runs_and_cleans_tests() {
    let dir = repo();
    let target = dir.path().join("tgt");
    let test_exe = plant(&target, "mycrate-0123456789abcdef");
    let rlib = plant(&target, "libmycrate-0123456789abcdef.rlib");
    let out = heavy(
        dir.path(),
        &target,
        &["sh", "-c", "echo $CARGO_TARGET_DIR > seen.txt"],
    )
    .output()
    .expect("run");
    assert_eq!(out.status.code(), Some(0), "{out:?}");
    let seen = std::fs::read_to_string(dir.path().join("seen.txt")).expect("seen");
    assert_eq!(
        seen.trim(),
        gob_path::Shown::with_home(&target, None).to_string()
    );
    assert!(dir.path().join(".git/frob-heavy.lock").is_file());
    assert!(!test_exe.exists(), "test executable should be cleaned");
    assert!(rlib.exists(), "non-executable artifacts stay");
}

// frob:tests crates/frob/src/agent_heavy_cmd.rs::AgentHeavy
#[test]
fn heavy_releases_lock_on_failure_and_on_kill() {
    let dir = repo();
    let target = dir.path().join("tgt");
    let fail = heavy(dir.path(), &target, &["sh", "-c", "exit 7"])
        .output()
        .expect("run");
    assert_eq!(fail.status.code(), Some(1), "{fail:?}");
    assert!(String::from_utf8_lossy(&fail.stdout).contains("\"exit_code\":7"));

    // Kill a holder mid-run (interrupt): the next invocation must not wait on it.
    let mut holder: Child = heavy(dir.path(), &target, &["sleep", "30"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("spawn");
    std::thread::sleep(Duration::from_millis(1500));
    holder.kill().expect("kill");
    holder.wait().expect("reap");
    let started = Instant::now();
    let ok = heavy(dir.path(), &target, &["true"]).output().expect("run");
    assert_eq!(ok.status.code(), Some(0), "{ok:?}");
    assert!(started.elapsed() < Duration::from_secs(20));
}

// frob:tests crates/frob/src/agent_heavy_cmd.rs::AgentHeavy
#[test]
fn concurrent_heavy_invocations_serialize() {
    let dir = repo();
    let target = dir.path().join("tgt");
    let log = dir.path().join("log.txt");
    let script = format!(
        "echo start >> {l}; sleep 1; echo end >> {l}",
        l = gob_path::Shown::with_home(&log, None)
    );
    let mut kids: Vec<Child> = (0..3)
        .map(|_| {
            heavy(dir.path(), &target, &["sh", "-c", &script])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("spawn")
        })
        .collect();
    for k in &mut kids {
        assert!(k.wait().expect("wait").success());
    }
    let lines: Vec<String> = std::fs::read_to_string(&log)
        .expect("log")
        .lines()
        .map(str::to_owned)
        .collect();
    let want: Vec<&str> = ["start", "end"].repeat(3);
    assert_eq!(lines, want, "runs interleaved: {lines:?}");
}

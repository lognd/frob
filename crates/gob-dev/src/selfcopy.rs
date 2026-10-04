//! Windows self-copy re-exec: a running `gob-dev.exe` cannot be replaced, so before a task that
//! rebuilds the workspace the runner copies itself to a temp file and runs from there.
// frob:ticket 01M424BWCSSMVHA9X5DJ9BCSXD

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};

/// Environment variable set on the re-executed copy so it does not copy itself again.
pub const MARKER: &str = "GOB_DEV_SELF_COPY";

/// Directory name, under the system temp dir, that holds the copies.
const DIR_NAME: &str = "gob-dev-selfcopy";

/// Wall-clock limit for the copied runner (a full `cargo dev ci` with cold caches).
const RUN_TIMEOUT: Duration = Duration::from_hours(6);

/// What the runner does before executing its task.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Plan {
    /// Run the task from the current executable.
    InPlace,
    /// Copy the executable to a temp path and run the task from the copy.
    ReExec,
}

/// Whether to re-exec: only on Windows, only for a task that rebuilds the workspace, never twice.
#[must_use]
pub fn plan(windows: bool, marker_set: bool, rebuilds_workspace: bool) -> Plan {
    if windows && rebuilds_workspace && !marker_set {
        Plan::ReExec
    } else {
        Plan::InPlace
    }
}

/// Why the self-copy re-exec failed.
#[derive(Debug, thiserror::Error)]
pub enum SelfCopyError {
    /// The running executable path or the copy could not be set up.
    #[error("self-copy {what}: {source}")]
    Io {
        /// The step that failed.
        what: &'static str,
        /// The underlying error.
        #[source]
        source: std::io::Error,
    },
    /// The copy could not be spawned or supervised.
    #[error("self-copy spawn: {0}")]
    Spawn(#[from] gob_exec::ExecError),
}

/// Unique file name for a copy made by process `pid` at `nanos` since the epoch.
#[must_use]
pub fn copy_name(pid: u32, nanos: u128, extension: Option<&str>) -> String {
    match extension {
        Some(ext) => format!("gob-dev-{pid}-{nanos}.{ext}"),
        None => format!("gob-dev-{pid}-{nanos}"),
    }
}

/// Delete copies left in `dir` by crashed runs; a copy still running cannot be deleted and stays.
pub fn clean_stale(dir: &Path) -> usize {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return 0;
    };
    let mut removed = 0;
    for entry in entries.flatten() {
        match std::fs::remove_file(entry.path()) {
            Ok(()) => {
                removed += 1;
                tracing::info!(path = %entry.path().display(), "removed stale self-copy");
            }
            Err(e) => {
                tracing::debug!(path = %entry.path().display(), error = %e, "stale self-copy kept");
            }
        }
    }
    removed
}

/// Copy the running executable, run it with `args` and the marker, relay its exit code, and
/// delete the copy.
///
/// # Errors
/// [`SelfCopyError::Io`] when the copy cannot be made, [`SelfCopyError::Spawn`] when it cannot run.
pub fn reexec(args: &[String]) -> Result<i32, SelfCopyError> {
    let io = |what| move |source| SelfCopyError::Io { what, source };
    let exe = std::env::current_exe().map_err(io("current_exe"))?;
    let dir: PathBuf = std::env::temp_dir().join(DIR_NAME);
    std::fs::create_dir_all(&dir).map_err(io("create temp dir"))?;
    clean_stale(&dir);
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let ext = exe.extension().and_then(|e| e.to_str());
    let copy = dir.join(copy_name(std::process::id(), nanos, ext));
    std::fs::copy(&exe, &copy).map_err(io("copy executable"))?;
    tracing::info!(from = %exe.display(), to = %copy.display(), "re-executing from a self-copy");
    let spec = Spec {
        program: Program::Hook { path: copy.clone() },
        args: args.to_vec(),
        cwd: None,
        env: vec![(MARKER.to_owned(), "1".to_owned())],
        timeout: RUN_TIMEOUT,
        capture: false,
    };
    let result = Runner::new(Limits { jobs: 1 }).run(&spec);
    match std::fs::remove_file(&copy) {
        Ok(()) => tracing::debug!(path = %copy.display(), "self-copy removed"),
        Err(e) => {
            tracing::warn!(path = %copy.display(), error = %e, "self-copy left for the next run");
        }
    }
    let out = result?;
    Ok(match out.status {
        Outcome::Exited(code) => code,
        Outcome::Signaled | Outcome::TimedOut => 1,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/selfcopy.rs::plan
    #[test]
    fn only_windows_rebuilding_tasks_without_marker_reexec() {
        assert_eq!(plan(true, false, true), Plan::ReExec);
        assert_eq!(
            plan(false, false, true),
            Plan::InPlace,
            "unix needs nothing"
        );
        assert_eq!(
            plan(true, true, true),
            Plan::InPlace,
            "the copy never copies itself"
        );
        assert_eq!(
            plan(true, false, false),
            Plan::InPlace,
            "gen does not rebuild"
        );
    }

    // frob:tests crates/gob-dev/src/selfcopy.rs::copy_name
    #[test]
    fn copy_names_are_unique_and_keep_the_extension() {
        assert_eq!(copy_name(7, 9, Some("exe")), "gob-dev-7-9.exe");
        assert_ne!(copy_name(7, 9, None), copy_name(7, 10, None));
    }

    // frob:tests crates/gob-dev/src/selfcopy.rs::clean_stale
    #[test]
    fn stale_copies_are_removed() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("gob-dev-1-1.exe"), b"x").unwrap();
        assert_eq!(clean_stale(tmp.path()), 1);
        assert_eq!(std::fs::read_dir(tmp.path()).unwrap().count(), 0);
        assert_eq!(clean_stale(&tmp.path().join("absent")), 0);
    }

    // frob:tests crates/gob-dev/src/selfcopy.rs::reexec
    #[test]
    #[cfg(unix)]
    fn reexec_relays_the_exit_code_and_deletes_the_copy() {
        // The test binary re-executes itself filtered to a no-op test; exit 0 is relayed.
        let args = vec!["--exact".to_owned(), "selfcopy::tests::noop".to_owned()];
        assert_eq!(reexec(&args).unwrap(), 0);
        let left =
            std::fs::read_dir(std::env::temp_dir().join(DIR_NAME)).map_or(0, Iterator::count);
        assert_eq!(left, 0, "the copy is deleted afterwards");
        let bad = vec!["--no-such-flag".to_owned()];
        assert_ne!(reexec(&bad).unwrap(), 0);
    }

    #[test]
    fn noop() {}
}

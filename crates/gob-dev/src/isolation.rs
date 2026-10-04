//! Windows cannot replace a running executable, so a task that rebuilds the workspace must not
//! run from `target/debug/gob-dev.exe`; `cargo dev-isolated` runs it from `target/dev-tool`.
// frob:ticket 01M42C6MJZRH5NZGARX3YYNHAC

use std::path::Path;

/// The target dir (relative to the workspace root) the `dev-isolated` alias builds gob-dev into.
pub const ISOLATED_DIR: &str = "target/dev-tool";

/// A rebuilding task was started from the shared target dir on Windows.
#[derive(Debug, thiserror::Error)]
#[error(
    "gob-dev is running from {exe}, which this task's build would replace, and Windows locks a \
     running executable; run it as `cargo dev-isolated <same arguments>` instead"
)]
pub struct SharedTargetDir {
    /// The running executable.
    pub exe: String,
}

/// Fail fast on Windows when `exe` lives in the workspace target dir outside `target/dev-tool`.
///
/// # Errors
/// [`SharedTargetDir`] when `windows`, `rebuilds` and `exe` is under `<root>/target` but not
/// under `<root>/target/dev-tool`.
pub fn check(
    windows: bool,
    rebuilds: bool,
    exe: &Path,
    root: &Path,
) -> Result<(), SharedTargetDir> {
    let shared = exe.starts_with(root.join("target")) && !exe.starts_with(root.join(ISOLATED_DIR));
    tracing::debug!(windows, rebuilds, shared, exe = %exe.display(), "isolation check");
    if windows && rebuilds && shared {
        return Err(SharedTargetDir {
            exe: exe.display().to_string(),
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/isolation.rs::check
    #[test]
    fn windows_rebuild_from_the_shared_target_dir_names_the_alias() {
        let root = Path::new("/w");
        let err = check(true, true, Path::new("/w/target/debug/gob-dev.exe"), root).unwrap_err();
        assert!(err.to_string().contains("cargo dev-isolated"), "{err}");
    }

    // frob:tests crates/gob-dev/src/isolation.rs::check
    #[test]
    fn isolated_non_windows_and_non_rebuilding_runs_pass() {
        let root = Path::new("/w");
        let shared = Path::new("/w/target/debug/gob-dev.exe");
        assert!(
            check(
                true,
                true,
                Path::new("/w/target/dev-tool/debug/gob-dev.exe"),
                root
            )
            .is_ok()
        );
        assert!(check(false, true, shared, root).is_ok());
        assert!(check(true, false, shared, root).is_ok());
    }
}

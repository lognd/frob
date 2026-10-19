//! `cargo dev test-size`: sum the linked test executables of a build against a disk budget.
//!
//! A full workspace test build links one executable per integration-test file; this measures the
//! total so the "under 3 GB" budget of ~ZM1HA1J is a number a script reports, not a guess.

use std::path::{Path, PathBuf};

// frob:ticket 01M4MGEZBQ9DD7BKKZ8ZM1HA1J

/// Default budget for the executables of a full workspace test build, in bytes (3 GB).
pub const DEFAULT_BUDGET_BYTES: u64 = 3_000_000_000;

/// Why the executables could not be summed.
#[derive(Debug, thiserror::Error)]
pub enum TestSizeError {
    /// The deps directory could not be read.
    #[error("read {path}: {source}")]
    Io {
        /// The directory or file involved.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
}

/// Count and total size of the test executables found.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Measured {
    /// Executables found.
    pub count: usize,
    /// Their summed size in bytes.
    pub bytes: u64,
}

/// Whether `path` names a linked executable cargo wrote to `deps/` (hash-suffixed, no library extension).
fn is_executable(path: &Path, meta: &std::fs::Metadata) -> bool {
    if !meta.is_file() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        path.extension().is_none() && meta.permissions().mode() & 0o111 != 0
    }
    #[cfg(not(unix))]
    {
        path.extension().is_some_and(|e| e == "exe")
    }
}

/// Sum the executables directly inside `deps` (the `target/<profile>/deps` directory).
///
/// # Errors
/// [`TestSizeError::Io`] when the directory or an entry cannot be read.
pub fn measure(deps: &Path) -> Result<Measured, TestSizeError> {
    let io = |path: &Path| {
        let path = path.to_path_buf();
        move |source| TestSizeError::Io { path, source }
    };
    let mut total = Measured::default();
    for entry in std::fs::read_dir(deps).map_err(io(deps))? {
        let entry = entry.map_err(io(deps))?;
        let path = entry.path();
        let meta = entry.metadata().map_err(io(&path))?;
        if is_executable(&path, &meta) {
            total.count += 1;
            total.bytes += meta.len();
        }
    }
    tracing::debug!(dir = %deps.display(), count = total.count, bytes = total.bytes, "measured test executables");
    Ok(total)
}

#[expect(clippy::cast_precision_loss, reason = "a human-readable GB figure")]
/// One summary line and whether the total is within `budget` bytes.
#[must_use]
pub fn summary(measured: Measured, budget: u64) -> (String, bool) {
    let ok = measured.bytes <= budget;
    let line = format!(
        "{} test executables, {:.2} GB (budget {:.2} GB): {}",
        measured.count,
        measured.bytes as f64 / 1e9,
        budget as f64 / 1e9,
        if ok { "ok" } else { "OVER BUDGET" }
    );
    (line, ok)
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt as _;

    fn write(dir: &Path, name: &str, len: usize, mode: u32) {
        let p = dir.join(name);
        std::fs::write(&p, vec![0u8; len]).unwrap();
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(mode)).unwrap();
    }

    // frob:tests crates/gob-dev/src/test_size.rs::measure
    #[test]
    fn measure_sums_only_executables() {
        let d = tempfile::tempdir().unwrap();
        write(d.path(), "a-1", 100, 0o755);
        write(d.path(), "b-2", 50, 0o755);
        write(d.path(), "liba-1.rlib", 999, 0o644);
        write(d.path(), "a-1.d", 999, 0o755);
        write(d.path(), "data", 999, 0o644);
        let m = measure(d.path()).unwrap();
        assert_eq!(
            m,
            Measured {
                count: 2,
                bytes: 150
            }
        );
    }

    // frob:tests crates/gob-dev/src/test_size.rs::measure
    #[test]
    fn measure_reports_a_missing_directory() {
        assert!(measure(Path::new("/nonexistent-deps-dir")).is_err());
    }

    // frob:tests crates/gob-dev/src/test_size.rs::summary
    #[test]
    fn summary_flags_over_budget() {
        let m = Measured {
            count: 3,
            bytes: 4_000_000_000,
        };
        assert!(!summary(m, DEFAULT_BUDGET_BYTES).1);
        assert!(summary(m, 5_000_000_000).1);
    }
}

//! `cargo dev test-size`: sum the test executables a workspace test build left on disk, so the
//! cost of one-binary-per-test-file layouts stays visible and bounded (~ZM1HA1J).
// frob:ticket 01M4MGEZBQ9DD7BKKZ8ZM1HA1J

use std::path::{Path, PathBuf};

/// The largest total, in bytes, of test executables a full workspace test build may leave (3 GB).
pub const DEFAULT_MAX_BYTES: u64 = 3_000_000_000;

/// What the scan of one `deps` directory found.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Report {
    /// Number of executables counted.
    pub files: usize,
    /// Their total size in bytes.
    pub bytes: u64,
}

/// A `deps` directory could not be read.
#[derive(Debug, thiserror::Error)]
#[error("cannot read {path}: {source}")]
pub struct ScanError {
    /// The directory or entry that failed.
    pub path: PathBuf,
    /// The underlying I/O error.
    #[source]
    pub source: std::io::Error,
}

/// Whether `name` (with its file mode) is a linked executable rather than an rlib, `.d` or dylib.
fn is_executable(name: &str, path: &Path) -> bool {
    if name.starts_with("build_script_") || name.starts_with("build-script-") {
        return false;
    }
    let ext = path.extension().and_then(|e| e.to_str());
    if cfg!(windows) {
        return ext == Some("exe");
    }
    if ext.is_some() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt as _;
        path.metadata()
            .is_ok_and(|m| m.is_file() && m.permissions().mode() & 0o111 != 0)
    }
    #[cfg(not(unix))]
    false
}

/// Sum the executables directly inside `deps` (`target/<profile>/deps`).
///
/// # Errors
/// [`ScanError`] when the directory or one of its entries cannot be read.
pub fn measure(deps: &Path) -> Result<Report, ScanError> {
    let fail = |path: &Path, source| ScanError {
        path: path.to_path_buf(),
        source,
    };
    let mut report = Report { files: 0, bytes: 0 };
    for entry in std::fs::read_dir(deps).map_err(|e| fail(deps, e))? {
        let entry = entry.map_err(|e| fail(deps, e))?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().into_owned();
        if is_executable(&name, &path) {
            let len = entry.metadata().map_err(|e| fail(&path, e))?.len();
            tracing::trace!(%name, len, "counted test executable");
            report.files += 1;
            report.bytes += len;
        }
    }
    tracing::debug!(files = report.files, bytes = report.bytes, dir = %deps.display(), "measured");
    Ok(report)
}

/// One human line for a report and the budget it is judged against.
pub fn summary(report: &Report, max_bytes: u64) -> String {
    #[allow(
        clippy::cast_precision_loss,
        reason = "a size line, not an accounting figure"
    )]
    let gb = |b: u64| b as f64 / 1e9;
    let verdict = if report.bytes <= max_bytes {
        "ok"
    } else {
        "OVER BUDGET"
    };
    format!(
        "{} test executables, {:.2} GB (budget {:.2} GB): {verdict}",
        report.files,
        gb(report.bytes),
        gb(max_bytes)
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/test_size.rs::measure
    #[cfg(unix)]
    #[test]
    fn only_executables_without_an_extension_are_summed() {
        use std::os::unix::fs::PermissionsExt as _;
        let dir = tempfile::tempdir().unwrap();
        let exe = dir.path().join("main-0123abcd");
        std::fs::write(&exe, vec![0u8; 100]).unwrap();
        std::fs::set_permissions(&exe, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::write(dir.path().join("libx-01.rlib"), vec![0u8; 500]).unwrap();
        std::fs::write(dir.path().join("main-0123abcd.d"), "deps").unwrap();
        std::fs::write(dir.path().join("plain-file"), "not executable").unwrap();
        let build = dir.path().join("build_script_build-ff");
        std::fs::write(&build, vec![0u8; 50]).unwrap();
        std::fs::set_permissions(&build, std::fs::Permissions::from_mode(0o755)).unwrap();
        assert_eq!(
            measure(dir.path()).unwrap(),
            Report {
                files: 1,
                bytes: 100
            }
        );
    }

    // frob:tests crates/gob-dev/src/test_size.rs::measure
    #[test]
    fn a_missing_directory_is_an_error() {
        assert!(measure(Path::new("/nonexistent/deps")).is_err());
    }

    // frob:tests crates/gob-dev/src/test_size.rs::summary
    #[test]
    fn summary_flags_a_report_over_budget() {
        let r = Report {
            files: 2,
            bytes: 4_000_000_000,
        };
        assert!(summary(&r, DEFAULT_MAX_BYTES).ends_with("OVER BUDGET"));
        assert!(summary(&r, 5_000_000_000).ends_with("ok"));
    }
}

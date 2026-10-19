//! Test prerequisites: a missing host program is a named skip, never a confusing failure.

/// Whether a POSIX `sh` is on `PATH` (absent on a Windows host without Git for Windows' `usr\bin`).
pub fn sh_available() -> bool {
    which::which("sh").is_ok()
}

/// Gate a shell-specific test: false, with the named prerequisite logged, when `sh` is missing.
///
/// Use as `if !gob_exec::require_sh("my_test") { return; }`; the product never needs `sh`.
pub fn require_sh(test: &str) -> bool {
    let present = sh_available();
    if !present {
        tracing::warn!(
            test,
            prerequisite = "sh",
            "SKIPPED: requires a POSIX sh on PATH"
        );
        eprintln!("SKIPPED {test}: requires prerequisite `sh` on PATH");
    }
    present
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-exec/src/prereq.rs::require_sh
    #[test]
    fn require_sh_agrees_with_sh_available() {
        assert_eq!(
            require_sh("require_sh_agrees_with_sh_available"),
            sh_available()
        );
    }
}

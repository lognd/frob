//! Finding the project's own `tailwindcss` install and reading its version.
//!
//! The search walks `node_modules` from the project root upward, nearest first, like Node's own
//! `require` resolution, so a hoisted monorepo install resolves as it would in the project's
//! node process. A global install is never used.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use std::path::{Path, PathBuf};

use super::model::TailwindVersion;

/// The nearest `node_modules/tailwindcss` directory (one holding a `package.json`) at or above
/// `project_root`, or `None`.
pub fn find_tailwindcss_dir(project_root: &Path) -> Option<PathBuf> {
    let start = gob_exec::canonical(project_root).unwrap_or_else(|_| project_root.to_path_buf());
    for dir in start.ancestors() {
        let candidate = dir.join("node_modules").join("tailwindcss");
        if candidate.join("package.json").is_file() {
            tracing::debug!(dir = %candidate.display(), "tailwindcss resolved");
            return Some(candidate);
        }
    }
    tracing::debug!(root = %project_root.display(), "no tailwindcss found walking up");
    None
}

/// The `version` string of `<tailwindcss_dir>/package.json`.
///
/// # Errors
///
/// A description when the file is missing, not JSON, or has no string `version`.
pub fn read_version(tailwindcss_dir: &Path) -> Result<String, String> {
    let path = tailwindcss_dir.join("package.json");
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    let json: serde_json::Value =
        serde_json::from_str(&text).map_err(|e| format!("{} is not JSON: {e}", path.display()))?;
    json.get("version")
        .and_then(serde_json::Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| format!("{} has no `version` field", path.display()))
}

/// The leading integer of a semver string (`4.3.3` is 4), or `None` when it is not digits.
pub fn major_of(version: &str) -> Option<u64> {
    version.split('.').next()?.parse().ok()
}

/// The supported [`TailwindVersion`] of a major number.
pub fn version_of_major(major: u64) -> Option<TailwindVersion> {
    match major {
        3 => Some(TailwindVersion::V3),
        4 => Some(TailwindVersion::V4),
        _ => None,
    }
}

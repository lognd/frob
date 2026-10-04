//! The throttle stamp and last-pass record under `<git common dir>/frob/gc.json`.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::{Path, PathBuf};

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Disk used by one category of collectable data.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Usage {
    /// Category: `build`, `worktrees`, `caches`, `artifacts`, `land-base`.
    pub category: String,
    /// Bytes in use after the pass.
    pub bytes: u64,
}

/// What the last pass did, persisted so the next verb can throttle and `doctor` can report.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Stamp {
    /// Unix seconds when the last pass finished (0 when none ran).
    pub last_run_unix: i64,
    /// Bytes the last pass reclaimed.
    pub last_reclaimed_bytes: u64,
    /// Bytes reclaimed over all passes.
    pub total_reclaimed_bytes: u64,
    /// Number of passes so far.
    pub passes: u64,
    /// Usage per category after the last pass.
    pub usage: Vec<Usage>,
}

impl Stamp {
    /// True when no pass ran within `interval_secs` before `now_unix`.
    pub fn due(&self, now_unix: i64, interval_secs: u64) -> bool {
        let interval = i64::try_from(interval_secs).unwrap_or(i64::MAX);
        self.last_run_unix == 0 || now_unix.saturating_sub(self.last_run_unix) >= interval
    }
}

/// Where the stamp of the repository with this common dir lives.
pub fn path(common_dir: &Path) -> PathBuf {
    common_dir.join("frob").join("gc.json")
}

/// Read the stamp; a missing or unreadable one is the empty stamp (so a pass is due).
pub fn load(common_dir: &Path) -> Stamp {
    let p = path(common_dir);
    match std::fs::read_to_string(&p) {
        Ok(text) => serde_json::from_str(&text).unwrap_or_else(|e| {
            tracing::warn!(path = %p.display(), error = %e, "gc stamp unreadable; treating as absent");
            Stamp::default()
        }),
        Err(_) => Stamp::default(),
    }
}

/// Write the stamp atomically (temporary file, then rename).
///
/// # Errors
///
/// The OS error text when the directory or file cannot be written.
pub fn save(common_dir: &Path, stamp: &Stamp) -> Result<(), String> {
    let p = path(common_dir);
    let dir = p.parent().unwrap_or(common_dir);
    std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let tmp = dir.join(format!("gc.json.{}.tmp", std::process::id()));
    let json = serde_json::to_string_pretty(stamp).map_err(|e| e.to_string())?;
    std::fs::write(&tmp, json).map_err(|e| format!("{}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, &p).map_err(|e| format!("{}: {e}", p.display()))?;
    tracing::debug!(path = %p.display(), "gc stamp saved");
    Ok(())
}

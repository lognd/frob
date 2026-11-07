//! Token-savings telemetry: each agent guard appends a `kind=guard` row to `.frob/telemetry.jsonl`.
//!
//! A row says which guard fired and how many bytes it kept out of the agent's context (or off the
//! disk). The `basis` field says how honest the number is: `file_size` and `freed_bytes` are measured,
//! `unmeasured` means the guard acted on output it never saw (the byte count is then 0). Writing is
//! best effort: a failure is logged and never changes what the guard does.

// frob:ticket 01M4P2N20QFNBWY0GMKG0YE19W

use std::io::Write;
use std::path::Path;

use gob_time::Clock;
use serde_json::json;

/// File name of the shared telemetry log inside the state directory.
const FILE: &str = "telemetry.jsonl";

/// The state directory that holds the log, relative to the repository root.
const STATE_DIR: &str = ".frob";

/// How a guard's byte count was obtained.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Basis {
    /// The size of the file a denied whole-file read would have loaded.
    FileSize,
    /// The bytes of files deleted from disk.
    FreedBytes,
    /// The guard acted on output it never saw, so no byte count exists.
    Unmeasured,
}

impl Basis {
    /// The stable text written to the log.
    fn as_str(self) -> &'static str {
        match self {
            Self::FileSize => "file_size",
            Self::FreedBytes => "freed_bytes",
            Self::Unmeasured => "unmeasured",
        }
    }
}

/// The JSON line for one guard firing (no paths, no command text).
#[must_use]
pub fn line(at: &str, guard: &str, bytes_avoided: u64, basis: Basis) -> String {
    json!({
        "kind": "guard",
        "at": at,
        "guard": guard,
        "bytes_avoided": bytes_avoided,
        "basis": basis.as_str(),
    })
    .to_string()
}

/// Append `text` (one line) to the log under `root`'s state directory.
fn append(root: &Path, text: &str) -> std::io::Result<()> {
    let dir = root.join(STATE_DIR);
    std::fs::create_dir_all(&dir)?;
    std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join(FILE))
        .and_then(|mut f| f.write_all(text.as_bytes()))
}

/// Append one guard row under `root`; failures are logged, never raised.
pub fn record(root: &Path, guard: &str, bytes_avoided: u64, basis: Basis) {
    let at = gob_time::SystemClock.now().precise();
    let mut text = line(&at, guard, bytes_avoided, basis);
    text.push('\n');
    match append(root, &text) {
        Ok(()) => tracing::debug!(guard, bytes_avoided, "guard telemetry appended"),
        Err(err) => tracing::warn!(guard, %err, "guard telemetry not written"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/agent/telemetry.rs::record
    #[test]
    fn guard_row_lands_in_frob_telemetry_jsonl() {
        let dir = tempfile::tempdir().expect("tempdir");
        record(dir.path(), "pre-read", 4096, Basis::FileSize);
        let text = std::fs::read_to_string(dir.path().join(".frob/telemetry.jsonl")).expect("log");
        let row: serde_json::Value = serde_json::from_str(text.trim()).expect("json");
        assert_eq!(row["guard"], "pre-read");
        assert_eq!(row["bytes_avoided"], 4096);
        assert_eq!(row["basis"], "file_size");
        assert_eq!(row["kind"], "guard");
    }
}

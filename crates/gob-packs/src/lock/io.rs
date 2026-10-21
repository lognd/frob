//! Reading and writing the lock file as TOML.

use std::path::Path;

use tracing::{info, warn};

use super::Lock;
use crate::{MAX_MANIFEST_BYTES, PackError};

const HEADER: &str = "# pack lock -- written by an explicit lock or update; do not edit\n";

/// Reads the lock at `path`, bounded by the manifest size limit.
///
/// # Errors
/// PACK005 when the file is unreadable, oversized, not UTF-8 or not a valid lock.
pub fn read(path: &Path) -> Result<Lock, PackError> {
    let file = gob_path::Shown::with_home(path, None).to_string();
    let bad = |reason: String| {
        let e = PackError::malformed(&file, "<file>", reason);
        warn!(error = %e, "pack lock refused");
        e
    };
    let bytes = std::fs::read(path).map_err(|e| bad(format!("cannot read: {e}")))?;
    if bytes.len() > MAX_MANIFEST_BYTES * 16 {
        return Err(bad("lock exceeds the size bound".to_owned()));
    }
    let text = String::from_utf8(bytes).map_err(|_| bad("must be UTF-8".to_owned()))?;
    let lock: Lock = toml::from_str(&text).map_err(|e| bad(e.to_string()))?;
    info!(file = %file, packs = lock.pack.len(), "pack lock read");
    Ok(lock)
}

/// Writes `lock` to `path` (the only writer; callers invoke it on an explicit update).
///
/// # Errors
/// PACK005 when serialization or the write fails.
pub fn write(path: &Path, lock: &Lock) -> Result<(), PackError> {
    let file = gob_path::Shown::with_home(path, None).to_string();
    let body = toml::to_string(lock)
        .map_err(|e| PackError::malformed(&file, "<file>", format!("cannot serialize: {e}")))?;
    std::fs::write(path, format!("{HEADER}{body}"))
        .map_err(|e| PackError::malformed(&file, "<file>", format!("cannot write: {e}")))?;
    info!(file = %file, packs = lock.pack.len(), "pack lock written");
    Ok(())
}

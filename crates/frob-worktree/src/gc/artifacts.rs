//! Evidence blobs under `<git common dir>/frob/artifacts`: old and unreferenced ones go.
//!
//! Blob files are named by their 64-hex blake3 digest. A blob is removed when it is
//! older than the retention and no open ticket mentions its digest; anything else in
//! the directory (temporary files, unknown names) is left alone.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

/// One blob eligible for removal.
#[derive(Debug, Clone)]
pub struct Blob {
    /// The blob file.
    pub path: PathBuf,
    /// Its size.
    pub bytes: u64,
}

/// The blob directory of a repository with this common dir.
pub fn dir(common_dir: &Path) -> PathBuf {
    common_dir.join("frob").join("artifacts")
}

/// True for a 64-character lowercase hex name.
fn is_digest(name: &str) -> bool {
    name.len() == 64
        && name
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// Every 64-hex token in `text`, the digests a ticket's events mention.
pub fn digests_in(text: &str, into: &mut BTreeSet<String>) {
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i].is_ascii_hexdigit() {
            let start = i;
            while i < bytes.len() && bytes[i].is_ascii_hexdigit() {
                i += 1;
            }
            if i - start == 64 {
                into.insert(text[start..i].to_ascii_lowercase());
            }
        } else {
            i += 1;
        }
    }
}

/// Bytes held by every digest-named blob, referenced or not.
pub fn usage(common_dir: &Path) -> u64 {
    list(common_dir).iter().map(|(_, b, _)| *b).sum()
}

fn list(common_dir: &Path) -> Vec<(PathBuf, u64, SystemTime)> {
    let Ok(rd) = std::fs::read_dir(dir(common_dir)) else {
        return Vec::new();
    };
    rd.filter_map(Result::ok)
        .filter(|e| is_digest(&e.file_name().to_string_lossy()))
        .filter_map(|e| {
            let m = e.metadata().ok().filter(std::fs::Metadata::is_file)?;
            Some((e.path(), m.len(), m.modified().ok()?))
        })
        .collect()
}

/// The blobs older than `retention` at `now` whose digest is not in `referenced`.
pub fn plan(
    common_dir: &Path,
    referenced: &BTreeSet<String>,
    retention: Duration,
    now: SystemTime,
) -> Vec<Blob> {
    list(common_dir)
        .into_iter()
        .filter(|(p, _, m)| {
            let name = p
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            now.duration_since(*m).unwrap_or_default() > retention && !referenced.contains(&name)
        })
        .map(|(path, bytes, _)| Blob { path, bytes })
        .collect()
}

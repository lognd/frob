//! The DUP001 clone index: per-file window hashes, content addressed, shared by every worktree.
//!
//! The index lives under the git common directory (`<common>/frob/dup-index`), so the primary
//! checkout and every linked worktree read and extend one store. An entry is keyed by the digest
//! of the file text plus the window size, the language style and [`FORMAT`], so a changed file gets
//! a new entry and an unchanged file is never hashed again: the index is built once and updated
//! only for changed files.
//!
//! The store fails closed. An existing directory without a valid manifest, an entry that is
//! truncated or fails its checksum, or a store that cannot be written is an [`IndexError`], which
//! the pass reports as `DUP003` with a rebuild hint instead of silently recomputing and hiding the
//! damage. The only silent build is the first one, when the directory does not exist yet.

// frob:ticket 01M4P0SXCZQTRS8W10VXJ1W4P0

use std::fmt;
use std::path::{Path, PathBuf};

/// Bump when the lexer, the window hash or the entry layout changes; old entries then miss.
const FORMAT: u32 = 1;
/// The manifest text that marks a directory as a DUP index of this [`FORMAT`].
const MANIFEST: &str = "frob-dup-index 1\n";
/// Manifest file name inside the index directory.
const MANIFEST_FILE: &str = "MANIFEST";
/// Magic bytes opening every entry.
const MAGIC: &[u8; 6] = b"FDUP1\0";
/// Rungs hashed per window (R1, R2, R3).
pub(crate) const RUNGS: usize = 3;

/// Why the index could not be used; each variant carries the path involved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum IndexError {
    /// The directory exists but its manifest is absent or foreign.
    Missing(PathBuf),
    /// An entry or the manifest is damaged.
    Corrupt(PathBuf, String),
    /// The store could not be created or written.
    Io(PathBuf, String),
}

impl fmt::Display for IndexError {
    /// The message, always ending with the rebuild hint.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let (what, path) = match self {
            IndexError::Missing(p) => ("clone index manifest is missing".to_owned(), p),
            IndexError::Corrupt(p, why) => (format!("clone index is corrupt ({why})"), p),
            IndexError::Io(p, why) => (format!("clone index is unusable ({why})"), p),
        };
        write!(
            f,
            "{what}: {}; delete that directory to rebuild it on the next check",
            gob_path::Shown::of(path)
        )
    }
}

/// The window hashes of one file: `keys[rung][position]`, one list per rung.
pub(crate) type Windows = [Vec<u128>; RUNGS];

/// An opened clone index directory.
#[derive(Debug, Clone)]
pub(crate) struct DupIndex {
    /// The index directory.
    dir: PathBuf,
}

/// The index directory for the checkout at `root`: under the git common dir, `None` outside git.
pub(crate) fn dir_for(root: &Path) -> Option<PathBuf> {
    gob_fs::git_common_dir(root).map(|c| c.join("frob").join("dup-index"))
}

impl DupIndex {
    /// Open (creating on first use) the index at `dir`, failing closed on a damaged store.
    pub(crate) fn open(dir: &Path) -> Result<Self, IndexError> {
        let manifest = dir.join(MANIFEST_FILE);
        if dir.exists() {
            return match std::fs::read_to_string(&manifest) {
                Ok(text) if text == MANIFEST => Ok(Self {
                    dir: dir.to_owned(),
                }),
                Ok(_) => Err(IndexError::Corrupt(
                    dir.to_owned(),
                    "foreign manifest".into(),
                )),
                Err(_) => Err(IndexError::Missing(dir.to_owned())),
            };
        }
        tracing::info!(dir = %gob_path::Shown::of(dir), "building the DUP clone index");
        let io = |e: std::io::Error| IndexError::Io(dir.to_owned(), e.to_string());
        std::fs::create_dir_all(dir).map_err(io)?;
        gob_fs::write_atomic(&manifest, MANIFEST.as_bytes()).map_err(io)?;
        Ok(Self {
            dir: dir.to_owned(),
        })
    }

    /// The windows of `text` (`m` tokens, `hash_style` language), from the store or `compute`d and stored.
    pub(crate) fn windows(
        &self,
        text: &str,
        hash_style: bool,
        m: usize,
        compute: impl FnOnce() -> Windows,
    ) -> Result<Windows, IndexError> {
        let path = self
            .dir
            .join(format!("{}.win", entry_key(text, hash_style, m)));
        match std::fs::read(&path) {
            Ok(bytes) => {
                tracing::trace!(path = %gob_path::Shown::of(&path), "DUP index hit");
                decode(&bytes).map_err(|why| IndexError::Corrupt(path, why))
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                let windows = compute();
                tracing::debug!(path = %gob_path::Shown::of(&path), "DUP index miss; storing");
                gob_fs::write_atomic(&path, &encode(&windows))
                    .map_err(|e| IndexError::Io(path, e.to_string()))?;
                Ok(windows)
            }
            Err(e) => Err(IndexError::Io(path, e.to_string())),
        }
    }
}

/// The hex digest naming the entry for this text and parameters.
fn entry_key(text: &str, hash_style: bool, m: usize) -> String {
    let mut h = blake3::Hasher::new();
    h.update(&FORMAT.to_le_bytes());
    h.update(&(m as u64).to_le_bytes());
    h.update(&[u8::from(hash_style)]);
    h.update(text.as_bytes());
    h.finalize().to_hex().to_string()
}

/// The entry bytes: magic, window count, every rung's hashes, then a checksum of all before it.
fn encode(w: &Windows) -> Vec<u8> {
    let n = w[0].len();
    let mut out = Vec::with_capacity(MAGIC.len() + 8 + RUNGS * n * 16 + 32);
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&(n as u64).to_le_bytes());
    for rung in w {
        for k in rung {
            out.extend_from_slice(&k.to_le_bytes());
        }
    }
    let sum = blake3::hash(&out);
    out.extend_from_slice(sum.as_bytes());
    out
}

/// Decode entry bytes, naming what is wrong when they are damaged.
fn decode(bytes: &[u8]) -> Result<Windows, String> {
    let head = MAGIC.len() + 8;
    if bytes.len() < head + 32 || &bytes[..MAGIC.len()] != MAGIC {
        return Err("bad header".into());
    }
    let (body, sum) = bytes.split_at(bytes.len() - 32);
    if blake3::hash(body).as_bytes() != sum {
        return Err("checksum mismatch".into());
    }
    let n = usize::try_from(u64::from_le_bytes(
        body[MAGIC.len()..head].try_into().expect("8 bytes"),
    ))
    .map_err(|_| "length overflow".to_owned())?;
    if n.checked_mul(RUNGS * 16) != Some(body.len() - head) {
        return Err("length mismatch".into());
    }
    let mut cells = body[head..]
        .as_chunks::<16>()
        .0
        .iter()
        .map(|c| u128::from_le_bytes(*c));
    Ok(std::array::from_fn(|_| cells.by_ref().take(n).collect()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Windows {
        [vec![1, 2, 3], vec![4, 5, 6], vec![7, 8, 9]]
    }

    // frob:tests crates/grimble-arch/src/dup_index.rs::DupIndex.windows
    #[test]
    fn built_once_then_served_from_the_store() {
        let tmp = tempfile::tempdir().unwrap();
        let idx = DupIndex::open(&tmp.path().join("ix")).unwrap();
        let first = idx.windows("a b c", false, 3, sample).unwrap();
        let again = idx
            .windows("a b c", false, 3, || panic!("must not recompute"))
            .unwrap();
        assert_eq!(first, again);
        let changed = idx
            .windows("a b d", false, 3, || [vec![], vec![], vec![]])
            .unwrap();
        assert!(changed[0].is_empty());
    }

    // frob:tests crates/grimble-arch/src/dup_index.rs::DupIndex.open
    #[test]
    fn a_reopened_store_keeps_its_entries_and_a_foreign_dir_fails_closed() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("ix");
        DupIndex::open(&dir)
            .unwrap()
            .windows("x", true, 2, sample)
            .unwrap();
        let again = DupIndex::open(&dir).unwrap();
        again
            .windows("x", true, 2, || panic!("hit expected"))
            .unwrap();
        std::fs::remove_file(dir.join(MANIFEST_FILE)).unwrap();
        assert!(matches!(DupIndex::open(&dir), Err(IndexError::Missing(_))));
    }

    // frob:tests crates/grimble-arch/src/dup_index.rs::DupIndex.windows
    #[test]
    fn a_corrupt_entry_fails_closed_with_a_rebuild_hint() {
        let tmp = tempfile::tempdir().unwrap();
        let dir = tmp.path().join("ix");
        let idx = DupIndex::open(&dir).unwrap();
        idx.windows("x", false, 2, sample).unwrap();
        let entry = std::fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().path())
            .find(|p| p.extension().is_some_and(|e| e == "win"))
            .unwrap();
        let mut bytes = std::fs::read(&entry).unwrap();
        bytes[20] ^= 0xff;
        std::fs::write(&entry, bytes).unwrap();
        let err = idx.windows("x", false, 2, sample).unwrap_err();
        assert!(matches!(err, IndexError::Corrupt(..)), "{err:?}");
        assert!(err.to_string().contains("delete that directory to rebuild"));
    }

    // frob:tests crates/grimble-arch/src/dup_index.rs::dir_for
    #[test]
    fn no_index_directory_outside_git() {
        let tmp = tempfile::tempdir().unwrap();
        assert_eq!(dir_for(tmp.path()), None);
    }
}

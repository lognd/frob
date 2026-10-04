//! The authenticated, atomically written entry store.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use crate::error::TrustError;
use crate::key::MachineKey;
use crate::mac::{Canonical, CanonicalWriter, Tag, mac_record};

const MAGIC: &[u8; 8] = b"GOBSTAT1";
const HEADER: usize = MAGIC.len() + 32 + 8;
const CONTEXT: &str = "gob-state-entry/v1";

/// Why a state operation failed (never "the data was bad": that is [`Lookup::Discarded`]).
#[derive(Debug, thiserror::Error)]
pub enum StateError {
    /// Key or path trouble from the trust layer.
    #[error(transparent)]
    Trust(#[from] TrustError),
    /// The store root lies inside the work tree, where the repository can write.
    #[error("state root {root} is inside the work tree {tree}; derived state must live outside it")]
    InsideWorkTree {
        /// The offending root.
        root: PathBuf,
        /// The work tree.
        tree: PathBuf,
    },
    /// The product or kind is not a plain name.
    #[error("invalid state name {0:?}: use ascii letters, digits, '-', '_' or '.'")]
    BadName(String),
}

/// Why a stored entry was thrown away.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Discard {
    /// Shorter than the header or than its declared payload (truncation).
    Truncated,
    /// Wrong magic, or trailing bytes beyond the declared payload.
    Malformed,
    /// The MAC does not match (tamper, wrong key, moved file).
    BadMac,
}

/// The result of reading an entry.
#[derive(Debug, PartialEq, Eq)]
pub enum Lookup {
    /// A verified payload.
    Hit(Vec<u8>),
    /// No entry stored.
    Miss,
    /// An entry existed but failed verification; it was deleted and must be rebuilt.
    Discarded(Discard),
}

/// A directory of MAC'd entries addressed by (kind, key); the key is a digest, never a path.
#[derive(Debug)]
pub struct StateStore {
    root: PathBuf,
    key: MachineKey,
}

fn valid_name(s: &str) -> bool {
    !s.is_empty()
        && s != "."
        && s != ".."
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
}

fn io(op: &'static str, path: &Path) -> impl FnOnce(std::io::Error) -> StateError {
    let path = path.to_owned();
    move |source| StateError::Trust(TrustError::Io { op, path, source })
}

impl StateStore {
    /// Open the per-user store for `product`, loading or creating the machine key.
    ///
    /// # Errors
    /// [`StateError`] when the key or the directory cannot be obtained; the caller then runs with no state.
    pub fn open_default(product: &str, work_tree: Option<&Path>) -> Result<Self, StateError> {
        if !valid_name(product) {
            return Err(StateError::BadName(product.to_owned()));
        }
        let key = MachineKey::load_or_create()?;
        Self::open_at(crate::state::cache_dir(product)?, key, work_tree)
    }

    /// Open a store at `root` with `key`, refusing a root inside `work_tree`.
    ///
    /// # Errors
    /// [`StateError::InsideWorkTree`] or an I/O failure creating the directory.
    pub fn open_at(
        root: PathBuf,
        key: MachineKey,
        work_tree: Option<&Path>,
    ) -> Result<Self, StateError> {
        make_dir(&root)?;
        if let Some(tree) = work_tree {
            let real = fs::canonicalize(&root).map_err(io("canonicalize", &root))?;
            let tree_real = fs::canonicalize(tree).map_err(io("canonicalize", tree))?;
            if real.starts_with(&tree_real) {
                tracing::error!(root = %real.display(), "state root inside work tree refused");
                return Err(StateError::InsideWorkTree {
                    root: real,
                    tree: tree_real,
                });
            }
        }
        tracing::debug!(root = %root.display(), "state store opened");
        Ok(Self { root, key })
    }

    fn entry_path(&self, kind: &str, id: &str) -> Result<PathBuf, StateError> {
        if !valid_name(kind) {
            return Err(StateError::BadName(kind.to_owned()));
        }
        let name = blake3::hash(id.as_bytes()).to_hex().to_string();
        Ok(self.root.join(kind).join(name))
    }

    fn tag(&self, kind: &str, id: &str, payload: &[u8]) -> Tag {
        mac_record(&self.key, CONTEXT, &Entry { kind, id, payload })
    }

    /// Store `payload` under (`kind`, `id`) atomically: temp file, fsync, rename.
    ///
    /// # Errors
    /// [`StateError`] on a bad name or I/O failure; the previous entry is left intact.
    pub fn put(&self, kind: &str, id: &str, payload: &[u8]) -> Result<(), StateError> {
        let path = self.entry_path(kind, id)?;
        let dir = self.root.join(kind);
        make_dir(&dir)?;
        let mut bytes = Vec::with_capacity(HEADER + payload.len());
        bytes.extend_from_slice(MAGIC);
        bytes.extend_from_slice(self.tag(kind, id, payload).as_bytes());
        bytes.extend_from_slice(&(payload.len() as u64).to_le_bytes());
        bytes.extend_from_slice(payload);
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).map_err(|e| TrustError::Random(e.to_string()))?;
        let tmp = dir.join(format!(".tmp.{:x}", u64::from_le_bytes(nonce)));
        let written = write_private(&tmp, &bytes);
        let result = written.and_then(|()| fs::rename(&tmp, &path).map_err(io("rename", &path)));
        if result.is_err() {
            let _ = fs::remove_file(&tmp);
        }
        tracing::debug!(
            kind,
            bytes = bytes.len(),
            ok = result.is_ok(),
            "state entry written"
        );
        result
    }

    /// Read and verify the entry; an entry that fails verification is deleted and reported.
    ///
    /// # Errors
    /// [`StateError`] on a bad name or an I/O failure other than absence.
    pub fn get(&self, kind: &str, id: &str) -> Result<Lookup, StateError> {
        let path = self.entry_path(kind, id)?;
        let bytes = match fs::read(&path) {
            Ok(b) => b,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Lookup::Miss),
            Err(e) => return Err(io("read", &path)(e)),
        };
        match self.verify(kind, id, &bytes) {
            Ok(payload) => Ok(Lookup::Hit(payload.to_vec())),
            Err(why) => {
                tracing::warn!(kind, ?why, "state entry failed verification; discarded");
                if let Err(e) = fs::remove_file(&path)
                    && e.kind() != std::io::ErrorKind::NotFound
                {
                    tracing::warn!(error = %e, "could not delete discarded state entry");
                }
                Ok(Lookup::Discarded(why))
            }
        }
    }

    fn verify<'a>(&self, kind: &str, id: &str, bytes: &'a [u8]) -> Result<&'a [u8], Discard> {
        if bytes.len() < HEADER {
            return Err(Discard::Truncated);
        }
        if &bytes[..MAGIC.len()] != MAGIC {
            return Err(Discard::Malformed);
        }
        let tag_bytes: [u8; 32] = bytes[MAGIC.len()..MAGIC.len() + 32]
            .try_into()
            .expect("slice is 32 bytes");
        let len = u64::from_le_bytes(
            bytes[MAGIC.len() + 32..HEADER]
                .try_into()
                .expect("slice is 8 bytes"),
        );
        let have = (bytes.len() - HEADER) as u64;
        if have < len {
            return Err(Discard::Truncated);
        }
        if have > len {
            return Err(Discard::Malformed);
        }
        let payload = &bytes[HEADER..];
        if self.tag(kind, id, payload) == Tag::from(tag_bytes) {
            Ok(payload)
        } else {
            Err(Discard::BadMac)
        }
    }
}

/// The authenticated fields of an entry: kind and id bind it to its slot, so a moved file fails.
struct Entry<'a> {
    kind: &'a str,
    id: &'a str,
    payload: &'a [u8],
}

impl Canonical for Entry<'_> {
    fn write_canonical(&self, w: &mut CanonicalWriter) {
        w.str(self.kind).str(self.id).field(self.payload);
    }
}

#[cfg(unix)]
fn make_dir(dir: &Path) -> Result<(), StateError> {
    use std::os::unix::fs::DirBuilderExt;
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(dir)
        .map_err(io("create dir", dir))
}

#[cfg(not(unix))]
fn make_dir(dir: &Path) -> Result<(), StateError> {
    fs::create_dir_all(dir).map_err(io("create dir", dir))
}

fn write_private(tmp: &Path, bytes: &[u8]) -> Result<(), StateError> {
    let mut opts = fs::OpenOptions::new();
    opts.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        opts.mode(0o600);
    }
    let mut f = opts.open(tmp).map_err(io("create", tmp))?;
    f.write_all(bytes).map_err(io("write", tmp))?;
    f.sync_all().map_err(io("sync", tmp))
}

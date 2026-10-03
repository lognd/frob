//! The per-machine key: location, first-use creation, permission checks.

use std::ffi::OsString;
use std::fmt;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use crate::error::TrustError;

/// Key length in bytes (the blake3 key size).
pub const KEY_LEN: usize = 32;

/// The per-machine secret; `Debug` redacts it and it has no `Display`.
#[derive(Clone)]
pub struct MachineKey([u8; KEY_LEN]);

impl fmt::Debug for MachineKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("MachineKey(<redacted>)")
    }
}

impl MachineKey {
    /// Wrap explicit bytes; for tests only, never used by default.
    pub fn from_bytes(bytes: [u8; KEY_LEN]) -> Self {
        Self(bytes)
    }

    /// Read a 64-hex-char key from env var `var` (CI secret injection); never used by default.
    ///
    /// # Errors
    /// [`TrustError::BadEnvKey`] when the variable is unset or malformed.
    pub fn from_env_var(var: &str) -> Result<Self, TrustError> {
        let bad = || TrustError::BadEnvKey {
            var: var.to_owned(),
        };
        let text = std::env::var(var).map_err(|_| bad())?;
        let text = text.trim().as_bytes();
        if text.len() != KEY_LEN * 2 {
            return Err(bad());
        }
        let mut out = [0u8; KEY_LEN];
        for (slot, pair) in out.iter_mut().zip(text.chunks(2)) {
            let hi = hex_val(pair[0]).ok_or_else(bad)?;
            let lo = hex_val(pair[1]).ok_or_else(bad)?;
            *slot = hi << 4 | lo;
        }
        tracing::debug!(var, "machine key injected from environment");
        Ok(Self(out))
    }

    /// Load the key at the default path, creating it on first use.
    ///
    /// # Errors
    /// Any [`TrustError`] from path resolution, creation or validation.
    pub fn load_or_create() -> Result<Self, TrustError> {
        Self::load_or_create_at(&default_key_path()?)
    }

    /// Load the key at `path`, creating it atomically with owner-only permissions if absent.
    ///
    /// # Errors
    /// [`TrustError::InsecurePermissions`], [`TrustError::Malformed`], [`TrustError::Io`]
    /// or [`TrustError::Random`].
    pub fn load_or_create_at(path: &Path) -> Result<Self, TrustError> {
        match load(path) {
            Ok(Some(key)) => return Ok(key),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        create(path)?;
        // Whoever won the creation race, read back what is on disk and validate it.
        load(path)?.ok_or_else(|| TrustError::Malformed {
            path: path.to_owned(),
            why: "vanished after creation",
        })
    }

    pub(crate) fn as_bytes(&self) -> &[u8; KEY_LEN] {
        &self.0
    }
}

fn hex_val(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(b - b'a' + 10),
        b'A'..=b'F' => Some(b - b'A' + 10),
        _ => None,
    }
}

fn io(op: &'static str, path: &Path) -> impl FnOnce(std::io::Error) -> TrustError {
    let path = path.to_owned();
    move |source| TrustError::Io { op, path, source }
}

/// The key path for this platform and environment.
///
/// # Errors
/// [`TrustError::NoConfigDir`] when no base directory is derivable.
pub fn default_key_path() -> Result<PathBuf, TrustError> {
    resolve_key_path(|k| std::env::var_os(k))
}

/// Resolve the key path from an environment lookup (injectable for tests).
///
/// Order: absolute `XDG_CONFIG_HOME`; then Windows `APPDATA`; macOS
/// `$HOME/Library/Application Support`; other unix `$HOME/.config`. The file is
/// `<base>/gob/machine.key`.
///
/// # Errors
/// [`TrustError::NoConfigDir`] when no base directory is derivable.
pub fn resolve_key_path(env: impl Fn(&str) -> Option<OsString>) -> Result<PathBuf, TrustError> {
    let abs = |k: &str| env(k).map(PathBuf::from).filter(|p| p.is_absolute());
    let base = abs("XDG_CONFIG_HOME")
        .or_else(|| {
            if cfg!(windows) {
                abs("APPDATA")
            } else if cfg!(target_os = "macos") {
                abs("HOME").map(|h| h.join("Library").join("Application Support"))
            } else {
                abs("HOME").map(|h| h.join(".config"))
            }
        })
        .ok_or(TrustError::NoConfigDir)?;
    Ok(base.join("gob").join("machine.key"))
}

/// Read and validate the key at `path`; `Ok(None)` when it does not exist.
fn load(path: &Path) -> Result<Option<MachineKey>, TrustError> {
    let meta = match fs::symlink_metadata(path) {
        Ok(m) => m,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(io("stat", path)(e)),
    };
    if !meta.is_file() {
        return Err(TrustError::Malformed {
            path: path.to_owned(),
            why: "not a regular file",
        });
    }
    check_mode(path, &meta)?;
    let bytes = fs::read(path).map_err(io("read", path))?;
    let arr: [u8; KEY_LEN] = bytes.try_into().map_err(|_| TrustError::Malformed {
        path: path.to_owned(),
        why: "not exactly 32 bytes",
    })?;
    tracing::debug!(path = %path.display(), "machine key loaded");
    Ok(Some(MachineKey(arr)))
}

#[cfg(unix)]
fn check_mode(path: &Path, meta: &fs::Metadata) -> Result<(), TrustError> {
    use std::os::unix::fs::PermissionsExt;
    let mode = meta.permissions().mode() & 0o7777;
    if mode & 0o077 != 0 {
        tracing::error!(path = %path.display(), mode, "machine key permissions too open");
        return Err(TrustError::InsecurePermissions {
            path: path.to_owned(),
            mode,
        });
    }
    Ok(())
}

#[cfg(not(unix))]
fn check_mode(_path: &Path, _meta: &fs::Metadata) -> Result<(), TrustError> {
    Ok(())
}

/// Create the key file: random bytes into an owner-only temp file, then publish
/// with a no-clobber hard link so exactly one creator wins; losers keep the winner's key.
fn create(path: &Path) -> Result<(), TrustError> {
    let dir = path.parent().ok_or(TrustError::NoConfigDir)?;
    make_dir(dir)?;
    let mut bytes = [0u8; KEY_LEN];
    getrandom::fill(&mut bytes).map_err(|e| TrustError::Random(e.to_string()))?;
    let mut nonce = [0u8; 8];
    getrandom::fill(&mut nonce).map_err(|e| TrustError::Random(e.to_string()))?;
    let tmp = dir.join(format!(".machine.key.{:x}.tmp", u64::from_le_bytes(nonce)));
    let written = write_private(&tmp, &bytes);
    let linked = written.and_then(|()| match fs::hard_link(&tmp, path) {
        Ok(()) => {
            tracing::info!(path = %path.display(), "machine key created");
            Ok(())
        }
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
            tracing::debug!(path = %path.display(), "machine key created concurrently; using existing");
            Ok(())
        }
        Err(e) => Err(io("publish", path)(e)),
    });
    if let Err(e) = fs::remove_file(&tmp) {
        tracing::warn!(path = %tmp.display(), error = %e, "could not remove temp key file");
    }
    linked
}

#[cfg(unix)]
fn make_dir(dir: &Path) -> Result<(), TrustError> {
    use std::os::unix::fs::DirBuilderExt;
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(dir)
        .map_err(io("create dir", dir))
}

#[cfg(not(unix))]
fn make_dir(dir: &Path) -> Result<(), TrustError> {
    fs::create_dir_all(dir).map_err(io("create dir", dir))
}

fn write_private(tmp: &Path, bytes: &[u8]) -> Result<(), TrustError> {
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

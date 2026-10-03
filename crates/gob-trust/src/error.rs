//! Typed errors for key handling and MAC verification.

use std::path::PathBuf;

/// Why a key could not be obtained or a MAC did not verify.
#[derive(Debug, thiserror::Error)]
pub enum TrustError {
    /// No config directory could be determined for this platform and environment.
    #[error("cannot locate a per-user config directory: set XDG_CONFIG_HOME (or HOME)")]
    NoConfigDir,
    /// The key file is readable or writable by group or others.
    #[error(
        "machine key {path} has mode {mode:04o}, which lets other users read or write it; fix: chmod 600 {path}"
    )]
    InsecurePermissions {
        /// The key file.
        path: PathBuf,
        /// Its permission bits (low 12).
        mode: u32,
    },
    /// The key file is not a regular file of exactly 32 bytes.
    #[error(
        "machine key {path} is malformed ({why}); fix: delete it to generate a new key (this invalidates every MAC made with the old one)"
    )]
    Malformed {
        /// The key file.
        path: PathBuf,
        /// What is wrong.
        why: &'static str,
    },
    /// An environment-supplied key is unset or not 64 hex characters.
    #[error("environment key {var} is unset or not 64 hex characters")]
    BadEnvKey {
        /// The variable name.
        var: String,
    },
    /// The operating system gave no randomness.
    #[error("operating system random source failed: {0}")]
    Random(String),
    /// Filesystem failure at a path.
    #[error("{op} {path}: {source}")]
    Io {
        /// What was being done.
        op: &'static str,
        /// The path involved.
        path: PathBuf,
        /// The underlying error.
        #[source]
        source: std::io::Error,
    },
    /// The tag does not match the data under this key and context.
    #[error("MAC verification failed")]
    Mismatch,
}

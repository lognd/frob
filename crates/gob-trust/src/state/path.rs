//! Where derived state lives, and when in-tree caches are ignored.

use std::ffi::OsString;
use std::path::PathBuf;

use crate::error::TrustError;

/// The per-user state root for `product`, from the process environment.
///
/// # Errors
/// [`TrustError::NoConfigDir`] when no base directory is derivable.
pub fn cache_dir(product: &str) -> Result<PathBuf, TrustError> {
    resolve_cache_dir(|k| std::env::var_os(k), product)
}

/// Resolve `<base>/<product>/state` from an environment lookup (injectable for tests).
///
/// Order: absolute `XDG_CACHE_HOME`; then Windows `LOCALAPPDATA`; macOS
/// `$HOME/Library/Caches`; other unix `$HOME/.cache`.
///
/// # Errors
/// [`TrustError::NoConfigDir`] when no base directory is derivable.
pub fn resolve_cache_dir(
    env: impl Fn(&str) -> Option<OsString>,
    product: &str,
) -> Result<PathBuf, TrustError> {
    let abs = |k: &str| env(k).map(PathBuf::from).filter(|p| p.is_absolute());
    let base = abs("XDG_CACHE_HOME")
        .or_else(|| {
            if cfg!(windows) {
                abs("LOCALAPPDATA")
            } else if cfg!(target_os = "macos") {
                abs("HOME").map(|h| h.join("Library").join("Caches"))
            } else {
                abs("HOME").map(|h| h.join(".cache"))
            }
        })
        .ok_or(TrustError::NoConfigDir)?;
    Ok(base.join(product).join("state"))
}

/// True when CI mode is on (`CI` set to anything but empty, `0` or `false`).
///
/// The store never reads from the work tree in any mode; CI additionally makes
/// callers skip their in-tree caches, and they ask this one function.
pub fn ci_active(env: impl Fn(&str) -> Option<OsString>) -> bool {
    env("CI").is_some_and(|v| {
        let v = v.to_string_lossy();
        let v = v.trim();
        !(v.is_empty() || v == "0" || v.eq_ignore_ascii_case("false"))
    })
}

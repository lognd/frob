//! Local-only config locations: files that must never be committed.
//!
//! `frob.toml` is committed, so anything private (a name that must not be published) cannot live in it.
//! Local-only files live in two places: the per-user config directory of the platform and the
//! repository's git common directory. Nothing here writes into a work tree.

use std::ffi::OsString;
use std::path::{Path, PathBuf};

// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72

/// The per-user config directory for `env` (an environment lookup, injectable for tests), when one is derivable.
///
/// Order: absolute `XDG_CONFIG_HOME`; then Windows `APPDATA`; macOS `$HOME/Library/Application Support`;
/// other unix `$HOME/.config`.
pub fn user_config_dir_with(env: impl Fn(&str) -> Option<OsString>) -> Option<PathBuf> {
    let abs = |k: &str| env(k).map(PathBuf::from).filter(|p| p.is_absolute());
    abs("XDG_CONFIG_HOME").or_else(|| {
        if cfg!(windows) {
            abs("APPDATA")
        } else if cfg!(target_os = "macos") {
            abs("HOME").map(|h| h.join("Library").join("Application Support"))
        } else {
            abs("HOME").map(|h| h.join(".config"))
        }
    })
}

/// The per-user config directory of this process's environment.
pub fn user_config_dir() -> Option<PathBuf> {
    user_config_dir_with(|k| std::env::var_os(k))
}

/// The directory of a local-only file `name` of `product` in the user config: `<config>/<product>/<name>`.
pub fn user_file(product: &str, name: &str) -> Option<PathBuf> {
    user_config_dir().map(|d| d.join(product).join(name))
}

/// The per-repository local-only file `name` of `product`: `<git common dir>/<product>/<name>`.
///
/// The common dir is shared by every linked worktree and is never part of a commit.
pub fn repo_file(common_dir: &Path, product: &str, name: &str) -> PathBuf {
    common_dir.join(product).join(name)
}

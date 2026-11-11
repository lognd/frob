//! One cargo target directory shared by every checkout of a repository (frob:ticket 01M4Y2XTH8Q817362APA13CTAJ).
//!
//! sccache cannot make a second worktree compile zero workspace crates (it hashes the manifest
//! dir and cwd), but with source mtimes normalized ([`crate::normalize_mtimes`]) a shared
//! `CARGO_TARGET_DIR` reuses cargo's own fingerprints. [`export_shared_target`] computes
//! `<git common dir>/frob/cargo-target/<toolchain>` and records it as `CARGO_TARGET_DIR` for the
//! cargo stages this process runs (via [`gob_exec::set_ambient_env`]). Cargo keeps `debug/` and
//! `release/` apart inside the directory, so the key is the toolchain; profile needs no part of it.
//! An explicit `CARGO_TARGET_DIR` is never overridden and `[worktree] shared_target = false` opts out.

use std::path::{Path, PathBuf};

use gob_path::Shown;

use crate::config::WorktreeConfig;

/// Environment variable cargo reads for its target directory.
const TARGET_VAR: &str = "CARGO_TARGET_DIR";

/// Environment variable rustup sets to the active toolchain.
const RUSTUP_VAR: &str = "RUSTUP_TOOLCHAIN";

/// Directory (under `<common>/frob/`) holding one shared target per toolchain.
pub const SHARED_TARGETS_DIR: &str = "cargo-target";

/// Toolchain key used when neither rustup nor a toolchain file names one.
const DEFAULT_TOOLCHAIN: &str = "default";

/// Why a shared target directory could not be computed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum SharedTargetError {
    /// The git common dir is relative, so the result would depend on the working directory.
    #[error("git common dir {0} is not absolute")]
    RelativeCommon(String),
}

/// What [`export_shared_target`] did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Exported {
    /// `CARGO_TARGET_DIR` now points at this directory for every cargo stage.
    Set(PathBuf),
    /// `[worktree] shared_target` is false.
    Disabled,
    /// The user already set `CARGO_TARGET_DIR`; left alone.
    Explicit,
    /// The directory could not be computed or created; cargo stages build in each checkout's own `target/`.
    Skipped,
}

/// Reduce a toolchain name to a single safe path component (`stable-x86_64-unknown-linux-gnu` stays as is).
fn sanitize(toolchain: &str) -> String {
    let clean: String = toolchain
        .trim()
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-') {
                c
            } else {
                '_'
            }
        })
        .collect();
    if clean.trim_matches('.').is_empty() {
        DEFAULT_TOOLCHAIN.to_owned()
    } else {
        clean
    }
}

/// The shared target directory for `toolchain` under the absolute git `common` dir.
///
/// # Errors
///
/// [`SharedTargetError::RelativeCommon`] when `common` is not absolute.
pub fn shared_target_dir(common: &Path, toolchain: &str) -> Result<PathBuf, SharedTargetError> {
    if !common.is_absolute() {
        return Err(SharedTargetError::RelativeCommon(
            Shown::of(common).to_string(),
        ));
    }
    Ok(common
        .join("frob")
        .join(SHARED_TARGETS_DIR)
        .join(sanitize(toolchain)))
}

/// The toolchain key from rustup's variable, else a toolchain file's `channel`, else `default`.
///
/// `file` is the text of `rust-toolchain.toml` (TOML `[toolchain] channel`) or of a legacy
/// `rust-toolchain` file (first line); whichever parses as a channel wins.
#[must_use]
pub fn toolchain_key(rustup: Option<&str>, file: Option<&str>) -> String {
    let from_file = file.and_then(|text| {
        let channel = text
            .parse::<toml::Table>()
            .ok()
            .and_then(|t| {
                t.get("toolchain")?
                    .get("channel")?
                    .as_str()
                    .map(str::to_owned)
            })
            .or_else(|| {
                let first = text.lines().next()?.trim();
                (!first.is_empty() && !first.contains('=') && !first.starts_with('['))
                    .then(|| first.to_owned())
            });
        channel.filter(|c| !c.trim().is_empty())
    });
    let named = rustup
        .filter(|r| !r.trim().is_empty())
        .map(str::to_owned)
        .or(from_file);
    sanitize(named.as_deref().unwrap_or(DEFAULT_TOOLCHAIN))
}

/// The toolchain key for the checkout at `root`, reading its toolchain file when rustup names none.
fn checkout_toolchain(root: &Path) -> String {
    let rustup = std::env::var(RUSTUP_VAR).ok();
    let file = ["rust-toolchain.toml", "rust-toolchain"]
        .iter()
        .find_map(|name| std::fs::read_to_string(root.join(name)).ok());
    toolchain_key(rustup.as_deref(), file.as_deref())
}

/// Export the shared `CARGO_TARGET_DIR` for the checkout at `root` to every cargo stage this process runs.
///
/// Best effort: any failure is logged and the stages build in each checkout's own `target/`.
pub fn export_shared_target(root: &Path) -> Exported {
    export_unless_explicit(root, std::env::var_os(TARGET_VAR).is_some())
}

/// [`export_shared_target`] with the "caller already set `CARGO_TARGET_DIR`" fact passed in.
fn export_unless_explicit(root: &Path, explicit: bool) -> Exported {
    if explicit {
        tracing::debug!("CARGO_TARGET_DIR is set explicitly; not overriding it");
        return Exported::Explicit;
    }
    match WorktreeConfig::load(root) {
        Ok(cfg) if !cfg.shared_target => {
            tracing::debug!("[worktree] shared_target is off; checkouts keep their own target");
            return Exported::Disabled;
        }
        Ok(_) => {}
        Err(e) => {
            tracing::warn!(error = %e, "worktree config unreadable; no shared cargo target");
            return Exported::Skipped;
        }
    }
    let Ok(repo) = gob_git::Repo::discover(root) else {
        tracing::debug!(root = %Shown::of(root), "not a git checkout; no shared cargo target");
        return Exported::Skipped;
    };
    let common =
        gob_exec::canonical(repo.common_dir()).unwrap_or_else(|_| repo.common_dir().to_path_buf());
    let dir = match shared_target_dir(&common, &checkout_toolchain(root)) {
        Ok(dir) => dir,
        Err(e) => {
            tracing::warn!(error = %e, "no shared cargo target");
            return Exported::Skipped;
        }
    };
    if let Err(e) = std::fs::create_dir_all(&dir) {
        tracing::warn!(error = %e, dir = %Shown::of(&dir), "shared cargo target not created");
        return Exported::Skipped;
    }
    gob_exec::set_ambient_env(TARGET_VAR, &crate::pathtext::text(&dir));
    tracing::info!(dir = %Shown::of(&dir), "cargo stages share one target directory");
    Exported::Set(dir)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-worktree/src/shared_target.rs::shared_target_dir
    #[test]
    fn the_dir_is_keyed_by_toolchain_under_the_common_dir() {
        let common = std::env::temp_dir().join("repo.git");
        let dir = shared_target_dir(&common, "stable").expect("dir");
        assert_eq!(dir, common.join("frob").join("cargo-target").join("stable"));
        let odd = shared_target_dir(&common, "../x y").expect("dir");
        assert_eq!(odd.parent(), dir.parent());
        assert_eq!(
            odd.file_name().map(crate::pathtext::name_text).as_deref(),
            Some(".._x_y")
        );
    }

    // frob:tests crates/frob-worktree/src/shared_target.rs::shared_target_dir
    #[test]
    fn a_relative_common_dir_is_refused() {
        let err = shared_target_dir(Path::new("rel/.git"), "stable").expect_err("relative");
        assert!(matches!(err, SharedTargetError::RelativeCommon(_)));
    }

    // frob:tests crates/frob-worktree/src/shared_target.rs::toolchain_key
    #[test]
    fn the_toolchain_key_prefers_rustup_then_the_file_then_default() {
        let toml = "[toolchain]\nchannel = \"1.90.0\"\n";
        assert_eq!(toolchain_key(Some("nightly-x"), Some(toml)), "nightly-x");
        assert_eq!(toolchain_key(None, Some(toml)), "1.90.0");
        assert_eq!(toolchain_key(None, Some("beta\n")), "beta");
        assert_eq!(toolchain_key(Some(" "), None), "default");
        assert_eq!(toolchain_key(None, Some("[toolchain]\n")), "default");
    }

    // frob:tests crates/frob-worktree/src/shared_target.rs::export_shared_target
    #[test]
    fn an_explicit_target_dir_is_never_overridden() {
        let dir = tempfile::tempdir().expect("tmp");
        assert_eq!(export_unless_explicit(dir.path(), true), Exported::Explicit);
    }

    // frob:tests crates/frob-worktree/src/shared_target.rs::export_shared_target
    #[test]
    fn the_knob_opts_out() {
        let off = tempfile::tempdir().expect("tmp");
        std::fs::write(
            off.path().join("frob.toml"),
            "[worktree]\nshared_target = false\n",
        )
        .expect("write");
        assert_eq!(
            export_unless_explicit(off.path(), false),
            Exported::Disabled
        );
    }

    // frob:tests crates/frob-worktree/src/shared_target.rs::export_shared_target
    #[test]
    fn a_non_git_dir_is_skipped() {
        let plain = tempfile::tempdir().expect("tmp");
        assert_eq!(
            export_unless_explicit(plain.path(), false),
            Exported::Skipped
        );
    }
}

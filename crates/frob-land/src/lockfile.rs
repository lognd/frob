//! Resolving a base-merge conflict confined to generated lockfiles (frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4).
//!
//! A lockfile is generated, so a textual conflict in it carries no intent:
//! take the base side (`git checkout --theirs`, the base is the branch being
//! merged in) and let the ecosystem's offline resolver re-add what the ticket's
//! manifest changes need. Only Cargo has a resolver today; any other lockfile
//! refuses with a remedy. The resolver is `cargo metadata --offline`: it
//! reconciles `Cargo.lock` with the manifests keeping every locked version it
//! can, while `cargo update --workspace --offline` re-resolves workspace
//! members and rewrites more of the file.

use std::path::Path;

use frob_lease::LeaseConfig;
use frob_lease::overlap::glob_set;
use gob_git::Repo;

use crate::error::{LandError, needs_action};
use crate::git::{cargo, git};

/// Stable code of the refusal when a lockfile conflict cannot be regenerated.
const CODE_LOCKFILE: &str = "E-LAND-LOCKFILE";

/// The `[lease] shared_files` globs committed at `base`, read before any merge starts (frob:ticket 01M43FX5KWVP277RX5666MMPM1).
///
/// Land never reads configuration from the worktree while a merge may be in
/// progress: its `frob.toml` can hold conflict markers. The base is the
/// authority land merges toward, so its committed file decides.
pub(crate) fn committed_shared_files(wt: &Repo, base: &str) -> Result<Vec<String>, LandError> {
    let label = Path::new("frob.toml");
    let text = match wt.read_blob_at(base, "frob.toml")? {
        Some(bytes) => String::from_utf8(bytes)
            .map_err(|e| LandError::Config(format!("{base}:frob.toml is not UTF-8: {e}")))?,
        None => String::new(),
    };
    let cfg = LeaseConfig::from_toml_str(&text, label)
        .map_err(|e| LandError::Config(format!("{base}:frob.toml: {e}")))?;
    Ok(cfg.shared_files)
}

/// True when every conflicted path is a shared lockfile matching `shared_files`.
pub(crate) fn all_shared(shared_files: &[String], paths: &[String]) -> Result<bool, LandError> {
    if paths.is_empty() {
        return Ok(false);
    }
    let shared = glob_set(shared_files).map_err(|e| LandError::Config(e.to_string()))?;
    Ok(paths.iter().all(|p| shared.is_match(p)))
}

/// Resolve the in-progress merge whose only conflicts are the lockfiles `paths`, then commit it.
///
/// The merge is aborted and a refusal returned when a lockfile has no offline
/// resolver or the resolver fails.
pub(crate) fn resolve(
    wt: &Repo,
    wt_path: &Path,
    base: &str,
    paths: &[String],
) -> Result<String, LandError> {
    let abort = |why: String, remedy: String| -> LandError {
        match git(wt, wt_path, &["merge", "--abort"]) {
            Ok(run) => tracing::warn!(aborted = run.ok(), "lockfile conflict unresolved"),
            Err(e) => tracing::error!(error = %e, "merge abort failed"),
        }
        needs_action(CODE_LOCKFILE, why, remedy)
    };
    for path in paths {
        if file_name(path) != "Cargo.lock" {
            return Err(abort(
                format!("merging {base} conflicts in {path}, a lockfile with no offline resolver"),
                format!(
                    "git -C {} merge {base}, regenerate {path} with your package manager, commit, then frob land again",
                    wt_path.display()
                ),
            ));
        }
    }
    for path in paths {
        let taken = git(wt, wt_path, &["checkout", "--theirs", "--", path])?;
        if !taken.ok() {
            return Err(abort(
                format!("taking the {base} side of {path} failed: {}", taken.text),
                format!(
                    "git -C {} merge {base} and resolve by hand",
                    wt_path.display()
                ),
            ));
        }
        let dir = wt_path.join(Path::new(path).parent().unwrap_or_else(|| Path::new("")));
        let regen = cargo(
            wt,
            &dir,
            &["metadata", "--offline", "--format-version", "1"],
        )?;
        tracing::info!(path, ok = regen.ok(), "Cargo.lock regenerated offline");
        if !regen.ok() {
            return Err(abort(
                format!(
                    "regenerating {path} with `cargo metadata --offline` failed: {}",
                    regen.text
                ),
                format!(
                    "git -C {} merge {base}, run cargo update in the failing crate, commit, then frob land again",
                    wt_path.display()
                ),
            ));
        }
        let mut add = vec!["add", "--"];
        add.push(path);
        git(wt, wt_path, &add)?;
    }
    let commit = git(wt, wt_path, &["commit", "--no-edit"])?;
    if !commit.ok() {
        return Err(abort(
            format!("committing the lockfile merge failed: {}", commit.text),
            format!(
                "git -C {} merge {base} and resolve by hand",
                wt_path.display()
            ),
        ));
    }
    tracing::info!(
        count = paths.len(),
        "lockfile conflicts resolved by regeneration"
    );
    Ok("merged (lockfile regenerated)".to_owned())
}

fn file_name(path: &str) -> &str {
    path.rsplit('/').next().unwrap_or(path)
}

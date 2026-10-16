//! Resolving a base-merge conflict confined to generated files (frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4, frob:ticket 01M51CKG5T7817RJXJ57H020EB).
//!
//! Generated outputs (`[lease] generated_files`, the `gen all` pages and
//! schemas) are resolved the same way: take the base side, then re-run
//! `cargo dev gen all` on the merged tree and commit what it writes.
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

/// Stable code of the refusal when a generated-file conflict cannot be regenerated.
const CODE_GENERATED: &str = "E-LAND-GENERATED";

/// The `[lease]` globs whose conflicts land resolves by regeneration.
#[derive(Debug, Clone, Default)]
pub(crate) struct Regenerable {
    /// `shared_files`: lockfiles an offline resolver rebuilds.
    pub shared: Vec<String>,
    /// `generated_files`: outputs `cargo dev gen all` rewrites.
    pub generated: Vec<String>,
}

/// The `[lease] shared_files` and `generated_files` globs committed at `base`, read before any merge starts (frob:ticket 01M43FX5KWVP277RX5666MMPM1).
///
/// Land never reads configuration from the worktree while a merge may be in
/// progress: its `frob.toml` can hold conflict markers. The base is the
/// authority land merges toward, so its committed file decides.
pub(crate) fn committed_regenerable(wt: &Repo, base: &str) -> Result<Regenerable, LandError> {
    let label = Path::new("frob.toml");
    let text = match wt.read_blob_at(base, "frob.toml")? {
        Some(bytes) => String::from_utf8(bytes)
            .map_err(|e| LandError::Config(format!("{base}:frob.toml is not UTF-8: {e}")))?,
        None => String::new(),
    };
    let cfg = gob_config::load_str::<LeaseConfig>(&text, label)
        .map_err(|e| LandError::Config(format!("{base}:frob.toml: {e}")))?;
    Ok(Regenerable {
        shared: cfg.value.shared_files,
        generated: cfg.value.generated_files,
    })
}

/// True when every conflicted path is a shared lockfile or a generated output.
pub(crate) fn all_regenerable(globs: &Regenerable, paths: &[String]) -> Result<bool, LandError> {
    if paths.is_empty() {
        return Ok(false);
    }
    let shared = glob_set(&globs.shared).map_err(|e| LandError::Config(e.to_string()))?;
    let generated = glob_set(&globs.generated).map_err(|e| LandError::Config(e.to_string()))?;
    Ok(paths
        .iter()
        .all(|p| shared.is_match(p) || generated.is_match(p)))
}

/// Resolve the in-progress merge whose only conflicts are the lockfiles and generated outputs `paths`, then commit it.
// frob:ticket 01M50C2K3H0STZWFR5P29BWY8G
///
/// The merge is aborted and a refusal returned when a lockfile has no offline
/// resolver or the resolver fails.
pub(crate) fn resolve(
    wt: &Repo,
    wt_path: &Path,
    base: &str,
    globs: &Regenerable,
    paths: &[String],
) -> Result<String, LandError> {
    let generated = glob_set(&globs.generated).map_err(|e| LandError::Config(e.to_string()))?;
    let (generated_paths, paths): (Vec<String>, Vec<String>) =
        paths.iter().cloned().partition(|p| generated.is_match(p));
    let paths = paths.as_slice();
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
    if !generated_paths.is_empty() {
        regenerate(wt, wt_path, base, globs, &generated_paths, &abort)?;
    }
    // Explicit identity so the merge commit never depends on ambient git config (CI has none).
    let commit = git(
        wt,
        wt_path,
        &[
            "-c",
            "user.name=frob-land",
            "-c",
            "user.email=frob-land@localhost",
            "commit",
            "--no-edit",
        ],
    )?;
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
        lockfiles = paths.len(),
        generated = generated_paths.len(),
        "conflicts resolved by regeneration"
    );
    Ok("merged (lockfile regenerated)".to_owned())
}

/// Take the base side of each generated conflict, re-run `cargo dev gen all` on the merged tree and stage what it wrote.
fn regenerate(
    wt: &Repo,
    wt_path: &Path,
    base: &str,
    globs: &Regenerable,
    generated_paths: &[String],
    abort: &dyn Fn(String, String) -> LandError,
) -> Result<(), LandError> {
    let by_hand = format!(
        "git -C {} merge {base}, run `cargo dev gen all`, commit, then frob land again",
        wt_path.display()
    );
    for path in generated_paths {
        let taken = git(wt, wt_path, &["checkout", "--theirs", "--", path])?;
        if !taken.ok() {
            return Err(abort_with(
                abort,
                CODE_GENERATED,
                format!("taking the {base} side of {path} failed: {}", taken.text),
                by_hand,
            ));
        }
    }
    let regen = cargo(wt, wt_path, &["dev", "gen", "all"])?;
    tracing::info!(
        ok = regen.ok(),
        "generated files regenerated on the merged tree"
    );
    if !regen.ok() {
        return Err(abort_with(
            abort,
            CODE_GENERATED,
            format!(
                "`cargo dev gen all` on the merged tree failed: {}",
                regen.text
            ),
            by_hand,
        ));
    }
    for glob in &globs.generated {
        let spec = format!(":(glob){glob}");
        let add = git(wt, wt_path, &["add", "-A", "--", &spec])?;
        if !add.ok() {
            return Err(abort_with(
                abort,
                CODE_GENERATED,
                format!("staging {glob} failed: {}", add.text),
                by_hand,
            ));
        }
    }
    Ok(())
}

/// Run the merge-aborting closure, then swap its error's code for `code`.
fn abort_with(
    abort: &dyn Fn(String, String) -> LandError,
    code: &str,
    why: String,
    remedy: String,
) -> LandError {
    let _ = abort(String::new(), String::new());
    needs_action(code, why, remedy)
}

fn file_name(path: &str) -> &str {
    path.rsplit('/').next().unwrap_or(path)
}

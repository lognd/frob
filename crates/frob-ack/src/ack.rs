//! Recording acknowledgements in `frob.lock` and committing them.

use std::collections::BTreeSet;
use std::path::Path;

use gob_git::{CommitOptions, RelPath, Repo};
use gob_lock::{Current, CurrentSymbol, FacetSet, LockTarget, Plan, PlanOptions, file_name};
use gob_symbols::{SymbolRecord, Symref};

use crate::error::AckError;
use crate::inputs::{Inputs, PRODUCT, section_digest};

/// What [`ack`] did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AckOutcome {
    /// Symrefs whose entry was added or changed, sorted.
    pub acked: Vec<String>,
    /// The commit that recorded `frob.lock`, when one was made.
    pub commit: Option<String>,
    /// The branch committed on.
    pub branch: Option<String>,
    /// The lock file path, repo-relative.
    pub lock_file: String,
}

/// Resolves `input` to records: a repo path means every symbol in the file.
fn resolve_target<'g>(inputs: &'g Inputs, input: &str) -> Result<Vec<&'g SymbolRecord>, AckError> {
    if !input.contains("::")
        && !input.contains('#')
        && inputs.graph.get(&Symref::file(input)).is_some()
    {
        let all: Vec<_> = inputs
            .graph
            .records()
            .filter(|r| r.symref.path() == input)
            .collect();
        tracing::debug!(
            path = input,
            symbols = all.len(),
            "path expanded to its symbols"
        );
        return Ok(all);
    }
    inputs
        .graph
        .resolve(input)
        .map(|r| vec![r])
        .map_err(|source| AckError::Resolve {
            input: input.to_owned(),
            source,
        })
}

/// What `--all` adds beyond the lock's own entries: every symbol a `frob:doc` binding names.
fn doc_bound(inputs: &Inputs) -> impl Iterator<Item = &SymbolRecord> {
    inputs
        .docs
        .iter()
        .filter_map(|d| inputs.graph.get(&d.symbol))
}

/// The ack-relevant state of `rec` now: facets and bound doc section digests.
fn current_of(inputs: &Inputs, rec: &SymbolRecord) -> CurrentSymbol {
    let d = &rec.digests;
    let targets = inputs
        .docs
        .iter()
        .filter(|b| b.symbol == rec.symref)
        .filter_map(|b| {
            inputs.graph.get(&b.target).map(|t| LockTarget {
                target: b.target.to_string(),
                digest: section_digest(&t.digests).to_string(),
            })
        })
        .collect();
    CurrentSymbol {
        identity: None,
        facets: FacetSet {
            sig: d.sig.to_string(),
            body: d.body.to_string(),
            doc: d.doc.to_string(),
            attr: d.attr.to_string(),
            contract: d.contract.to_string(),
        },
        targets,
    }
}

/// `Name <email>` from git config, else `unknown`.
fn actor_of(repo: Option<&Repo>) -> String {
    repo.and_then(Repo::config_user)
        .map_or_else(|| "unknown".to_owned(), |(n, e)| format!("{n} <{e}>"))
}

/// Works out the new lock for an ack without writing anything.
///
/// Resolution (symrefs, paths, `--all` doc bindings) happens here; the decision is
/// [`gob_lock::plan`].
///
/// # Errors
///
/// [`AckError::Resolve`] for a target that matches no (or several) symbols,
/// [`AckError::Plan`] for an empty selection or a stale lock that `--all --reason` has not
/// migrated, plus input collection errors.
pub fn plan_ack(
    root: &Path,
    targets: &[String],
    all: bool,
    reason: Option<&str>,
    at: gob_time::Stamp,
) -> Result<Plan, AckError> {
    let inputs = Inputs::collect(root)?;
    let mut selected: Vec<&SymbolRecord> = Vec::new();
    for t in targets {
        selected.extend(resolve_target(&inputs, t)?);
    }
    if all {
        selected.extend(doc_bound(&inputs));
    }
    let mut current = Current::default();
    let lock_known = inputs
        .lock
        .entries
        .keys()
        .filter_map(|k| Symref::parse(k).ok())
        .filter_map(|s| inputs.graph.get(&s));
    for rec in selected.iter().copied().chain(lock_known) {
        current
            .symbols
            .insert(rec.symref.to_string(), current_of(&inputs, rec));
    }
    let keys: Vec<String> = selected
        .iter()
        .map(|r| r.symref.to_string())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let repo = Repo::discover(root).ok();
    let options = PlanOptions {
        actor: actor_of(repo.as_ref()),
        at: at.to_string(),
        reason: reason.map(str::to_owned),
        all,
    };
    Ok(gob_lock::plan(&inputs.lock, &current, &keys, &options)?)
}

/// Acks `targets` (symrefs or paths) and/or everything tracked (`all`), then commits `frob.lock`
/// on the current branch with the message `ack: <n> symbols`.
///
/// `root` is the work tree root. Outside a git repository the lock is only
/// written to disk. Nothing is written when every digest is already acked.
///
/// # Errors
///
/// As [`plan_ack`], plus [`AckError::DetachedHead`], [`AckError::Lock`] and git failures
/// (local edits to `frob.lock`, a lost compare-and-swap, no identity).
pub fn ack(
    root: &Path,
    targets: &[String],
    all: bool,
    reason: Option<&str>,
    at: gob_time::Stamp,
) -> Result<AckOutcome, AckError> {
    let plan = plan_ack(root, targets, all, reason, at)?;
    let lock_file = file_name(PRODUCT);
    let mut out = AckOutcome {
        acked: plan.acked,
        commit: None,
        branch: None,
        lock_file: lock_file.clone(),
    };
    if out.acked.is_empty() {
        return Ok(out);
    }
    match Repo::discover(root) {
        Ok(repo) => {
            let branch = repo.current_branch()?.ok_or(AckError::DetachedHead)?;
            let bytes = plan.lock.to_toml()?.into_bytes();
            let message = match reason {
                Some(r) => format!("ack: {} symbols\n\n{r}", out.acked.len()),
                None => format!("ack: {} symbols", out.acked.len()),
            };
            let done = repo.commit_paths(
                &branch,
                &[(RelPath::new(lock_file)?, Some(bytes))],
                &message,
                &CommitOptions::default(),
            )?;
            tracing::info!(%branch, commit = %done.oid, "frob.lock committed");
            out.commit = Some(done.oid.to_string());
            out.branch = Some(branch);
        }
        Err(err) => {
            tracing::warn!(%err, "not a git repository; frob.lock written but not committed");
            plan.lock.save(&root.join(&lock_file))?;
        }
    }
    Ok(out)
}

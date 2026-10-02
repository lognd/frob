//! Recording acknowledgements in `frob.lock` and committing them.

use std::collections::BTreeSet;
use std::path::Path;

use gob_git::{CommitOptions, RelPath, Repo};
use gob_lock::{LockEntry, LockFile, LockTarget, file_name};
use gob_symbols::{SymbolRecord, Symref};

use crate::error::AckError;
use crate::inputs::{Inputs, PRODUCT, section_digest};

/// What [`plan_ack`] decided: the lock to write and which symbols changed.
#[derive(Debug, Clone)]
pub struct Plan {
    /// The lock after the ack.
    pub lock: LockFile,
    /// Symrefs whose entry was added or changed, sorted.
    pub acked: Vec<String>,
}

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

/// Symbols `--all` re-acks: every acked symbol still present and every `frob:doc` binding.
fn tracked(inputs: &Inputs) -> Vec<&SymbolRecord> {
    let from_lock = inputs
        .lock
        .entries
        .keys()
        .filter_map(|k| Symref::parse(k).ok())
        .filter_map(|s| inputs.graph.get(&s));
    let from_docs = inputs
        .docs
        .iter()
        .filter_map(|d| inputs.graph.get(&d.symbol));
    from_lock.chain(from_docs).collect()
}

fn entry_for(
    inputs: &Inputs,
    rec: &SymbolRecord,
    actor: &str,
    at: &str,
    reason: Option<&str>,
) -> LockEntry {
    let mut targets: Vec<LockTarget> = inputs
        .docs
        .iter()
        .filter(|d| d.symbol == rec.symref)
        .filter_map(|d| {
            inputs.graph.get(&d.target).map(|t| LockTarget {
                target: d.target.to_string(),
                digest: section_digest(&t.digests).to_string(),
            })
        })
        .collect();
    targets.sort_by(|a, b| a.target.cmp(&b.target));
    targets.dedup_by(|a, b| a.target == b.target);
    let mut e = LockEntry::new(
        &rec.digests.sig.to_string(),
        &rec.digests.body.to_string(),
        &rec.digests.doc.to_string(),
        actor,
        at,
    );
    e.reason = reason.map(str::to_owned);
    e.targets = targets;
    e
}

fn same_facets(a: &LockEntry, b: &LockEntry) -> bool {
    (&a.sig, &a.body, &a.doc, &a.targets) == (&b.sig, &b.body, &b.doc, &b.targets)
}

/// `Name <email>` from git config, else `unknown`.
fn actor_of(repo: Option<&Repo>) -> String {
    repo.and_then(Repo::config_user)
        .map_or_else(|| "unknown".to_owned(), |(n, e)| format!("{n} <{e}>"))
}

/// Works out the new lock for an ack without writing anything.
///
/// # Errors
///
/// [`AckError::Resolve`] for a target that matches no (or several) symbols,
/// [`AckError::NothingToAck`] for an empty selection, plus input collection errors.
pub fn plan_ack(
    root: &Path,
    targets: &[String],
    all: bool,
    reason: Option<&str>,
) -> Result<Plan, AckError> {
    let inputs = Inputs::collect(root)?;
    let mut selected: Vec<&SymbolRecord> = Vec::new();
    for t in targets {
        selected.extend(resolve_target(&inputs, t)?);
    }
    if all {
        selected.extend(tracked(&inputs));
    }
    let selected: BTreeSet<&Symref> = selected.iter().map(|r| &r.symref).collect();
    if selected.is_empty() {
        return Err(AckError::NothingToAck);
    }
    let repo = Repo::discover(root).ok();
    let actor = actor_of(repo.as_ref());
    let at = jiff::Timestamp::now().to_string();
    let mut lock = inputs.lock.clone();
    let mut acked = Vec::new();
    for symref in selected {
        let Some(rec) = inputs.graph.get(symref) else {
            continue;
        };
        let fresh = entry_for(&inputs, rec, &actor, &at, reason);
        let key = symref.to_string();
        if lock
            .entries
            .get(&key)
            .is_some_and(|old| same_facets(old, &fresh))
        {
            tracing::debug!(symref = %key, "already acked at these digests");
            continue;
        }
        tracing::info!(symref = %key, "ack recorded");
        lock.entries.insert(key.clone(), fresh);
        acked.push(key);
    }
    Ok(Plan { lock, acked })
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
) -> Result<AckOutcome, AckError> {
    let plan = plan_ack(root, targets, all, reason)?;
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

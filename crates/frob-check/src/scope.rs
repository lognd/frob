//! `--ticket` scoping: the ticket's files plus dependents, and the diff-based rules.

use std::collections::{BTreeSet, HashMap};

use frob_lease::{Holder, Lease, LeaseConfig, LeaseStore, overlap::glob_set, scope001};
use frob_ledger::LedgerConfig;
use gob_git::{GitError, RelPath, Repo, TreeRef};
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_symbols::{Admit, CallEdge, SymbolGraph, SymbolRecord};

use gob_check::{CheckError, ScopeView, Snapshot};

use crate::product::Frob;

/// A resolved `--ticket`: where its scope lies and the lease SCOPE001 compares against.
pub struct TicketScope {
    /// The ticket handle with `~`.
    pub handle: String,
    /// The live lease, or one synthesized from the ticket scope.
    pub lease: Lease,
    /// Walked files in scope plus `ticket_hops` hops of dependents.
    pub files: BTreeSet<String>,
    /// `[lease] shared_files`: paths every ticket may touch without a lease violation.
    pub shared_files: Vec<String>,
}

impl ScopeView for TicketScope {
    fn label(&self) -> &str {
        &self.handle
    }

    fn files(&self) -> &BTreeSet<String> {
        &self.files
    }
}

/// Files whose symbols call into a symbol of the keyed file, from the call edges.
///
/// Resolved and ambiguous (May) edges count as written. An unresolved edge (a call into another
/// crate, or one the resolver cannot place) counts against every function or method of the same
/// name the call's qualifier does not rule out, so the cone only ever errs wide
/// (frob:ticket 01M4GRW6NH23YPTSAQED5ZJPVH).
fn dependents(graph: &SymbolGraph) -> HashMap<String, BTreeSet<String>> {
    let mut map: HashMap<String, BTreeSet<String>> = HashMap::new();
    let mut add = |callee: &str, caller: &str| {
        if callee != caller {
            map.entry(callee.to_owned())
                .or_default()
                .insert(caller.to_owned());
        }
    };
    let mut by_name: HashMap<&str, Vec<&SymbolRecord>> = HashMap::new();
    for rec in graph.records() {
        if let Some(name) = rec.symref.name() {
            by_name.entry(name).or_default().push(rec);
        }
    }
    for edge in graph.call_edges() {
        match edge {
            CallEdge::Resolved { caller, callee } => add(callee.path(), caller.path()),
            CallEdge::Ambiguous { caller, candidates } => {
                for c in candidates {
                    add(c.path(), caller.path());
                }
            }
            CallEdge::Unresolved {
                caller,
                name,
                qualifier,
            } => {
                for rec in by_name.get(name.as_str()).into_iter().flatten() {
                    let possible = match qualifier {
                        Some(q) => graph.admits(q, rec) != Admit::No,
                        None => true,
                    };
                    if possible {
                        add(rec.symref.path(), caller.path());
                    }
                }
            }
        }
    }
    map
}

/// Resolve `reference` against the ledger and compute the files of the scoped run.
pub(crate) fn resolve(
    snap: &Snapshot<Frob>,
    reference: &str,
    hops: u32,
    lease_cfg: LeaseConfig,
) -> Result<TicketScope, CheckError> {
    let shared_files = lease_cfg.shared_files.clone();
    let state = snap.inputs.ledger.as_ref().ok_or_else(|| {
        CheckError::NoLedger(
            "--ticket needs a git repository whose ledger holds tickets".to_owned(),
        )
    })?;
    let ledger = &state.ledger;
    let id = ledger
        .resolve(reference)
        .map_err(|e| CheckError::Ticket(format!("{reference}: {e}")))?;
    let view = ledger
        .show(id)
        .map_err(|e| CheckError::Ticket(format!("{reference}: {e}")))?;
    let handle = view.summary.handle.clone();
    let live = match LeaseStore::open(ledger.repo(), lease_cfg, ledger.clock().clone())
        .and_then(|s| s.live_lease(id))
    {
        Ok(l) => l,
        Err(err) => {
            tracing::warn!(%err, "lease lookup failed; using the ticket scope");
            None
        }
    };
    let (globs, lease) = if let Some(l) = live {
        tracing::info!(%handle, scope = ?l.scope, "scoping to the lease");
        (l.scope.clone(), l)
    } else {
        {
            let globs = view.ticket.front.scope.clone();
            tracing::info!(%handle, scope = ?globs, "no live lease; scoping to the ticket scope");
            let now = ledger.clock().now().seconds();
            let lease = Lease {
                ticket: id,
                holder: Holder {
                    actor: String::new(),
                    worktree: snap.core.root.clone(),
                },
                scope: globs.clone(),
                acquired_at: now,
                renewed_at: now,
                ttl_secs: 0,
                history: Vec::new(),
            };
            (globs, lease)
        }
    };
    let set = glob_set(&globs).map_err(|e| CheckError::Ticket(format!("{handle}: {e}")))?;
    let mut files: BTreeSet<String> = snap
        .core
        .entries
        .iter()
        .filter(|e| set.is_match(e.path.as_str()))
        .map(|e| e.path.clone())
        .collect();
    let deps = dependents(&snap.inputs.ack.graph);
    let mut frontier = files.clone();
    for hop in 0..hops {
        let next: BTreeSet<String> = frontier
            .iter()
            .filter_map(|f| deps.get(f))
            .flatten()
            .filter(|f| !files.contains(*f))
            .cloned()
            .collect();
        tracing::debug!(hop, added = next.len(), "dependents added");
        if next.is_empty() {
            break;
        }
        files.extend(next.iter().cloned());
        frontier = next;
    }
    tracing::info!(%handle, files = files.len(), "ticket file set computed");
    Ok(TicketScope {
        handle,
        lease,
        files,
        shared_files,
    })
}

fn id_of<R: Rule>(rule: &R) -> RuleId {
    rule.meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

fn unresolved<R: Rule>(rule: &R, message: String) -> Finding {
    Finding::new(id_of(rule), Severity::Unresolved, None, message, "base")
}

/// Root lock files written by frob's own verbs; SCOPE001 never counts them as branch changes.
const BOOKKEEPING_LOCKS: [&str; 2] = ["frob.lock", "grimble.lock"];

/// Paths this branch changed since it left `base`, committed or not, minus ledger bookkeeping.
///
/// Diffs the worktree against `merge_base(base, HEAD)` (three-dot semantics) so
/// commits that only landed on `base` never count. Everything under the ledger
/// directory is written by frob's own ledger commits, so it is exempt; so are
/// the root lock files (`frob.lock` by `frob ack`, `grimble.lock`), whose
/// content stays under the drift rules.
fn branch_changes(
    repo: &Repo,
    base: &str,
    ledger: &LedgerConfig,
) -> Result<Vec<RelPath>, GitError> {
    let from = if let Some(mb) = repo.merge_base(base, "HEAD")? {
        tracing::debug!(base, merge_base = %mb, "SCOPE001 diffs from the merge base");
        TreeRef::Oid(mb)
    } else {
        tracing::warn!(
            base,
            "no merge base with HEAD; diffing against the base tip"
        );
        TreeRef::Ref(base.to_owned())
    };
    let paths = repo
        .diff_names(&from, &TreeRef::WorkTree)?
        .into_iter()
        .filter(|c| {
            let ledger = ledger.is_ledger_path(&c.path);
            if ledger {
                tracing::trace!(path = %c.path, "ledger path exempt from SCOPE001");
            }
            let lock = BOOKKEEPING_LOCKS.contains(&c.path.as_str());
            if lock {
                tracing::trace!(path = %c.path, "lock file exempt from SCOPE001");
            }
            !ledger && !lock
        })
        .filter_map(|c| RelPath::new(c.path).ok())
        .collect();
    Ok(paths)
}

// frob:ticket 01M413V8CDKKBSBV8JDV92VDGB
/// `SCOPE001` (diff against `base` versus the lease) and `TICK002` (referenced tickets on `base`).
///
/// `diff` receives the paths of the branch diff (the set SCOPE001 judged) when it could be computed.
pub(crate) fn ticket_rules(
    snap: &Snapshot<Frob>,
    scope: &TicketScope,
    base: &str,
    diff: &mut Option<BTreeSet<String>>,
) -> Vec<Finding> {
    let shared = &scope.shared_files;
    let Some(state) = &snap.inputs.ledger else {
        return Vec::new();
    };
    let repo = match Repo::discover(&snap.core.root) {
        Ok(r) => r,
        Err(err) => {
            let msg = format!("repository unreadable ({err}); SCOPE001 and TICK002 not evaluated");
            return vec![
                unresolved(&frob_lease::Scope001, msg.clone()),
                unresolved(&frob_ledger::rules::Tick002, msg),
            ];
        }
    };
    if let Err(err) = repo.rev_parse(base) {
        tracing::warn!(base, %err, "base ref does not resolve");
        let msg = format!("base ref `{base}` does not resolve ({err}); set --base or [check] base");
        return vec![
            unresolved(
                &frob_lease::Scope001,
                format!("{msg}; SCOPE001 not evaluated"),
            ),
            unresolved(
                &frob_ledger::rules::Tick002,
                format!("{msg}; TICK002 not evaluated"),
            ),
        ];
    }
    let mut out = Vec::new();
    match branch_changes(&repo, base, state.ledger.config()) {
        Ok(paths) => {
            out.extend(scope001(&paths, &scope.lease, shared));
            tracing::debug!(paths = paths.len(), "ticket diff set recorded");
            *diff = Some(paths.iter().map(|p| p.as_str().to_owned()).collect());
        }
        Err(err) => out.push(unresolved(
            &frob_lease::Scope001,
            format!("diff against `{base}` failed ({err}); SCOPE001 not evaluated"),
        )),
    }
    let mut ids: BTreeSet<&str> = BTreeSet::new();
    for d in snap
        .inputs
        .directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "ticket")
    {
        let in_scope = snap
            .inputs
            .ack
            .files
            .path(d.span.file)
            .is_some_and(|p| scope.files.contains(p));
        if let (true, Some(tok)) = (in_scope, d.args.positional.first()) {
            ids.insert(tok.value.as_str());
        }
    }
    let ids: Vec<&str> = ids.into_iter().collect();
    match frob_ledger::rules::tick002(&ids, base, &state.ledger) {
        Ok(f) => out.extend(f),
        Err(err) => out.push(unresolved(
            &frob_ledger::rules::Tick002,
            format!("TICK002 could not read `{base}` ({err})"),
        )),
    }
    out
}

//! `--ticket` scoping: the ticket's files plus dependents, and the diff-based rules.

use std::collections::{BTreeSet, HashMap};

use frob_lease::{Holder, Lease, LeaseConfig, LeaseStore, overlap::glob_set, scope001};
use frob_ledger::model::Stamp;
use gob_git::{RelPath, Repo, TreeRef};
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_symbols::{CallEdge, SymbolGraph};

use crate::error::CheckError;
use crate::snapshot::Snapshot;

/// A resolved `--ticket`: where its scope lies and the lease SCOPE001 compares against.
pub(crate) struct TicketScope {
    /// The ticket handle with `~`.
    pub handle: String,
    /// The live lease, or one synthesized from the ticket scope.
    pub lease: Lease,
    /// Walked files in scope plus `ticket_hops` hops of dependents.
    pub files: BTreeSet<String>,
}

/// Files whose symbols call into a symbol of the keyed file, from the call edges.
fn dependents(graph: &SymbolGraph) -> HashMap<String, BTreeSet<String>> {
    let mut map: HashMap<String, BTreeSet<String>> = HashMap::new();
    let mut add = |callee: &str, caller: &str| {
        if callee != caller {
            map.entry(callee.to_owned())
                .or_default()
                .insert(caller.to_owned());
        }
    };
    for edge in graph.call_edges() {
        match edge {
            CallEdge::Resolved { caller, callee } => add(callee.path(), caller.path()),
            CallEdge::Ambiguous { caller, candidates } => {
                for c in candidates {
                    add(c.path(), caller.path());
                }
            }
            CallEdge::Unresolved { .. } => {}
        }
    }
    map
}

/// Resolve `reference` against the ledger and compute the files of the scoped run.
pub(crate) fn resolve(
    snap: &Snapshot,
    reference: &str,
    hops: u32,
    lease_cfg: LeaseConfig,
) -> Result<TicketScope, CheckError> {
    let state = snap.ledger.as_ref().ok_or_else(|| {
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
    let live = match LeaseStore::open(ledger.repo(), lease_cfg).and_then(|s| s.live_lease(id)) {
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
            let now = Stamp::now();
            let lease = Lease {
                ticket: id,
                holder: Holder {
                    actor: String::new(),
                    worktree: snap.root.clone(),
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
        .entries
        .iter()
        .filter(|e| set.is_match(e.path.as_str()))
        .map(|e| e.path.clone())
        .collect();
    let deps = dependents(&snap.ack.graph);
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

/// `SCOPE001` (diff against `base` versus the lease) and `TICK002` (referenced tickets on `base`).
pub(crate) fn ticket_rules(
    snap: &Snapshot,
    scope: &TicketScope,
    base: &str,
    shared: &[String],
) -> Vec<Finding> {
    let Some(state) = &snap.ledger else {
        return Vec::new();
    };
    let repo = match Repo::discover(&snap.root) {
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
    match repo.diff_names(&TreeRef::Ref(base.to_owned()), &TreeRef::WorkTree) {
        Ok(changed) => {
            let paths: Vec<RelPath> = changed
                .iter()
                .filter_map(|c| RelPath::new(c.path.clone()).ok())
                .collect();
            out.extend(scope001(&paths, &scope.lease, shared));
        }
        Err(err) => out.push(unresolved(
            &frob_lease::Scope001,
            format!("diff against `{base}` failed ({err}); SCOPE001 not evaluated"),
        )),
    }
    let mut ids: BTreeSet<&str> = BTreeSet::new();
    for d in snap
        .directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "ticket")
    {
        let in_scope = snap
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

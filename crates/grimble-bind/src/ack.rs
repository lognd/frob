//! Planning `grimble ack`: which identities and flows an attestation may cover and what the
//! lock becomes (binding.md 5.3 and 5.5). Nothing is written here; the verb commits the bytes.
//!
//! Honesty rules (5.3 item 1): only a Must row with Exact facets can be acked. A May row, an
//! unbound identity, an F0 or F1 language or a facet with a parse hole is refused with the list
//! of rows, because the tool cannot see what a human would be attesting. Acking a flow covers
//! both end identities; acking a contract covers its shape identity; a node is never acked
//! wholesale.

// frob:ticket 01M3Z714820D1SK6X44T9R1B70

use std::collections::BTreeSet;
use std::path::Path;

use gob_lock::{
    Current, CurrentFlow, CurrentSymbol, FlowEnd, LockError, LockFile, Plan, PlanError,
    PlanOptions, file_name,
};

use crate::Binding;
use crate::PRODUCT;
use crate::drift::{End, Shape, live_end, live_shape};
use crate::live::LiveSymbol;
use crate::types::{Role, Row, Source, Status};

/// What the caller asked `grimble ack` to do.
#[derive(Debug, Clone, Default)]
pub struct AckRequest {
    /// Flows (`flow/x` or `x`), contracts, symrefs or repo paths.
    pub targets: Vec<String>,
    /// Re-ack every lock entry that still exists (`--all`).
    pub all: bool,
    /// The reason (binding.md 5.3): mandatory, [`plan_ack`] refuses a missing or blank one.
    pub reason: Option<String>,
    /// `--rename OLD NEW` pairs, applied before the rest.
    pub renames: Vec<(String, String)>,
    /// `Name <email>` or `unknown`.
    pub actor: String,
    /// RFC 3339 UTC timestamp.
    pub at: String,
}

/// Why an ack could not be planned.
#[derive(Debug, thiserror::Error)]
pub enum AckError {
    /// `grimble.lock` could not be read.
    #[error(transparent)]
    Lock(#[from] LockError),
    /// The planner refused: empty selection, or a stale lock not yet migrated (E-LOCK-REATTEST).
    #[error(transparent)]
    Plan(#[from] PlanError),
    /// No reason was given; an ack is an attestation and always says why (binding.md 5.3).
    #[error(
        "E-ACK-REASON: grimble ack needs a reason; rerun with --reason \"why the current state is acknowledged\""
    )]
    ReasonRequired,
    /// A target names nothing this snapshot knows.
    #[error("E-ACK-RESOLVE: `{input}`: {why}")]
    Resolve {
        /// What the caller typed.
        input: String,
        /// Why it did not resolve.
        why: String,
    },
    /// A target is not Must and Exact; the lines say which rows and why.
    #[error("E-ACK-REFUSED: {target} cannot be acked:\n  {}", .lines.join("\n  "))]
    Refused {
        /// The target.
        target: String,
        /// One line per offending row or reason.
        lines: Vec<String>,
    },
    /// A `--rename` pairing does not hold (5.5 item 1).
    #[error("E-ACK-RENAME: {old} -> {new}: {why}")]
    Rename {
        /// The old anchor.
        old: String,
        /// The new anchor.
        new: String,
        /// Which condition failed.
        why: String,
    },
}

/// What an ack will do: the planner's result and the renames applied.
#[derive(Debug, Clone)]
pub struct AckPlan {
    /// The lock after the ack, with what was acked, re-attested and dropped.
    pub plan: Plan,
    /// `(old, new)` pairs re-keyed by `--rename`.
    pub renamed: Vec<(String, String)>,
}

fn current_symbol(l: &LiveSymbol) -> CurrentSymbol {
    CurrentSymbol {
        identity: None,
        facets: l.facets.clone(),
        targets: Vec::new(),
    }
}

fn row_line(r: &Row) -> String {
    format!(
        "{} {} {} {}{}",
        r.entity,
        r.role.as_str(),
        r.identity.as_deref().unwrap_or("-"),
        r.status.as_str(),
        r.reason
            .as_deref()
            .map_or_else(String::new, |x| format!(" ({x})"))
    )
}

fn is_bound(r: &Row) -> bool {
    r.status == Status::Must && r.source != Source::Residual
}

/// `Ok` when `symref` is bound at Must by some row and its facets are Exact.
fn acceptable<'a>(b: &'a Binding, symref: &str, target: &str) -> Result<&'a LiveSymbol, AckError> {
    let refuse = |lines: Vec<String>| AckError::Refused {
        target: target.to_owned(),
        lines,
    };
    let Some(live) = b.live.symbols.get(symref) else {
        return Err(refuse(vec![format!(
            "{symref}: no such symbol in the walk"
        )]));
    };
    let rows: Vec<&Row> = b
        .rows
        .iter()
        .filter(|r| r.identity.as_deref() == Some(symref))
        .collect();
    if !rows.iter().any(|r| is_bound(r)) {
        let mut lines: Vec<String> = rows.iter().map(|r| row_line(r)).collect();
        if lines.is_empty() {
            lines.push(format!("{symref}: bound by no entity"));
        }
        return Err(refuse(lines));
    }
    if let Some(reason) = live.inexact() {
        return Err(refuse(vec![format!(
            "{symref}: facets are not Exact ({})",
            reason.code()
        )]));
    }
    Ok(live)
}

fn end_of_flow(
    b: &Binding,
    flow: &str,
    role: Role,
    recorded: Option<&str>,
    target: &str,
) -> Result<(FlowEnd, LiveSymbol), AckError> {
    match live_end(&b.rows, &b.live, flow, role, recorded) {
        End::Exact { identity, contract } => {
            let live = b.live.symbols[&identity].clone();
            Ok((
                FlowEnd {
                    identity,
                    contract,
                    shape_contract: None,
                },
                live,
            ))
        }
        End::Absent => Err(AckError::Refused {
            target: target.to_owned(),
            lines: vec![format!("{flow} has no {} row", role.as_str())],
        }),
        End::Unresolved(reason, why) => Err(AckError::Refused {
            target: target.to_owned(),
            lines: vec![format!("{why} ({})", reason.code())],
        }),
    }
}

/// Adds `flow` and both end symbols to `cur`; the error says which end cannot be attested.
fn add_flow(
    b: &Binding,
    flow: &str,
    recorded: Option<&gob_lock::FlowEntry>,
    target: &str,
    cur: &mut Current,
) -> Result<(), AckError> {
    let (mut p, pl) = end_of_flow(
        b,
        flow,
        Role::Producer,
        recorded.map(|r| r.producer.identity.as_str()),
        target,
    )?;
    let (mut c, cl) = end_of_flow(
        b,
        flow,
        Role::Consumer,
        recorded.map(|r| r.consumer.identity.as_str()),
        target,
    )?;
    if let Some(k) = b.flow_contracts.get(flow) {
        match live_shape(&b.rows, &b.live, &k.anchor) {
            Shape::Exact(d) => {
                p.shape_contract = Some(d.clone());
                c.shape_contract = Some(d);
            }
            Shape::Absent | Shape::Unresolved(..) => {
                tracing::warn!(flow, contract = %k.anchor, "contract shape is not Exact; the ack records no shape digest");
            }
        }
    }
    cur.symbols.insert(p.identity.clone(), current_symbol(&pl));
    cur.symbols.insert(c.identity.clone(), current_symbol(&cl));
    cur.flows.insert(
        flow.to_owned(),
        CurrentFlow {
            producer: p,
            consumer: c,
        },
    );
    Ok(())
}

fn entity_anchor(b: &Binding, t: &str) -> Option<String> {
    let has = |a: &str| b.rows.iter().any(|r| r.entity == a);
    if has(t) {
        return Some(t.to_owned());
    }
    ["flow/", "contract/"]
        .iter()
        .map(|k| format!("{k}{t}"))
        .find(|a| has(a))
}

/// Resolves one target into `cur`, returning the keys to ack.
fn resolve(b: &Binding, t: &str, cur: &mut Current) -> Result<Vec<String>, AckError> {
    if let Some(anchor) = entity_anchor(b, t) {
        if anchor.starts_with("flow/") {
            add_flow(b, &anchor, None, t, cur)?;
            let f = &cur.flows[&anchor];
            return Ok(vec![
                anchor.clone(),
                f.producer.identity.clone(),
                f.consumer.identity.clone(),
            ]);
        }
        if anchor.starts_with("contract/") {
            let shapes: Vec<&Row> = b
                .rows
                .iter()
                .filter(|r| r.entity == anchor && r.role == Role::Shape && is_bound(r))
                .collect();
            let [shape] = shapes.as_slice() else {
                return Err(AckError::Refused {
                    target: t.to_owned(),
                    lines: vec![format!(
                        "{anchor} has {} Must shape rows, need one",
                        shapes.len()
                    )],
                });
            };
            let id = shape.identity.clone().unwrap_or_default();
            let live = acceptable(b, &id, t)?;
            cur.symbols.insert(id.clone(), current_symbol(live));
            return Ok(vec![id]);
        }
        return Err(AckError::Resolve {
            input: t.to_owned(),
            why:
                "a node or claim is not digest-locked wholesale; ack a flow, a contract or a symref"
                    .to_owned(),
        });
    }
    if t.contains("::") {
        let live = acceptable(b, t, t)?;
        cur.symbols.insert(t.to_owned(), current_symbol(live));
        return Ok(vec![t.to_owned()]);
    }
    let in_file: Vec<&String> = b
        .live
        .symbols
        .iter()
        .filter(|(_, l)| l.path == t)
        .map(|(k, _)| k)
        .collect();
    if in_file.is_empty() {
        return Err(AckError::Resolve {
            input: t.to_owned(),
            why: "not a bound entity anchor, a symref or a path with symbols".to_owned(),
        });
    }
    let mut keys = Vec::new();
    for k in in_file {
        match acceptable(b, k, t) {
            Ok(live) => {
                cur.symbols.insert(k.clone(), current_symbol(live));
                keys.push(k.clone());
            }
            Err(err) => {
                tracing::debug!(symref = %k, %err, "path ack skips a symbol that is not Must and Exact");
            }
        }
    }
    if keys.is_empty() {
        return Err(AckError::Refused {
            target: t.to_owned(),
            lines: vec!["no symbol of the file is bound at Must with Exact facets".to_owned()],
        });
    }
    Ok(keys)
}

fn apply_renames(
    b: &Binding,
    lock: &mut LockFile,
    req: &AckRequest,
    reason: &str,
) -> Result<(), AckError> {
    let stale = lock.reattest();
    if !stale.is_empty() && !req.renames.is_empty() {
        return Err(PlanError::MigrationRequired {
            entries: stale.len(),
            file_version: lock.version,
            digest_scheme: lock.digest_scheme,
        }
        .into());
    }
    for (old, new) in &req.renames {
        let fail = |why: &str| AckError::Rename {
            old: old.clone(),
            new: new.clone(),
            why: why.to_owned(),
        };
        let Some(entry) = lock.entries.get(old) else {
            return Err(fail("the lock has no entry for the old anchor"));
        };
        if b.live.symbols.contains_key(old) {
            return Err(fail("the old anchor still exists, so this is not a rename"));
        }
        if lock.entries.contains_key(new) {
            return Err(fail("the new anchor already has an entry"));
        }
        let live = acceptable(b, new, new).map_err(|e| fail(&e.to_string()))?;
        if live.facets.body != entry.body {
            return Err(fail(
                "the Body of the new anchor differs from the acked Body",
            ));
        }
        if !lock.rename(old, new) {
            return Err(fail("the lock refused the re-key"));
        }
        lock.log_rename(old, new, &req.actor, &req.at, reason);
    }
    Ok(())
}

/// Works out the new lock for an ack without writing anything.
///
/// # Errors
///
/// [`AckError`]: a missing reason, an unreadable lock, a target that does not resolve or is not Must and Exact, a
/// rename that does not hold, or the planner's refusals (empty selection; stale lock without
/// `--all --reason`, E-LOCK-REATTEST).
pub fn plan_ack(binding: &Binding, root: &Path, req: &AckRequest) -> Result<AckPlan, AckError> {
    let Some(reason) = req.reason.as_deref().filter(|r| !r.trim().is_empty()) else {
        return Err(AckError::ReasonRequired);
    };
    let mut lock = LockFile::load(&root.join(file_name(PRODUCT)))?;
    apply_renames(binding, &mut lock, req, reason)?;
    let renamed = req.renames.clone();
    let mut cur = Current::default();
    let mut keys: BTreeSet<String> = BTreeSet::new();
    for t in &req.targets {
        keys.extend(resolve(binding, t, &mut cur)?);
    }
    if req.all {
        for k in lock.entries.keys() {
            if let Ok(l) = acceptable(binding, k, k) {
                cur.symbols.insert(k.clone(), current_symbol(l));
            } else {
                tracing::warn!(symref = %k, "acked symbol is not Must and Exact now; --all leaves it alone");
            }
        }
        for (k, fe) in &lock.flows {
            if let Err(err) = add_flow(binding, k, Some(fe), k, &mut cur) {
                tracing::warn!(flow = %k, %err, "acked flow cannot be re-attested now; --all leaves it alone");
            }
        }
    }
    let options = PlanOptions {
        actor: req.actor.clone(),
        at: req.at.clone(),
        reason: req.reason.clone(),
        all: req.all,
    };
    let keys: Vec<String> = keys.into_iter().collect();
    let plan = if renamed.is_empty() || !keys.is_empty() || req.all {
        gob_lock::plan(&lock, &cur, &keys, &options)?
    } else {
        Plan {
            acked: renamed.iter().map(|(_, n)| n.clone()).collect(),
            lock,
            reattested: Vec::new(),
            dropped: Vec::new(),
        }
    };
    tracing::info!(
        acked = plan.acked.len(),
        renamed = renamed.len(),
        "ack planned"
    );
    Ok(AckPlan { plan, renamed })
}

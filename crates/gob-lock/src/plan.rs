//! The product-neutral ack planner: decides the lock after an ack without writing anything.

use std::collections::{BTreeMap, BTreeSet};

use crate::file::{DIGEST_SCHEME, FlowEnd, FlowEntry, LockEntry, LockFile, LockTarget, Reattest};

/// Why a plan could not be made.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PlanError {
    /// Nothing was selected to acknowledge.
    #[error("E-ACK-EMPTY: name a symref or path, or pass --all")]
    NothingToAck,
    /// The lock predates this build; only an all-entries ack with a reason may rewrite it.
    #[error(
        "E-LOCK-REATTEST: the lock has {entries} entries recorded under file version {file_version} / digest scheme {digest_scheme} (this build: scheme {DIGEST_SCHEME}); re-attest them all with `ack --all --reason ...`"
    )]
    MigrationRequired {
        /// How many entries need re-attestation.
        entries: usize,
        /// The file version read.
        file_version: u32,
        /// The digest scheme read.
        digest_scheme: u32,
    },
}

/// The five facet digests (hex) of one symbol as it stands now.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct FacetSet {
    /// Signature digest.
    pub sig: String,
    /// Body digest.
    pub body: String,
    /// Doc digest.
    pub doc: String,
    /// Attribute-set digest.
    pub attr: String,
    /// Contract digest.
    pub contract: String,
}

/// A symbol as it stands now: what an ack would record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentSymbol {
    /// The stable identity when it differs from the symref.
    pub identity: Option<String>,
    /// The five facet digests.
    pub facets: FacetSet,
    /// Bound doc sections with their current digests, in any order.
    pub targets: Vec<LockTarget>,
}

/// A flow as it stands now: both ends.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentFlow {
    /// The producing end.
    pub producer: FlowEnd,
    /// The consuming end.
    pub consumer: FlowEnd,
}

/// Everything current that an ack may record, keyed by symref and by flow key.
#[derive(Debug, Clone, Default)]
pub struct Current {
    /// Symbols present now, by symref string.
    pub symbols: BTreeMap<String, CurrentSymbol>,
    /// Flows present now, by flow key.
    pub flows: BTreeMap<String, CurrentFlow>,
}

/// Who acks, when, why, and whether the whole lock is re-attested.
#[derive(Debug, Clone, Default)]
pub struct PlanOptions {
    /// `Name <email>` or `unknown`.
    pub actor: String,
    /// RFC 3339 UTC timestamp.
    pub at: String,
    /// The reason; required to migrate a stale lock.
    pub reason: Option<String>,
    /// Also ack every entry already in the lock that still exists (`--all`).
    pub all: bool,
}

/// What [`plan`] decided: the lock to write and which entries changed.
#[derive(Debug, Clone)]
pub struct Plan {
    /// The lock after the ack.
    pub lock: LockFile,
    /// Symrefs and flow keys whose entry was added or changed, sorted.
    pub acked: Vec<String>,
    /// Entries that were stale and are now re-attested (empty unless the lock was migrated).
    pub reattested: Vec<Reattest>,
    /// Stale entries whose subject no longer exists, removed by the migration, sorted.
    pub dropped: Vec<String>,
}

fn symbol_entry(cur: &CurrentSymbol, key: &str, opts: &PlanOptions) -> LockEntry {
    let mut targets = cur.targets.clone();
    targets.sort_by(|a, b| a.target.cmp(&b.target));
    targets.dedup_by(|a, b| a.target == b.target);
    LockEntry {
        identity: cur.identity.clone().filter(|i| i != key),
        sig: cur.facets.sig.clone(),
        body: cur.facets.body.clone(),
        doc: cur.facets.doc.clone(),
        attr: cur.facets.attr.clone(),
        contract: cur.facets.contract.clone(),
        acked_by: opts.actor.clone(),
        acked_at: opts.at.clone(),
        reason: opts.reason.clone(),
        targets,
    }
}

fn same_facets(a: &LockEntry, b: &LockEntry) -> bool {
    (
        &a.identity,
        &a.sig,
        &a.body,
        &a.doc,
        &a.attr,
        &a.contract,
        &a.targets,
    ) == (
        &b.identity,
        &b.sig,
        &b.body,
        &b.doc,
        &b.attr,
        &b.contract,
        &b.targets,
    )
}

/// Works out the new lock for an ack without writing anything.
///
/// `targets` are already-resolved symrefs or flow keys; with `options.all`
/// every lock entry whose subject still exists joins them. A symbol or flow
/// already recorded at the current digests is left alone. A lock written under
/// another file version or digest scheme is migrated only by an `all` plan with
/// a reason: each present entry is re-recorded under the current scheme and each
/// vanished one is dropped and reported, never silently accepted.
///
/// # Errors
///
/// [`PlanError::NothingToAck`] for an empty selection, [`PlanError::MigrationRequired`]
/// when the lock is stale and the plan is not `all` with a reason.
pub fn plan(
    lock: &LockFile,
    current: &Current,
    targets: &[String],
    options: &PlanOptions,
) -> Result<Plan, PlanError> {
    let stale = lock.reattest();
    if !stale.is_empty() && (!options.all || options.reason.is_none()) {
        return Err(PlanError::MigrationRequired {
            entries: stale.len(),
            file_version: lock.version,
            digest_scheme: lock.digest_scheme,
        });
    }
    let mut selected: BTreeSet<&str> = targets.iter().map(String::as_str).collect();
    if options.all {
        selected.extend(
            lock.entries
                .keys()
                .filter(|k| current.symbols.contains_key(*k))
                .chain(lock.flows.keys().filter(|k| current.flows.contains_key(*k)))
                .map(String::as_str),
        );
    }
    if selected.is_empty() && stale.is_empty() {
        return Err(PlanError::NothingToAck);
    }
    let migrating = lock.is_stale();
    let mut next = lock.clone();
    let mut acked = Vec::new();
    let mut dropped = Vec::new();
    if migrating {
        for r in &stale {
            let present =
                current.symbols.contains_key(&r.key) || current.flows.contains_key(&r.key);
            if !present {
                next.entries.remove(&r.key);
                next.flows.remove(&r.key);
                dropped.push(r.key.clone());
            }
        }
        next.adopt_current_header();
        tracing::warn!(
            reattested = stale.len() - dropped.len(),
            dropped = dropped.len(),
            "lock migrated to the current format and digest scheme"
        );
    }
    for key in selected {
        if let Some(cur) = current.symbols.get(key) {
            let fresh = symbol_entry(cur, key, options);
            if !migrating
                && next
                    .entries
                    .get(key)
                    .is_some_and(|o| same_facets(o, &fresh))
            {
                tracing::debug!(symref = key, "already acked at these digests");
                continue;
            }
            tracing::info!(symref = key, "ack recorded");
            next.entries.insert(key.to_owned(), fresh);
            acked.push(key.to_owned());
        } else if let Some(cur) = current.flows.get(key) {
            let same = next
                .flows
                .get(key)
                .is_some_and(|o| o.producer == cur.producer && o.consumer == cur.consumer);
            if same && !migrating {
                tracing::debug!(flow = key, "already acked at these contracts");
                continue;
            }
            tracing::info!(flow = key, "flow ack recorded");
            next.flows.insert(
                key.to_owned(),
                FlowEntry {
                    producer: cur.producer.clone(),
                    consumer: cur.consumer.clone(),
                    acked_by: options.actor.clone(),
                    acked_at: options.at.clone(),
                    reason: options.reason.clone(),
                },
            );
            acked.push(key.to_owned());
        }
    }
    let reattested = stale
        .into_iter()
        .filter(|r| !dropped.contains(&r.key))
        .collect();
    dropped.sort();
    Ok(Plan {
        lock: next,
        acked,
        reattested,
        dropped,
    })
}

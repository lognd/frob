//! Create protocol (mirror.md 3.3 "Create protocol"; F3, F5).
//!
//! Before a create the run derives a nonce, flags the shard create-uncertain with the nonce and
//! start time, and journals "create started"; both are durable before the tracker is called. A
//! create that is confirmed clears the flag. A create whose outcome is unknown leaves it set, and
//! while it is set no further create is made for the ticket. [`recover`] lists the bot's issues
//! back to the create's start time and matches the nonce through the verified creation marker.
//! GitHub's create has no idempotency key, so a timed-out create that lands after its retry can
//! still leave one extra issue; that is bounded here and closed by the duplicates pass.

// frob:ticket 01M4052S7VEWJEYG78GNA1Z28V

use thiserror::Error;
use tracing::{debug, info, warn};

use crate::adapter::{AdapterError, AdapterResult, CreateOutcome, IssueRef, TrackerAdapter};
use crate::cursor::{Committed, PendingCursor};
use crate::github::lookup::{ListingSource, lookup_since};
use crate::github::read::{HistorySource, creation_revision};
use crate::journal::{JournalEntry, WriteStatus, journaled_write, value_digest};
use crate::keyring::Keyring;
use crate::mapfile::{CreateUncertain, MapError, Shard, ShardStore, write_shard};
use crate::marker::{MarkerVerdict, evaluate};
use crate::projection::IssueProjection;

/// Journal field name of a "create started" entry.
pub const CREATE_FIELD: &str = "create";

/// Failures of the create protocol.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum CreateError {
    /// The shard or journal could not be committed; no create was sent.
    #[error("map store: {0}")]
    Map(#[from] MapError),
    /// Listing or reading the tracker failed; the ticket stays create-uncertain.
    #[error("tracker: {0}")]
    Tracker(#[from] AdapterError),
    /// The tracker returned an issue reference that is not a number.
    #[error("tracker returned a non-numeric issue reference {0:?}")]
    BadIssueRef(String),
}

/// Where a create attempt ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreateStep {
    /// The tracker confirmed the issue; the shard (committed) names it.
    Created(CreatedIssue),
    /// Outcome unknown: the shard (committed) stays create-uncertain until [`recover`] runs.
    Uncertain(Shard),
    /// A prior create is still uncertain: no request was made.
    Blocked(Shard),
    /// The tracker definitely rejected the create; the flag is cleared and a retry is allowed.
    Rejected(Shard, String),
}

/// A confirmed create: the committed shard and the history cursor held across it (F3).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CreatedIssue {
    /// The committed shard naming the new issue.
    pub shard: Shard,
    /// The cursor taken before the ticket's issues were listed, unchanged by the create.
    pub pending: PendingCursor,
}

impl CreatedIssue {
    /// Stores the held cursor into the shard once the proposals it covers are committed.
    ///
    /// # Errors
    /// `CreateError::Map` when the shard cannot be committed.
    pub fn store_cursor<S: ShardStore>(
        self,
        store: &mut S,
        proof: Committed,
    ) -> Result<Shard, CreateError> {
        let shard = self.pending.advance(self.shard, proof);
        write_shard(store, &shard)?;
        info!(ulid = %shard.ulid, "create: held history cursor stored");
        Ok(shard)
    }
}

/// What recovery of a create-uncertain ticket concluded.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Recovery {
    /// The nonce matched an issue; it is adopted and the uncertainty is cleared.
    Adopted(Shard),
    /// The listing back to the start time holds no match; the flag is cleared and a create may
    /// be retried (a late landing of the first attempt can then add one extra issue).
    NotLanded(Shard),
    /// The shard was not create-uncertain; nothing changed.
    Nothing(Shard),
}

/// Derives the nonce of a create from the ticket, the run and the start time.
pub fn derive_nonce(ulid: &str, run_id: &str, started: &str) -> String {
    let mut h = blake3::Hasher::new();
    for part in [ulid, run_id, started] {
        h.update(&u64::try_from(part.len()).unwrap_or(u64::MAX).to_le_bytes());
        h.update(part.as_bytes());
    }
    h.finalize().to_hex().as_str()[..32].to_owned()
}

fn parse_number(issue: &IssueRef) -> Result<u64, CreateError> {
    issue
        .0
        .parse()
        .map_err(|_| CreateError::BadIssueRef(issue.0.clone()))
}

/// Runs the create protocol for the ticket in `shard`.
///
/// `pending` is the history cursor taken before the ticket's issues were listed; it is returned
/// untouched with a confirmed create so it survives it. `started` is the create-start time
/// (RFC 3339 UTC).
///
/// # Errors
/// `CreateError::Map` when the create-started record cannot be committed (nothing is sent), or
/// when the result cannot be committed; `CreateError::BadIssueRef` for a non-numeric reference.
pub fn create_issue<S: ShardStore, A: TrackerAdapter>(
    store: &mut S,
    adapter: &mut A,
    mut shard: Shard,
    projection: &IssueProjection,
    run_id: &str,
    started: &str,
    pending: PendingCursor,
) -> Result<CreateStep, CreateError> {
    if shard.create_uncertain.is_some() {
        warn!(ulid = %shard.ulid, "create: blocked, a prior create is uncertain");
        return Ok(CreateStep::Blocked(shard));
    }
    let nonce = derive_nonce(&shard.ulid, run_id, started);
    shard.create_uncertain = Some(CreateUncertain {
        nonce: nonce.clone(),
        started: started.to_owned(),
    });
    write_shard(store, &shard)?;
    info!(ulid = %shard.ulid, run_id, "create: started");
    let entry = JournalEntry {
        issue: IssueRef(format!("create:{}", shard.ulid)),
        field: CREATE_FIELD.to_owned(),
        value_digest: value_digest(&nonce),
        run_id: run_id.to_owned(),
        time: started.to_owned(),
        status: WriteStatus::Unconfirmed,
    };
    let outcome = journaled_write(store, &shard.ulid.clone(), entry, || {
        adapter.create(projection, &nonce)
    })?;
    match outcome {
        CreateOutcome::Created(issue) => {
            shard.issue_number = Some(parse_number(&issue)?);
            shard.create_uncertain = None;
            write_shard(store, &shard)?;
            info!(ulid = %shard.ulid, issue = %issue.0, "create: confirmed");
            Ok(CreateStep::Created(CreatedIssue { shard, pending }))
        }
        CreateOutcome::Failed(reason) => {
            shard.create_uncertain = None;
            write_shard(store, &shard)?;
            warn!(ulid = %shard.ulid, %reason, "create: rejected");
            Ok(CreateStep::Rejected(shard, reason))
        }
        CreateOutcome::Unknown => {
            warn!(ulid = %shard.ulid, "create: outcome unknown, ticket is create-uncertain");
            Ok(CreateStep::Uncertain(shard))
        }
    }
}

/// Everything recovery reads: the listing, the history source and the marker trust inputs.
pub struct RecoveryEnv<'a> {
    /// The bot's issue listing, newest first.
    pub listing: &'a dyn ListingSource,
    /// Raw issue reads, for the creation revision.
    pub source: &'a dyn HistorySource,
    /// Keyring verifying marker MACs.
    pub ring: &'a Keyring,
    /// Mirror bot user ids; the first is the creator whose issues are listed.
    pub bot_ids: &'a [u64],
    /// Repository node id the marker MAC is bound to.
    pub repo_node_id: &'a str,
    /// Unix time for key validity.
    pub now: i64,
}

/// Recovers a create-uncertain ticket: lists the bot's issues back to the create's start time and
/// adopts the one whose verified creation marker carries the ticket's ULID and the create's nonce.
///
/// A failed listing or read is returned as an error and leaves the ticket create-uncertain.
///
/// # Errors
/// `CreateError::Tracker` when listing or reading fails; `CreateError::Map` when the result
/// cannot be committed.
pub fn recover<S: ShardStore>(
    store: &mut S,
    env: &RecoveryEnv<'_>,
    mut shard: Shard,
) -> Result<Recovery, CreateError> {
    let (Some(uncertain), Some(&bot)) = (shard.create_uncertain.clone(), env.bot_ids.first())
    else {
        debug!(ulid = %shard.ulid, "recover: nothing to recover");
        return Ok(Recovery::Nothing(shard));
    };
    let found = find_nonce(env, bot, &shard.ulid, &uncertain).inspect_err(|e| {
        warn!(ulid = %shard.ulid, error = %e, "recover: read failed, still uncertain");
    })?;
    shard.create_uncertain = None;
    let result = if let Some(issue) = found {
        shard.issue_number = Some(parse_number(&issue)?);
        info!(ulid = %shard.ulid, issue = %issue.0, "recover: nonce matched, issue adopted");
        Recovery::Adopted(shard.clone())
    } else {
        info!(ulid = %shard.ulid, "recover: no match back to the start time");
        Recovery::NotLanded(shard.clone())
    };
    write_shard(store, &shard)?;
    Ok(result)
}

fn find_nonce(
    env: &RecoveryEnv<'_>,
    bot: u64,
    ulid: &str,
    uncertain: &CreateUncertain,
) -> AdapterResult<Option<IssueRef>> {
    let issues = lookup_since(env.listing, bot, &uncertain.started)?;
    debug!(
        ulid,
        candidates = issues.len(),
        "recover: listed back to start"
    );
    for item in issues {
        let creation = creation_revision(env.source, &item.issue, item.creator_id)?;
        let verdict = evaluate(&creation, env.bot_ids, env.ring, env.repo_node_id, env.now);
        if let MarkerVerdict::Adopted(m) = verdict
            && m.fields.ulid == ulid
            && m.fields.nonce == uncertain.nonce
        {
            return Ok(Some(item.issue));
        }
    }
    Ok(None)
}

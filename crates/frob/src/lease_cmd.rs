//! Keeping a held lease in step with its ticket's scope: `lease widen` and `ticket update`.
//!
//! Ordering (ticket 01M3ZBRRMQ55G1B8VCNKDR4ZBR): the lease is rescoped first,
//! under the lease lock, and only then is the ledger event committed. A refusal
//! (the widened scope overlaps another live lease) therefore leaves both the
//! lease and the ticket untouched; if the ledger commit itself fails after the
//! lease moved, the lease is restored to the old scope. The caller counts as the
//! holder when its ledger actor equals the lease holder's actor (the verb may
//! run from any worktree; the lease keeps the holder's own worktree path).

use frob_lease::error::SAME_TICKET;
use frob_lease::{Holder, Lease, LeaseError, LeaseStore};
use frob_ledger::ops::Patch;
use frob_ledger::{Applied, Ledger, TicketId};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::ticket::{
    ChangeData, cli_err, get, get_many, many_flag, open, open_lease_store, resolve, ticket_arg,
};

/// What the lease side of a scope change did.
enum LeaseSide {
    /// The ticket has no live lease; nothing to refresh.
    None,
    /// The caller holds the lease; it was rescoped from the given globs.
    Refreshed {
        /// Scope before.
        old: Vec<String>,
        /// The holder (as recorded in the lease).
        holder: Holder,
    },
    /// Someone else holds the lease; it was left alone.
    Foreign(Holder),
}

/// The live lease of `id` and whether `actor` holds it.
fn classify(store: &LeaseStore, id: TicketId, actor: &str) -> Result<Option<Lease>, CliError> {
    let lease = store.live_lease(id)?;
    tracing::debug!(ticket = %id, actor, held = lease.is_some(), "lease classified");
    Ok(lease)
}

/// Apply `patch` to ticket `id`, refreshing the caller's lease when the scope changes.
///
/// Returns the ledger result and the warnings to put in the envelope.
pub(crate) fn update_with_lease(
    ctx: &Context,
    ledger: &Ledger,
    id: TicketId,
    patch: &Patch,
) -> Result<(Applied, Vec<String>), CliError> {
    let old = ledger.show(id).map_err(cli_err)?.ticket.front.scope;
    let new = ledger.scope_after(id, patch).map_err(cli_err)?;
    if old == new {
        return Ok((ledger.update(id, patch).map_err(cli_err)?, Vec::new()));
    }
    let (store, _) = open_lease_store(ctx)?;
    let actor = ledger.actor().map_err(cli_err)?;
    let state = match classify(&store, id, &actor)? {
        None => LeaseSide::None,
        Some(l) if l.holder.actor == actor => {
            store.rescope(id, &l.holder, &new, store.config())?;
            tracing::info!(ticket = %id, "lease rescoped ahead of the ledger commit");
            LeaseSide::Refreshed {
                old: l.scope,
                holder: l.holder,
            }
        }
        Some(l) => LeaseSide::Foreign(l.holder),
    };
    let applied = match ledger.update(id, patch) {
        Ok(a) => a,
        Err(e) => {
            if let LeaseSide::Refreshed { old, holder } = &state
                && let Err(r) = store.rescope(id, holder, old, store.config())
            {
                tracing::warn!(ticket = %id, error = %r, "restoring the lease after a failed update failed");
            }
            return Err(cli_err(e));
        }
    };
    let mut warnings = Vec::new();
    if !patch.add_scope.is_empty() {
        let front = &applied.ticket.front;
        warnings.extend(frob_lease::unmatched::scope_warnings(
            ledger.repo(),
            id,
            &patch.add_scope,
            &front.labels,
        ));
    }
    if let LeaseSide::Foreign(holder) = state {
        tracing::warn!(ticket = %id, %holder, "scope changed but the lease belongs to someone else");
        warnings.push(format!(
            "lease not refreshed: ticket {id} is leased by {holder}; the holder must run `frob lease widen {id}`"
        ));
    }
    Ok((applied, warnings))
}

/// Output of `lease widen`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct WidenData {
    /// The ticket change (events empty when only the lease moved).
    pub ticket: ChangeData,
    /// The ticket's scope, which is now the lease's scope.
    pub scope: Vec<String>,
    /// The lease after the rescope.
    pub lease: Lease,
}

/// Re-read the ticket scope (optionally adding globs to it) and rescope the caller's lease to match.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "lease widen",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct LeaseWiden {
    ticket: String,
    globs: Vec<String>,
    new_globs: Vec<String>,
}

impl Command for LeaseWiden {
    type Data = WidenData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(ticket_arg()).arg(many_flag(
            "glob",
            "Scope glob to add to the ticket first (repeatable)",
        ))
        .arg(many_flag(
            "new-glob",
            "Like --glob, for files the ticket will create: adds a `creates:` label that silences the zero-match warning (repeatable)",
        ))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            globs: get_many(m, "glob"),
            new_globs: get_many(m, "new-glob"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<WidenData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let (store, _) = open_lease_store(ctx)?;
        let actor = ledger.actor().map_err(cli_err)?;
        let Some(lease) = classify(&store, id, &actor)? else {
            return Err(LeaseError::NotHeld { ticket: id }.into());
        };
        if lease.holder.actor != actor {
            tracing::info!(ticket = %id, holder = %lease.holder, %actor, "lease widen refused: not the holder");
            return Err(LeaseError::Held {
                holder: lease.holder,
                ticket: id,
                since: lease.acquired_at,
                overlap: SAME_TICKET.to_owned(),
            }
            .into());
        }
        let patch = Patch {
            add_scope: [self.globs.clone(), self.new_globs.clone()].concat(),
            add_labels: self
                .new_globs
                .iter()
                .map(|g| frob_lease::unmatched::creates_label(g))
                .collect(),
            ..Patch::default()
        };
        let before = lease.scope.clone();
        let (applied, warnings) = update_with_lease(ctx, &ledger, id, &patch)?;
        let scope = applied.ticket.front.scope.clone();
        let lease = store.rescope(id, &lease.holder, &scope, store.config())?;
        let changed = before != lease.scope;
        tracing::info!(ticket = %id, changed, "lease widen");
        let mut payload = Payload::new(WidenData {
            ticket: ChangeData::from(&applied),
            scope,
            lease,
        })
        .with_already(applied.already && !changed);
        for w in warnings {
            payload = payload.with_warning(w);
        }
        Ok(payload)
    }
}

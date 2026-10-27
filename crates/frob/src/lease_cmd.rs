//! Keeping a held lease in step with its ticket's scope: `lease widen`, `lease release` and `ticket update`.
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
use std::time::Duration;

use crate::ticket::{ChangeData, TicketArg, cli_err, open, open_lease_store, resolve};

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
    wait: Duration,
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
            rescope_waiting(&store, id, &l.holder, &new, wait)?;
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
    if let LeaseSide::Foreign(holder) = state {
        tracing::warn!(ticket = %id, %holder, "scope changed but the lease belongs to someone else");
        warnings.push(format!(
            "lease not refreshed: ticket {id} is leased by {holder}; the holder must run `frob lease widen {id}`"
        ));
    }
    if !patch.add_scope.is_empty() {
        let front = &applied.ticket.front;
        warnings.extend(frob_lease::unmatched::scope_warnings(
            ledger.repo(),
            id,
            &patch.add_scope,
            &front.labels,
        ));
    }
    Ok((applied, warnings))
}

/// Rescope under the lease lock, waiting up to `wait` and reporting the blocking holder on stderr.
fn rescope_waiting(
    store: &LeaseStore,
    id: TicketId,
    holder: &Holder,
    scope: &[String],
    wait: Duration,
) -> Result<Lease, LeaseError> {
    store.rescope_waiting(id, holder, scope, store.config(), wait, |blocker| {
        tracing::warn!(ticket = %id, wait_secs = wait.as_secs(), %blocker, "waiting for the blocking lease holder");
    })
}

/// The `--wait` flag shared by `lease widen` and `ticket update`.
#[derive(Debug, Clone, Copy, Default, clap::Args)]
#[command(about = None, long_about = None)]
pub(crate) struct WaitArg {
    #[arg(
        long = "wait",
        value_name = "SECS",
        default_value_t = 0,
        help = "When a scope addition overlaps another ticket's lease, wait up to SECS seconds (reporting the holder) for it to release; 0 fails at once"
    )]
    pub(crate) secs: u64,
}

/// The `--wait` argument as a duration.
pub(crate) fn wait_duration(a: WaitArg) -> Duration {
    Duration::from_secs(a.secs)
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
    wait: Duration,
}

/// The flags of `lease widen`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct WidenArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long = "glob",
        value_name = "TEXT",
        help = "Scope glob to add to the ticket first (repeatable)"
    )]
    globs: Vec<String>,
    #[arg(
        long = "new-glob",
        value_name = "TEXT",
        help = "Like --glob, for files the ticket will create: adds a `creates:` label that silences the zero-match warning (repeatable)"
    )]
    new_globs: Vec<String>,
    #[command(flatten)]
    wait: WaitArg,
}

impl Command for LeaseWiden {
    type Data = WidenData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<WidenArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<WidenArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            globs: a.globs,
            new_globs: a.new_globs,
            wait: wait_duration(a.wait),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<WidenData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let (store, _) = open_lease_store(ctx)?;
        let actor = ledger.actor().map_err(cli_err)?;
        let lease = own_lease(&store, id, &actor)?;
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
        let (applied, warnings) = update_with_lease(ctx, &ledger, id, &patch, self.wait)?;
        let scope = applied.ticket.front.scope.clone();
        let lease = rescope_waiting(&store, id, &lease.holder, &scope, self.wait)?;
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

/// Output of `lease release`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ReleaseData {
    /// The ticket whose lease was released.
    pub ticket: TicketId,
    /// The lease that was given up; absent when the ticket held none.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub released: Option<Lease>,
}

/// Give up the caller's lease on a finished-but-unlanded ticket; the ticket stays in-progress and `land` re-takes the lease.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "lease release",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct LeaseRelease {
    ticket: String,
}

impl Command for LeaseRelease {
    type Data = ReleaseData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<TicketArg>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TicketArg>(m)?;
        Ok(Self { ticket: a.ticket })
    }

    fn run(&self, ctx: &Context) -> Outcome<ReleaseData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let (store, _) = open_lease_store(ctx)?;
        let actor = ledger.actor().map_err(cli_err)?;
        let released = store.release(id, Some(&actor))?;
        tracing::info!(ticket = %id, %actor, released = released.is_some(), "lease release");
        Ok(Payload::new(ReleaseData {
            ticket: id,
            released: released.clone(),
        })
        .with_already(released.is_none()))
    }
}

/// The caller's live lease on `id`, or the refusal for no lease or someone else's.
fn own_lease(store: &LeaseStore, id: TicketId, actor: &str) -> Result<Lease, CliError> {
    let Some(lease) = classify(store, id, actor)? else {
        return Err(LeaseError::NotHeld { ticket: id }.into());
    };
    if lease.holder.actor != actor {
        tracing::info!(ticket = %id, holder = %lease.holder, %actor, "refused: not the holder");
        return Err(LeaseError::Held {
            holder: lease.holder,
            ticket: id,
            since: lease.acquired_at,
            overlap: SAME_TICKET.to_owned(),
        }
        .into());
    }
    Ok(lease)
}

/// Output of `claim touch` and `lease rekind`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ClaimData {
    /// The ticket whose claim changed.
    pub ticket: TicketId,
    /// The lease after the change.
    pub lease: Lease,
}

/// The `--note` flag of `claim touch`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct TouchArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long = "note",
        value_name = "TEXT",
        help = "What the holder is doing; shown next to the claim"
    )]
    note: Option<String>,
}

/// Soft heartbeat for the caller's claim; an agent harness runs it from a hook while its session lives.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "claim touch",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ClaimTouch {
    ticket: String,
    note: Option<String>,
}

impl Command for ClaimTouch {
    type Data = ClaimData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<TouchArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TouchArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            note: a.note,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ClaimData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let (store, _) = open_lease_store(ctx)?;
        let actor = ledger.actor().map_err(cli_err)?;
        let held = own_lease(&store, id, &actor)?;
        let lease = store.touch(id, &held.holder, self.note.as_deref())?;
        // The ledger event is what other clones observe as soft activity; the lease only serves this one.
        ledger
            .append(
                id,
                frob_ledger::claim_hold::renew_event(self.note.as_deref()),
            )
            .map_err(cli_err)?;
        tracing::info!(ticket = %id, %actor, "claim touch");
        Ok(Payload::new(ClaimData { ticket: id, lease }))
    }
}

/// The `--agent` flag of `lease rekind`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct RekindArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long = "agent",
        value_name = "LABEL",
        help = "Re-claim as this agent (short window); omit to re-claim as a human"
    )]
    agent: Option<String>,
}

/// Re-claim the caller's lease as a human (or as `--agent LABEL`), switching its idle window.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "lease rekind",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct LeaseRekind {
    ticket: String,
    agent: Option<String>,
}

impl Command for LeaseRekind {
    type Data = ClaimData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<RekindArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<RekindArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            agent: a.agent,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ClaimData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let (store, _) = open_lease_store(ctx)?;
        let actor = ledger.actor().map_err(cli_err)?;
        let held = own_lease(&store, id, &actor)?;
        let before = held.holder_kind();
        let lease = store.rekind(id, &held.holder, self.agent.clone())?;
        let changed = before != lease.holder_kind();
        tracing::info!(ticket = %id, %actor, changed, "lease rekind");
        Ok(Payload::new(ClaimData { ticket: id, lease }).with_already(!changed))
    }
}

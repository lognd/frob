//! The proposal verbs: `ticket proposals list` and `ticket proposals decline` (design: `mirror.md` 3.5).
//!
//! Proposals are tracker edits held by reference in the ledger. Listing shows each
//! pending one with its tracker item, field, actor id, time, digest and a capped,
//! escaped excerpt (origin `tracker`, `security.md` 2.10); declining records a reason
//! and appends `proposal-declined`. Accepting, with its guards, is a separate verb.
// frob:ticket 01M3ZXGAWKZPVY6HF9NJ8GAFQV

use frob_check::proposals_summary::pending_by_ticket;
use frob_ledger::event::{EventBody, ProposalCloseData};
use frob_ledger::model::Stamp;
use frob_ledger::proposal::{ProposalState, fold_proposals};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use gob_diagnostics::{TextOrigin, escape_for_origin, escape_non_ascii};
use schemars::JsonSchema;
use serde::Serialize;

use super::{TicketArg, cli_err, open, resolve};

/// Longest excerpt shown, in characters (mirror.md 3.5).
const EXCERPT_CAP: usize = 200;

/// One pending proposal as listed.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ProposalRow {
    /// The ticket it is held on (`~handle`).
    pub ticket: String,
    /// The tracker's event id: what `decline` takes.
    pub tracker_event: String,
    /// The tracker item (issue) id.
    pub item: String,
    /// The ticket field the edit touches.
    pub field: String,
    /// The tracker user id of the editor.
    pub actor_id: String,
    /// When the editor made the edit.
    pub time: Stamp,
    /// Digest of the full proposed value.
    pub digest: String,
    /// Capped, escaped excerpt of the value.
    pub excerpt: String,
    /// Where the text came from: `tracker`.
    pub origin: String,
}

/// Output of `ticket proposals list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ProposalsData {
    /// Number of pending proposals listed.
    pub count: usize,
    /// The pending proposals, by ticket then first-recorded order.
    pub proposals: Vec<ProposalRow>,
}

/// Escape tracker text for display and cap it at [`EXCERPT_CAP`] characters.
fn shown_excerpt(text: &str) -> String {
    let escaped = escape_for_origin(text, &TextOrigin::Tracker);
    escaped.chars().take(EXCERPT_CAP).collect()
}

/// The flags of `ticket proposals list`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ListArgs {
    #[arg(
        value_name = "TICKET",
        help = "Only this ticket (full ULID, ~handle or alias); default every ticket"
    )]
    ticket: Option<String>,
}

/// List the pending tracker proposals, escaped and capped.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket proposals list",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct List {
    ticket: Option<String>,
}

impl Command for List {
    type Data = ProposalsData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ListArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ListArgs>(m)?;
        Ok(Self { ticket: a.ticket })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ProposalsData> {
        let ledger = open(ctx)?;
        let only = self
            .ticket
            .as_deref()
            .map(|t| resolve(&ledger, t))
            .transpose()?;
        let held = pending_by_ticket(&ledger, only).map_err(cli_err)?;
        let mut proposals = Vec::new();
        for t in held {
            let handle = ledger.show(t.ticket).map_err(cli_err)?.summary.handle;
            for p in t.pending {
                proposals.push(ProposalRow {
                    ticket: handle.clone(),
                    tracker_event: p.data.tracker_event,
                    item: p.data.item,
                    field: p.data.field,
                    actor_id: p.data.actor_id,
                    time: p.data.time,
                    digest: p.data.digest,
                    excerpt: shown_excerpt(&p.data.excerpt),
                    origin: p.data.origin,
                });
            }
        }
        tracing::info!(count = proposals.len(), "ticket proposals list");
        Ok(Payload::new(ProposalsData {
            count: proposals.len(),
            proposals,
        }))
    }
}

/// Output of `ticket proposals decline`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DeclineData {
    /// The ticket the proposal was held on (`~handle`).
    pub ticket: String,
    /// The tracker event id of the declined proposal.
    pub tracker_event: String,
    /// The recorded reason.
    pub reason: String,
}

/// The flags of `ticket proposals decline`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DeclineArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        value_name = "TRACKER_EVENT",
        help = "The tracker event id of the proposal, as `proposals list` shows it"
    )]
    tracker_event: String,
    #[arg(
        long,
        value_name = "TEXT",
        required = true,
        help = "Why it is declined"
    )]
    reason: String,
}

/// Decline a pending proposal with a reason: appends `proposal-declined`; the ticket is untouched.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket proposals decline",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Decline {
    ticket: String,
    tracker_event: String,
    reason: String,
}

impl Command for Decline {
    type Data = DeclineData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<DeclineArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DeclineArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            tracker_event: a.tracker_event,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<DeclineData> {
        let reason = self.reason.trim();
        if reason.is_empty() {
            return Err(CliError::Usage("--reason must not be empty".to_owned()));
        }
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let events = ledger.events(id).map_err(cli_err)?;
        let state = fold_proposals(&events)
            .into_iter()
            .find(|p| p.data.tracker_event == self.tracker_event)
            .map(|p| p.state);
        let handle = ledger.show(id).map_err(cli_err)?.summary.handle;
        let data = DeclineData {
            ticket: handle,
            tracker_event: self.tracker_event.clone(),
            reason: reason.to_owned(),
        };
        match state {
            None => Err(CliError::Usage(format!(
                "{} holds no proposal with tracker event `{}`; see `frob ticket proposals list`",
                data.ticket,
                escape_non_ascii(&self.tracker_event)
            ))),
            Some(ProposalState::Declined) => {
                tracing::info!(ticket = %id, key = %self.tracker_event, "proposal already declined");
                Ok(Payload::new(data).with_already(true))
            }
            Some(ProposalState::Pending) => {
                let body = EventBody::ProposalDeclined(ProposalCloseData {
                    tracker_event: self.tracker_event.clone(),
                    reason: Some(escape_non_ascii(reason)),
                });
                ledger.append(id, body).map_err(cli_err)?;
                tracing::info!(ticket = %id, key = %self.tracker_event, "proposal declined");
                Ok(Payload::new(data))
            }
            Some(other) => Err(CliError::Usage(format!(
                "that proposal is already {other:?} and is never reopened"
            ))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/ticket/proposals_cmd.rs::shown_excerpt
    #[test]
    fn an_excerpt_is_escaped_and_capped() {
        let long = "a".repeat(300);
        assert_eq!(shown_excerpt(&long).chars().count(), EXCERPT_CAP);
        let shown = shown_excerpt("x\u{1b}[31my\u{e9}");
        assert!(shown.is_ascii(), "{shown}");
        assert!(!shown.contains('\u{1b}'), "{shown}");
    }
}

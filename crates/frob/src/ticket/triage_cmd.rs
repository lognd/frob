//! The triage inbox verbs: `ticket triage accept|decline|snooze|duplicate` (the inbox listing is `ticket list --category triage`; `triage list` stays a hidden alias).
//!
//! Thin layer over [`Ledger::triage`] and [`Ledger::inbox`]: tickets come from
//! positional arguments or from a query (`--label`, `--type`) evaluated against the
//! inbox, the whole selection is decided in one ledger commit, and the report names
//! every ticket. A query that matches nothing is an empty, successful report, so a
//! repeated batch is a no-op.
// frob:ticket 01M44C546DQRE4D11HHPM0HX6M

use frob_ledger::index::ListFilter;
use frob_ledger::model::{Stamp, TicketType, TriageAction};
use frob_ledger::triage::{InboxEntry, TriageReport, TriageRequest, TriageStatus};
use frob_ledger::{Ledger, TicketId};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::{TicketArg, choices, cli_err, open, parsed, resolve};

/// Parse a date (`2026-11-01`, midnight UTC) or an RFC 3339 timestamp.
pub(crate) fn parse_when(flag: &str, text: &str) -> Result<Stamp, CliError> {
    let full = if text.len() == 10 && !text.contains('T') {
        format!("{text}T00:00:00Z")
    } else {
        text.to_owned()
    };
    full.parse::<Stamp>().map_err(|_| {
        CliError::Usage(format!(
            "--{flag} expects a date (2026-11-01) or an RFC 3339 timestamp, got `{text}`"
        ))
    })
}

/// How a verb names its tickets: positionals, or a query over the inbox.
#[derive(Debug, Clone, Default)]
struct Selection {
    tickets: Vec<String>,
    label: Option<String>,
    ty: Option<TicketType>,
}

/// The selection flags shared by the triage decision verbs, declared once.
#[derive(Debug, Clone, clap::Args)]
struct SelectionArgs {
    #[arg(
        value_name = "TICKET",
        num_args = 0..,
        help = "Full ULID, ~handle or alias of each ticket; or select with --label/--type"
    )]
    tickets: Vec<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Select every ticket in the inbox with this label"
    )]
    label: Option<String>,
    #[arg(long = "type", value_name = "VALUE", value_parser = choices(TicketType::NAMES), help = "Select every ticket in the inbox of this type")]
    ty: Option<String>,
}

impl Selection {
    /// Build the selection from its parsed flags.
    fn from_args(a: SelectionArgs) -> Result<Self, CliError> {
        Ok(Self {
            tickets: a.tickets,
            label: a.label,
            ty: parsed("type", a.ty)?,
        })
    }

    /// The tickets selected, in order; a query lists the inbox (snoozed tickets excluded).
    fn resolve(&self, ledger: &Ledger, now: Stamp) -> Result<Vec<TicketId>, CliError> {
        let queried = self.label.is_some() || self.ty.is_some();
        match (self.tickets.is_empty(), queried) {
            (true, false) => Err(CliError::Usage(
                "name the tickets, or select with --label or --type".to_owned(),
            )),
            (false, true) => Err(CliError::Usage(
                "name tickets or select with --label/--type, not both".to_owned(),
            )),
            (false, false) => self.tickets.iter().map(|t| resolve(ledger, t)).collect(),
            (true, true) => {
                let filter = ListFilter {
                    label: self.label.clone(),
                    ty: self.ty,
                    ..ListFilter::default()
                };
                let found = ledger.inbox(&filter, now, false).map_err(cli_err)?;
                tracing::info!(count = found.len(), "triage query selected tickets");
                Ok(found.into_iter().map(|e| e.summary.id).collect())
            }
        }
    }
}

/// Run `req` over `sel` and wrap the report; `already` when nothing was written.
fn decide(
    ctx: &Context,
    sel: &Selection,
    build: impl FnOnce(&Ledger) -> Result<TriageRequest, CliError>,
) -> CliOutcome<TriageReport> {
    let ledger = open(ctx)?;
    let now = ctx.clock.now();
    let req = build(&ledger)?;
    let ids = sel.resolve(&ledger, now)?;
    let report = ledger.triage(&ids, &req, now).map_err(cli_err)?;
    let applied = report
        .entries
        .iter()
        .filter(|e| e.status == TriageStatus::Applied)
        .count();
    tracing::info!(action = %req.action, tickets = report.entries.len(), applied, "ticket triage");
    let already = applied == 0;
    let warnings = report.warnings.clone();
    Ok(warnings.into_iter().fold(
        Payload::new(report).with_already(already),
        Payload::with_warning,
    ))
}

/// Declares a decision verb with only `--reason` beyond the selection; `$action` is its [`TriageAction`].
macro_rules! decision_verb {
    ($(#[$doc:meta])* $name:ident, $args:ident, $verb:literal, $action:expr, $help:literal) => {
        /// The flags of a triage decision verb, declared once.
        #[derive(Debug, Clone, clap::Args)]
        #[command(about = None, long_about = None)]
        struct $args {
            #[command(flatten)]
            sel: SelectionArgs,
            #[arg(long, value_name = "TEXT", help = $help)]
            reason: Option<String>,
        }

        $(#[$doc])*
        #[derive(Debug, Clone, gob_cli::Command)]
        #[command(
            verb = $verb,
            product = "frob",
            idempotent = true,
            exits(ok, refused, usage, internal)
        )]
        pub struct $name {
            sel: Selection,
            reason: Option<String>,
        }

        impl Command for $name {
            type Data = TriageReport;

            fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
                gob_cli::augment::<$args>(cmd)
            }

            fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
                let a = gob_cli::parse::<$args>(m)?;
                Ok(Self {
                    sel: Selection::from_args(a.sel)?,
                    reason: a.reason,
                })
            }

            fn run(&self, ctx: &Context) -> CliOutcome<TriageReport> {
                decide(ctx, &self.sel, |_| {
                    Ok(TriageRequest {
                        action: $action,
                        until: None,
                        reason: self.reason.clone(),
                        target: None,
                    })
                })
            }
        }
    };
}

decision_verb!(
    /// Accept tickets from the inbox: triage becomes todo, all in one ledger commit.
    Accept,
    AcceptArgs,
    "ticket triage accept",
    TriageAction::Accept,
    "Why the tickets are accepted (optional)"
);

decision_verb!(
    /// Decline tickets from the inbox: close them as wont-fix with a required reason.
    Decline,
    DeclineArgs,
    "ticket triage decline",
    TriageAction::Decline,
    "Why the tickets are declined (required)"
);

/// The flags of `ticket triage snooze`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct SnoozeArgs {
    #[command(flatten)]
    sel: SelectionArgs,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why the tickets are snoozed (optional)"
    )]
    reason: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        required = true,
        help = "Date (2026-11-01) or RFC 3339 time the tickets return to the inbox"
    )]
    until: String,
}

/// Snooze tickets: hide them from the inbox until a date.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket triage snooze",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Snooze {
    sel: Selection,
    reason: Option<String>,
    until: String,
}

impl Command for Snooze {
    type Data = TriageReport;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<SnoozeArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<SnoozeArgs>(m)?;
        Ok(Self {
            sel: Selection::from_args(a.sel)?,
            reason: a.reason,
            until: a.until,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<TriageReport> {
        let until = parse_when("until", &self.until)?;
        decide(ctx, &self.sel, |_| {
            Ok(TriageRequest {
                action: TriageAction::Snooze,
                until: Some(until),
                reason: self.reason.clone(),
                target: None,
            })
        })
    }
}

/// The flags of `ticket triage duplicate`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DuplicateArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long,
        value_name = "TEXT",
        required = true,
        help = "The ticket this one duplicates"
    )]
    of: String,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why it is a duplicate (default: duplicate of the target)"
    )]
    reason: Option<String>,
}

/// Close a ticket from the inbox as a duplicate of another, linking the two.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket triage duplicate",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Duplicate {
    ticket: String,
    of: String,
    reason: Option<String>,
}

impl Command for Duplicate {
    type Data = TriageReport;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<DuplicateArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DuplicateArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            of: a.of,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<TriageReport> {
        let sel = Selection {
            tickets: vec![self.ticket.clone()],
            ..Selection::default()
        };
        decide(ctx, &sel, |ledger| {
            let target = resolve(ledger, &self.of)?;
            Ok(TriageRequest {
                action: TriageAction::Duplicate,
                until: None,
                reason: Some(
                    self.reason
                        .clone()
                        .unwrap_or_else(|| format!("duplicate of {}", self.of)),
                ),
                target: Some(target),
            })
        })
    }
}

/// Output of `ticket triage list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct InboxData {
    /// Number of tickets listed.
    pub count: usize,
    /// The inbox instant the listing was computed for.
    pub at: Stamp,
    /// The tickets, oldest first.
    pub tickets: Vec<InboxEntry>,
}

/// The flags of `ticket triage list`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct InboxListArgs {
    #[arg(long, value_name = "TEXT", help = "Only tickets with this label")]
    label: Option<String>,
    #[arg(long = "type", value_name = "VALUE", value_parser = choices(TicketType::NAMES), help = "Only this type")]
    ty: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "List the inbox as of this date or RFC 3339 time (default now)"
    )]
    at: Option<String>,
    #[arg(long, help = "Include snoozed tickets, with the time each returns")]
    all: bool,
}

/// Deprecated alias of `ticket list --category triage`, removed in the next minor release.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket triage list",
    read_only,
    product = "frob",
    deprecated = "ticket list --category triage",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct InboxList {
    label: Option<String>,
    ty: Option<TicketType>,
    at: Option<String>,
    all: bool,
}

impl Command for InboxList {
    type Data = InboxData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<InboxListArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<InboxListArgs>(m)?;
        Ok(Self {
            label: a.label,
            ty: parsed("type", a.ty)?,
            at: a.at,
            all: a.all,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<InboxData> {
        let at = self
            .at
            .as_deref()
            .map(|a| parse_when("at", a))
            .transpose()?
            .unwrap_or_else(|| ctx.clock.now());
        let ledger = open(ctx)?;
        let filter = ListFilter {
            label: self.label.clone(),
            ty: self.ty,
            ..ListFilter::default()
        };
        let tickets = ledger.inbox(&filter, at, self.all).map_err(cli_err)?;
        tracing::debug!(count = tickets.len(), %at, "ticket triage list");
        Ok(Payload::new(InboxData {
            count: tickets.len(),
            at,
            tickets,
        }))
    }
}

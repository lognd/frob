//! Read-only ticket verbs: show, list, doable, brief.

use frob_ledger::TicketId;
use frob_ledger::event::{Event, EventBody};
use frob_ledger::guards::NoLeases;
use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::{Category, TicketType};
use frob_ledger::ops::TicketView;
use gob_cli::clap::{ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::{choice_flag, cli_err, get, get_parsed, open, resolve, text_flag, ticket_arg};

/// One event as shown by `show --events`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EventView {
    /// Event ULID.
    pub id: String,
    /// When it happened.
    pub at: String,
    /// Who did it.
    pub actor: String,
    /// The kind string.
    pub kind: String,
    /// Kind-specific fields (null for kinds this version does not interpret).
    pub body: serde_json::Value,
}

impl From<&Event> for EventView {
    fn from(e: &Event) -> Self {
        let body = match &e.body {
            EventBody::Other => serde_json::Value::Null,
            other => serde_json::to_value(other).unwrap_or(serde_json::Value::Null),
        };
        Self {
            id: e.id.to_string(),
            at: e.at.to_string(),
            actor: e.actor.clone(),
            kind: e.kind.clone(),
            body,
        }
    }
}

/// Output of `ticket show`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ShowData {
    /// The ticket with its links and children.
    #[serde(flatten)]
    pub view: TicketView,
    /// The timeline, with `--events`.
    pub events: Option<Vec<EventView>>,
}

/// Show one ticket from the index; `--events` adds its timeline.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket show",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Show {
    ticket: String,
    events: bool,
}

impl Command for Show {
    type Data = ShowData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg()).arg(
            gob_cli::clap::Arg::new("events")
                .long("events")
                .action(ArgAction::SetTrue)
                .help("Include the event timeline"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            events: m.get_flag("events"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ShowData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let view = ledger.show(id).map_err(cli_err)?;
        let events = if self.events {
            Some(
                ledger
                    .events(id)
                    .map_err(cli_err)?
                    .iter()
                    .map(EventView::from)
                    .collect(),
            )
        } else {
            None
        };
        Ok(Payload::new(ShowData { view, events }))
    }
}

/// Output of `ticket list` and `ticket doable`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ListData {
    /// Number of tickets listed.
    pub count: usize,
    /// The tickets, oldest first.
    pub tickets: Vec<Summary>,
}

impl ListData {
    fn of(tickets: Vec<Summary>) -> Self {
        Self {
            count: tickets.len(),
            tickets,
        }
    }
}

/// List tickets from the index, filtered by category, type, parent, label or blocked.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket list",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct List {
    category: Option<Category>,
    ty: Option<TicketType>,
    parent: Option<String>,
    label: Option<String>,
    blocked: bool,
}

impl Command for List {
    type Data = ListData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(choice_flag(
            "category",
            Category::NAMES,
            "Only this category",
        ))
        .arg(choice_flag("type", TicketType::NAMES, "Only this type"))
        .arg(text_flag("parent", "Only children of this ticket"))
        .arg(text_flag("label", "Only tickets with this label"))
        .arg(
            gob_cli::clap::Arg::new("blocked")
                .long("blocked")
                .action(ArgAction::SetTrue)
                .help("Only tickets blocked by an open blocker"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            category: get_parsed(m, "category")?,
            ty: get_parsed(m, "type")?,
            parent: get(m, "parent"),
            label: get(m, "label"),
            blocked: m.get_flag("blocked"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ListData> {
        let ledger = open(ctx)?;
        let parent: Option<TicketId> = self
            .parent
            .as_deref()
            .map(|p| resolve(&ledger, p))
            .transpose()?;
        let filter = ListFilter {
            category: self.category,
            ty: self.ty,
            parent,
            label: self.label.clone(),
            blocked: self.blocked.then_some(true),
        };
        let tickets = ledger.list(&filter).map_err(cli_err)?;
        tracing::debug!(count = tickets.len(), "ticket list");
        Ok(Payload::new(ListData::of(tickets)))
    }
}

/// List tickets that can be started: todo, no open blocker, scope not leased.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket doable",
    product = "frob",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Doable {
    limit: Option<usize>,
}

impl Command for Doable {
    type Data = ListData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(text_flag("limit", "Show at most this many tickets"))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let limit = get(m, "limit")
            .map(|l| {
                l.parse::<usize>()
                    .map_err(|_| CliError::Usage(format!("--limit expects a number, got `{l}`")))
            })
            .transpose()?;
        Ok(Self { limit })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ListData> {
        let ledger = open(ctx)?;
        // frob-lease (T-0019) replaces NoLeases with the real overlap check.
        let mut tickets = ledger.doable(&NoLeases).map_err(cli_err)?;
        if let Some(n) = self.limit {
            tickets.truncate(n);
        }
        Ok(Payload::new(ListData::of(tickets)))
    }
}

/// Output of `ticket brief`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BriefData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// The brief as markdown.
    pub markdown: String,
}

/// Print a ticket as markdown: title, body, acceptance, scope, links, last events.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket brief",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Brief {
    ticket: String,
}

impl Command for Brief {
    type Data = BriefData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<BriefData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let view = ledger.show(id).map_err(cli_err)?;
        let markdown = ledger.brief(id).map_err(cli_err)?;
        Ok(Payload::new(BriefData {
            id,
            handle: view.summary.handle,
            markdown,
        }))
    }
}

//! Read-only ticket verbs: show (`--format md` is the brief), list (`--category triage` is the inbox), doable; `brief` stays as a hidden alias.

use frob_ledger::TicketId;
use frob_ledger::event::{Event, EventBody};
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::{Category, Stamp, TicketType};
use frob_ledger::ops::TicketView;
use frob_ledger::triage::InboxEntry;
use gob_cli::clap::{ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::triage_cmd::parse_when;
use super::{choice_flag, cli_err, get, get_parsed, open, resolve, text_flag, ticket_arg};
use crate::config::FrobConfig;

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

/// One evidence record of a ticket as `show` and `brief` present it: an attestation is labelled, never a measurement.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EvidenceView {
    /// The evidence event id.
    pub event: String,
    /// `nextest`, `command`, `file` or `attestation`.
    pub provider: String,
    /// What was measured (for an attestation, a digest key of the statement).
    pub reference: String,
    /// The criteria it is offered for, numbered as they are now (removed ones dropped).
    pub accepts: Vec<usize>,
    /// The verdict, when there is one.
    pub passed: Option<bool>,
    /// `[attested by X: "statement"]` (escaped, origin ledger) when a person attested; absent for a tool measurement.
    pub label: Option<String>,
    /// The attestation exactly as stored; text renders use `label`.
    pub attestation: Option<frob_evidence::record::Attestation>,
}

impl EvidenceView {
    /// The one-line markdown form: attestations lead with their label, tool records with provider and verdict.
    fn line(&self) -> String {
        let at = if self.accepts.is_empty() {
            "no criterion".to_owned()
        } else {
            format!(
                "criterion {}",
                self.accepts
                    .iter()
                    .map(ToString::to_string)
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        };
        if let (Some(label), Some(a)) = (&self.label, &self.attestation) {
            let facts = if a.facts.is_empty() {
                String::new()
            } else {
                let each: Vec<String> = a
                    .facts
                    .iter()
                    .map(|f| frob_evidence::attestation::escape_line(f))
                    .collect();
                format!(" (facts: {})", each.join(", "))
            };
            return format!("- {at}: {label}{facts}");
        }
        let verdict = match self.passed {
            Some(true) => "passed",
            Some(false) => "failed",
            None => "recorded",
        };
        format!(
            "- {at}: {} {} {verdict}",
            self.provider,
            frob_evidence::attestation::escape_line(&self.reference)
        )
    }
}

/// The evidence records of ticket `id`, criteria renumbered to now, attestations labelled.
fn evidence_views(
    ledger: &frob_ledger::Ledger,
    id: TicketId,
) -> Result<Vec<EvidenceView>, CliError> {
    let mut out = Vec::new();
    for stored in
        frob_evidence::events::list(ledger, id).map_err(frob_evidence::EvidenceError::into_cli)?
    {
        let event: frob_ledger::EventId = stored
            .event
            .parse()
            .map_err(|e: frob_ledger::id::ParseIdError| CliError::internal(e))?;
        let accepts = ledger
            .criteria_now(id, event, &stored.record.accepts)
            .map_err(cli_err)?
            .into_iter()
            .flatten()
            .collect();
        out.push(EvidenceView {
            event: stored.event,
            provider: stored.record.provider.as_str().to_owned(),
            label: stored.record.attestation_label(),
            reference: stored.record.reference,
            accepts,
            passed: stored.record.passed,
            attestation: stored.record.attestation,
        });
    }
    Ok(out)
}

/// Output of `ticket show`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ShowData {
    /// The ticket with its links and children.
    #[serde(flatten)]
    pub view: TicketView,
    /// Every frontmatter field by name (unset scalars null, empty lists `[]`), plus `body`.
    pub fields: serde_json::Map<String, serde_json::Value>,
    /// The timeline, with `--events`.
    pub events: Option<Vec<EventView>>,
    /// Evidence records, each attestation marked as one.
    pub evidence: Vec<EvidenceView>,
    /// The `--no-changelog` exemption the ticket was closed with: who, when and why.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub changelog_exempt: Option<frob_ledger::event::ChangelogExemption>,
}

/// Show one ticket from the index; `--events` adds its timeline, `--format md` prints it as markdown.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket show",
    product = "frob",
    markdown,
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
        let all = ledger.events(id).map_err(cli_err)?;
        let changelog_exempt = frob_ledger::event::changelog_exemption(&all);
        let events = self
            .events
            .then(|| all.iter().map(EventView::from).collect());
        let fields = frob_ledger::schema::field_map(&view.ticket);
        let evidence = evidence_views(&ledger, id)?;
        let rendered = if ctx.markdown() {
            let md = brief_markdown(&ledger, id)?;
            tracing::debug!(ticket = %id, bytes = md.len(), "ticket show: markdown view");
            Some(md.lines().map(str::to_owned).collect::<Vec<_>>())
        } else {
            None
        };
        let payload = Payload::new(ShowData {
            view,
            fields,
            events,
            evidence,
            changelog_exempt,
        });
        Ok(match rendered {
            Some(rows) => payload.with_rendered(rows),
            None => payload,
        })
    }
}

/// The markdown brief of ticket `id`: the ledger brief plus an Evidence section.
fn brief_markdown(ledger: &frob_ledger::Ledger, id: TicketId) -> Result<String, CliError> {
    let mut markdown = ledger.brief(id).map_err(cli_err)?;
    let evidence = evidence_views(ledger, id)?;
    if !evidence.is_empty() {
        markdown.push_str("\n## Evidence\n\n");
        for e in &evidence {
            markdown.push_str(&e.line());
            markdown.push('\n');
        }
    }
    Ok(markdown)
}

/// One listed ticket: its index row, plus when it returns if it is a snoozed triage ticket.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ListRow {
    /// The ticket's index row.
    #[serde(flatten)]
    pub summary: Summary,
    /// Set for a snoozed ticket listed with `--category triage --all`: when it returns.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub snoozed_until: Option<Stamp>,
    /// With `--full`: the ticket's v1 aliases.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub aliases: Option<Vec<String>>,
    /// With `--full`: the ticket's events in fold order.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub events: Option<Vec<EventView>>,
}

impl From<InboxEntry> for ListRow {
    fn from(e: InboxEntry) -> Self {
        Self {
            summary: e.summary,
            snoozed_until: e.snoozed_until,
            aliases: None,
            events: None,
        }
    }
}

/// Output of `ticket list` and `ticket doable`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ListData {
    /// Number of tickets listed.
    pub count: usize,
    /// The inbox instant of a `--category triage` listing.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub at: Option<Stamp>,
    /// The tickets, oldest first.
    pub tickets: Vec<ListRow>,
}

impl ListData {
    fn of(tickets: Vec<Summary>) -> Self {
        Self {
            count: tickets.len(),
            at: None,
            tickets: tickets
                .into_iter()
                .map(|summary| ListRow {
                    summary,
                    snoozed_until: None,
                    aliases: None,
                    events: None,
                })
                .collect(),
        }
    }
}

/// List tickets from the index, filtered by category, type, parent, label or blocked; `--category triage` is the inbox.
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
    at: Option<String>,
    all: bool,
    full: bool,
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
        .arg(text_flag(
            "at",
            "With --category triage: list the inbox as of this date or RFC 3339 time (default now)",
        ))
        .arg(
            gob_cli::clap::Arg::new("all")
                .long("all")
                .action(ArgAction::SetTrue)
                .help(
                    "With --category triage: include snoozed tickets, with the time each returns",
                ),
        )
        .arg(
            gob_cli::clap::Arg::new("full")
                .long("full")
                .action(ArgAction::SetTrue)
                .help("Also emit every listed ticket's aliases and events, read in one pass"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            category: get_parsed(m, "category")?,
            ty: get_parsed(m, "type")?,
            parent: get(m, "parent"),
            label: get(m, "label"),
            blocked: m.get_flag("blocked"),
            at: get(m, "at"),
            all: m.get_flag("all"),
            full: m.get_flag("full"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ListData> {
        if self.category != Some(Category::Triage) && (self.at.is_some() || self.all) {
            return Err(CliError::Usage(
                "--at and --all apply only with --category triage".to_owned(),
            ));
        }
        let ledger = open(ctx)?;
        if self.category == Some(Category::Triage) {
            return self.run_inbox(&ledger, ctx);
        }
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
        let mut data = ListData::of(tickets);
        if self.full {
            fill_full(&ledger, &mut data)?;
        }
        Ok(Payload::new(data))
    }
}

// frob:ticket 01M4GKAYSGHAE5QAXN1BJBTQN2
/// Add aliases and events to every row of `data` with one ledger sync and one tree walk.
fn fill_full(ledger: &frob_ledger::Ledger, data: &mut ListData) -> Result<(), CliError> {
    let ids: std::collections::BTreeSet<TicketId> =
        data.tickets.iter().map(|r| r.summary.id).collect();
    let mut aliases = ledger.aliases_many(&ids).map_err(cli_err)?;
    let mut events = ledger.events_many(&ids).map_err(cli_err)?;
    for row in &mut data.tickets {
        row.aliases = aliases.remove(&row.summary.id);
        row.events = events
            .remove(&row.summary.id)
            .map(|all| all.iter().map(EventView::from).collect());
    }
    tracing::debug!(tickets = data.tickets.len(), "ticket list --full filled");
    Ok(())
}

impl List {
    /// The triage inbox (snoozed tickets hidden until their date unless `--all`), as the old `ticket triage list` printed it.
    fn run_inbox(&self, ledger: &frob_ledger::Ledger, ctx: &Context) -> CliOutcome<ListData> {
        let at = self
            .at
            .as_deref()
            .map(|a| parse_when("at", a))
            .transpose()?
            .unwrap_or_else(|| ctx.clock.now());
        let parent: Option<TicketId> = self
            .parent
            .as_deref()
            .map(|p| resolve(ledger, p))
            .transpose()?;
        let filter = ListFilter {
            label: self.label.clone(),
            ty: self.ty,
            parent,
            blocked: self.blocked.then_some(true),
            ..ListFilter::default()
        };
        let entries = ledger.inbox(&filter, at, self.all).map_err(cli_err)?;
        tracing::debug!(count = entries.len(), %at, "ticket list: triage inbox");
        Ok(Payload::new(ListData {
            count: entries.len(),
            at: Some(at),
            tickets: entries.into_iter().map(ListRow::from).collect(),
        }))
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
        let (leases, warning) = lease_check(ctx);
        let mut tickets = ledger.doable(&*leases).map_err(cli_err)?;
        if let Some(n) = self.limit {
            tickets.truncate(n);
        }
        let payload = Payload::new(ListData::of(tickets));
        Ok(match warning {
            Some(w) => payload.with_warning(w),
            None => payload,
        })
    }
}

/// The live-lease check for `doable`, or `NoLeases` plus a warning when it cannot be built.
///
/// The store is opened with the materialized `[lease]` config, like every other verb.
fn lease_check(ctx: &Context) -> (Box<dyn LeaseCheck>, Option<String>) {
    match build_lease_guard(&ctx.cwd, ctx.clock.clone()) {
        Ok(g) => (Box::new(g), None),
        Err(msg) => {
            tracing::warn!(error = %msg, "lease check unavailable; showing every ticket");
            (
                Box::new(NoLeases),
                Some(format!(
                    "lease check skipped, scope overlaps not hidden: {msg}"
                )),
            )
        }
    }
}

/// Snapshot live leases with the materialized `[lease]` config.
fn build_lease_guard(
    cwd: &std::path::Path,
    clock: std::sync::Arc<dyn gob_time::Clock>,
) -> Result<frob_lease::LeaseGuard, String> {
    let repo = gob_git::Repo::discover(cwd).map_err(|e| e.to_string())?;
    let root = repo
        .work_dir()
        .map(std::path::Path::to_path_buf)
        .ok_or_else(|| format!("{} is not inside a git work tree", cwd.display()))?;
    let cfg = FrobConfig::load(&root).map_err(|e| e.to_string())?.lease;
    let store = frob_lease::LeaseStore::open(&repo, cfg, clock).map_err(|e| e.to_string())?;
    frob_lease::LeaseGuard::new(store).map_err(|e| e.to_string())
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

/// Deprecated alias of `ticket show --format md`, removed in the next minor release.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket brief",
    product = "frob",
    deprecated = "ticket show --format md",
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
        let markdown = brief_markdown(&ledger, id)?;
        Ok(Payload::new(BriefData {
            id,
            handle: view.summary.handle,
            markdown,
        }))
    }
}

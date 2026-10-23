//! Read-only ticket verbs: show (`--format md` is the brief), list (`--category triage` is the inbox), doable; `brief` stays as a hidden alias.

use frob_ledger::TicketId;
use frob_ledger::event::{Event, EventBody};
use frob_ledger::guards::{LeaseCheck, NoLeases};
use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::{Category, Stamp, TicketType};
use frob_ledger::ops::TicketView;
use frob_ledger::triage::InboxEntry;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use gob_path::Shown;
use schemars::JsonSchema;
use serde::Serialize;

use super::triage_cmd::parse_when;
use super::{TicketArg, choices, cli_err, open, parsed, resolve};
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
    pub(crate) fn line(&self) -> String {
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
    read_only,
    product = "frob",
    markdown,
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Show {
    ticket: String,
    events: bool,
}

/// The flags of `ticket show`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ShowArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, help = "Include the event timeline")]
    events: bool,
}

impl Command for Show {
    type Data = ShowData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ShowArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ShowArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            events: a.events,
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
        let data = ShowData {
            view,
            fields,
            events,
            evidence,
            changelog_exempt,
        };
        let rows = rendered.unwrap_or_else(|| crate::text_view::show_rows(&data));
        Ok(Payload::new(data).with_rendered(rows))
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
    /// With `--newcomer`: the ticket's `## Start here` notes.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start_here: Option<String>,
}

impl From<InboxEntry> for ListRow {
    fn from(e: InboxEntry) -> Self {
        Self {
            summary: e.summary,
            snoozed_until: e.snoozed_until,
            aliases: None,
            events: None,
            start_here: None,
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
    /// With `--tree`: the same tickets as a backlog hierarchy with roll-ups (`tickets` is then empty).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tree: Option<frob_ledger::backlog::Backlog>,
}

impl ListData {
    fn of(tickets: Vec<Summary>) -> Self {
        Self {
            count: tickets.len(),
            at: None,
            tree: None,
            tickets: tickets
                .into_iter()
                .map(|summary| ListRow {
                    summary,
                    snoozed_until: None,
                    aliases: None,
                    events: None,
                    start_here: None,
                })
                .collect(),
        }
    }
}

/// List tickets from the index, filtered by category, type, parent, label or blocked; `--category triage` is the inbox.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket list",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
#[allow(clippy::struct_excessive_bools)] // one bool per CLI switch
pub struct List {
    category: Option<Category>,
    ty: Option<TicketType>,
    parent: Option<String>,
    label: Option<String>,
    blocked: bool,
    at: Option<String>,
    all: bool,
    full: bool,
    tree: bool,
    depth: Option<usize>,
}

/// The flags of `ticket list`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
#[allow(clippy::struct_excessive_bools)] // one bool per CLI flag
struct ListArgs {
    #[arg(long, value_name = "VALUE", value_parser = choices(Category::NAMES), help = "Only this category")]
    category: Option<String>,
    #[arg(long = "type", value_name = "VALUE", value_parser = choices(TicketType::NAMES), help = "Only this type")]
    ty: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Only children of this ticket")]
    parent: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Only tickets with this label")]
    label: Option<String>,
    #[arg(long, help = "Only tickets blocked by an open blocker")]
    blocked: bool,
    #[arg(
        long,
        value_name = "TEXT",
        help = "With --category triage: list the inbox as of this date or RFC 3339 time (default now)"
    )]
    at: Option<String>,
    #[arg(
        long,
        help = "With --category triage: include snoozed tickets, with the time each returns"
    )]
    all: bool,
    #[arg(
        long,
        help = "Also emit every listed ticket's aliases and events, read in one pass"
    )]
    full: bool,
    #[arg(
        long,
        help = "The backlog as a parent hierarchy with points roll-ups and percent done"
    )]
    tree: bool,
    #[arg(
        long,
        value_name = "TEXT",
        help = "With --tree: show this many levels (1 = top only); deeper tickets fold into a count"
    )]
    depth: Option<String>,
}

impl Command for List {
    type Data = ListData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ListArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ListArgs>(m)?;
        Ok(Self {
            category: parsed("category", a.category)?,
            ty: parsed("type", a.ty)?,
            parent: a.parent,
            label: a.label,
            blocked: a.blocked,
            at: a.at,
            all: a.all,
            full: a.full,
            tree: a.tree,
            depth: a
                .depth
                .map(|d| match d.parse::<usize>() {
                    Ok(n) if n > 0 => Ok(n),
                    _ => Err(CliError::Usage(format!(
                        "--depth expects a positive number, got `{d}`"
                    ))),
                })
                .transpose()?,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ListData> {
        if self.category != Some(Category::Triage) && (self.at.is_some() || self.all) {
            return Err(CliError::Usage(
                "--at and --all apply only with --category triage".to_owned(),
            ));
        }
        if self.depth.is_some() && !self.tree {
            return Err(CliError::Usage(
                "--depth applies only with --tree".to_owned(),
            ));
        }
        if self.tree && (self.category == Some(Category::Triage) || self.full) {
            return Err(CliError::Usage(
                "--tree cannot combine with --full or --category triage".to_owned(),
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
        if self.tree {
            return Ok(self.tree_payload(ctx, &ledger, &tickets));
        }
        let mut data = ListData::of(tickets);
        if self.full {
            fill_full(&ledger, &mut data)?;
        }
        let rows = crate::text_view::list_rows(&data);
        Ok(Payload::new(data).with_rendered(rows))
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
    /// The `--tree` view of `tickets`: doable markers from the live-lease check, text rendered as an indented hierarchy.
    // frob:ticket 01M48Q2A6GSSETPGKGJ6NJDNWV
    fn tree_payload(
        &self,
        ctx: &Context,
        ledger: &frob_ledger::Ledger,
        tickets: &[Summary],
    ) -> Payload<ListData> {
        let (leases, warning) = lease_check(ctx);
        let doable: std::collections::BTreeSet<TicketId> = match ledger.doable(&*leases) {
            Ok(rows) => rows.into_iter().map(|s| s.id).collect(),
            Err(e) => {
                tracing::warn!(error = %e, "ticket list --tree: doable markers unavailable");
                std::collections::BTreeSet::new()
            }
        };
        let tree = frob_ledger::backlog::build(tickets, &doable, self.depth);
        tracing::debug!(nodes = tree.len(), depth = ?self.depth, "ticket list --tree");
        let rows = tree.render();
        let payload = Payload::new(ListData {
            count: tickets.len(),
            at: None,
            tickets: Vec::new(),
            tree: Some(tree),
        })
        .with_rendered(rows);
        match warning {
            Some(w) => payload.with_warning(w),
            None => payload,
        }
    }

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
        let data = ListData {
            count: entries.len(),
            at: Some(at),
            tree: None,
            tickets: entries.into_iter().map(ListRow::from).collect(),
        };
        let rows = crate::text_view::list_rows(&data);
        Ok(Payload::new(data).with_rendered(rows))
    }
}

/// List tickets that can be started: todo, no open blocker, scope not leased; `--newcomer` keeps the good-first ones, smallest first, with start notes.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket doable",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Doable {
    limit: Option<usize>,
    newcomer: bool,
}

/// The flags of `ticket doable`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DoableArgs {
    #[arg(long, value_name = "TEXT", help = "Show at most this many tickets")]
    limit: Option<String>,
    #[arg(
        long,
        help = "Only good-first tickets, smallest first, with their start notes"
    )]
    newcomer: bool,
}

impl Command for Doable {
    type Data = ListData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<DoableArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DoableArgs>(m)?;
        let limit = a
            .limit
            .map(|l| {
                l.parse::<usize>()
                    .map_err(|_| CliError::Usage(format!("--limit expects a number, got `{l}`")))
            })
            .transpose()?;
        Ok(Self {
            limit,
            newcomer: a.newcomer,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ListData> {
        let ledger = open(ctx)?;
        let (leases, warning) = lease_check(ctx);
        let freshness = freshness_notice(ctx);
        let tickets = ledger.doable(&*leases).map_err(cli_err)?;
        let mut data = if self.newcomer {
            newcomer_rows(&ledger, tickets)?
        } else if crate::profile::Profile::for_cwd(&ctx.cwd) == crate::profile::Profile::Newcomer {
            good_first_first(&ledger, tickets)?
        } else {
            ListData::of(tickets)
        };
        if let Some(n) = self.limit {
            data.tickets.truncate(n);
            data.count = data.tickets.len();
        }
        let rows = crate::text_view::list_rows(&data);
        let payload = Payload::new(data).with_rendered(rows);
        let payload = match warning {
            Some(w) => payload.with_warning(w),
            None => payload,
        };
        Ok(match freshness {
            Some(n) => payload.with_warning(n),
            None => payload,
        })
    }
}

/// Probe the remote within the foreground budget and describe a stale ticket view, if it is one (`distributed-tickets.md` section 5.3, `doable`).
// frob:ticket 01M5CW04GHM970H5KR4EV5KK0X
fn freshness_notice(ctx: &Context) -> Option<String> {
    let (repo, root) = crate::workspace::Located::discover(&ctx.cwd)
        .into_repo()
        .ok()?;
    let cfg = FrobConfig::load(&root).ok()?;
    crate::sync_hook::foreground(&repo, &cfg, ctx)
}

/// Every ticket in `tickets`: the good-first ones first (as `--newcomer` orders them, with start notes), then the rest in priority order.
// frob:ticket 01M3ZX87VKDKC0N65NH77EBEJP
fn good_first_first(
    ledger: &frob_ledger::Ledger,
    tickets: Vec<Summary>,
) -> Result<ListData, CliError> {
    let good = newcomer_rows(ledger, tickets.clone())?;
    let first: std::collections::BTreeSet<_> = good.tickets.iter().map(|r| r.summary.id).collect();
    let rest: Vec<Summary> = tickets
        .into_iter()
        .filter(|s| !first.contains(&s.id))
        .collect();
    tracing::debug!(
        good_first = first.len(),
        rest = rest.len(),
        "doable: newcomer order"
    );
    let mut rows = good.tickets;
    rows.extend(ListData::of(rest).tickets);
    Ok(ListData {
        count: rows.len(),
        at: None,
        tree: None,
        tickets: rows,
    })
}

/// The good-first subset of `tickets`, ordered like `indexes/good-first.md`, with start notes.
// frob:ticket 01M3ZX87QPD21PCSSSAJHVK7HJ
fn newcomer_rows(
    ledger: &frob_ledger::Ledger,
    tickets: Vec<Summary>,
) -> Result<ListData, CliError> {
    use frob_ledger::r#gen::good_first;
    let mut rows = Vec::new();
    for summary in tickets {
        let view = ledger.show(summary.id).map_err(cli_err)?;
        if good_first::is_good_first(&view.ticket.front.labels) {
            let start_here = good_first::start_here(&view.ticket.body);
            rows.push(ListRow {
                summary,
                snoozed_until: None,
                aliases: None,
                events: None,
                start_here,
            });
        }
    }
    rows.sort_by_key(|r| good_first::order_key(r.summary.points, r.summary.id));
    Ok(ListData {
        count: rows.len(),
        at: None,
        tree: None,
        tickets: rows,
    })
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
pub(super) fn build_lease_guard(
    cwd: &std::path::Path,
    clock: std::sync::Arc<dyn gob_time::Clock>,
) -> Result<frob_lease::LeaseGuard, String> {
    let repo = gob_git::Repo::discover(cwd).map_err(|e| e.to_string())?;
    let root = repo
        .work_dir()
        .map(std::path::Path::to_path_buf)
        .ok_or_else(|| format!("{} is not inside a git work tree", Shown::of(cwd)))?;
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
    read_only,
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
        gob_cli::augment::<TicketArg>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TicketArg>(m)?;
        Ok(Self { ticket: a.ticket })
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

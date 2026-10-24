//! Mutating ticket verbs: new, update, link, unlink, comment, close, drop, reopen.

use frob_ledger::guards::default_close_guards;
use frob_ledger::model::{
    Category, Class, CommentSubtype, LinkKind, Outcome, Points, Priority, TicketType,
};
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::schema::parse_text_value;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome};

use super::{ChangeData, TicketArg, choices, cli_err, open, parsed, payload, resolve};

/// Create a ticket; with `--idempotency-key` a repeat returns the first ticket.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket new",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct New {
    req: Box<NewRequest>,
}

/// The flags of `ticket new`, parsed but not yet resolved against the ledger.
#[derive(Debug, Clone)]
struct NewRequest {
    title: String,
    ty: TicketType,
    category: Category,
    priority: Priority,
    class: Class,
    points: Option<Points>,
    parent: Option<String>,
    blocked_by: Vec<String>,
    scope: Vec<String>,
    new_scope: Vec<String>,
    labels: Vec<String>,
    acceptance: Vec<String>,
    aliases: Vec<String>,
    body: String,
    key: Option<String>,
    persona: Option<String>,
    capability: Option<String>,
    so_that: Option<String>,
    flavour: Option<String>,
    assignee: Option<String>,
    good_first: bool,
}

/// The flags of `ticket new`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct NewArgs {
    #[arg(long, value_name = "TEXT", help = "Ticket title")]
    title: String,
    #[arg(long = "type", value_name = "VALUE", value_parser = choices(TicketType::NAMES), help = "Ticket type (default task)")]
    ty: Option<String>,
    #[arg(long, value_name = "VALUE", value_parser = choices(Priority::NAMES), help = "Priority (default medium)")]
    priority: Option<String>,
    #[arg(long, value_name = "VALUE", value_parser = choices(Class::NAMES), help = "Class of service (default standard)")]
    class: Option<String>,
    #[arg(long, value_name = "VALUE", value_parser = choices(&["triage", "todo"]), help = "Starting category (default todo)")]
    category: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Story points: 1, 2, 3, 5, 8 or 13")]
    points: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Parent ticket")]
    parent: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "A ticket that blocks this one (repeatable)"
    )]
    blocked_by: Vec<String>,
    #[arg(long, value_name = "TEXT", help = "Write-scope glob (repeatable)")]
    scope: Vec<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Write-scope glob for files this ticket will create: scope plus a `creates:` label that silences the zero-match warning (repeatable)"
    )]
    new_scope: Vec<String>,
    #[arg(long = "label", value_name = "TEXT", help = "Label (repeatable)")]
    labels: Vec<String>,
    #[arg(long, value_name = "TEXT", help = "Acceptance criterion (repeatable)")]
    acceptance: Vec<String>,
    #[arg(
        long = "alias",
        value_name = "TEXT",
        help = "Id from another system, such as v1 T-0042 (repeatable)"
    )]
    aliases: Vec<String>,
    #[arg(long, value_name = "TEXT", help = "Markdown body")]
    body: Option<String>,
    #[arg(
        long = "idempotency-key",
        value_name = "TEXT",
        help = "Return the same ticket for the same key"
    )]
    key: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Story persona")]
    persona: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Story capability")]
    capability: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Story outcome (so that ...)")]
    so_that: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Free-form flavour such as user_story"
    )]
    flavour: Option<String>,
    #[arg(long, value_name = "TEXT", help = "Assignee")]
    assignee: Option<String>,
    #[arg(
        long,
        help = "Label the ticket good-first and append a `## Start here` scaffold to the body"
    )]
    good_first: bool,
}

impl Command for New {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<NewArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<NewArgs>(m)?;
        let points = parsed::<Points>("points", a.points)?;
        Ok(Self {
            req: Box::new(NewRequest {
                title: a.title,
                ty: parsed("type", a.ty)?.unwrap_or(TicketType::Task),
                category: parsed("category", a.category)?.unwrap_or(Category::Todo),
                priority: parsed("priority", a.priority)?.unwrap_or(Priority::Medium),
                class: parsed("class", a.class)?.unwrap_or_default(),
                points,
                parent: a.parent,
                blocked_by: a.blocked_by,
                scope: a.scope,
                new_scope: a.new_scope,
                labels: a.labels,
                acceptance: a.acceptance,
                aliases: a.aliases,
                body: a.body.unwrap_or_default(),
                key: a.key,
                persona: a.persona,
                capability: a.capability,
                so_that: a.so_that,
                flavour: a.flavour,
                assignee: a.assignee,
                // frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
                good_first: a.good_first,
            }),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let r = &*self.req;
        let mut req = NewTicket::new(r.title.clone(), r.ty);
        req.category = r.category;
        req.priority = r.priority;
        req.class = r.class;
        req.points = r.points;
        req.parent = r
            .parent
            .as_deref()
            .map(|p| resolve(&ledger, p))
            .transpose()?;
        req.blocked_by = r
            .blocked_by
            .iter()
            .map(|b| resolve(&ledger, b))
            .collect::<Result<_, _>>()?;
        req.scope.clone_from(&r.scope);
        req.labels.clone_from(&r.labels);
        for g in &r.new_scope {
            req.scope.push(g.clone());
            req.labels.push(frob_lease::unmatched::creates_label(g));
        }
        req.acceptance.clone_from(&r.acceptance);
        req.aliases.clone_from(&r.aliases);
        // frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
        req.body = good_first_body(&r.body, r.good_first, &mut req.labels);
        req.idempotency_key.clone_from(&r.key);
        req.persona.clone_from(&r.persona);
        req.capability.clone_from(&r.capability);
        req.outcome_text.clone_from(&r.so_that);
        req.flavour.clone_from(&r.flavour);
        req.assignee.clone_from(&r.assignee);
        let applied = ledger.new_ticket(req).map_err(cli_err)?;
        tracing::info!(ticket = %applied.ticket.front.id, already = applied.already, "ticket new");
        let f = &applied.ticket.front;
        let misses =
            frob_lease::unmatched::scope_warnings(ledger.repo(), f.id, &f.scope, &f.labels);
        // frob:ticket 01M5DJ4K69T67D50C19B4NY6RM
        let split = if applied.already {
            None
        } else {
            f.parent
                .and_then(|p| claim_cover(ctx, &ledger).split_notice(p, f.id))
        };
        Ok(misses
            .into_iter()
            .chain(split)
            .fold(payload(&applied), gob_cli::Payload::with_warning))
    }
}

/// The body for `ticket new`: `body` plus, under `--good-first`, the Start here scaffold, with the label added to `labels`.
// frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
fn good_first_body(body: &str, good_first: bool, labels: &mut Vec<String>) -> String {
    if !good_first {
        return body.to_owned();
    }
    let label = frob_pm::legacy::good_first::GOOD_FIRST_LABEL;
    if !labels.iter().any(|l| l == label) {
        labels.push(label.to_owned());
    }
    if body.is_empty() {
        return frob_pm::legacy::good_first::START_HERE_SCAFFOLD.to_owned();
    }
    format!(
        "{}\n\n{}",
        body.trim_end(),
        frob_pm::legacy::good_first::START_HERE_SCAFFOLD
    )
}

/// Patch fields of a ticket: `--set key=value`, dedicated flags, label, scope and acceptance edits.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket update",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Update {
    ticket: String,
    sets: Vec<(String, String)>,
    add_labels: Vec<String>,
    remove_labels: Vec<String>,
    add_scope: Vec<String>,
    add_new_scope: Vec<String>,
    remove_scope: Vec<String>,
    clears: Vec<String>,
    add_acceptance: Vec<String>,
    remove_acceptance: Vec<usize>,
    clear_acceptance: bool,
    reason: Option<String>,
    wait: std::time::Duration,
}

/// An evidence record whose acceptance criterion an update removed.
#[derive(Debug, Clone, serde::Serialize, schemars::JsonSchema)]
pub struct LostEvidence {
    /// The evidence event id.
    pub event: String,
    /// The provider that measured it.
    pub provider: String,
    /// What was measured (the record's `ref`).
    pub reference: String,
    /// The removed criteria it was offered for, numbered as before this update.
    pub lost: Vec<usize>,
    /// Its criteria that survive, numbered as after this update.
    pub kept: Vec<usize>,
}

/// Output of `ticket update`: the change plus the evidence that lost a criterion.
#[derive(Debug, Clone, serde::Serialize, schemars::JsonSchema)]
pub struct UpdateData {
    /// The ticket change.
    #[serde(flatten)]
    pub change: ChangeData,
    /// Evidence that lost a criterion to this update, empty when none did.
    pub lost_evidence: Vec<LostEvidence>,
}

/// Evidence on ticket `id` offered for any of the criteria `removed` (numbered now), before the update.
///
/// Each record's recorded positions are first mapped through every earlier
/// acceptance edit (`Ledger::criteria_now`), so a record written before an
/// earlier removal is judged by the criterion it was really offered for.
/// Write the reindex commit right after a decision commit that changed a parent or title.
///
/// Only on the ticket-branch layout and only when `[tickets] index_writer = "local"`; a failure
/// is a warning because the decision commit already landed and `ticket reindex` repeats the work.
fn reindex_after(
    ctx: &Context,
    ledger: &frob_ledger::Ledger,
    id: frob_ledger::TicketId,
    applied: &frob_ledger::Applied,
) -> Result<Option<String>, CliError> {
    if applied.already || ledger.layout() != frob_ledger::Layout::Branch {
        return Ok(None);
    }
    let (_, root) = crate::workspace::Located::discover(&ctx.cwd).into_repo()?;
    let cfg =
        crate::config::FrobConfig::load(&root).map_err(|e| crate::workspace::config_refusal(&e))?;
    if cfg.tickets.index_writer != crate::config::IndexWriterKnob::Local {
        return Ok(None);
    }
    let moves = ledger.events(id).map_err(cli_err)?.into_iter().rev().find(|e| {
        applied.events.contains(&e.id)
            && matches!(&e.body, frob_ledger::event::EventBody::Field(f) if f.field == "parent" || f.field == "title")
    });
    let Some(event) = moves else { return Ok(None) };
    Ok(Some(match ledger.reindex_commit(Some(event.id)) {
        Ok(Some(c)) => format!("reindex commit {c} follows the decision commit"),
        Ok(None) => "ticket files already at their computed paths".to_owned(),
        Err(e) => format!("reindex commit failed ({e}); run `frob ticket reindex`"),
    }))
}

fn lost_evidence(
    ledger: &frob_ledger::Ledger,
    id: frob_ledger::TicketId,
    patch: &Patch,
) -> Result<Vec<LostEvidence>, CliError> {
    if patch.remove_acceptance.is_empty() && !patch.clear_acceptance {
        return Ok(Vec::new());
    }
    let removed = ledger.acceptance_removed(id, patch).map_err(cli_err)?;
    let mut out = Vec::new();
    if removed.is_empty() {
        return Ok(out);
    }
    let records =
        frob_evidence::events::list(ledger, id).map_err(frob_evidence::EvidenceError::into_cli)?;
    for stored in records {
        let event: frob_ledger::EventId = stored
            .event
            .parse()
            .map_err(|e: frob_ledger::id::ParseIdError| CliError::internal(e))?;
        let now = ledger
            .criteria_now(id, event, &stored.record.accepts)
            .map_err(cli_err)?;
        let lost: Vec<usize> = now
            .iter()
            .flatten()
            .copied()
            .filter(|n| removed.contains(n))
            .collect();
        if lost.is_empty() {
            continue;
        }
        let kept = now
            .iter()
            .flatten()
            .filter(|n| !removed.contains(n))
            .map(|n| n - removed.iter().filter(|r| **r < *n).count())
            .collect();
        tracing::warn!(ticket = %id, evidence = %stored.event, ?lost, "evidence loses its criterion");
        out.push(LostEvidence {
            event: stored.event,
            provider: stored.record.provider.as_str().to_owned(),
            reference: stored.record.reference,
            lost,
            kept,
        });
    }
    Ok(out)
}

/// The flags of `ticket update`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct UpdateArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long = "set",
        value_name = "TEXT",
        help = "FIELD=VALUE to set (repeatable; empty value unsets a scalar, lists need --clear); lists are comma separated; acceptance needs --add-acceptance"
    )]
    sets: Vec<String>,
    #[arg(long, value_name = "TEXT", help = "New title")]
    title: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "New parent ticket (handle, id or alias); empty unsets it"
    )]
    parent: Option<String>,
    #[arg(long, value_name = "VALUE", value_parser = choices(Priority::NAMES), help = "New priority")]
    priority: Option<String>,
    #[arg(long, value_name = "VALUE", value_parser = choices(Class::NAMES), help = "New class of service")]
    class: Option<String>,
    #[arg(long, value_name = "TEXT", help = "New story points")]
    points: Option<String>,
    #[arg(
        long = "add-label",
        value_name = "TEXT",
        help = "Label to add (repeatable)"
    )]
    add_labels: Vec<String>,
    #[arg(
        long = "remove-label",
        value_name = "TEXT",
        help = "Label to remove (repeatable)"
    )]
    remove_labels: Vec<String>,
    #[arg(long, value_name = "TEXT", help = "Scope glob to add (repeatable)")]
    add_scope: Vec<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Scope glob to add for files this ticket will create: scope plus a `creates:` label that silences the zero-match warning (repeatable)"
    )]
    add_new_scope: Vec<String>,
    #[arg(long, value_name = "TEXT", help = "Scope glob to remove (repeatable)")]
    remove_scope: Vec<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Acceptance criterion to add, taken whole, commas included (repeatable)"
    )]
    add_acceptance: Vec<String>,
    #[arg(
        long,
        value_name = "N",
        help = "1-based acceptance criterion to remove, as `ticket show` numbers them (repeatable); reports evidence that loses it"
    )]
    remove_acceptance: Vec<usize>,
    #[arg(
        long,
        help = "Remove every acceptance criterion; reports evidence that loses one"
    )]
    clear_acceptance: bool,
    #[arg(
        long = "clear",
        value_name = "TEXT",
        help = "List field to empty (repeatable); the only way to empty a list"
    )]
    clears: Vec<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why (required when changing flavour)"
    )]
    reason: Option<String>,
    #[command(flatten)]
    wait: crate::lease_cmd::WaitArg,
}

impl Command for Update {
    type Data = UpdateData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<UpdateArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<UpdateArgs>(m)?;
        let mut sets = Vec::new();
        for raw in a.sets {
            let (k, v) = raw.split_once('=').ok_or_else(|| {
                CliError::Usage(format!("--set expects FIELD=VALUE, got `{raw}`"))
            })?;
            sets.push((k.trim().to_owned(), v.to_owned()));
        }
        for (field, value) in [
            ("title", a.title),
            ("parent", a.parent),
            ("priority", a.priority),
            ("class", a.class),
            ("points", a.points),
        ] {
            if let Some(v) = value {
                sets.push((field.to_owned(), v));
            }
        }
        Ok(Self {
            ticket: a.ticket.ticket,
            sets,
            add_labels: a.add_labels,
            remove_labels: a.remove_labels,
            add_scope: a.add_scope,
            add_new_scope: a.add_new_scope,
            remove_scope: a.remove_scope,
            clears: a.clears,
            add_acceptance: a.add_acceptance,
            remove_acceptance: a.remove_acceptance,
            clear_acceptance: a.clear_acceptance,
            reason: a.reason,
            wait: a.wait.duration(),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<UpdateData> {
        frob_lease::heartbeat(&ctx.cwd, ctx.clock.clone());
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let creates = frob_lease::unmatched::creates_label;
        let mut patch = Patch {
            add_labels: [
                self.add_labels.clone(),
                self.add_new_scope.iter().map(|g| creates(g)).collect(),
            ]
            .concat(),
            remove_labels: [
                self.remove_labels.clone(),
                self.remove_scope.iter().map(|g| creates(g)).collect(),
            ]
            .concat(),
            add_scope: [self.add_scope.clone(), self.add_new_scope.clone()].concat(),
            remove_scope: self.remove_scope.clone(),
            clears: self.clears.clone(),
            add_acceptance: self.add_acceptance.clone(),
            remove_acceptance: self.remove_acceptance.clone(),
            clear_acceptance: self.clear_acceptance,
            reason: self.reason.clone(),
            ..Patch::default()
        };
        for (name, text) in &self.sets {
            let text = if name == "parent" && !text.is_empty() {
                resolve(&ledger, text)?.to_string()
            } else {
                text.clone()
            };
            let value = parse_text_value(name, &text).map_err(CliError::Usage)?;
            patch.sets.push((name.clone(), value));
        }
        let lost = lost_evidence(&ledger, id, &patch)?;
        // frob:ticket 01M5DJ4K69T67D50C19B4NY6RM
        let moved = patch
            .sets
            .iter()
            .find(|(name, _)| name == "parent")
            .and_then(|(_, v)| move_target(v.as_ref()))
            .and_then(|new_parent| claim_cover(ctx, &ledger).move_warning(id, new_parent));
        let (applied, warnings) =
            crate::lease_cmd::update_with_lease(ctx, &ledger, id, &patch, self.wait)?;
        tracing::info!(ticket = %id, already = applied.already, lost = lost.len(), "ticket update");
        // frob:ticket 01M3ZX85X37W6QSQSJD1WYVKZG
        let reindex_note = reindex_after(ctx, &ledger, id, &applied)?;
        let note = (!lost.is_empty() && !applied.already).then(|| {
            let each: Vec<String> = lost
                .iter()
                .map(|l| format!("{} ({} {}) lost criteria {:?}", l.event, l.provider, l.reference, l.lost))
                .collect();
            format!(
                "evidence lost its acceptance criterion: {}; re-offer it with a new `ticket evidence add --accepts N`",
                each.join("; ")
            )
        });
        let lost = if applied.already { Vec::new() } else { lost };
        let data = UpdateData {
            change: ChangeData::from(&applied),
            lost_evidence: lost,
        };
        let out = gob_cli::Payload::new(data).with_already(applied.already);
        let out = warnings
            .into_iter()
            .chain(note)
            .chain(moved.filter(|_| !applied.already))
            .chain(reindex_note)
            .chain(applied.warnings.iter().cloned())
            .fold(out, gob_cli::Payload::with_warning);
        Ok(out)
    }
}

/// The live claims folded into a coverage map; empty (nothing covered) when the lease view or the ledger is unavailable.
// frob:ticket 01M5DJ4K69T67D50C19B4NY6RM
fn claim_cover(ctx: &Context, ledger: &frob_ledger::Ledger) -> frob_ledger::claim_cover::CoverMap {
    use frob_ledger::guards::LeaseCheck;
    let claims = match super::read::build_lease_guard(&ctx.cwd, ctx.clock.clone()) {
        Ok(g) => g.claims(),
        Err(msg) => {
            tracing::warn!(error = %msg, "claim coverage unavailable: lease view failed");
            return frob_ledger::claim_cover::CoverMap::default();
        }
    };
    ledger.cover_map(claims).unwrap_or_else(|e| {
        tracing::warn!(error = %e, "claim coverage unavailable: ledger view failed");
        frob_ledger::claim_cover::CoverMap::default()
    })
}

/// The new parent a `parent` patch value names: `Some(None)` for unset, `Some(Some(id))` for a ticket, `None` when unparseable.
// frob:ticket 01M5DJ4K69T67D50C19B4NY6RM
#[allow(clippy::option_option)] // outer: key absent; inner: parent cleared
fn move_target(value: Option<&toml::Value>) -> Option<Option<frob_ledger::TicketId>> {
    match value {
        None => Some(None),
        Some(toml::Value::String(s)) if s.is_empty() => Some(None),
        Some(toml::Value::String(s)) => s.parse().ok().map(Some),
        Some(_) => None,
    }
}

/// Spellings `link` and `unlink` accept: the canonical kinds plus `parent` and `child`.
fn link_kind_names() -> &'static [&'static str] {
    &[
        "blocks",
        "blocked-by",
        "relates",
        "duplicates",
        "duplicated-by",
        "causes",
        "caused-by",
        "split-from",
        "splits",
        "discovered-from",
        "spawned",
        "enabler-for",
        "enabled-by",
        "supersedes",
        "superseded-by",
        "parent",
        "child",
    ]
}

/// A link kind as typed: a table kind, or the field-backed `parent` and `child`.
#[derive(Debug, Clone, Copy)]
enum KindArg {
    Table(LinkKind),
    Parent,
    Child,
}

/// The positionals and flag of `ticket link` and `ticket unlink`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct KindArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(value_name = "TARGET", help = "The other ticket")]
    target: String,
    #[arg(long, value_name = "VALUE", value_parser = choices(link_kind_names()), help = "Link kind from the canonical table")]
    kind: String,
}

fn parse_kind(name: &str) -> Result<KindArg, CliError> {
    match name {
        "parent" => Ok(KindArg::Parent),
        "child" => Ok(KindArg::Child),
        other => other
            .parse::<LinkKind>()
            .map(KindArg::Table)
            .map_err(|e| CliError::Usage(e.to_string())),
    }
}

/// Add a typed link between two tickets; repeating it is a no-op.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket link",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Link {
    ticket: String,
    target: String,
    kind: KindArg,
}

/// Remove a typed link between two tickets; removing a missing link is a no-op.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket unlink",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Unlink {
    ticket: String,
    target: String,
    kind: KindArg,
}

fn parent_patch(parent: Option<String>) -> Patch {
    Patch {
        sets: vec![("parent".to_owned(), parent.map(toml::Value::String))],
        ..Patch::default()
    }
}

impl Command for Link {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<KindArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<KindArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            target: a.target,
            kind: parse_kind(&a.kind)?,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let (id, target) = (
            resolve(&ledger, &self.ticket)?,
            resolve(&ledger, &self.target)?,
        );
        let applied = match self.kind {
            KindArg::Table(k) => ledger.link(id, k, target),
            KindArg::Parent => ledger.update(id, &parent_patch(Some(target.to_string()))),
            KindArg::Child => ledger.update(target, &parent_patch(Some(id.to_string()))),
        }
        .map_err(cli_err)?;
        tracing::info!(ticket = %id, target = %target, already = applied.already, "ticket link");
        Ok(payload(&applied))
    }
}

impl Command for Unlink {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<KindArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<KindArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            target: a.target,
            kind: parse_kind(&a.kind)?,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let (id, target) = (
            resolve(&ledger, &self.ticket)?,
            resolve(&ledger, &self.target)?,
        );
        let applied = match self.kind {
            KindArg::Table(k) => ledger.unlink(id, k, target),
            KindArg::Parent => unset_parent_if(&ledger, id, target),
            KindArg::Child => unset_parent_if(&ledger, target, id),
        }
        .map_err(cli_err)?;
        tracing::info!(ticket = %id, target = %target, already = applied.already, "ticket unlink");
        Ok(payload(&applied))
    }
}

/// Clear `child`'s parent only when it is `parent`; anything else is already unlinked.
fn unset_parent_if(
    ledger: &frob_ledger::Ledger,
    child: frob_ledger::TicketId,
    parent: frob_ledger::TicketId,
) -> frob_ledger::Result<frob_ledger::Applied> {
    let view = ledger.show(child)?;
    if view.ticket.front.parent == Some(parent) {
        ledger.update(child, &parent_patch(None))
    } else {
        ledger.update(child, &Patch::default())
    }
}

/// Add a comment (note, decision, question or answer) to a ticket.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket comment",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct Comment {
    ticket: String,
    body: String,
    subtype: CommentSubtype,
}

/// The flags of `ticket comment`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct CommentArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, value_name = "TEXT", help = "Comment text (markdown)")]
    body: String,
    #[arg(long, value_name = "VALUE", value_parser = choices(CommentSubtype::NAMES), help = "note (default), decision, question or answer")]
    subtype: Option<String>,
}

impl Command for Comment {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<CommentArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<CommentArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            body: a.body,
            subtype: parsed("subtype", a.subtype)?.unwrap_or(CommentSubtype::Note),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let applied = ledger
            .comment(id, self.subtype, &self.body)
            .map_err(cli_err)?;
        tracing::info!(ticket = %id, subtype = %self.subtype, "ticket comment");
        Ok(payload(&applied))
    }
}

/// Close a ticket with an outcome once every close guard passes; repeating is a no-op.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket close",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Close {
    ticket: String,
    outcome: Option<Outcome>,
    reason: Option<String>,
    no_evidence: bool,
    no_changelog: bool,
    no_land: bool,
}

/// The flags of `ticket close`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct CloseArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, value_name = "VALUE", value_parser = choices(Outcome::NAMES), help = "Why the ticket is done (required)")]
    outcome: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Free-text reason recorded on the event; required with --no-evidence and --no-changelog"
    )]
    reason: Option<String>,
    #[arg(
        long,
        help = "Close without measured evidence; needs --reason and is audited"
    )]
    no_evidence: bool,
    #[arg(
        long,
        help = "Close done although the ticket branch holds commits not merged into the base; needs --reason and is audited"
    )]
    no_land: bool,
    #[arg(
        long,
        help = "Close without a changelog fragment; needs --reason and is audited"
    )]
    no_changelog: bool,
}

impl Command for Close {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<CloseArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<CloseArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            outcome: parsed("outcome", a.outcome)?,
            reason: a.reason,
            no_evidence: a.no_evidence,
            no_changelog: a.no_changelog,
            no_land: a.no_land,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        if self.no_evidence && self.reason.as_deref().is_none_or(|r| r.trim().is_empty()) {
            return Err(CliError::Usage(
                "--no-evidence needs --reason <text> saying why no evidence is recorded".to_owned(),
            ));
        }
        if self.no_changelog && self.reason.as_deref().is_none_or(|r| r.trim().is_empty()) {
            return Err(CliError::Usage(
                "--no-changelog needs --reason <text> saying why the change needs no changelog note"
                    .to_owned(),
            ));
        }
        // frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
        if self.no_land && self.reason.as_deref().is_none_or(|r| r.trim().is_empty()) {
            return Err(CliError::Usage(
                "--no-land needs --reason <text> saying why the unmerged branch is acceptable"
                    .to_owned(),
            ));
        }
        // frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
        if let Some(msg) = frob_evidence::done::missing_reason(self.outcome, self.reason.as_deref())
        {
            return Err(CliError::Usage(msg));
        }
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let ws = frob_evidence::Workspace::open(&ctx.cwd, ctx.clock.clone())
            .map_err(CliError::internal)?;
        let mut evidence = frob_evidence::EvidenceGuard::for_ticket(&ledger, &ws.store, id)
            .map_err(CliError::internal)?;
        if self.no_evidence {
            evidence = evidence.allow_bypass(self.reason.clone().unwrap_or_default());
        }
        let mut done = frob_evidence::DoneGuard::for_ticket(&ledger, id, &ws.root)
            .map_err(CliError::internal)?;
        if self.no_evidence {
            done = done.allow_bypass(self.reason.clone().unwrap_or_default());
        }
        if self.no_changelog {
            done = done.allow_no_changelog(self.reason.clone().unwrap_or_default());
        }
        // frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
        let view = ledger.show(id).map_err(cli_err)?;
        let mut merged = frob_evidence::done::MergedGuard::for_ticket(
            &ledger,
            ledger.repo(),
            id,
            &frob_worktree::work::base_branch(&ledger),
            &view.summary.handle,
        )
        .map_err(CliError::internal)?;
        if self.no_land {
            merged = merged.allow_no_land(self.reason.clone().unwrap_or_default());
        }
        let already_done = view.summary.category == frob_ledger::model::Category::Done;
        if !already_done {
            done.record_exemption(&ledger, id)
                .map_err(CliError::internal)?;
            if frob_evidence::done::guards_apply(self.outcome) {
                merged
                    .record_exemption(&ledger, id)
                    .map_err(CliError::internal)?;
            }
        }
        let guards = default_close_guards();
        let mut refs: Vec<&dyn frob_ledger::guards::CloseGuard> =
            guards.iter().map(|g| &**g).collect();
        refs.push(&evidence);
        refs.push(&done);
        refs.push(&merged);
        let applied = ledger
            .close(id, self.outcome, self.reason.clone(), &refs)
            .map_err(cli_err)?;
        if !applied.already {
            let recorded = evidence
                .record_bypass(&ledger, id)
                .map_err(CliError::internal)?;
            tracing::info!(ticket = %id, bypass = recorded.is_some(), "evidence bypass audited");
        }
        tracing::info!(ticket = %id, already = applied.already, "ticket close");
        // frob:ticket 01M42MGN8882Y65TVXH0V1WTNR
        let release_warnings = super::terminal_lease::release_on_terminal(ctx, id);
        let mut data = ChangeData::from(&applied);
        if !applied.already {
            data.changelog_exempt = done.exemption_reason().map(str::to_owned);
        }
        let out = gob_cli::Payload::new(data).with_already(applied.already);
        let out = release_warnings
            .into_iter()
            .chain(applied.warnings.iter().cloned())
            .fold(out, gob_cli::Payload::with_warning);
        Ok(if applied.already {
            out
        } else {
            done.warnings(&applied.ticket)
                .into_iter()
                .fold(out, gob_cli::Payload::with_warning)
        })
    }
}

// frob:ticket 01M4FDQFHJKT30DHZEEA6GWB4R
/// Close a finished ticket after the fact: needs bound evidence and a reason, takes no lease and counts toward no cycle.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket closeout",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Closeout {
    ticket: String,
    reason: String,
}

/// The flags of `ticket closeout`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct CloseoutArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why the ticket is closed after the fact; recorded on the close event"
    )]
    reason: String,
}

impl Command for Closeout {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<CloseoutArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<CloseoutArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        if self.reason.trim().is_empty() {
            return Err(CliError::Usage(
                "--reason needs text saying why the ticket is closed after the fact".to_owned(),
            ));
        }
        // The evidence, changelog and merge guards all apply: only the lease and the cycle are skipped.
        Close {
            ticket: self.ticket.clone(),
            outcome: Some(Outcome::Done),
            reason: Some(format!(
                "{}{}",
                frob_pm::cycle::velocity::RETROACTIVE_PREFIX,
                self.reason.trim()
            )),
            no_evidence: false,
            no_changelog: false,
            no_land: false,
        }
        .run(ctx)
    }
}

/// Drop a ticket: close it as wont-fix with a required reason.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket drop",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct DropTicket {
    ticket: String,
    reason: String,
}

/// The flags of `ticket drop`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DropTicketArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, value_name = "TEXT", help = "Why the ticket is dropped")]
    reason: String,
}

impl Command for DropTicket {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<DropTicketArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DropTicketArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let applied = ledger.drop_ticket(id, &self.reason).map_err(cli_err)?;
        tracing::info!(ticket = %id, already = applied.already, "ticket drop");
        // frob:ticket 01M42MGN8882Y65TVXH0V1WTNR
        Ok(super::terminal_lease::release_on_terminal(ctx, id)
            .into_iter()
            .fold(payload(&applied), gob_cli::Payload::with_warning))
    }
}

/// Reopen a done ticket into todo with a required reason.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket reopen",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Reopen {
    ticket: String,
    reason: String,
}

/// The flags of `ticket reopen`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ReopenArgs {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(long, value_name = "TEXT", help = "Why the ticket is reopened")]
    reason: String,
}

impl Command for Reopen {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ReopenArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ReopenArgs>(m)?;
        Ok(Self {
            ticket: a.ticket.ticket,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let applied = ledger.reopen(id, &self.reason).map_err(cli_err)?;
        tracing::info!(ticket = %id, already = applied.already, "ticket reopen");
        Ok(payload(&applied))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
    #[test]
    fn good_first_adds_the_label_and_a_start_here_scaffold() {
        let mut labels = vec!["x".to_owned()];
        let body = good_first_body("", true, &mut labels);
        assert_eq!(labels, ["x", "good-first"]);
        assert!(body.starts_with("## Start here\n"), "{body}");
        assert!(body.contains("Test command:"), "{body}");
    }

    // frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
    #[test]
    fn good_first_keeps_the_given_body_and_does_not_repeat_the_label() {
        let mut labels = vec!["good-first".to_owned()];
        let body = good_first_body("why\n", true, &mut labels);
        assert_eq!(labels, ["good-first"]);
        assert!(body.starts_with("why\n\n## Start here"), "{body}");
    }

    // frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
    #[test]
    fn without_the_flag_body_and_labels_are_untouched() {
        let mut labels = Vec::new();
        assert_eq!(good_first_body("b", false, &mut labels), "b");
        assert!(labels.is_empty());
    }
}

//! Mutating ticket verbs: new, update, link, unlink, comment, close, drop, reopen.

use frob_ledger::guards::default_close_guards;
use frob_ledger::model::{
    Category, CommentSubtype, LinkKind, Outcome, Points, Priority, TicketType,
};
use frob_ledger::ops::{NewTicket, Patch};
use frob_ledger::schema::parse_text_value;
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome};

use super::{
    ChangeData, choice_flag, cli_err, get, get_many, get_parsed, many_flag, open, payload, resolve,
    text_flag, ticket_arg,
};

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
    points: Option<Points>,
    parent: Option<String>,
    blocked_by: Vec<String>,
    scope: Vec<String>,
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
}

impl Command for New {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(text_flag("title", "Ticket title").required(true))
            .arg(choice_flag(
                "type",
                TicketType::NAMES,
                "Ticket type (default task)",
            ))
            .arg(choice_flag(
                "priority",
                Priority::NAMES,
                "Priority (default medium)",
            ))
            .arg(choice_flag(
                "category",
                &["triage", "todo"],
                "Starting category (default todo)",
            ))
            .arg(text_flag("points", "Story points: 1, 2, 3, 5, 8 or 13"))
            .arg(text_flag("parent", "Parent ticket"))
            .arg(many_flag(
                "blocked-by",
                "A ticket that blocks this one (repeatable)",
            ))
            .arg(many_flag("scope", "Write-scope glob (repeatable)"))
            .arg(many_flag("label", "Label (repeatable)"))
            .arg(many_flag("acceptance", "Acceptance criterion (repeatable)"))
            .arg(many_flag(
                "alias",
                "Id from another system, such as v1 T-0042 (repeatable)",
            ))
            .arg(text_flag("body", "Markdown body"))
            .arg(text_flag(
                "idempotency-key",
                "Return the same ticket for the same key",
            ))
            .arg(text_flag("persona", "Story persona"))
            .arg(text_flag("capability", "Story capability"))
            .arg(text_flag("so-that", "Story outcome (so that ...)"))
            .arg(text_flag("flavour", "Free-form flavour such as user_story"))
            .arg(text_flag("assignee", "Assignee"))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let points = get(m, "points")
            .map(|p| {
                p.parse::<Points>()
                    .map_err(|e| CliError::Usage(format!("--points: {e}")))
            })
            .transpose()?;
        Ok(Self {
            req: Box::new(NewRequest {
                title: get(m, "title").unwrap_or_default(),
                ty: get_parsed(m, "type")?.unwrap_or(TicketType::Task),
                category: get_parsed(m, "category")?.unwrap_or(Category::Todo),
                priority: get_parsed(m, "priority")?.unwrap_or(Priority::Medium),
                points,
                parent: get(m, "parent"),
                blocked_by: get_many(m, "blocked-by"),
                scope: get_many(m, "scope"),
                labels: get_many(m, "label"),
                acceptance: get_many(m, "acceptance"),
                aliases: get_many(m, "alias"),
                body: get(m, "body").unwrap_or_default(),
                key: get(m, "idempotency-key"),
                persona: get(m, "persona"),
                capability: get(m, "capability"),
                so_that: get(m, "so-that"),
                flavour: get(m, "flavour"),
                assignee: get(m, "assignee"),
            }),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let r = &*self.req;
        let mut req = NewTicket::new(r.title.clone(), r.ty);
        req.category = r.category;
        req.priority = r.priority;
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
        req.acceptance.clone_from(&r.acceptance);
        req.aliases.clone_from(&r.aliases);
        req.body.clone_from(&r.body);
        req.idempotency_key.clone_from(&r.key);
        req.persona.clone_from(&r.persona);
        req.capability.clone_from(&r.capability);
        req.outcome_text.clone_from(&r.so_that);
        req.flavour.clone_from(&r.flavour);
        req.assignee.clone_from(&r.assignee);
        let applied = ledger.new_ticket(req).map_err(cli_err)?;
        tracing::info!(ticket = %applied.ticket.front.id, already = applied.already, "ticket new");
        Ok(payload(&applied))
    }
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
    remove_scope: Vec<String>,
    clears: Vec<String>,
    add_acceptance: Vec<String>,
    remove_acceptance: Vec<usize>,
    clear_acceptance: bool,
    reason: Option<String>,
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

impl Command for Update {
    type Data = UpdateData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
            .arg(many_flag(
                "set",
                "FIELD=VALUE to set (repeatable; empty value unsets a scalar, lists need --clear); lists are comma separated; acceptance needs --add-acceptance",
            ))
            .arg(text_flag("title", "New title"))
            .arg(choice_flag("priority", Priority::NAMES, "New priority"))
            .arg(text_flag("points", "New story points"))
            .arg(many_flag("add-label", "Label to add (repeatable)"))
            .arg(many_flag("remove-label", "Label to remove (repeatable)"))
            .arg(many_flag("add-scope", "Scope glob to add (repeatable)"))
            .arg(many_flag(
                "remove-scope",
                "Scope glob to remove (repeatable)",
            ))
            .arg(many_flag(
                "add-acceptance",
                "Acceptance criterion to add, taken whole, commas included (repeatable)",
            ))
            .arg(
                Arg::new("remove-acceptance")
                    .long("remove-acceptance")
                    .value_name("N")
                    .action(ArgAction::Append)
                    .value_parser(gob_cli::clap::value_parser!(usize))
                    .help("1-based acceptance criterion to remove, as `ticket show` numbers them (repeatable); reports evidence that loses it"),
            )
            .arg(
                Arg::new("clear-acceptance")
                    .long("clear-acceptance")
                    .action(ArgAction::SetTrue)
                    .help("Remove every acceptance criterion; reports evidence that loses one"),
            )
            .arg(many_flag(
                "clear",
                "List field to empty (repeatable); the only way to empty a list",
            ))
            .arg(text_flag("reason", "Why (required when changing flavour)"))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let mut sets = Vec::new();
        for raw in get_many(m, "set") {
            let (k, v) = raw.split_once('=').ok_or_else(|| {
                CliError::Usage(format!("--set expects FIELD=VALUE, got `{raw}`"))
            })?;
            sets.push((k.trim().to_owned(), v.to_owned()));
        }
        for (flag, field) in [
            ("title", "title"),
            ("priority", "priority"),
            ("points", "points"),
        ] {
            if let Some(v) = get(m, flag) {
                sets.push((field.to_owned(), v));
            }
        }
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            sets,
            add_labels: get_many(m, "add-label"),
            remove_labels: get_many(m, "remove-label"),
            add_scope: get_many(m, "add-scope"),
            remove_scope: get_many(m, "remove-scope"),
            clears: get_many(m, "clear"),
            add_acceptance: get_many(m, "add-acceptance"),
            remove_acceptance: m
                .get_many::<usize>("remove-acceptance")
                .map(|v| v.copied().collect())
                .unwrap_or_default(),
            clear_acceptance: m.get_flag("clear-acceptance"),
            reason: get(m, "reason"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<UpdateData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let mut patch = Patch {
            add_labels: self.add_labels.clone(),
            remove_labels: self.remove_labels.clone(),
            add_scope: self.add_scope.clone(),
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
        let (applied, warnings) = crate::lease_cmd::update_with_lease(ctx, &ledger, id, &patch)?;
        tracing::info!(ticket = %id, already = applied.already, lost = lost.len(), "ticket update");
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
            .fold(out, gob_cli::Payload::with_warning);
        Ok(out)
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

fn kind_args() -> [Arg; 3] {
    [
        ticket_arg(),
        Arg::new("target")
            .required(true)
            .value_name("TARGET")
            .help("The other ticket"),
        choice_flag(
            "kind",
            link_kind_names(),
            "Link kind from the canonical table",
        )
        .required(true),
    ]
}

fn parse_kind(m: &ArgMatches) -> Result<KindArg, CliError> {
    let name = get(m, "kind").unwrap_or_default();
    match name.as_str() {
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
        cmd.args(kind_args())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            target: get(m, "target").unwrap_or_default(),
            kind: parse_kind(m)?,
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
        cmd.args(kind_args())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            target: get(m, "target").unwrap_or_default(),
            kind: parse_kind(m)?,
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

impl Command for Comment {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
            .arg(text_flag("body", "Comment text (markdown)").required(true))
            .arg(choice_flag(
                "subtype",
                CommentSubtype::NAMES,
                "note (default), decision, question or answer",
            ))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            body: get(m, "body").unwrap_or_default(),
            subtype: get_parsed(m, "subtype")?.unwrap_or(CommentSubtype::Note),
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
}

impl Command for Close {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
            .arg(choice_flag(
                "outcome",
                Outcome::NAMES,
                "Why the ticket is done (required)",
            ))
            .arg(text_flag(
                "reason",
                "Free-text reason recorded on the event; required with --no-evidence and --no-changelog",
            ))
            .arg(
                Arg::new("no-evidence")
                    .long("no-evidence")
                    .action(ArgAction::SetTrue)
                    .help("Close without measured evidence; needs --reason and is audited"),
            )
            .arg(
                Arg::new("no-changelog")
                    .long("no-changelog")
                    .action(ArgAction::SetTrue)
                    .help("Close without a changelog fragment; needs --reason and is audited"),
            )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            outcome: get_parsed(m, "outcome")?,
            reason: get(m, "reason"),
            no_evidence: m.get_flag("no-evidence"),
            no_changelog: m.get_flag("no-changelog"),
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
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let ws = frob_evidence::Workspace::open(&ctx.cwd).map_err(CliError::internal)?;
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
        let already_done = ledger.show(id).map_err(cli_err)?.summary.category
            == frob_ledger::model::Category::Done;
        if !already_done {
            done.record_exemption(&ledger, id)
                .map_err(CliError::internal)?;
        }
        let guards = default_close_guards();
        let mut refs: Vec<&dyn frob_ledger::guards::CloseGuard> =
            guards.iter().map(|g| &**g).collect();
        refs.push(&evidence);
        refs.push(&done);
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
        let mut data = ChangeData::from(&applied);
        if !applied.already {
            data.changelog_exempt = done.exemption_reason().map(str::to_owned);
        }
        let out = gob_cli::Payload::new(data).with_already(applied.already);
        Ok(if applied.already {
            out
        } else {
            done.warnings(&applied.ticket)
                .into_iter()
                .fold(out, gob_cli::Payload::with_warning)
        })
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

impl Command for DropTicket {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
            .arg(text_flag("reason", "Why the ticket is dropped").required(true))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            reason: get(m, "reason").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ChangeData> {
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let applied = ledger.drop_ticket(id, &self.reason).map_err(cli_err)?;
        tracing::info!(ticket = %id, already = applied.already, "ticket drop");
        Ok(payload(&applied))
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

impl Command for Reopen {
    type Data = ChangeData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
            .arg(text_flag("reason", "Why the ticket is reopened").required(true))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            reason: get(m, "reason").unwrap_or_default(),
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

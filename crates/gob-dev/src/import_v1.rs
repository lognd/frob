//! One-off converter from the v1 ledger (`tickets/T-NNNN/ticket.md`, YAML) to
//! v2 ULID tickets (`tickets/<ulid>/ticket.md` plus `events/*.toml`), T-0025.
//!
//! Every v2 file is produced by `frob-ledger` itself: events are rendered with
//! [`Event::to_toml`], the ticket document is the [`fold`] of those events
//! rendered with [`doc::render`], so the integrity invariant holds by
//! construction and is then re-checked from the rendered text ([`verify`]).
//!
//! # Identity and time
//!
//! v1 keeps only a creation *date*. A ticket ULID is minted with the
//! timestamp of that date at 00:00:00 UTC plus the v1 ticket number as
//! milliseconds, so creation order survives and no two ids share a prefix.
//! Events of a ticket take the same time base: event `i` is at
//! `date + i` seconds with the ticket number again as milliseconds, so the
//! ULID time and `at` agree (the doctor skew check) and the `create` event
//! sorts first. These instants are synthetic: real times live in git history.

// frob:ticket 01M3WYJ80SHJ13W4MKEA81AHGY
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use frob_evidence::events::KIND_EVIDENCE;
use frob_evidence::record::{EvidenceRecord, Provider, Status};
use frob_ledger::event::{
    CommentData, CreateData, EVENT_REV, Event, EventBody, TransitionData, kind_name,
};
use frob_ledger::fold::fold;
use frob_ledger::id::compute_handles;
use frob_ledger::model::{
    Category, CommentSubtype, Link, LinkKind, Outcome, Points, Priority, Stamp, TicketType,
};
use frob_ledger::rules::{tick001, tick003};
use frob_ledger::{EventId, TicketId, doc};
use serde::{Deserialize, Serialize};
use ulid::Ulid;

/// Actor recorded on every imported event that has no better attribution.
pub const IMPORT_ACTOR: &str = "import";

/// v1 keys that are carried into the v2 ticket (or into its events).
const CARRIED: &[&str] = &[
    "id",
    "title",
    "state",
    "kind",
    "origin",
    "created",
    "priority",
    "parent",
    "tier",
    "milestone",
    "flavour",
    "points",
    "scope",
    "labels",
    "blocked_by",
    "component",
    "acceptance",
    "evidence",
];

/// Every v1 field that cannot be carried, with the reason; also written to `docs/migration/v1-import.md`.
pub const DROPPED_FIELDS: &[(&str, &str)] = &[
    (
        "worktree",
        "per-checkout lease state; v2 leases are local runtime state and worktrees derive from the handle",
    ),
    (
        "branch",
        "per-checkout lease state; v2 derives the branch name from the handle",
    ),
    (
        "sprint",
        "v2 has no sprint field (cycles arrive in milestone 2)",
    ),
    ("due", "v2 has no due-date field"),
    ("rank", "v2 orders by priority and points; no manual rank"),
    (
        "runs_last",
        "v1 scheduling hint; v2 leases replace the run-last queue",
    ),
    (
        "runs_last_parallel_safe",
        "v1 scheduling hint with no v2 equivalent",
    ),
    (
        "runs_last_parallel_safe_reason",
        "reason for a dropped v1 scheduling hint",
    ),
    (
        "unsized_ack",
        "v1 sizing-gate waiver; v2 has no sizing gate",
    ),
    (
        "unsized_ack_reason",
        "reason for a dropped v1 sizing-gate waiver",
    ),
    (
        "tokens_in",
        "v1 cost telemetry; v2 cost events arrive in milestone 2",
    ),
    ("tokens_out", "v1 cost telemetry; see tokens_in"),
    ("tokens_cache_read", "v1 cost telemetry; see tokens_in"),
    ("usage", "v1 cost telemetry; see tokens_in"),
    (
        "scope_breadth_ack",
        "v1 scope-breadth gate waiver; v2 has no such gate",
    ),
    (
        "scope_breadth_ack_reason",
        "reason for a dropped v1 scope-breadth waiver",
    ),
    (
        "no_scope_declared",
        "v1 scope gate waiver; v2 treats an empty scope as unscoped",
    ),
    (
        "no_scope_declared_reason",
        "reason for a dropped v1 scope waiver",
    ),
    (
        "scope_changes",
        "v1 scope audit trail; v2 records changes as field events going forward, the old trail stays in git history",
    ),
    (
        "body_changes",
        "v1 body audit trail; the old trail stays in git history",
    ),
    (
        "triage_changes",
        "v1 triage audit trail; the old trail stays in git history",
    ),
    (
        "designated_repro_test",
        "v1 bug repro binding; v2 binds tests with `frob:tests`",
    ),
    (
        "threat",
        "v1 security threat text; v2 keeps threats in the body",
    ),
    ("anchor", "v1 anchor gate; no v2 equivalent"),
    ("anchor_reason", "reason for a dropped v1 anchor"),
    (
        "land_commit",
        "v1 land record; v2 derives the landing commit from git history",
    ),
    (
        "findings",
        "v1 post-land sweep findings of dropped draft tickets; v1 gate output, not ticket data",
    ),
];

/// Behaviour that is dropped without being a frontmatter key.
pub const DROPPED_BEHAVIOUR: &[(&str, &str)] = &[
    (
        "per-criterion acceptance evidence",
        "criteria are imported with bound=false; the v1 evidence lines become `evidence` events whose `accepts` lists the criteria they were offered for",
    ),
    (
        "evidence transcripts",
        "v1 stored only `cmd`, exit code and a 12-hex sha256 prefix; the digest field holds that prefix (not a blake3 hash) and no blob exists",
    ),
    (
        "state history",
        "v1 keeps only the current state, so each ticket gets one `transition` to its final state; in-progress becomes todo (leases do not carry over)",
    ),
    (
        "real timestamps",
        "v1 `created` has day granularity; all imported event times are synthetic offsets from it (see the module docs)",
    ),
];

/// Failure of an import run.
#[derive(Debug, thiserror::Error)]
pub enum ImportError {
    /// A file could not be read, written or listed.
    #[error("{path}: {message}")]
    Io {
        /// The path involved.
        path: String,
        /// The OS error text.
        message: String,
    },
    /// A v1 ticket could not be mapped.
    #[error("{ticket}: {message}")]
    Ticket {
        /// The v1 id or file label.
        ticket: String,
        /// What is wrong.
        message: String,
    },
    /// The target directory already holds files.
    #[error("{0} exists and is not empty; refusing to overwrite")]
    TargetNotEmpty(String),
    /// The ledger integrity check over the converted tree failed.
    #[error("integrity check failed:\n{0}")]
    Integrity(String),
}

fn io_err(path: &Path, e: &std::io::Error) -> ImportError {
    ImportError::Io {
        path: path.display().to_string(),
        message: e.to_string(),
    }
}

fn ticket_err(ticket: &str, message: impl Into<String>) -> ImportError {
    ImportError::Ticket {
        ticket: ticket.to_owned(),
        message: message.into(),
    }
}

/// Options of one import run.
#[derive(Debug, Clone)]
pub struct ImportOptions {
    /// The v1 ledger directory (`tickets`).
    pub from: PathBuf,
    /// Where to write the v2 tree.
    pub to: PathBuf,
    /// Convert and verify in memory, write nothing.
    pub dry_run: bool,
}

#[derive(Debug, Deserialize)]
struct V1Acceptance {
    text: String,
    #[serde(default)]
    evidence: Vec<String>,
}

/// The v1 frontmatter keys the importer carries; everything else is counted as dropped.
#[derive(Debug, Deserialize)]
struct V1Front {
    id: String,
    title: String,
    state: String,
    kind: String,
    #[serde(default)]
    origin: Option<String>,
    created: String,
    #[serde(default)]
    priority: Option<String>,
    #[serde(default)]
    parent: Option<String>,
    #[serde(default)]
    tier: Option<String>,
    #[serde(default)]
    milestone: Option<String>,
    #[serde(default)]
    flavour: Option<String>,
    #[serde(default)]
    points: Option<u8>,
    #[serde(default)]
    scope: Vec<String>,
    #[serde(default)]
    labels: Vec<String>,
    #[serde(default)]
    blocked_by: Vec<String>,
    #[serde(default)]
    component: Option<String>,
    #[serde(default)]
    acceptance: Vec<V1Acceptance>,
    #[serde(default)]
    evidence: Vec<String>,
}

/// One parsed v1 ticket.
#[derive(Debug)]
struct V1Ticket {
    front: V1Front,
    body: String,
    done_report: Option<String>,
    /// Frontmatter keys present with a non-empty value.
    present: BTreeSet<String>,
}

/// A converted ticket as text: what is written to disk and what [`verify`] reads.
#[derive(Debug, Clone)]
pub struct Rendered {
    /// The v1 id (or the directory name when read back from disk).
    pub v1_id: String,
    /// The v2 id.
    pub id: TicketId,
    /// Text of `ticket.md`.
    pub ticket_md: String,
    /// Event files, `(id, toml text)`.
    pub events: Vec<(EventId, String)>,
}

/// One row of the summary table.
#[derive(Debug, Clone, Serialize)]
pub struct Row {
    /// The v1 id.
    pub v1: String,
    /// The v2 ULID.
    pub ulid: String,
    /// The v2 handle (`~suffix`).
    pub handle: String,
    /// The v2 type.
    pub ty: String,
    /// The v2 category (with outcome when done).
    pub category: String,
}

/// The outcome of an import run.
#[derive(Debug, Default)]
pub struct ImportReport {
    /// One row per ticket, in v1 id order.
    pub rows: Vec<Row>,
    /// Count of tickets per v2 type.
    pub by_type: BTreeMap<String, usize>,
    /// Count of tickets per v2 category.
    pub by_category: BTreeMap<String, usize>,
    /// Count of tickets that carried a non-empty value for each dropped v1 key.
    pub dropped: BTreeMap<String, usize>,
    /// Non-fatal oddities (unknown keys, skipped links).
    pub warnings: Vec<String>,
    /// Events written (or that would be written).
    pub events: usize,
}

/// Mint a ULID for `unix_secs` plus `millis` milliseconds with a random tail.
fn mint(unix_secs: i64, millis: u64) -> Result<Ulid, ImportError> {
    let secs = u64::try_from(unix_secs)
        .map_err(|_| ticket_err("clock", format!("{unix_secs} is before the epoch")))?;
    Ok(Ulid::from_parts(secs * 1000 + millis, Ulid::new().random()))
}

/// Unix seconds of `YYYY-MM-DD` at 00:00:00 UTC.
fn day_start(v1: &str, day: &str) -> Result<i64, ImportError> {
    let date: jiff::civil::Date = day
        .parse()
        .map_err(|e| ticket_err(v1, format!("created `{day}` is not a date: {e}")))?;
    let zoned = date
        .at(0, 0, 0, 0)
        .to_zoned(jiff::tz::TimeZone::UTC)
        .map_err(|e| ticket_err(v1, format!("created `{day}` is out of range: {e}")))?;
    Ok(zoned.timestamp().as_second())
}

/// The number in `T-0003`.
fn ticket_number(v1: &str) -> Result<u64, ImportError> {
    v1.strip_prefix("T-")
        .and_then(|n| n.parse().ok())
        .ok_or_else(|| ticket_err(v1, "id is not T-<number>"))
}

/// Issues the event ids and instants of one ticket.
struct Clock {
    day: i64,
    number: u64,
    next: i64,
    v1: String,
}

impl Clock {
    fn new(v1: &str, day: i64, number: u64) -> Self {
        Self {
            day,
            number,
            next: 0,
            v1: v1.to_owned(),
        }
    }

    fn tick(&mut self) -> Result<(EventId, Stamp), ImportError> {
        let secs = self.day + self.next;
        self.next += 1;
        let id = EventId::from_ulid(
            mint(secs, self.number).map_err(|e| ticket_err(&self.v1, e.to_string()))?,
        );
        Ok((id, Stamp::from_unix(secs)))
    }
}

fn split_front<'a>(label: &str, text: &'a str) -> Result<(&'a str, &'a str), ImportError> {
    let rest = text
        .strip_prefix("---\n")
        .ok_or_else(|| ticket_err(label, "missing opening `---` fence"))?;
    let mut offset = 0;
    for line in rest.split_inclusive('\n') {
        if line.trim_end() == "---" {
            return Ok((&rest[..offset], &rest[offset + line.len()..]));
        }
        offset += line.len();
    }
    Err(ticket_err(label, "missing closing `---` fence"))
}

fn is_empty_value(v: &serde_yaml_ng::Value) -> bool {
    use serde_yaml_ng::Value;
    match v {
        Value::Null | Value::Bool(false) => true,
        Value::Sequence(s) => s.is_empty(),
        Value::Mapping(m) => m.is_empty(),
        _ => false,
    }
}

fn parse_v1(label: &str, text: &str, done_report: Option<String>) -> Result<V1Ticket, ImportError> {
    let (front_text, body) = split_front(label, text)?;
    let value: serde_yaml_ng::Value =
        serde_yaml_ng::from_str(front_text).map_err(|e| ticket_err(label, e.to_string()))?;
    let present = value
        .as_mapping()
        .map(|m| {
            m.iter()
                .filter(|(_, v)| !is_empty_value(v))
                .filter_map(|(k, _)| k.as_str().map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();
    let front: V1Front =
        serde_yaml_ng::from_value(value).map_err(|e| ticket_err(label, e.to_string()))?;
    Ok(V1Ticket {
        front,
        body: body.trim_matches('\n').to_owned(),
        done_report,
        present,
    })
}

/// Read every `T-<number>/ticket.md` under `from` (drafts and other names are skipped).
fn read_v1(from: &Path) -> Result<Vec<V1Ticket>, ImportError> {
    let mut dirs: Vec<(u64, PathBuf)> = Vec::new();
    for entry in std::fs::read_dir(from).map_err(|e| io_err(from, &e))? {
        let entry = entry.map_err(|e| io_err(from, &e))?;
        let name = entry.file_name().to_string_lossy().into_owned();
        match ticket_number(&name) {
            Ok(n) if entry.path().join("ticket.md").is_file() => dirs.push((n, entry.path())),
            _ => tracing::info!(%name, "skipped: not a v1 ticket directory"),
        }
    }
    dirs.sort();
    let mut out = Vec::new();
    for (_, dir) in dirs {
        let md = dir.join("ticket.md");
        let text = std::fs::read_to_string(&md).map_err(|e| io_err(&md, &e))?;
        let report_path = dir.join("done-report.md");
        let report = if report_path.is_file() {
            Some(std::fs::read_to_string(&report_path).map_err(|e| io_err(&report_path, &e))?)
        } else {
            None
        };
        out.push(parse_v1(&md.display().to_string(), &text, report)?);
    }
    tracing::info!(count = out.len(), "v1 tickets read");
    Ok(out)
}

fn map_type(v1: &V1Front) -> Result<(TicketType, Option<String>), ImportError> {
    let flavour = v1.flavour.clone();
    match v1.tier.as_deref() {
        Some("epic") => return Ok((TicketType::Epic, flavour)),
        Some("story") => return Ok((TicketType::Story, flavour)),
        _ => {}
    }
    let (ty, forced) = match v1.kind.as_str() {
        "feature" => (TicketType::Task, None),
        "ux" => (TicketType::Task, Some("ux".to_owned())),
        "bug" => (TicketType::Bug, None),
        "security" => (TicketType::Security, None),
        "docs" => (TicketType::Docs, None),
        "invariant" => (TicketType::Invariant, None),
        "incident" => (TicketType::Incident, None),
        other => return Err(ticket_err(&v1.id, format!("unknown kind `{other}`"))),
    };
    Ok((ty, forced.or(flavour)))
}

fn map_state(v1: &V1Front) -> Result<(Category, Option<Outcome>), ImportError> {
    match v1.state.as_str() {
        "queued" | "planned" | "in-progress" => Ok((Category::Todo, None)),
        "done" | "archived" => Ok((Category::Done, Some(Outcome::Done))),
        "dropped" => Ok((Category::Done, Some(Outcome::WontFix))),
        other => Err(ticket_err(&v1.id, format!("unknown state `{other}`"))),
    }
}

/// Text under `## Drop reason` in a v1 body, up to the next heading.
fn drop_reason(body: &str) -> Option<String> {
    let mut lines = body.lines().skip_while(|l| l.trim() != "## Drop reason");
    lines.next()?;
    let text: Vec<&str> = lines.take_while(|l| !l.starts_with("## ")).collect();
    let text = text.join("\n").trim().to_owned();
    (!text.is_empty()).then_some(text)
}

/// A parsed v1 evidence line: `cmd:<command> exit=<n> sha256=<hex>`.
fn parse_evidence(line: &str) -> Option<(String, i32, String)> {
    let rest = line.strip_prefix("cmd:")?;
    let (rest, digest) = rest.rsplit_once(" sha256=")?;
    let (command, exit) = rest.rsplit_once(" exit=")?;
    Some((command.to_owned(), exit.parse().ok()?, digest.to_owned()))
}

fn evidence_text(
    id: EventId,
    at: Stamp,
    record: &EvidenceRecord,
) -> Result<(EventId, String), ImportError> {
    #[derive(Serialize)]
    struct Envelope<'a> {
        kind: &'a str,
        at: Stamp,
        actor: &'a str,
        rev: u32,
    }
    let envelope = Envelope {
        kind: KIND_EVIDENCE,
        at,
        actor: IMPORT_ACTOR,
        rev: EVENT_REV,
    };
    let mut text = toml::to_string(&envelope).map_err(|e| ticket_err("evidence", e.to_string()))?;
    text.push_str(&toml::to_string(record).map_err(|e| ticket_err("evidence", e.to_string()))?);
    Ok((id, text))
}

/// Evidence events of one ticket, deduplicated by command, with the criteria each was offered for.
fn evidence_events(
    v1: &V1Ticket,
    clock: &mut Clock,
    report: &mut ImportReport,
) -> Result<Vec<(EventId, String)>, ImportError> {
    let mut accepts: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
    for line in &v1.front.evidence {
        accepts.entry(line).or_default();
    }
    for (i, a) in v1.front.acceptance.iter().enumerate() {
        for line in &a.evidence {
            accepts.entry(line).or_default().push(i + 1);
        }
    }
    let mut out = Vec::new();
    for (line, accepted) in accepts {
        let Some((command, exit, digest)) = parse_evidence(line) else {
            report.warnings.push(format!(
                "{}: evidence `{line}` is not a cmd record; skipped",
                v1.front.id
            ));
            continue;
        };
        let (id, at) = clock.tick()?;
        let record = EvidenceRecord {
            provider: Provider::Command,
            reference: command,
            digest,
            uri: None,
            status: if exit == 0 {
                Status::Measured
            } else {
                Status::Unmeasured
            },
            captured_at: at,
            accepts: accepted,
            passed: Some(exit == 0),
            exit_code: Some(exit),
            tests: Vec::new(),
            inline: None,
            size: 0,
        };
        out.push(evidence_text(id, at, &record)?);
    }
    Ok(out)
}

fn event_text(
    clock: &mut Clock,
    actor: &str,
    body: EventBody,
) -> Result<(EventId, String), ImportError> {
    let (id, at) = clock.tick()?;
    let ev = Event {
        id,
        at,
        actor: actor.to_owned(),
        rev: EVENT_REV,
        kind: kind_name(&body).to_owned(),
        body,
    };
    let text = ev
        .to_toml()
        .map_err(|e| ticket_err(&clock.v1, e.to_string()))?;
    Ok((id, text))
}

fn links_of(
    v1: &V1Front,
    ids: &BTreeMap<String, TicketId>,
    report: &mut ImportReport,
) -> (Option<TicketId>, Vec<Link>) {
    let mut resolve = |what: &str, target: &str| {
        let found = ids.get(target).copied();
        if found.is_none() {
            report.warnings.push(format!(
                "{}: {what} {target} is not in the v1 ledger; dropped",
                v1.id
            ));
        }
        found
    };
    let parent = v1.parent.as_deref().and_then(|p| resolve("parent", p));
    let links = v1
        .blocked_by
        .iter()
        .filter_map(|b| resolve("blocked_by", b))
        .map(|target| Link {
            kind: LinkKind::BlockedBy,
            target,
        })
        .collect();
    (parent, links)
}

fn create_data(
    v1: &V1Ticket,
    ids: &BTreeMap<String, TicketId>,
    report: &mut ImportReport,
) -> Result<CreateData, ImportError> {
    let f = &v1.front;
    let (ty, flavour) = map_type(f)?;
    let priority = f
        .priority
        .as_deref()
        .map_or(Ok(Priority::Medium), str::parse::<Priority>)
        .map_err(|e| ticket_err(&f.id, e.to_string()))?;
    let points = f
        .points
        .map(Points::new)
        .transpose()
        .map_err(|e| ticket_err(&f.id, e.to_string()))?;
    let (parent, links) = links_of(f, ids, report);
    let mut labels = f.labels.clone();
    labels.extend(f.milestone.iter().map(|m| format!("milestone:{m}")));
    labels.extend(f.component.iter().map(|c| format!("component:{c}")));
    Ok(CreateData {
        title: f.title.clone(),
        ty,
        category: Category::Todo,
        priority,
        flavour,
        points,
        parent,
        assignee: None,
        persona: None,
        capability: None,
        outcome_text: None,
        idempotency_key: None,
        aliases: vec![f.id.clone()],
        labels,
        scope: f.scope.clone(),
        acceptance: f.acceptance.iter().map(|a| a.text.clone()).collect(),
        body: v1.body.clone(),
        links,
    })
}

/// Convert one v1 ticket into rendered v2 text.
fn convert(
    v1: &V1Ticket,
    id: TicketId,
    ids: &BTreeMap<String, TicketId>,
    report: &mut ImportReport,
) -> Result<Rendered, ImportError> {
    let f = &v1.front;
    let mut clock = Clock::new(&f.id, day_start(&f.id, &f.created)?, ticket_number(&f.id)?);
    let actor = f.origin.as_deref().unwrap_or(IMPORT_ACTOR);
    let (category, outcome) = map_state(f)?;
    let mut events = vec![event_text(
        &mut clock,
        actor,
        EventBody::Create(Box::new(create_data(v1, ids, report)?)),
    )?];
    events.extend(evidence_events(v1, &mut clock, report)?);
    let dropped_reason = (f.state == "dropped")
        .then(|| drop_reason(&v1.body))
        .flatten();
    if let Some(reason) = &dropped_reason {
        let body = CommentData {
            subtype: CommentSubtype::Note,
            body: format!("v1 drop reason: {reason}"),
        };
        events.push(event_text(
            &mut clock,
            IMPORT_ACTOR,
            EventBody::Comment(body),
        )?);
    }
    if let Some(text) = &v1.done_report {
        let body = CommentData {
            subtype: CommentSubtype::Decision,
            body: format!("# v1 done-report\n\n{}", text.trim()),
        };
        events.push(event_text(
            &mut clock,
            IMPORT_ACTOR,
            EventBody::Comment(body),
        )?);
    }
    if category == Category::Done {
        let data = TransitionData {
            from: Category::Todo,
            to: category,
            outcome,
            reason: Some(format!("imported from v1 state `{}`", f.state)),
        };
        events.push(event_text(
            &mut clock,
            IMPORT_ACTOR,
            EventBody::Transition(data),
        )?);
    }
    let parsed = parse_events(&events)?;
    let folded = fold(id, &parsed).map_err(|e| ticket_err(&f.id, e.to_string()))?;
    let ticket_md = doc::render(&folded.ticket).map_err(|e| ticket_err(&f.id, e.to_string()))?;
    Ok(Rendered {
        v1_id: f.id.clone(),
        id,
        ticket_md,
        events,
    })
}

fn parse_events(texts: &[(EventId, String)]) -> Result<Vec<Event>, ImportError> {
    texts
        .iter()
        .map(|(id, text)| Event::parse(*id, text).map_err(|e| ticket_err("events", e.to_string())))
        .collect()
}

/// Check ledger integrity over rendered tickets: fold equals frontmatter, links resolve, ids and aliases are unique.
///
/// Returns one message per problem; empty means clean.
pub fn verify(tickets: &[Rendered]) -> Vec<String> {
    let known: BTreeSet<TicketId> = tickets.iter().map(|t| t.id).collect();
    let mut problems = Vec::new();
    let mut aliases: BTreeMap<String, TicketId> = BTreeMap::new();
    for t in tickets {
        let label = format!("{} ({})", t.v1_id, t.id);
        let stored = match doc::parse(&label, &t.ticket_md) {
            Ok(s) => s,
            Err(e) => {
                problems.push(format!("{label}: {e}"));
                continue;
            }
        };
        if stored.front.id != t.id {
            problems.push(format!(
                "{label}: ticket.md id {} differs from its directory",
                stored.front.id
            ));
        }
        for alias in &stored.front.aliases {
            if let Some(prev) = aliases.insert(alias.clone(), t.id) {
                problems.push(format!("{label}: alias {alias} also on {prev}"));
            }
        }
        problems.extend(
            tick003(&stored.front, &|id| known.contains(&id))
                .into_iter()
                .map(|f| f.message),
        );
        match parse_events(&t.events)
            .and_then(|ev| fold(t.id, &ev).map_err(|e| ticket_err(&label, e.to_string())))
        {
            Ok(folded) => {
                if !folded.conflicts.is_empty() {
                    problems.push(format!(
                        "{label}: {} fold conflicts",
                        folded.conflicts.len()
                    ));
                }
                problems.extend(
                    tick001(t.id, &folded.ticket, &stored)
                        .into_iter()
                        .map(|f| f.message),
                );
            }
            Err(e) => problems.push(format!("{label}: {e}")),
        }
    }
    tracing::info!(
        tickets = tickets.len(),
        problems = problems.len(),
        "import verified"
    );
    problems
}

/// Read a written v2 tree back as [`Rendered`] tickets (directory name as the id).
///
/// # Errors
///
/// [`ImportError::Io`] for unreadable files, [`ImportError::Ticket`] for names that are not ULIDs.
pub fn load_tree(dir: &Path) -> Result<Vec<Rendered>, ImportError> {
    let mut out = Vec::new();
    for entry in std::fs::read_dir(dir).map_err(|e| io_err(dir, &e))? {
        let path = entry.map_err(|e| io_err(dir, &e))?.path();
        let name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        let id: TicketId = name
            .parse()
            .map_err(|_| ticket_err(&name, "directory is not a ULID"))?;
        let md = path.join("ticket.md");
        let ticket_md = std::fs::read_to_string(&md).map_err(|e| io_err(&md, &e))?;
        let mut events = Vec::new();
        let events_dir = path.join("events");
        for ev in std::fs::read_dir(&events_dir).map_err(|e| io_err(&events_dir, &e))? {
            let ev_path = ev.map_err(|e| io_err(&events_dir, &e))?.path();
            let stem = ev_path
                .file_stem()
                .map(|s| s.to_string_lossy().into_owned())
                .unwrap_or_default();
            let ev_id: EventId = stem
                .parse()
                .map_err(|_| ticket_err(&name, format!("event file {stem} is not a ULID")))?;
            events.push((
                ev_id,
                std::fs::read_to_string(&ev_path).map_err(|e| io_err(&ev_path, &e))?,
            ));
        }
        events.sort_by_key(|(id, _)| *id);
        out.push(Rendered {
            v1_id: name,
            id,
            ticket_md,
            events,
        });
    }
    out.sort_by_key(|t| t.id);
    Ok(out)
}

fn write_tree(to: &Path, tickets: &[Rendered]) -> Result<(), ImportError> {
    for t in tickets {
        let dir = to.join(t.id.to_string());
        let events = dir.join("events");
        std::fs::create_dir_all(&events).map_err(|e| io_err(&events, &e))?;
        let md = dir.join("ticket.md");
        std::fs::write(&md, &t.ticket_md).map_err(|e| io_err(&md, &e))?;
        for (id, text) in &t.events {
            let path = events.join(format!("{id}.toml"));
            std::fs::write(&path, text).map_err(|e| io_err(&path, &e))?;
        }
    }
    tracing::info!(tickets = tickets.len(), to = %to.display(), "v2 tree written");
    Ok(())
}

fn target_is_free(to: &Path) -> Result<(), ImportError> {
    match std::fs::read_dir(to) {
        Ok(it) => {
            if it.count() > 0 {
                return Err(ImportError::TargetNotEmpty(to.display().to_string()));
            }
            Ok(())
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(io_err(to, &e)),
    }
}

/// Convert the v1 ledger at `opts.from` into v2 tickets, verify them and (unless dry-run) write them.
///
/// # Errors
///
/// [`ImportError`] for unreadable or unmappable v1 tickets, a non-empty target, or a failed integrity check.
pub fn run(opts: &ImportOptions) -> Result<ImportReport, ImportError> {
    let v1s = read_v1(&opts.from)?;
    let mut ids = BTreeMap::new();
    for v in &v1s {
        let f = &v.front;
        let ulid = mint(day_start(&f.id, &f.created)?, ticket_number(&f.id)?)?;
        ids.insert(f.id.clone(), TicketId::from_ulid(ulid));
    }
    let mut report = ImportReport::default();
    let mut rendered = Vec::new();
    for v in &v1s {
        for key in &v.present {
            if DROPPED_FIELDS.iter().any(|(k, _)| k == key) {
                *report.dropped.entry(key.clone()).or_default() += 1;
            } else if !CARRIED.contains(&key.as_str()) {
                report
                    .warnings
                    .push(format!("{}: unmapped v1 key `{key}`", v.front.id));
            }
        }
        rendered.push(convert(v, ids[&v.front.id], &ids, &mut report)?);
    }
    let problems = verify(&rendered);
    if !problems.is_empty() {
        return Err(ImportError::Integrity(problems.join("\n")));
    }
    if !opts.dry_run {
        target_is_free(&opts.to)?;
        write_tree(&opts.to, &rendered)?;
        let problems = verify(&load_tree(&opts.to)?);
        if !problems.is_empty() {
            return Err(ImportError::Integrity(problems.join("\n")));
        }
    }
    summarize(&rendered, &mut report)?;
    Ok(report)
}

fn summarize(rendered: &[Rendered], report: &mut ImportReport) -> Result<(), ImportError> {
    let all: Vec<TicketId> = rendered.iter().map(|r| r.id).collect();
    let handles = compute_handles(&all, frob_ledger::id::DEFAULT_HANDLE_MIN_LEN);
    for (r, handle) in rendered.iter().zip(handles) {
        let stored =
            doc::parse(&r.v1_id, &r.ticket_md).map_err(|e| ticket_err(&r.v1_id, e.to_string()))?;
        let f = &stored.front;
        let category = f
            .outcome
            .map_or_else(|| f.category.to_string(), |o| format!("{}/{o}", f.category));
        *report.by_type.entry(f.ty.to_string()).or_default() += 1;
        *report.by_category.entry(category.clone()).or_default() += 1;
        report.events += r.events.len();
        report.rows.push(Row {
            v1: r.v1_id.clone(),
            ulid: r.id.to_string(),
            handle: format!("~{handle}"),
            ty: f.ty.to_string(),
            category,
        });
    }
    Ok(())
}

/// Render the summary table (v1 id, ulid, handle, type, category) as aligned text lines.
pub fn render_table(rows: &[Row]) -> Vec<String> {
    let mut lines = vec![format!(
        "{:<8} {:<26} {:<9} {:<10} {}",
        "v1", "ulid", "handle", "type", "category"
    )];
    lines.extend(rows.iter().map(|r| {
        format!(
            "{:<8} {:<26} {:<9} {:<10} {}",
            r.v1, r.ulid, r.handle, r.ty, r.category
        )
    }));
    lines
}

/// Render the v1 id to ULID map, one `T-0003<TAB>ulid` line per ticket.
pub fn render_id_map(rows: &[Row]) -> String {
    rows.iter().fold(String::new(), |mut out, r| {
        out.push_str(&r.v1);
        out.push('\t');
        out.push_str(&r.ulid);
        out.push('\n');
        out
    })
}

/// Render `docs/migration/v1-import.md`: the mapping rules, counts and every dropped v1 field with its reason.
///
/// The page names no ULIDs (they are random per run); resolve ids with `frob ticket show T-0003`.
pub fn render_report_md(report: &ImportReport) -> String {
    let mut out = String::from(
        "# v1 ticket import\n\n\
         Written by `cargo dev import-v1-tickets` (T-0025). Every v1 ticket became a v2 ULID \
         ticket whose `aliases` hold the v1 id, so `frob ticket show T-0003` resolves. The v1 \
         ledger itself stays in git history before the import commit.\n\n\
         ## Identity and time\n\n\
         v1 keeps only a creation date. A ticket ULID carries that date at 00:00:00 UTC plus \
         the v1 ticket number as milliseconds, so creation order is preserved and ids never \
         share a prefix. Event `i` of a ticket sits `i` seconds after the date (ULID time and \
         `at` agree). These instants are synthetic; real times are in git history.\n\n\
         ## Field mapping\n\n\
         | v1 | v2 |\n|---|---|\n\
         | `kind` feature, ux | type `task` (ux also sets flavour `ux`) |\n\
         | `kind` bug, security, docs, invariant, incident | the same type |\n\
         | `tier` epic, story | type `epic`, `story` (wins over `kind`) |\n\
         | `state` queued, planned, in-progress | category `todo` (leases do not carry over) |\n\
         | `state` done, archived | category `done`, outcome `done` |\n\
         | `state` dropped | category `done`, outcome `wont-fix`, drop reason kept as a comment event |\n\
         | `blocked_by`, `parent` | `blocked-by` links, `parent` (mapped through the id map) |\n\
         | `milestone`, `component` | labels `milestone:<v>`, `component:<v>` |\n\
         | `origin` | actor of the `create` event and reporter |\n\
         | `acceptance` | acceptance criteria with `bound = false` |\n\
         | `evidence` (`cmd:` lines) | `evidence` events, provider `command`, status measured when exit is 0 |\n\
         | `done-report.md` | `decision` comment event titled `v1 done-report` |\n\
         | body | the markdown body |\n\n",
    );
    out.push_str(&format!(
        "## Result\n\n{} tickets and {} events. By type: {}. By category: {}.\n\n",
        report.rows.len(),
        report.events,
        counts_text(&report.by_type),
        counts_text(&report.by_category),
    ));
    out.push_str("## Dropped v1 fields\n\n| v1 field | Tickets with a value | Why it is not carried |\n|---|---|---|\n");
    for (field, reason) in DROPPED_FIELDS {
        let n = report.dropped.get(*field).copied().unwrap_or(0);
        out.push_str(&format!("| `{field}` | {n} | {reason} |\n"));
    }
    out.push_str("\n## Dropped behaviour\n\n| What | Why |\n|---|---|\n");
    for (what, reason) in DROPPED_BEHAVIOUR {
        out.push_str(&format!("| {what} | {reason} |\n"));
    }
    out
}

fn counts_text(counts: &BTreeMap<String, usize>) -> String {
    counts
        .iter()
        .map(|(k, v)| format!("{k} {v}"))
        .collect::<Vec<_>>()
        .join(", ")
}

//! `milestone criterion add|remove` and `milestone evidence add|list`.
//!
//! Milestone exit criteria bind to evidence exactly as ticket acceptance does
//! (tickets.md section 9): the capture is `frob_evidence::provider::capture`
//! and the record format is `frob_evidence::events::to_data`, so providers, the
//! `allowed_tools` allowlist and measurement are identical; only the target
//! differs (a milestone's `evidence` event instead of a ticket's).

use frob_evidence::attestation::Presence;
use frob_evidence::events::{self, StoredEvidence};
use frob_evidence::verbs::{CaptureArgs, ListData, Listed, capture_args, with_record_warnings};
use frob_evidence::{EvidenceError, EvidenceRecord, Workspace};
use frob_pm::{Milestone, PmStore};
use gob_cli::clap::{Arg, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::milestone_cmd::{MilestoneData, MilestoneView, find, pm_err, version_arg};
use crate::ticket::{get, open};

/// Refuse a criterion number outside `1..=count` with the command that lists them.
fn bad_position(m: &Milestone, n: usize) -> CliError {
    tracing::info!(version = %m.version, position = n, "criterion position refused");
    Refusal::new(
        "E-MILESTONE-CRITERION",
        RefusalClass::UsageError,
        format!(
            "criterion {n} does not exist: milestone {} has {} (1-based)",
            m.version,
            m.criteria.len()
        ),
    )
    .with_remedy(format!("frob milestone show {}", m.version))
    .into()
}

/// The result of one `milestone criterion` change.
fn data(m: &Milestone, ledger: &frob_ledger::Ledger, a: Option<frob_pm::Applied>) -> MilestoneData {
    match a {
        None => MilestoneData {
            milestone: MilestoneView::of(m, ledger),
            events: Vec::new(),
            commit: None,
        },
        Some(a) => {
            let frob_pm::Object::Milestone(m) = a.object else {
                unreachable!("a milestone event folds to a milestone")
            };
            MilestoneData {
                milestone: MilestoneView::of(&m, ledger),
                events: a.events.iter().map(ToString::to_string).collect(),
                commit: Some(a.commit),
            }
        }
    }
}

/// Add an exit criterion to a milestone; an identical criterion already there returns `already`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone criterion add",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CriterionAdd {
    version: String,
    text: String,
}

impl Command for CriterionAdd {
    type Data = MilestoneData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(version_arg()).arg(
            Arg::new("criterion")
                .required(true)
                .value_name("CRITERION")
                .help("Exit criterion, taken whole; starts unbound"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            text: get(m, "criterion").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<MilestoneData> {
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let m = find(store, &self.version)?;
        let already = m.criteria.iter().any(|c| c.text == self.text);
        let applied = if already {
            None
        } else {
            Some(store.add_criterion(m.id, &self.text).map_err(pm_err)?)
        };
        tracing::info!(version = %m.version, already, "milestone criterion add");
        Ok(Payload::new(data(&m, &ledger, applied)).with_already(already))
    }
}

/// An evidence record whose exit criterion a removal took away.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct LostEvidence {
    /// The evidence event id.
    pub event: String,
    /// The provider that measured it.
    pub provider: String,
    /// What was measured (the record's `ref`).
    pub reference: String,
    /// `[attested by X: "statement"]` (escaped) when the lost record was an attestation.
    pub label: Option<String>,
    /// The removed criterion it was offered for, numbered as before this removal.
    pub lost: Vec<usize>,
    /// Its criteria that survive, numbered as after this removal.
    pub kept: Vec<usize>,
}

/// Output of `milestone criterion remove`: the milestone plus the evidence that lost its criterion.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CriterionRemoveData {
    /// The milestone after the removal, with the events and commit.
    #[serde(flatten)]
    pub change: MilestoneData,
    /// Evidence that was offered for the removed criterion and now binds nothing there.
    pub lost_evidence: Vec<LostEvidence>,
}

/// Remove the exit criterion at a 1-based position; evidence for later criteria follows its criterion.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone criterion remove",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct CriterionRemove {
    version: String,
    position: usize,
}

impl Command for CriterionRemove {
    type Data = CriterionRemoveData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(version_arg()).arg(
            Arg::new("position")
                .required(true)
                .value_name("N")
                .value_parser(gob_cli::clap::value_parser!(usize))
                .help("1-based position of the criterion, from `milestone show`"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            position: m
                .get_one::<usize>("position")
                .copied()
                .ok_or_else(|| CliError::Usage("criterion remove needs N".to_owned()))?,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<CriterionRemoveData> {
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let m = find(store, &self.version)?;
        if self.position == 0 || self.position > m.criteria.len() {
            return Err(bad_position(&m, self.position));
        }
        let lost = lost_evidence(store, &m, self.position)?;
        let a = store
            .remove_criterion(m.id, self.position)
            .map_err(pm_err)?;
        tracing::info!(version = %m.version, position = self.position, lost = lost.len(), "milestone criterion remove");
        let note = (!lost.is_empty()).then(|| {
            let each: Vec<String> = lost
                .iter()
                .map(|l| {
                    format!(
                        "{} ({} {}) lost criteria {:?}",
                        l.event,
                        l.provider,
                        l.label.as_deref().unwrap_or(&l.reference),
                        l.lost
                    )
                })
                .collect();
            format!(
                "evidence lost its exit criterion: {}; re-offer it with a new `milestone evidence add --accepts N`",
                each.join("; ")
            )
        });
        let out = Payload::new(CriterionRemoveData {
            change: data(&m, &ledger, Some(a)),
            lost_evidence: lost,
        });
        Ok(note.into_iter().fold(out, Payload::with_warning))
    }
}

/// The evidence of `m` that criterion `position` carries, as the report of a removal.
fn lost_evidence(
    store: PmStore<'_>,
    m: &Milestone,
    position: usize,
) -> Result<Vec<LostEvidence>, CliError> {
    let lost = store.lost_evidence(m.id, position).map_err(pm_err)?;
    let records: std::collections::BTreeMap<String, EvidenceRecord> = store
        .evidence_events(m.id)
        .map_err(pm_err)?
        .into_iter()
        .filter_map(|(ev, d)| {
            let id = ev.id.to_string();
            events::record_from_data(&id, &d).ok().map(|r| (id, r))
        })
        .collect();
    Ok(lost
        .into_iter()
        .map(|l| {
            let event = l.event.to_string();
            LostEvidence {
                label: records
                    .get(&event)
                    .and_then(EvidenceRecord::attestation_label),
                event,
                provider: l.provider,
                reference: l.reference,
                lost: l.lost,
                kept: l.kept,
            }
        })
        .collect())
}

/// Output of `milestone evidence add`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EvidenceAddData {
    /// The milestone after the evidence was appended, with each criterion's bound state.
    pub milestone: MilestoneView,
    /// The new event's id.
    pub event: String,
    /// The ledger commit holding it.
    pub commit: String,
    /// The record that was written.
    pub record: EvidenceRecord,
}

/// Capture evidence with a provider and offer it for milestone exit criteria.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone evidence add",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct EvidenceAdd {
    version: String,
    args: CaptureArgs,
}

fn ev_err(e: impl Into<EvidenceError>) -> CliError {
    e.into().into_cli()
}

impl Command for EvidenceAdd {
    type Data = EvidenceAddData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        capture_args(cmd.arg(version_arg()))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            args: CaptureArgs::from_matches(m)?,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<EvidenceAddData> {
        let ws = Workspace::open(&ctx.cwd, ctx.clock.clone()).map_err(EvidenceError::into_cli)?;
        add_evidence(&ws, &self.version, &self.args, &Presence::detect())
    }
}

/// Capture evidence for milestone `version` and append it; an attestation needs `presence` to show a person.
///
/// # Errors
///
/// A refusal for an unknown version, a bad `--accepts`, a failed attestation check or a ledger failure; nothing is written then.
pub fn add_evidence(
    ws: &Workspace,
    version: &str,
    args: &CaptureArgs,
    presence: &Presence,
) -> Outcome<EvidenceAddData> {
    let store = PmStore::new(&ws.ledger);
    let m = find(store, version)?;
    if let Some(bad) = args
        .accepts
        .iter()
        .find(|n| **n == 0 || **n > m.criteria.len())
    {
        return Err(ev_err(EvidenceError::BadAccepts(format!(
            "--accepts {bad} but milestone {} has {} exit criteria (1-based)",
            m.version,
            m.criteria.len()
        ))));
    }
    let record = args.capture(ws, presence).map_err(ev_err)?;
    let applied = store
        .add_evidence(m.id, events::to_data(&record).map_err(ev_err)?)
        .map_err(pm_err)?;
    let event = applied
        .events
        .first()
        .map(ToString::to_string)
        .ok_or_else(|| {
            CliError::internal(EvidenceError::Malformed(
                "the evidence event was not written".to_owned(),
            ))
        })?;
    let frob_pm::Object::Milestone(after) = applied.object else {
        unreachable!("a milestone event folds to a milestone")
    };
    tracing::info!(version = %after.version, %event, provider = record.provider.as_str(), "milestone evidence add");
    let payload = Payload::new(EvidenceAddData {
        milestone: MilestoneView::of(&after, &ws.ledger),
        event,
        commit: applied.commit,
        record: record.clone(),
    });
    Ok(with_record_warnings(payload, &record))
}

/// List the evidence records of a milestone with their effective status.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone evidence list",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct EvidenceList {
    version: String,
}

impl Command for EvidenceList {
    type Data = ListData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(version_arg())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ListData> {
        let ws = Workspace::open(&ctx.cwd, ctx.clock.clone()).map_err(EvidenceError::into_cli)?;
        let store = PmStore::new(&ws.ledger);
        let m = find(store, &self.version)?;
        let mut records = Vec::new();
        for (i, (ev, d)) in store
            .evidence_events(m.id)
            .map_err(pm_err)?
            .into_iter()
            .enumerate()
        {
            let record = events::record_from_data(&ev.id.to_string(), &d).map_err(ev_err)?;
            records.push(Listed {
                index: i + 1,
                effective_status: record.effective_status(&ws.store),
                label: record.attestation_label(),
                stored: StoredEvidence {
                    event: ev.id.to_string(),
                    at: ev.at.to_string(),
                    actor: ev.actor,
                    record,
                },
            });
        }
        Ok(Payload::new(ListData {
            count: records.len(),
            records,
        }))
    }
}

/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<CriterionAdd>()
        .register::<CriterionRemove>()
        .register::<EvidenceAdd>()
        .register::<EvidenceList>()
}

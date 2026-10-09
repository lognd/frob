//! The `milestone` verbs: `new`, `add`, `show`, `list` over `frob-pm`.
//!
//! A milestone's alias is its version (semver). `new` and `add` are idempotent:
//! an identical repeat returns `already: true`; a conflicting `new` is refused
//! with the command that shows what exists. Membership lives on the milestone,
//! never on the ticket (releases.md section 6a).

use frob_ledger::Ledger;
use frob_ledger::model::{Stamp, TicketType};
use frob_pm::milestone::{MilestoneError, NewPlan, parse_version, plan_new, unknown_version};
use frob_pm::model::{Day, Milestone};
use frob_pm::{NewObject, ObjectKind, PmError, PmStore};
use gob_cli::clap::{Arg, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::ticket::{cli_err, get, get_many, many_flag, open, resolve, text_flag};

/// A member epic as listed under a milestone.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EpicRef {
    /// Full ULID of the epic.
    pub id: String,
    /// Handle with `~`, when the ticket is readable.
    pub handle: Option<String>,
    /// Title, when the ticket is readable.
    pub title: Option<String>,
}

/// One exit criterion with its 1-based position.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CriterionView {
    /// 1-based position (the number evidence `--accepts` uses).
    pub position: usize,
    /// The criterion text.
    pub text: String,
    /// True when passing evidence is bound to it.
    pub bound: bool,
    /// `bound` or `unbound`, spelled for display.
    pub state: String,
    /// True when any binding record is a person's attestation rather than a tool measurement.
    pub attested: bool,
    /// The passing evidence records that bind it (empty when unbound).
    pub bound_by: Vec<BoundBy>,
}

/// One passing evidence record binding a criterion.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BoundBy {
    /// The evidence event id.
    pub event: String,
    /// The provider that measured it.
    pub provider: String,
    /// What was measured (the record's `ref`).
    pub reference: String,
    /// `[attested by X: "statement"]` (escaped, origin ledger) when a person attested; absent for a tool measurement.
    pub label: Option<String>,
    /// The attestation exactly as stored (JSON keeps exact strings; text renders use `label`).
    pub attestation: Option<frob_evidence::record::Attestation>,
}

/// A milestone as every `milestone` verb reports it.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MilestoneView {
    /// Full ULID.
    pub id: String,
    /// Handle with `~`.
    pub handle: String,
    /// The version, also the alias.
    pub version: String,
    /// One-line goal.
    pub goal: String,
    /// Target date (`YYYY-MM-DD`), absent when unscheduled.
    pub target: Option<String>,
    /// State: open, released or dropped.
    pub state: String,
    /// Member epics.
    pub epics: Vec<EpicRef>,
    /// Exit criteria in order.
    pub criteria: Vec<CriterionView>,
    /// Creation time.
    pub created: Stamp,
    /// Time of the latest event.
    pub updated: Stamp,
}

impl MilestoneView {
    /// View `m`, looking each member epic up in `ledger` for its handle and title.
    pub(crate) fn of(m: &Milestone, ledger: &Ledger) -> Self {
        let epics = m
            .epics
            .iter()
            .map(|id| match ledger.show(*id) {
                Ok(v) => EpicRef {
                    id: id.to_string(),
                    handle: Some(v.summary.handle),
                    title: Some(v.summary.title),
                },
                Err(e) => {
                    tracing::warn!(epic = %id, error = %e, "member epic unreadable");
                    EpicRef {
                        id: id.to_string(),
                        handle: None,
                        title: None,
                    }
                }
            })
            .collect();
        let mut bindings = PmStore::new(ledger)
            .criterion_bindings(m.id, m.criteria.len())
            .unwrap_or_else(|e| {
                tracing::warn!(milestone = %m.id, error = %e, "criterion bindings unreadable");
                vec![Vec::new(); m.criteria.len()]
            });
        let attestations = attestations_of(ledger, m);
        Self {
            id: m.id.to_string(),
            handle: m.id.handle(),
            version: m.version.clone(),
            goal: m.goal.clone(),
            target: m.target.map(|d| d.to_string()),
            state: m.state.to_string(),
            epics,
            criteria: m
                .criteria
                .iter()
                .enumerate()
                .map(|(i, c)| CriterionView {
                    position: i + 1,
                    text: c.text.clone(),
                    bound: c.bound,
                    state: if c.bound { "bound" } else { "unbound" }.to_owned(),
                    attested: bindings[i]
                        .iter()
                        .any(|b| attestations.contains_key(&b.event.to_string())),
                    bound_by: std::mem::take(&mut bindings[i])
                        .into_iter()
                        .map(|b| {
                            let attestation = attestations.get(&b.event.to_string()).cloned();
                            BoundBy {
                                event: b.event.to_string(),
                                provider: b.provider,
                                reference: b.reference,
                                label: attestation
                                    .as_ref()
                                    .map(frob_evidence::record::Attestation::label),
                                attestation,
                            }
                        })
                        .collect(),
                })
                .collect(),
            created: m.created,
            updated: m.updated,
        }
    }
}

/// The attestations among the evidence events of milestone `m`, by event id.
fn attestations_of(
    ledger: &Ledger,
    m: &Milestone,
) -> std::collections::BTreeMap<String, frob_evidence::record::Attestation> {
    let events = PmStore::new(ledger)
        .evidence_events(m.id)
        .unwrap_or_else(|e| {
            tracing::warn!(milestone = %m.id, error = %e, "evidence events unreadable");
            Vec::new()
        });
    events
        .into_iter()
        .filter_map(|(ev, data)| {
            let id = ev.id.to_string();
            match frob_evidence::events::record_from_data(&id, &data) {
                Ok(r) => r.attestation.map(|a| (id, a)),
                Err(e) => {
                    tracing::warn!(event = %id, error = %e, "evidence record unreadable");
                    None
                }
            }
        })
        .collect()
}

/// Output of `milestone new`, `add` and `show`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MilestoneData {
    /// The milestone after the verb ran.
    pub milestone: MilestoneView,
    /// Ids of the events written (empty when `already` or read-only).
    pub events: Vec<String>,
    /// The ledger commit, when one was made.
    pub commit: Option<String>,
}

/// Output of `milestone list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MilestoneListData {
    /// Number of milestones.
    pub count: usize,
    /// The milestones, oldest first.
    pub milestones: Vec<MilestoneView>,
}

/// Map a milestone rule failure to its refusal, with the command that fixes it.
fn refusal(e: &MilestoneError) -> CliError {
    use RefusalClass::{GuardNeedsAction, UsageError};
    let r = match e {
        MilestoneError::BadVersion { .. } => {
            Refusal::new("E-MILESTONE-VERSION", UsageError, e.to_string()).with_remedy(
                "use MAJOR.MINOR.PATCH, for example `frob milestone new 0.533.0 --goal <text>`",
            )
        }
        MilestoneError::Conflict { version, .. } => {
            Refusal::new("E-MILESTONE-EXISTS", GuardNeedsAction, e.to_string())
                .with_remedy(format!("frob milestone show {version}"))
        }
        MilestoneError::UnknownVersion { suggestions, .. } => {
            let msg = match suggestions.as_slice() {
                [] => e.to_string(),
                s => format!("{e}; did you mean {}?", s.join(", ")),
            };
            let remedy = match suggestions.first() {
                Some(s) => format!("frob milestone show {s}"),
                None => "frob milestone list".to_owned(),
            };
            Refusal::new("E-MILESTONE-NOT-FOUND", GuardNeedsAction, msg).with_remedy(remedy)
        }
    };
    r.into()
}

/// Map a `frob-pm` failure to the CLI error: a refusal when the caller can fix it, else internal.
pub(crate) fn pm_err(e: PmError) -> CliError {
    use RefusalClass::{GuardNeedsAction, UsageError};
    match e {
        PmError::Ledger(l) => cli_err(l),
        PmError::Invalid(m) => Refusal::new("E-MILESTONE-INPUT", UsageError, m).into(),
        PmError::NotFound { .. } | PmError::Ambiguous { .. } => {
            Refusal::new("E-MILESTONE-NOT-FOUND", GuardNeedsAction, e.to_string())
                .with_remedy("frob milestone list")
                .into()
        }
        other => CliError::internal(other),
    }
}

/// Every milestone folded at the current tip.
pub(crate) fn milestones(store: PmStore<'_>) -> Result<Vec<Milestone>, CliError> {
    Ok(store
        .list(ObjectKind::Milestone)
        .map_err(pm_err)?
        .into_iter()
        .filter_map(|o| match o {
            frob_pm::Object::Milestone(m) => Some(m),
            frob_pm::Object::Cycle(_) => None,
        })
        .collect())
}

/// Resolve `reference` (version, `~handle` or ULID) to a milestone, suggesting versions when none match.
pub(crate) fn find(store: PmStore<'_>, reference: &str) -> Result<Milestone, CliError> {
    match store.resolve(ObjectKind::Milestone, reference) {
        Ok(frob_pm::Object::Milestone(m)) => Ok(m),
        Ok(frob_pm::Object::Cycle(_)) => unreachable!("resolve of a milestone returns a milestone"),
        Err(PmError::NotFound { .. }) => {
            tracing::info!(reference, "unknown milestone");
            Err(refusal(&unknown_version(&milestones(store)?, reference)))
        }
        Err(e) => Err(pm_err(e)),
    }
}

/// The positional `VERSION` argument.
pub(crate) fn version_arg() -> Arg {
    Arg::new("version")
        .required(true)
        .value_name("VERSION")
        .help("Milestone version (semver, for example 0.533.0)")
}

/// Create a milestone; an identical repeat returns `already`, a different one is refused.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone new",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct MilestoneNew {
    version: String,
    goal: String,
    target: Option<String>,
    criteria: Vec<String>,
}

impl Command for MilestoneNew {
    type Data = MilestoneData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(version_arg())
            .arg(text_flag("goal", "One-line goal of the release").required(true))
            .arg(text_flag(
                "target",
                "Target date, YYYY-MM-DD (default unscheduled)",
            ))
            .arg(many_flag(
                "criterion",
                "Exit criterion, taken whole (repeatable); starts unbound",
            ))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            goal: get(m, "goal").unwrap_or_default(),
            target: get(m, "target"),
            criteria: get_many(m, "criterion"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<MilestoneData> {
        let version = parse_version(&self.version).map_err(|e| refusal(&e))?;
        let target = self
            .target
            .as_deref()
            .map(str::parse::<Day>)
            .transpose()
            .map_err(|e| CliError::Usage(format!("--target: {e}")))?;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let plan = plan_new(
            &milestones(store)?,
            &version,
            &self.goal,
            target,
            &self.criteria,
        )
        .map_err(|e| refusal(&e))?;
        let (m, events, commit, already) = match plan {
            NewPlan::Already(m) => (*m, Vec::new(), None, true),
            NewPlan::Create => {
                let a = store
                    .create(NewObject::Milestone {
                        version,
                        goal: self.goal.clone(),
                        target,
                        criteria: self.criteria.clone(),
                    })
                    .map_err(pm_err)?;
                let frob_pm::Object::Milestone(m) = a.object else {
                    unreachable!("a created milestone folds to a milestone")
                };
                let events = a.events.iter().map(ToString::to_string).collect();
                (m, events, Some(a.commit), false)
            }
        };
        tracing::info!(version = %m.version, already, "milestone new");
        Ok(Payload::new(MilestoneData {
            milestone: MilestoneView::of(&m, &ledger),
            events,
            commit,
        })
        .with_already(already))
    }
}

/// Add an epic to a milestone; a repeat returns `already`, a non-epic is refused.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone add",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct MilestoneAdd {
    epic: String,
    version: String,
}

impl Command for MilestoneAdd {
    type Data = MilestoneData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("epic")
                .required(true)
                .value_name("EPIC")
                .help("Full ULID, ~handle or alias of the epic ticket"),
        )
        .arg(version_arg())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            epic: get(m, "epic").unwrap_or_default(),
            version: get(m, "version").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<MilestoneData> {
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let m = find(store, &self.version)?;
        let id = resolve(&ledger, &self.epic)?;
        let view = ledger.show(id).map_err(cli_err)?;
        if view.summary.ty != TicketType::Epic {
            let remedy = match view.summary.parent {
                Some(p) => format!("frob milestone add {p} {}", m.version),
                None => "frob ticket list --type epic".to_owned(),
            };
            tracing::info!(ticket = %id, ty = %view.summary.ty, "milestone add refused: not an epic");
            return Err(Refusal::new(
                "E-MILESTONE-NOT-EPIC",
                RefusalClass::GuardNeedsAction,
                format!(
                    "{} is a {}, and only epics can be milestone members",
                    view.summary.handle, view.summary.ty
                ),
            )
            .with_remedy(remedy)
            .into());
        }
        let applied = store
            .set_member(ObjectKind::Milestone, m.id, id, frob_pm::event::Op::Add)
            .map_err(pm_err)?;
        let (m, events, commit, already) = match applied {
            None => (m, Vec::new(), None, true),
            Some(a) => {
                let frob_pm::Object::Milestone(m) = a.object else {
                    unreachable!("a milestone event folds to a milestone")
                };
                let events = a.events.iter().map(ToString::to_string).collect();
                (m, events, Some(a.commit), false)
            }
        };
        tracing::info!(version = %m.version, epic = %id, already, "milestone add");
        Ok(Payload::new(MilestoneData {
            milestone: MilestoneView::of(&m, &ledger),
            events,
            commit,
        })
        .with_already(already))
    }
}

/// Show one milestone with its member epics and exit criteria.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone show",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct MilestoneShow {
    version: String,
}

impl Command for MilestoneShow {
    type Data = MilestoneData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(version_arg())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<MilestoneData> {
        let ledger = open(ctx)?;
        let m = find(PmStore::new(&ledger), &self.version)?;
        Ok(Payload::new(MilestoneData {
            milestone: MilestoneView::of(&m, &ledger),
            events: Vec::new(),
            commit: None,
        }))
    }
}

/// List every milestone, oldest first.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "milestone list",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct MilestoneList;

impl Command for MilestoneList {
    type Data = MilestoneListData;

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<MilestoneListData> {
        let ledger = open(ctx)?;
        let ms = milestones(PmStore::new(&ledger))?;
        let milestones: Vec<MilestoneView> =
            ms.iter().map(|m| MilestoneView::of(m, &ledger)).collect();
        Ok(Payload::new(MilestoneListData {
            count: milestones.len(),
            milestones,
        }))
    }
}

/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    crate::milestone_evidence_cmd::register(cli)
        .register::<MilestoneNew>()
        .register::<MilestoneAdd>()
        .register::<MilestoneShow>()
        .register::<MilestoneList>()
}

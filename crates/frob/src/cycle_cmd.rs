//! The `cycle` verbs: `new`, `show`, `list`, `close`, `assign`, `unassign`, `plan`, `velocity` over `frob-pm`.
//!
//! A cycle's alias is its dates (`START..END`). `new` and `close` are
//! idempotent: an identical repeat returns `already: true`. Incomplete members
//! carry to the next cycle with `cycle` events (op `carried`) and the
//! commitment ratio is recorded at close (pm-enforcement.md section 4).
//! `assign` refuses past capacity unless `--over-commit --reason`, and moves a
//! ticket out of the open or planned cycle that held it. `plan` proposes a
//! fill of ready work (`--apply` assigns through the same path as `assign`).

// frob:ticket 01M4069RPPQE1ES1914K6V6Y0D
// frob:ticket 01M4069SHBAEWRX9WWCSS2FEHN
// frob:ticket 01M40VQWCV38B2JCABYNNNA877
// frob:ticket 01M4069SYRHMYXCFAZH0AN408B
// frob:ticket 01M4069T2V69X32EP8NZQHJH6H
use std::collections::BTreeMap;

use frob_ledger::Ledger;
use frob_ledger::TicketId;
use frob_ledger::model::Stamp;
use frob_pm::cycle::assign::{AssignError, AssignPlan, TicketFacts, default_cycle, plan_assign};
use frob_pm::cycle::history::{cycle_events, deliveries, done_points, member_status};
use frob_pm::cycle::lifecycle::{
    ClosePlan, CycleError, MemberFacts, NewPlan, plan_close, plan_new, plan_next, ratio,
    resolve_end, unknown_cycle, with_state,
};
use frob_pm::cycle::plan::{Candidate, PlanError, milestone_members, next_milestone, plan_fill};
use frob_pm::cycle::velocity::{
    Capacity, Delivery, ROLLING_CYCLES, capacity, committed, delivered, done_facts,
    history_capacity, recent_closed, velocity,
};
use frob_pm::event::{CycleEventData, CycleOp, MemberData, Op, PmBody, TransitionData};
use frob_pm::model::{Cycle, Day, State};
use frob_pm::{NewObject, ObjectKind, PmError, PmStore};
use gob_cli::clap::{Arg, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::milestone_cmd::pm_err;
use crate::ticket::{cli_err, get, open, open_lease_store, resolve, text_flag, ticket_arg};
use crate::workspace::{Located, config_refusal};

/// A member ticket as listed under a cycle.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TicketRef {
    /// Full ULID of the ticket.
    pub id: String,
    /// Handle with `~`, when the ticket is readable.
    pub handle: Option<String>,
    /// Title, when the ticket is readable.
    pub title: Option<String>,
    /// Workflow category, when readable.
    pub category: Option<String>,
    /// Story points, when estimated.
    pub points: Option<u8>,
}

/// One carried-over ticket as recorded by a `cycle` event.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CarriedView {
    /// Full ULID of the ticket that moved on.
    pub ticket: String,
    /// The cycle it moved to (ULID).
    pub to: String,
}

/// The commitment-versus-done record written at close.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RatioView {
    /// Story points committed (members' points at close).
    pub committed: u32,
    /// Story points done.
    pub done: u32,
    /// `done / committed`, absent when nothing was committed.
    pub ratio: Option<f64>,
}

/// An assignment past capacity that `--over-commit` allowed, as recorded on the cycle.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct OverCommitView {
    /// Full ULID of the ticket assigned.
    pub ticket: Option<String>,
    /// Committed points after the assignment.
    pub committed: Option<u32>,
    /// The capacity that was exceeded.
    pub capacity: Option<u32>,
    /// Why the over-commit was accepted.
    pub reason: String,
}

/// A cycle as every `cycle` verb reports it.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CycleView {
    /// Full ULID.
    pub id: String,
    /// Handle with `~`.
    pub handle: String,
    /// The `START..END` alias.
    pub alias: String,
    /// First day (`YYYY-MM-DD`).
    pub start: String,
    /// Last planned day (`YYYY-MM-DD`).
    pub end: String,
    /// Effective last day when the cycle closed before its planned end; absent otherwise.
    pub ended: Option<String>,
    /// One-line goal.
    pub goal: String,
    /// Committed story points, when set.
    pub capacity_points: Option<u32>,
    /// State: planned, active or closed.
    pub state: String,
    /// Member tickets (after a close: the ones that stayed).
    pub tickets: Vec<TicketRef>,
    /// Tickets carried out at close.
    pub carried: Vec<CarriedView>,
    /// The commitment ratio recorded at close.
    pub commitment: Option<RatioView>,
    /// The retro note recorded at close.
    pub retro: Option<String>,
    /// Assignments accepted past capacity, with their reasons.
    pub over_commits: Vec<OverCommitView>,
    /// Creation time.
    pub created: Stamp,
    /// Time of the latest event.
    pub updated: Stamp,
}

impl CycleView {
    /// View `c`, reading its member tickets from `ledger` and its review events from `store`.
    fn of(c: &Cycle, store: PmStore<'_>) -> Self {
        let ledger = store.ledger();
        let tickets = c
            .tickets
            .iter()
            .map(|id| match ledger.show(*id) {
                Ok(v) => TicketRef {
                    id: id.to_string(),
                    handle: Some(v.summary.handle),
                    title: Some(v.summary.title),
                    category: Some(v.summary.category.to_string()),
                    points: v.summary.points,
                },
                Err(e) => {
                    tracing::warn!(ticket = %id, error = %e, "member ticket unreadable");
                    TicketRef {
                        id: id.to_string(),
                        handle: None,
                        title: None,
                        category: None,
                        points: None,
                    }
                }
            })
            .collect();
        let events = cycle_events(store, c);
        let mut carried = Vec::new();
        let mut commitment = None;
        let mut retro = None;
        let mut over_commits = Vec::new();
        for d in events {
            match d.op {
                CycleOp::Carried => {
                    if let (Some(t), Some(to)) = (d.ticket, d.to) {
                        carried.push(CarriedView {
                            ticket: t.to_string(),
                            to: to.to_string(),
                        });
                    }
                }
                CycleOp::Ratio => {
                    if let (Some(committed), Some(done)) = (d.committed, d.done) {
                        commitment = Some(RatioView {
                            committed,
                            done,
                            ratio: ratio(committed, done),
                        });
                    }
                }
                CycleOp::Retro => retro = d.text,
                CycleOp::OverCommit => over_commits.push(OverCommitView {
                    ticket: d.ticket.map(|t| t.to_string()),
                    committed: d.committed,
                    capacity: d.capacity,
                    reason: d.text.unwrap_or_default(),
                }),
                CycleOp::Other => {}
            }
        }
        Self {
            id: c.id.to_string(),
            handle: c.id.handle(),
            alias: c.alias(),
            start: c.start.to_string(),
            end: c.end.to_string(),
            ended: c.ended.map(|d| d.to_string()),
            goal: c.goal.clone(),
            capacity_points: c.capacity_points,
            state: c.state.to_string(),
            tickets,
            carried,
            commitment,
            retro,
            over_commits,
            created: c.created,
            updated: c.updated,
        }
    }
}

/// Output of `cycle new`, `show` and `close`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CycleData {
    /// The cycle after the verb ran.
    pub cycle: CycleView,
    /// The next cycle `cycle close --next-goal` created for the carried tickets; absent otherwise.
    pub next: Option<CycleView>,
    /// Ids of the events written (empty when `already` or read-only).
    pub events: Vec<String>,
    /// The ledger commit, when one was made.
    pub commit: Option<String>,
}

/// Output of `cycle list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CycleListData {
    /// Number of cycles.
    pub count: usize,
    /// The cycles, earliest start first.
    pub cycles: Vec<CycleView>,
}

/// Map a cycle rule failure to its refusal, with the command that fixes it.
fn refusal(e: &CycleError) -> CliError {
    use RefusalClass::{GuardNeedsAction, UsageError};
    let r = match e {
        CycleError::BadWindow { .. } => {
            Refusal::new("E-CYCLE-WINDOW", UsageError, e.to_string())
                .with_remedy("pass --start and an --end on or after it, for example `frob cycle new --start 2026-10-05 --end 2026-10-11 --goal <text>`")
        }
        CycleError::Overlap { with, next_free, .. } => {
            Refusal::new("E-CYCLE-OVERLAP", GuardNeedsAction, e.to_string()).with_remedy(format!(
                "start after it (`frob cycle new --start {next_free} --goal <text>`) or inspect it with `frob cycle show {with}`"
            ))
        }
        CycleError::Conflict { alias, .. } => {
            Refusal::new("E-CYCLE-EXISTS", GuardNeedsAction, e.to_string())
                .with_remedy(format!("frob cycle show {alias}"))
        }
        CycleError::Unknown { suggestions, .. } => {
            let msg = match suggestions.as_slice() {
                [] => e.to_string(),
                s => format!("{e}; did you mean {}?", s.join(", ")),
            };
            let remedy = match suggestions.first() {
                Some(s) => format!("frob cycle show {s}"),
                None => "frob cycle list".to_owned(),
            };
            Refusal::new("E-CYCLE-NOT-FOUND", GuardNeedsAction, msg).with_remedy(remedy)
        }
        CycleError::LiveLease { handles, .. } => {
            Refusal::new("E-CYCLE-LEASE", GuardNeedsAction, e.to_string()).with_remedy(format!(
                // frob:ticket 01M40YQZF4422S88TN6992AN0Q
                "finish and land {}, or release it with `frob requeue <ticket> --reason <why>`, then close again",
                handles.join(", ")
            ))
        }
        CycleError::NoNextCycle { suggest_start, .. } => {
            Refusal::new("E-CYCLE-NO-NEXT", GuardNeedsAction, e.to_string()).with_remedy(format!(
                "close and create the next cycle in one step with `--next-goal <text>` (optionally `--next-days N`), create it first (`frob cycle new --start {suggest_start} --goal <text>`), or pass `--carry-to CYCLE`"
            ))
        }
        CycleError::BadCarryTarget { .. } => {
            Refusal::new("E-CYCLE-CARRY-TARGET", GuardNeedsAction, e.to_string())
                .with_remedy("frob cycle list")
        }
    };
    r.into()
}

/// Map an assignment failure to its refusal, with the command that fixes it.
fn assign_refusal(e: &AssignError, cycle: &str) -> CliError {
    use RefusalClass::GuardNeedsAction;
    let r = match e {
        AssignError::NoDefaultCycle { .. } => {
            Refusal::new("E-CYCLE-NONE", GuardNeedsAction, e.to_string())
                .with_remedy("create one (`frob cycle new --start YYYY-MM-DD --goal <text>`) or name a cycle")
        }
        AssignError::Closed { .. } => Refusal::new("E-CYCLE-CLOSED", GuardNeedsAction, e.to_string())
            .with_remedy("frob cycle list"),
        AssignError::NotAssignable { handle, .. } => {
            Refusal::new("E-CYCLE-NOT-ASSIGNABLE", GuardNeedsAction, e.to_string())
                .with_remedy(format!("assign one of its children (`frob ticket list --parent {handle}`)"))
        }
        AssignError::NoPoints { handle } => {
            Refusal::new("E-CYCLE-NO-POINTS", GuardNeedsAction, e.to_string())
                .with_remedy(format!("frob ticket update {handle} --points N"))
        }
        AssignError::OverCapacity { handle, .. } => {
            Refusal::new("E-CYCLE-OVER-CAPACITY", GuardNeedsAction, e.to_string()).with_remedy(format!(
                "assign it to a later cycle (`frob cycle list`), or accept the over-commit: `frob cycle assign {handle} {cycle} --over-commit --reason <why>`"
            ))
        }
    };
    r.into()
}

/// Map a `frob-pm` failure for a cycle verb: not-found and invalid input name cycle remedies.
fn cycle_pm_err(e: PmError) -> CliError {
    match e {
        PmError::Invalid(m) => Refusal::new("E-CYCLE-INPUT", RefusalClass::UsageError, m).into(),
        PmError::NotFound { .. } | PmError::Ambiguous { .. } => Refusal::new(
            "E-CYCLE-NOT-FOUND",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy("frob cycle list")
        .into(),
        other => pm_err(other),
    }
}

/// Every cycle folded at the current tip with its state derived for today, earliest start first.
fn cycles(store: PmStore<'_>) -> Result<Vec<Cycle>, CliError> {
    // frob:ticket 01M413V82EXMRXXVWZN0MQNY3G
    let today = store.today();
    let mut out: Vec<Cycle> = store
        .list(ObjectKind::Cycle)
        .map_err(cycle_pm_err)?
        .into_iter()
        .filter_map(|o| match o {
            frob_pm::Object::Cycle(c) => Some(with_state(c, today)),
            frob_pm::Object::Milestone(_) => None,
        })
        .collect();
    out.sort_by_key(|c| (c.start, c.end));
    Ok(out)
}

/// Resolve `reference` (ULID, `~handle` or `START..END`) to a cycle, suggesting aliases when none match.
fn find(store: PmStore<'_>, reference: &str) -> Result<Cycle, CliError> {
    match store.resolve(ObjectKind::Cycle, reference) {
        Ok(frob_pm::Object::Cycle(c)) => Ok(with_state(c, store.today())),
        Ok(frob_pm::Object::Milestone(_)) => unreachable!("resolve of a cycle returns a cycle"),
        Err(PmError::NotFound { .. }) => {
            tracing::info!(reference, "unknown cycle");
            Err(refusal(&unknown_cycle(&cycles(store)?, reference)))
        }
        Err(e) => Err(cycle_pm_err(e)),
    }
}

/// The cycle `show` picks without an argument: the open one holding `today`, else the next to start, else the latest.
fn current(all: &[Cycle], today: Day) -> Option<&Cycle> {
    let open = || all.iter().filter(|c| c.state != State::Closed);
    open()
        .find(|c| c.start <= today && today <= c.effective_end())
        .or_else(|| open().find(|c| c.start > today))
        .or_else(|| all.last())
}

/// The `[pm] cycle_days` setting of the repository containing `ctx.cwd`.
fn cycle_days(ctx: &Context) -> Result<u32, CliError> {
    let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
    Ok(cfg.pm.pm.cycle_days)
}

/// Parse a `YYYY-MM-DD` flag value.
fn parse_day(flag: &str, text: &str) -> Result<Day, CliError> {
    text.parse::<Day>()
        .map_err(|e| CliError::Usage(format!("--{flag}: {e}")))
}

/// The positional `CYCLE` argument.
fn cycle_arg(required: bool) -> Arg {
    Arg::new("cycle")
        .required(required)
        .value_name("CYCLE")
        .help("Cycle ULID, ~handle or START..END alias")
}

/// Create a cycle; an identical repeat returns `already`, an overlapping or different one is refused.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle new",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleNew {
    start: String,
    end: Option<String>,
    goal: String,
    capacity: Option<String>,
}

impl Command for CycleNew {
    type Data = CycleData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(text_flag("start", "First day, YYYY-MM-DD").required(true))
            .arg(text_flag(
                "end",
                "Last day, YYYY-MM-DD (default start + [pm] cycle_days - 1)",
            ))
            .arg(text_flag("goal", "One-line goal of the cycle").required(true))
            .arg(
                text_flag(
                    "capacity",
                    "Story points the team commits to (default unset, derived from history)",
                )
                .value_name("N")
                .visible_alias("capacity-points"),
            )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            start: get(m, "start").unwrap_or_default(),
            end: get(m, "end"),
            goal: get(m, "goal").unwrap_or_default(),
            capacity: get(m, "capacity"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<CycleData> {
        let start = parse_day("start", &self.start)?;
        let end = self
            .end
            .as_deref()
            .map(|e| parse_day("end", e))
            .transpose()?;
        let capacity_points = self
            .capacity
            .as_deref()
            .map(str::parse::<u32>)
            .transpose()
            .map_err(|e| CliError::Usage(format!("--capacity: {e}")))?;
        let end = resolve_end(start, end, cycle_days(ctx)?).map_err(|e| refusal(&e))?;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let plan = plan_new(&cycles(store)?, start, end, &self.goal, capacity_points)
            .map_err(|e| refusal(&e))?;
        let (c, events, commit, already) = match plan {
            NewPlan::Already(c) => (*c, Vec::new(), None, true),
            NewPlan::Create => {
                let a = store
                    .create(NewObject::Cycle {
                        start,
                        end,
                        goal: self.goal.clone(),
                        capacity_points,
                    })
                    .map_err(cycle_pm_err)?;
                let frob_pm::Object::Cycle(c) = a.object else {
                    unreachable!("a created cycle folds to a cycle")
                };
                let events = a.events.iter().map(ToString::to_string).collect();
                (c, events, Some(a.commit), false)
            }
        };
        let c = with_state(c, ctx.clock.today());
        tracing::info!(cycle = %c.alias(), already, "cycle new");
        Ok(Payload::new(CycleData {
            cycle: CycleView::of(&c, store),
            next: None,
            events,
            commit,
        })
        .with_already(already))
    }
}

/// Show one cycle (default: the current one) with its members, carried work, ratio and retro.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle show",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleShow {
    cycle: Option<String>,
}

impl Command for CycleShow {
    type Data = CycleData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(cycle_arg(false))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            cycle: get(m, "cycle"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<CycleData> {
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let c = if let Some(r) = &self.cycle {
            find(store, r)?
        } else {
            let all = cycles(store)?;
            current(&all, ctx.clock.today()).cloned().ok_or_else(|| {
                CliError::from(
                    Refusal::new(
                        "E-CYCLE-NONE",
                        RefusalClass::GuardNeedsAction,
                        "there are no cycles yet",
                    )
                    .with_remedy("frob cycle new --start YYYY-MM-DD --goal <text>"),
                )
            })?
        };
        Ok(Payload::new(CycleData {
            cycle: CycleView::of(&c, store),
            next: None,
            events: Vec::new(),
            commit: None,
        }))
    }
}

/// List every cycle, earliest start first.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle list",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleList;

impl Command for CycleList {
    type Data = CycleListData;

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<CycleListData> {
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let views: Vec<CycleView> = cycles(store)?
            .iter()
            .map(|c| CycleView::of(c, store))
            .collect();
        Ok(Payload::new(CycleListData {
            count: views.len(),
            cycles: views,
        }))
    }
}

/// What the close rules need to know about each member of `c`, read from the ledger and the lease store.
fn member_facts(ctx: &Context, ledger: &Ledger, c: &Cycle) -> Result<Vec<MemberFacts>, CliError> {
    let (leases, _) = open_lease_store(ctx)?;
    c.tickets
        .iter()
        .map(|id| member_fact(ledger, &leases, *id))
        .collect()
}

/// The close-rule facts of one ticket.
fn member_fact(
    ledger: &Ledger,
    leases: &frob_lease::LeaseStore,
    id: TicketId,
) -> Result<MemberFacts, CliError> {
    let s = ledger.show(id).map_err(cli_err)?.summary;
    let status = member_status(s.category, s.outcome);
    Ok(MemberFacts {
        id,
        handle: s.handle,
        status,
        live_lease: leases.live_lease(id)?.is_some(),
        points: u32::from(s.points.unwrap_or(0)),
    })
}

/// The events a close writes on the closing cycle: carried, ratio, retro, then the transition.
fn close_bodies(c: &Cycle, plan: &ClosePlan, retro: Option<&str>) -> Vec<PmBody> {
    let event = |d: CycleEventData| PmBody::Cycle(Box::new(d));
    let blank = |op| CycleEventData {
        op,
        ticket: None,
        to: None,
        committed: None,
        done: None,
        text: None,
        capacity: None,
    };
    let mut bodies: Vec<PmBody> = plan
        .carried
        .iter()
        .map(|t| {
            event(CycleEventData {
                ticket: Some(*t),
                to: plan.target,
                ..blank(CycleOp::Carried)
            })
        })
        .collect();
    bodies.push(event(CycleEventData {
        committed: Some(plan.committed),
        done: Some(plan.done),
        ..blank(CycleOp::Ratio)
    }));
    if let Some(text) = retro {
        bodies.push(event(CycleEventData {
            text: Some(text.to_owned()),
            ..blank(CycleOp::Retro)
        }));
    }
    bodies.push(PmBody::Transition(TransitionData {
        from: c.state,
        to: State::Closed,
        reason: None,
        ended: plan.ended,
    }));
    bodies
}

/// Create the cycle that follows `c` closing on `closed_on`, or return the identical one already there.
fn create_next(
    ctx: &Context,
    store: PmStore<'_>,
    c: &Cycle,
    others: &[Cycle],
    closed_on: Day,
    goal: &str,
    days: Option<u32>,
) -> Result<Cycle, CliError> {
    let days = match days {
        Some(d) => d,
        None => cycle_days(ctx)?,
    };
    let np = plan_next(c, others, closed_on, goal, days).map_err(|e| refusal(&e))?;
    match np.plan {
        NewPlan::Already(m) => Ok(*m),
        NewPlan::Create => {
            let a = store
                .create(NewObject::Cycle {
                    start: np.start,
                    end: np.end,
                    goal: goal.to_owned(),
                    capacity_points: None,
                })
                .map_err(cycle_pm_err)?;
            let frob_pm::Object::Cycle(m) = a.object else {
                unreachable!("a created cycle folds to a cycle")
            };
            Ok(with_state(m, ctx.clock.today()))
        }
    }
}

/// Close a cycle: carry incomplete work to the next, record the ratio and retro; refused while live work is in progress.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle close",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleClose {
    cycle: String,
    retro: Option<String>,
    carry_to: Option<String>,
    next_goal: Option<String>,
    next_days: Option<String>,
}

impl Command for CycleClose {
    type Data = CycleData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(cycle_arg(true))
            .arg(text_flag(
                "retro",
                "Retrospective note recorded with the close, taken whole",
            ))
            .arg(
                text_flag(
                    "carry-to",
                    "Cycle that takes the incomplete tickets (default: the next open or planned cycle by start date)",
                )
                .value_name("CYCLE"),
            )
            .arg(text_flag(
                "next-goal",
                "Goal of the next cycle, created the day after the effective end (also when nothing carries) unless one already follows",
            ))
            .arg(
                text_flag(
                    "next-days",
                    "Length of the cycle --next-goal creates (default [pm] cycle_days)",
                )
                .value_name("N"),
            )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            cycle: get(m, "cycle").unwrap_or_default(),
            retro: get(m, "retro"),
            carry_to: get(m, "carry-to"),
            next_goal: get(m, "next-goal"),
            next_days: get(m, "next-days"),
        })
    }

    // Write order (every step is safe to repeat, so a failed close is retried with the same arguments):
    //   1. create the next cycle (a retry finds it as the next open or planned cycle and skips this),
    //   2. add each carried ticket to it (adding an existing member writes nothing),
    //   3. one commit on the closing cycle: carried, ratio, retro and the close transition.
    // Until step 3 lands the cycle stays open, so a failure between steps never loses or double-counts work.
    fn run(&self, ctx: &Context) -> Outcome<CycleData> {
        if self.next_days.is_some() && self.next_goal.is_none() {
            return Err(CliError::Usage(
                "--next-days only applies with --next-goal".to_owned(),
            ));
        }
        let next_days = self
            .next_days
            .as_deref()
            .map(str::parse::<u32>)
            .transpose()
            .map_err(|e| CliError::Usage(format!("--next-days: {e}")))?;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let c = find(store, &self.cycle)?;
        if c.state == State::Closed {
            tracing::info!(cycle = %c.alias(), "cycle close: already closed");
            return Ok(Payload::new(CycleData {
                cycle: CycleView::of(&c, store),
                next: None,
                events: Vec::new(),
                commit: None,
            })
            .with_already(true));
        }
        let carry_to = self
            .carry_to
            .as_deref()
            .map(|r| find(store, r))
            .transpose()?;
        let others = cycles(store)?;
        let members = member_facts(ctx, &ledger, &c)?;
        let closed_on = ctx.clock.today();
        let mut next: Option<Cycle> = None;
        let mut planned = plan_close(&c, &others, carry_to.as_ref(), &members, closed_on);
        // frob:ticket 01M4CT13C64KEVBP74G6VCQP1Q
        // A given --next-goal is honoured when unfinished work needs a cycle and none exists, and also when
        // nothing carries: the flags are never silently dropped.
        let wants_next = match &planned {
            Err(CycleError::NoNextCycle { .. }) => true,
            Ok(p) => p.carried.is_empty() && carry_to.is_none(),
            Err(_) => false,
        };
        if let (true, Some(goal)) = (wants_next, self.next_goal.as_deref()) {
            let made = create_next(ctx, store, &c, &others, closed_on, goal, next_days)?;
            tracing::info!(cycle = %c.alias(), next = %made.alias(), "cycle close created the next cycle");
            let mut all = others.clone();
            all.push(made.clone());
            planned = plan_close(&c, &all, None, &members, closed_on);
            next = Some(made);
        }
        let plan = planned.map_err(|e| refusal(&e))?;
        if let Some(target) = plan.target {
            for t in &plan.carried {
                store
                    .set_member(ObjectKind::Cycle, target, *t, frob_pm::event::Op::Add)
                    .map_err(cycle_pm_err)?;
            }
        }
        let applied = store
            .append_many(
                ObjectKind::Cycle,
                c.id,
                close_bodies(&c, &plan, self.retro.as_deref()),
            )
            .map_err(cycle_pm_err)?;
        let frob_pm::Object::Cycle(closed) = applied.object else {
            unreachable!("a cycle event folds to a cycle")
        };
        tracing::info!(
            cycle = %closed.alias(),
            carried = plan.carried.len(),
            committed = plan.committed,
            done = plan.done,
            ended = ?plan.ended,
            target = ?plan.target_alias,
            "cycle closed"
        );
        let next = next
            .map(|n| find(store, &n.id.to_string()))
            .transpose()?
            .map(|n| CycleView::of(&n, store));
        Ok(Payload::new(CycleData {
            cycle: CycleView::of(&closed, store),
            next,
            events: applied.events.iter().map(ToString::to_string).collect(),
            commit: Some(applied.commit),
        }))
    }
}

/// The `(type, points)` of every member of `c`; unreadable members are logged and skipped.
fn member_points(ledger: &Ledger, c: &Cycle) -> Vec<(frob_ledger::model::TicketType, u32)> {
    c.tickets
        .iter()
        .filter_map(|id| match ledger.show(*id) {
            Ok(v) => Some((v.summary.ty, u32::from(v.summary.points.unwrap_or(0)))),
            Err(e) => {
                tracing::warn!(ticket = %id, error = %e, "member ticket unreadable; not counted");
                None
            }
        })
        .collect()
}

/// Output of `cycle assign` and `unassign`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AssignData {
    /// The cycle after the verb ran.
    pub cycle: CycleView,
    /// Handle of the ticket.
    pub ticket: String,
    /// Alias of the cycle the ticket left (assign moved it).
    pub moved_from: Option<String>,
    /// Committed story points of the cycle after the verb (velocity-counting tickets only).
    pub committed: u32,
    /// The capacity statement, for example `capacity not enforced yet: 1 of 3 cycles of history`.
    pub capacity: String,
    /// The enforced limit in points, absent when not enforced.
    pub capacity_limit: Option<u32>,
    /// True when the assignment went past capacity and an over-commit event was recorded.
    pub over_committed: bool,
    /// Ids of the events written (empty when `already`).
    pub events: Vec<String>,
    /// The ledger commit, when one was made.
    pub commit: Option<String>,
}

/// The trimmed `--reason` when `--over-commit` is set; usage errors for a missing reason or a reason alone.
fn over_commit_reason(over_commit: bool, reason: Option<&str>) -> Result<Option<String>, CliError> {
    match (over_commit, reason.map(str::trim)) {
        (true, Some(r)) if !r.is_empty() => Ok(Some(r.to_owned())),
        (true, _) => Err(CliError::Usage(
            "--over-commit needs --reason TEXT saying why the cycle may exceed capacity".to_owned(),
        )),
        (false, Some(_)) => Err(CliError::Usage(
            "--reason is only used with --over-commit".to_owned(),
        )),
        (false, None) => Ok(None),
    }
}

/// The events an assign writes: the membership and, when over-committing, the `(committed, capacity, reason)` record.
fn assign_bodies(ticket: TicketId, over: Option<(u32, Option<u32>, Option<&str>)>) -> Vec<PmBody> {
    let mut bodies = vec![PmBody::Member(MemberData {
        op: Op::Add,
        ticket,
    })];
    if let Some((committed, capacity, reason)) = over {
        bodies.push(PmBody::Cycle(Box::new(CycleEventData {
            op: CycleOp::OverCommit,
            ticket: Some(ticket),
            to: None,
            committed: Some(committed),
            done: None,
            text: reason.map(str::to_owned),
            capacity,
        })));
    }
    bodies
}

/// What one assignment did, as [`assign_one`] reports it to `cycle assign` and `cycle plan --apply`.
struct Assigned {
    cycle: Cycle,
    moved_from: Option<String>,
    committed: u32,
    over_committed: bool,
    events: Vec<String>,
    commit: Option<String>,
    already: bool,
}

/// Assign `facts` to `target` under `cap`: the one path `cycle assign` and `cycle plan --apply` share.
///
/// Capacity refusal, the move out of another cycle and the over-commit record all live here.
#[allow(clippy::too_many_arguments)]
fn assign_one(
    store: PmStore<'_>,
    ledger: &Ledger,
    target: &Cycle,
    all: &[Cycle],
    cap: &Capacity,
    facts: &TicketFacts,
    over_commit: bool,
    reason: Option<&str>,
) -> Result<Assigned, CliError> {
    let id = facts.id;
    let members = member_points(ledger, target);
    let plan = plan_assign(target, all, facts, &members, cap.clone(), over_commit)
        .map_err(|e| assign_refusal(&e, &target.alias()))?;
    match plan {
        AssignPlan::Already => Ok(Assigned {
            cycle: target.clone(),
            moved_from: None,
            committed: committed(&members),
            over_committed: false,
            events: Vec::new(),
            commit: None,
            already: true,
        }),
        AssignPlan::Add {
            moved_from,
            committed,
            capacity: _,
            over_commit,
        } => {
            if let Some((old, _)) = &moved_from {
                store
                    .set_member(ObjectKind::Cycle, *old, id, Op::Remove)
                    .map_err(cycle_pm_err)?;
            }
            let bodies = assign_bodies(id, over_commit.then_some((committed, cap.limit(), reason)));
            let applied = store
                .append_many(ObjectKind::Cycle, target.id, bodies)
                .map_err(cycle_pm_err)?;
            let frob_pm::Object::Cycle(c) = applied.object else {
                unreachable!("a cycle event folds to a cycle")
            };
            Ok(Assigned {
                cycle: c,
                moved_from: moved_from.map(|(_, a)| a),
                committed,
                over_committed: over_commit,
                events: applied.events.iter().map(ToString::to_string).collect(),
                commit: Some(applied.commit),
                already: false,
            })
        }
    }
}

/// Assign a ticket to a cycle (default: the open one containing today, else the next planned); refused past capacity unless over-committed.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle assign",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleAssign {
    ticket: String,
    cycle: Option<String>,
    over_commit: bool,
    reason: Option<String>,
}

impl Command for CycleAssign {
    type Data = AssignData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(ticket_arg())
            .arg(cycle_arg(false))
            .arg(
                Arg::new("over-commit")
                    .long("over-commit")
                    .action(gob_cli::clap::ArgAction::SetTrue)
                    .help("Allow the assignment past capacity; needs --reason"),
            )
            .arg(text_flag(
                "reason",
                "Why the cycle is over-committed, recorded as a cycle event (with --over-commit)",
            ))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            cycle: get(m, "cycle"),
            over_commit: m.get_flag("over-commit"),
            reason: get(m, "reason"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AssignData> {
        let reason = over_commit_reason(self.over_commit, self.reason.as_deref())?;
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let all = cycles(store)?;
        let target = match &self.cycle {
            Some(r) => find(store, r)?,
            None => default_cycle(&all, ctx.clock.today())
                .map_err(|e| assign_refusal(&e, "CYCLE"))?
                .clone(),
        };
        let id = resolve(&ledger, &self.ticket)?;
        let s = ledger.show(id).map_err(cli_err)?.summary;
        let facts = TicketFacts {
            id,
            handle: s.handle.clone(),
            ty: s.ty,
            points: s.points.map(u32::from),
        };
        let done = done_points(&deliveries(store, &ledger, &all));
        let cap = capacity(
            &target,
            &all,
            &done,
            cfg.pm.pm.min_history,
            cfg.pm.pm.capacity_k,
        );
        let a = assign_one(
            store,
            &ledger,
            &target,
            &all,
            &cap,
            &facts,
            self.over_commit,
            reason.as_deref(),
        )?;
        let (c, moved_from, committed_after, over, events, commit, already) = (
            a.cycle,
            a.moved_from,
            a.committed,
            a.over_committed,
            a.events,
            a.commit,
            a.already,
        );
        tracing::info!(
            cycle = %c.alias(), ticket = %facts.handle, already, over_committed = over,
            moved_from = ?moved_from, committed = committed_after, capacity = %cap.describe(),
            "cycle assign"
        );
        Ok(Payload::new(AssignData {
            cycle: CycleView::of(&c, store),
            ticket: facts.handle,
            moved_from,
            committed: committed_after,
            capacity: cap.describe(),
            capacity_limit: cap.limit(),
            over_committed: over,
            events,
            commit,
        })
        .with_already(already))
    }
}

/// Take a ticket out of a cycle; idempotent when it was not a member.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle unassign",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleUnassign {
    ticket: String,
    cycle: String,
}

impl Command for CycleUnassign {
    type Data = AssignData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(ticket_arg()).arg(cycle_arg(true))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: get(m, "ticket").unwrap_or_default(),
            cycle: get(m, "cycle").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AssignData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let target = find(store, &self.cycle)?;
        let id = resolve(&ledger, &self.ticket)?;
        let handle = ledger.show(id).map_err(cli_err)?.summary.handle;
        if target.state == State::Closed && target.tickets.contains(&id) {
            return Err(assign_refusal(
                &AssignError::Closed {
                    alias: target.alias(),
                },
                &target.alias(),
            ));
        }
        let applied = store
            .set_member(ObjectKind::Cycle, target.id, id, Op::Remove)
            .map_err(cycle_pm_err)?;
        let (c, events, commit, already) = match applied {
            None => (target, Vec::new(), None, true),
            Some(a) => {
                let frob_pm::Object::Cycle(c) = a.object else {
                    unreachable!("a cycle event folds to a cycle")
                };
                let events = a.events.iter().map(ToString::to_string).collect();
                (c, events, Some(a.commit), false)
            }
        };
        let all = cycles(store)?;
        let cap = capacity(
            &c,
            &all,
            &done_points(&deliveries(store, &ledger, &all)),
            cfg.pm.pm.min_history,
            cfg.pm.pm.capacity_k,
        );
        let committed = committed(&member_points(&ledger, &c));
        tracing::info!(cycle = %c.alias(), ticket = %handle, already, "cycle unassign");
        Ok(Payload::new(AssignData {
            cycle: CycleView::of(&c, store),
            ticket: handle,
            moved_from: None,
            committed,
            capacity: cap.describe(),
            capacity_limit: cap.limit(),
            over_committed: false,
            events,
            commit,
        })
        .with_already(already))
    }
}

/// One closed cycle in `cycle velocity`: its window, commitment and delivery.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct VelocityCycleView {
    /// The `START..END` alias.
    pub alias: String,
    /// First day (`YYYY-MM-DD`).
    pub start: String,
    /// Effective last day: the close day when closed early, else the planned end.
    pub end: String,
    /// Story points committed when the cycle closed; absent for cycles closed before commitments were recorded.
    pub committed: Option<u32>,
    /// Points done among the tickets committed to the cycle, as `cycle close` recorded them; carried work counts where it finished.
    pub done: u32,
    /// `done / committed`, absent when nothing was committed.
    pub ratio: Option<f64>,
    /// Points of tickets done inside the window that were not committed to the cycle; never part of the ratio, mean or capacity.
    pub unplanned_done: u32,
    /// Assignments accepted past capacity during the cycle, with their reasons.
    pub over_commits: Vec<OverCommitView>,
}

/// Output of `cycle velocity`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct VelocityData {
    /// How many cycles were asked for (`--last`).
    pub last: usize,
    /// Closed cycles shown, oldest first.
    pub cycles: Vec<VelocityCycleView>,
    /// Mean done points over the shown cycles; 0 with none.
    pub mean: f64,
    /// Population standard deviation of done points over the shown cycles.
    pub stddev: f64,
    /// Closed cycles that exist (the history sample count).
    pub samples: u32,
    /// `[pm] min_history`: closed cycles needed before capacity is enforced.
    pub min_history: u32,
    /// The capacity statement a cycle without `capacity_points` gets from `cycle assign`.
    pub capacity: String,
    /// The enforced limit in points, absent while history is too short.
    pub capacity_limit: Option<u32>,
    /// A hint when there is nothing to show; absent otherwise.
    pub message: Option<String>,
}

/// Show points delivered per closed cycle, the rolling mean and standard deviation, and the capacity `cycle assign` would use.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle velocity",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CycleVelocity {
    last: Option<String>,
}

impl Command for CycleVelocity {
    type Data = VelocityData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            text_flag(
                "last",
                "Closed cycles to show (default max(6, [pm] min_history))",
            )
            .value_name("N"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            last: get(m, "last"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<VelocityData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let min_history = cfg.pm.pm.min_history;
        let last = match self.last.as_deref().map(str::parse::<usize>).transpose() {
            Ok(Some(0)) => {
                return Err(CliError::Usage("--last must be at least 1".to_owned()));
            }
            Ok(n) => n.unwrap_or_else(|| ROLLING_CYCLES.max(min_history as usize)),
            Err(e) => return Err(CliError::Usage(format!("--last: {e}"))),
        };
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let all = cycles(store)?;
        let facts = done_facts(&ledger).map_err(cycle_pm_err)?;
        let deliv = deliveries(store, &ledger, &all);
        let done_map = done_points(&deliv);
        let shown: Vec<VelocityCycleView> = recent_closed(&all, last)
            .into_iter()
            .map(|c| {
                let view = CycleView::of(c, store);
                let d = deliv.get(&c.id).copied().unwrap_or(Delivery {
                    committed: None,
                    done: 0,
                });
                VelocityCycleView {
                    alias: view.alias,
                    start: view.start,
                    end: c.effective_end().to_string(),
                    committed: d.committed,
                    done: d.done,
                    ratio: d.committed.and_then(|k| ratio(k, d.done)),
                    unplanned_done: delivered(c, &facts).saturating_sub(d.done),
                    over_commits: view.over_commits,
                }
            })
            .collect();
        let v = velocity(&all, &done_map, last);
        let cap = history_capacity(&all, &done_map, min_history, cfg.pm.pm.capacity_k);
        let samples = u32::try_from(all.iter().filter(|c| c.state == State::Closed).count())
            .unwrap_or(u32::MAX);
        let message = shown.is_empty().then(|| {
            "no closed cycles yet: velocity is measured once a cycle closes (`frob cycle close CYCLE`)"
                .to_owned()
        });
        tracing::info!(
            shown = shown.len(), last, samples, mean = v.mean, stddev = v.stddev,
            capacity = %cap.describe(), "cycle velocity"
        );
        Ok(Payload::new(VelocityData {
            last,
            cycles: shown,
            mean: v.mean,
            stddev: v.stddev,
            samples,
            min_history,
            capacity: cap.describe(),
            capacity_limit: cap.limit(),
            message,
        }))
    }
}

/// One ticket `cycle plan` assigns, or assigned.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PlanPickView {
    /// Handle of the ticket.
    pub ticket: String,
    /// Its title.
    pub title: String,
    /// Points it adds to the commitment.
    pub points: u32,
    /// Committed points of the cycle after this ticket.
    pub running: u32,
    /// Why it ranks here: class of service and next-milestone preference.
    pub why: String,
}

/// A ready ticket `cycle plan` does not assign, with the reason.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PlanLeftOutView {
    /// Handle of the ticket.
    pub ticket: String,
    /// Why it was left out.
    pub reason: String,
}

/// Output of `cycle plan`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PlanData {
    /// Alias of the planned cycle.
    pub cycle: String,
    /// The next milestone the plan preferred, when one is open.
    pub milestone: Option<String>,
    /// The capacity statement the plan filled to.
    pub capacity: String,
    /// The limit in points.
    pub capacity_limit: Option<u32>,
    /// Committed points before the plan.
    pub committed_before: u32,
    /// Committed points after the plan (or after `--apply`).
    pub committed_after: u32,
    /// True when the picks were assigned (`--apply`); false for a proposal.
    pub applied: bool,
    /// Tickets to assign (or assigned), in rank order.
    pub picks: Vec<PlanPickView>,
    /// Ready tickets already in the cycle.
    pub already_in_cycle: Vec<String>,
    /// Ready tickets not assigned, with reasons.
    pub left_out: Vec<PlanLeftOutView>,
    /// The ledger commit of the last assignment, when `--apply` wrote any.
    pub commit: Option<String>,
}

/// The ready tickets `cycle plan` chooses from, in `doable` rank order, with what the verb needs to show and assign them.
struct Ready {
    /// Version of the next milestone, when one is open.
    milestone: Option<String>,
    ranked: Vec<Candidate>,
    facts: BTreeMap<TicketId, TicketFacts>,
    titles: BTreeMap<TicketId, String>,
}

/// Read the doable tickets (the one definition of ready) and mark those of the next milestone.
fn ready_candidates(ctx: &Context, ledger: &Ledger) -> Result<Ready, CliError> {
    let (lease_store, _) = open_lease_store(ctx)?;
    let guard = frob_lease::LeaseGuard::new(lease_store).map_err(CliError::internal)?;
    let doable = ledger.doable(&guard).map_err(cli_err)?;
    let milestones = frob_pm::rules::membership::milestones(ledger).map_err(cycle_pm_err)?;
    let next = next_milestone(&milestones);
    let in_next = match next {
        Some(m) => milestone_members(
            m,
            &frob_pm::rules::membership::claimants(ledger).map_err(cycle_pm_err)?,
        ),
        None => std::collections::BTreeSet::new(),
    };
    let mut facts = BTreeMap::new();
    let mut titles = BTreeMap::new();
    let ranked = doable
        .iter()
        .map(|s| {
            let f = TicketFacts {
                id: s.id,
                handle: s.handle.clone(),
                ty: s.ty,
                points: s.points.map(u32::from),
            };
            facts.insert(s.id, f.clone());
            titles.insert(s.id, s.title.clone());
            Candidate {
                facts: f,
                class: s.class,
                next_milestone: in_next.contains(&s.id),
            }
        })
        .collect();
    Ok(Ready {
        milestone: next.map(|m| m.version.clone()),
        ranked,
        facts,
        titles,
    })
}

/// Propose filling a cycle from ready work in rank order, preferring the next milestone, never past capacity; `--apply` assigns.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "cycle plan",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct CyclePlan {
    cycle: Option<String>,
    apply: bool,
    points: Option<String>,
}

impl Command for CyclePlan {
    type Data = PlanData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(cycle_arg(false))
            .arg(
                Arg::new("apply")
                    .long("apply")
                    .action(gob_cli::clap::ArgAction::SetTrue)
                    .help("Assign the proposed tickets (idempotent); without it nothing is written"),
            )
            .arg(text_flag(
                "points",
                "Fill to this many points instead of the cycle's capacity (needed while capacity is not enforced)",
            ))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            cycle: get(m, "cycle"),
            apply: m.get_flag("apply"),
            points: get(m, "points"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<PlanData> {
        let points = self
            .points
            .as_deref()
            .map(|p| {
                p.parse::<u32>()
                    .map_err(|e| CliError::Usage(format!("--points: {e}")))
            })
            .transpose()?;
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let all = cycles(store)?;
        let target = match &self.cycle {
            Some(r) => find(store, r)?,
            None => default_cycle(&all, ctx.clock.today())
                .map_err(|e| assign_refusal(&e, "CYCLE"))?
                .clone(),
        };
        let done = done_points(&deliveries(store, &ledger, &all));
        let cap = points.map_or_else(
            || {
                capacity(
                    &target,
                    &all,
                    &done,
                    cfg.pm.pm.min_history,
                    cfg.pm.pm.capacity_k,
                )
            },
            Capacity::Set,
        );
        let ready = ready_candidates(ctx, &ledger)?;
        let (next, ranked, facts, titles) =
            (ready.milestone, ready.ranked, ready.facts, ready.titles);
        let members = member_points(&ledger, &target);
        let plan =
            plan_fill(&target, &all, ranked, &members, &cap).map_err(|e| plan_refusal(&e))?;
        let mut commit = None;
        let mut committed_after = plan.committed;
        if self.apply {
            let mut at = target.clone();
            for p in &plan.picks {
                let a = assign_one(store, &ledger, &at, &all, &cap, &facts[&p.id], false, None)?;
                committed_after = a.committed;
                commit = a.commit.or(commit);
                at = a.cycle;
            }
        } else if let Some(last) = plan.picks.last() {
            committed_after = last.running;
        }
        tracing::info!(
            cycle = %target.alias(), apply = self.apply, picks = plan.picks.len(),
            left_out = plan.left_out.len(), committed_after, capacity = %cap.describe(),
            "cycle plan"
        );
        let nothing = plan.picks.is_empty();
        Ok(Payload::new(PlanData {
            cycle: target.alias(),
            milestone: next,
            capacity: cap.describe(),
            capacity_limit: cap.limit(),
            committed_before: plan.committed,
            committed_after,
            applied: self.apply,
            picks: plan
                .picks
                .iter()
                .map(|p| PlanPickView {
                    ticket: p.handle.clone(),
                    title: titles.get(&p.id).cloned().unwrap_or_default(),
                    points: p.points,
                    running: p.running,
                    why: p.why.clone(),
                })
                .collect(),
            already_in_cycle: plan.already,
            left_out: plan
                .left_out
                .into_iter()
                .map(|l| PlanLeftOutView {
                    ticket: l.handle,
                    reason: l.reason,
                })
                .collect(),
            commit,
        })
        .with_already(self.apply && nothing))
    }
}

/// Map a plan failure to its refusal, with the command that fixes it.
fn plan_refusal(e: &PlanError) -> CliError {
    match e {
        PlanError::Assign(a) => assign_refusal(a, "CYCLE"),
        PlanError::NoCapacity { .. } => Refusal::new(
            "E-CYCLE-NO-CAPACITY",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy("frob cycle plan --points N")
        .into(),
    }
}

/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<CycleNew>()
        .register::<CycleShow>()
        .register::<CycleList>()
        .register::<CycleClose>()
        .register::<CycleAssign>()
        .register::<CycleUnassign>()
        .register::<CyclePlan>()
        .register::<CycleVelocity>()
}

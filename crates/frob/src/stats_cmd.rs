//! The `stats` verb: velocity, capacity, points remaining, throughput, cycle and lead times and cost per point.
//!
//! Gathers the cycle history and per-ticket facts from the fold, hands them to the pure
//! functions in `frob-metrics`, and renders one [`StatsReport`] as text and JSON alike.
//! `cycle velocity` stays as a hidden alias of `stats --section velocity`.

// frob:ticket 01M48Q2AQXY69YKK3D2DC05ZWR

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::TicketId;
use frob_ledger::event::EventBody;
use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Outcome};
use frob_metrics::{
    Section, StatsInput, StatsReport, TicketFact, TicketState, compute, render_text,
};
use frob_pm::PmStore;
use frob_pm::cycle::history::{deliveries, done_points};
use frob_pm::cycle::velocity::{ROLLING_CYCLES, counts};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};

use crate::config::FrobConfig;
use crate::cycle_cmd::cycles;
use crate::milestone_cmd::milestones;
use crate::ticket::open;
use crate::workspace::{Located, config_refusal};

/// Trailing window, in days, that throughput is measured over.
const THROUGHPUT_WINDOW_DAYS: u32 = 28;

/// `stats` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct StatsArgs {
    #[arg(
        long,
        value_name = "NAME",
        value_delimiter = ',',
        help = "Sections to show: velocity, remaining, throughput, times, cost (default all)"
    )]
    section: Vec<String>,
}

/// Show velocity, capacity, points remaining, throughput, cycle and lead times and cost per point; a figure with too little history is Unresolved with its sample count.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "stats",
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, usage, refused, internal)
)]
pub struct Stats {
    sections: Vec<Section>,
}

impl Command for Stats {
    type Data = StatsReport;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<StatsArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<StatsArgs>(m)?;
        let sections = a
            .section
            .iter()
            .map(|s| {
                s.parse::<Section>()
                    .map_err(|e| CliError::Usage(format!("--section: {e}")))
            })
            .collect::<Result<Vec<_>, _>>()?;
        Ok(Self { sections })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<StatsReport> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let min_history = cfg.pm.pm.min_history;
        let ledger = open(ctx)?;
        let store = PmStore::new(&ledger);
        let all = cycles(store)?;
        let deliv = deliveries(store, &ledger, &all);
        let done = done_points(&deliv);
        let tickets = ticket_facts(&ledger)?;
        let ms = milestone_epics(store, &ledger)?;
        let report = compute(&StatsInput {
            sections: self.sections.clone(),
            cycles: &all,
            done: &done,
            tickets: &tickets,
            milestones: &ms,
            last: ROLLING_CYCLES.max(min_history as usize),
            min_history,
            k: cfg.pm.pm.capacity_k,
            now: ctx.clock.now().unix(),
            window_days: THROUGHPUT_WINDOW_DAYS,
        });
        tracing::info!(tickets = tickets.len(), cycles = all.len(), "stats");
        let rendered = render_text(&report);
        Ok(Payload::new(report).with_rendered(rendered))
    }
}

/// Facts about every velocity-counting ticket, with start and done times read from its events.
fn ticket_facts(ledger: &frob_ledger::Ledger) -> Result<Vec<TicketFact>, CliError> {
    let all = ledger
        .list(&ListFilter::default())
        .map_err(crate::ticket::cli_err)?;
    let handles: BTreeMap<TicketId, &str> = all.iter().map(|s| (s.id, s.handle.as_str())).collect();
    let timed: BTreeSet<TicketId> = all
        .iter()
        .filter(|s| counts(s.ty) && matches!(s.category, Category::Done | Category::InProgress))
        .map(|s| s.id)
        .collect();
    let mut events = ledger.events_many(&timed).map_err(crate::ticket::cli_err)?;
    let mut out = Vec::new();
    for s in all
        .iter()
        .filter(|s| counts(s.ty) && s.category != Category::Triage)
    {
        let evs = events.remove(&s.id).unwrap_or_default();
        let transition_to = |to: Category| {
            evs.iter().filter_map(move |e| match &e.body {
                EventBody::Transition(t) if t.to == to => Some(e.at.unix()),
                _ => None,
            })
        };
        let state = match (s.category, s.outcome) {
            (Category::Done, Some(Outcome::Fixed | Outcome::Done)) => TicketState::Finished,
            (Category::Done, _) => TicketState::Dropped,
            _ => TicketState::Open,
        };
        out.push(TicketFact {
            handle: s.handle.clone(),
            points: s.points.map(u32::from),
            state,
            parent: s
                .parent
                .and_then(|p| handles.get(&p))
                .map(|h| (*h).to_owned()),
            created: s.created.unix(),
            started: transition_to(Category::InProgress).min(),
            done_at: transition_to(Category::Done).max(),
            // frob:todo 01M59VC5Y4HWJYV4KWSM02ESM8 token spend is not recorded on tickets yet; cost reports wall-clock only.
            tokens: None,
        });
    }
    tracing::debug!(count = out.len(), "ticket facts gathered");
    Ok(out)
}

/// Each milestone version with the handles of its member epics.
fn milestone_epics(
    store: PmStore<'_>,
    ledger: &frob_ledger::Ledger,
) -> Result<Vec<(String, Vec<String>)>, CliError> {
    let all = ledger
        .list(&ListFilter::default())
        .map_err(crate::ticket::cli_err)?;
    let handles: BTreeMap<TicketId, &str> = all.iter().map(|s| (s.id, s.handle.as_str())).collect();
    Ok(milestones(store)?
        .into_iter()
        .map(|m| {
            let epics = m
                .epics
                .iter()
                .filter_map(|e| handles.get(e).map(|h| (*h).to_owned()))
                .collect();
            (m.version, epics)
        })
        .collect())
}

/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<Stats>()
}

//! `frob agent install`: register frob's own `frob agent hook` handlers in each agent's settings.
//!
//! Idempotent and conservative: only frob-marked entries are ever added or replaced, an unowned entry
//! that already calls a handler is reported as a conflict and left alone, and `--check` (or the global
//! `--dry-run`) prints the planned diff without writing. `frob agent uninstall` removes the entries.

// frob:ticket 01M4P2N1GFSA69RHJR4D41NVHV

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::agent::InstallReport;
use crate::agent::native::Action;
use crate::agent_cmd::{AgentArgs, PerAgent, Target, agent_refusal, per, targets};
use crate::pretty::PrettyExt;

/// The flags of `agent install`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct InstallArgs {
    #[command(flatten)]
    target: AgentArgs,
    #[arg(long, help = "Print the planned diff and write nothing")]
    check: bool,
}

/// Output of `agent install`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct InstallData {
    /// One entry per agent.
    pub agents: Vec<PerAgent<InstallReport>>,
    /// True when nothing was written (`--check` or `--dry-run`).
    pub dry_run: bool,
    /// Handlers left alone because an unowned entry already calls them.
    pub conflicts: usize,
}

/// Register the native `frob agent hook` handlers in each selected agent's settings, touching only frob-owned entries.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "agent install",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct AgentInstall {
    agent: String,
    home: Option<std::path::PathBuf>,
    check: bool,
}

impl Command for AgentInstall {
    type Data = InstallData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<InstallArgs>(cmd)
    }

    // frob:accept DUP004 because="clap glue: parse args and copy the shared target fields, shape-identical across agent verbs"
    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<InstallArgs>(m)?;
        Ok(Self {
            agent: a.target.agent,
            home: a.target.home,
            check: a.check,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<InstallData> {
        let dry_run = ctx.dry_run || self.check;
        let mut agents = Vec::new();
        for t in &targets(&self.agent, self.home.as_deref())? {
            agents.push(per(t, install_one(t, dry_run)?));
        }
        let conflicts = count(&agents, Action::Conflict);
        let already = agents.iter().all(|a| !a.report.changed);
        let rows = diff_lines(&agents);
        let mut payload = Payload::new(InstallData {
            agents,
            dry_run,
            conflicts,
        })
        .with_already(already)
        .with_pretty(rows);
        if conflicts > 0 {
            payload = payload.with_warning(format!(
                "{conflicts} handler(s) already registered by an unowned entry; left unchanged"
            ));
        }
        Ok(payload)
    }
}

/// Install (or plan) the native hooks for one target.
fn install_one(t: &Target, dry_run: bool) -> Result<InstallReport, CliError> {
    let report =
        t.em.install_native(&t.home, dry_run)
            .map_err(|e| agent_refusal(&e))?;
    tracing::info!(
        agent = t.em.id(),
        changed = report.changed,
        dry_run,
        "agent install done"
    );
    Ok(report)
}

/// How many rows across `agents` carry `action`.
fn count(agents: &[PerAgent<InstallReport>], action: Action) -> usize {
    agents
        .iter()
        .flat_map(|a| &a.report.hooks)
        .filter(|r| r.action == action)
        .count()
}

/// One `+`/`~`/`!`/`=` line per planned row, so `--check` reads as a diff.
fn diff_lines(agents: &[PerAgent<InstallReport>]) -> Vec<String> {
    let mut out = Vec::new();
    for a in agents {
        for r in &a.report.hooks {
            let sign = match r.action {
                Action::Add => '+',
                Action::Update => '~',
                Action::Conflict => '!',
                Action::Present => '=',
            };
            out.push(format!(
                "{sign} {} {} [{}] {}",
                a.agent, r.event, r.matcher, r.command
            ));
        }
    }
    out
}

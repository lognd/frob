//! `frob agent sync`, `frob agent status`, `frob agent uninstall` and `frob agent brief`.
//!
//! Thin verbs over the agent-neutral engine in [`crate::agent`]: they resolve the repository, the
//! `[agent]` manifest and the selected emitters (`--agent claude|...|all`), then report per agent. The
//! stale-source guard lives here because it needs the repository.

// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ

use gob_path::Shown;
use std::path::{Path, PathBuf};

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_git::Repo;
use schemars::JsonSchema;
use serde::Serialize;

use crate::agent::brief::{self, ActiveTicket, BriefInput};
use crate::agent::engine::{self, Planned, StatusReport, SyncReport, UninstallReport};
use crate::agent::{self, AgentError, Emitter, Manifest};
use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// The shared `--agent` and `--home` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct AgentArgs {
    #[arg(
        long,
        value_name = "AGENT",
        default_value = "all",
        help = "Agent to act on: an emitter id such as claude, or all"
    )]
    agent: String,
    #[arg(
        long,
        value_name = "DIR",
        help = "Target directory (single agent only; default: the agent's usual home)"
    )]
    home: Option<PathBuf>,
}

/// The flags of `agent sync`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct SyncArgs {
    #[command(flatten)]
    target: AgentArgs,
    #[arg(long, help = "Sync even a source file that is behind the base branch")]
    allow_stale: bool,
}

pub(crate) fn agent_refusal(e: &AgentError) -> CliError {
    tracing::error!(error = %e, "agent operation failed");
    if matches!(e, AgentError::UnknownAgent(_)) {
        return CliError::Usage(e.to_string());
    }
    Refusal::new("E-AGENT", RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy("fix the path, file or [agent] entry named above, then rerun")
        .into()
}

/// An emitter paired with the home directory it acts on.
struct Target {
    em: Box<dyn Emitter>,
    home: PathBuf,
}

/// Resolve `--agent` / `--home` into targets; `--home` needs exactly one agent.
fn targets(agent: &str, home: Option<&Path>) -> Result<Vec<Target>, CliError> {
    let picked = agent::select(agent).map_err(|e| agent_refusal(&e))?;
    if home.is_some() && picked.len() != 1 {
        return Err(CliError::Usage(
            "--home needs a single --agent (not `all`)".to_owned(),
        ));
    }
    picked
        .into_iter()
        .map(|em| {
            let home = match home {
                Some(h) => h.to_path_buf(),
                None => em.default_home().ok_or_else(|| {
                    CliError::Usage(format!(
                        "no default home for agent {}; pass --home DIR",
                        em.id()
                    ))
                })?,
            };
            Ok(Target { em, home })
        })
        .collect()
}

/// The repository, its root and its parsed, non-empty manifest.
fn setup(ctx: &Context) -> Result<(Repo, PathBuf, FrobConfig, Manifest), CliError> {
    let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
    let manifest =
        Manifest::parse(&cfg.agent.items, &cfg.agent.hooks).map_err(|e| agent_refusal(&e))?;
    if manifest.is_empty() {
        return Err(Refusal::new(
            "E-AGENT-NO-MANIFEST",
            RefusalClass::GuardNeedsAction,
            "frob.toml has no [agent] items or hooks to manage".to_owned(),
        )
        .with_remedy("add `items = [\"hook:NAME = SRC\"]` under [agent] in frob.toml")
        .into());
    }
    Ok((repo, root, cfg, manifest))
}

/// Source files whose worktree copy equals the merge-base copy while `base` holds a newer one.
fn stale_sources(repo: &Repo, root: &Path, base: &str, manifest: &Manifest) -> Vec<String> {
    if repo.rev_parse(base).is_err() {
        tracing::debug!(base, "base ref does not resolve; stale guard skipped");
        return Vec::new();
    }
    let Ok(Some(mb)) = repo.merge_base("HEAD", base) else {
        return Vec::new();
    };
    let mb = mb.to_string();
    manifest
        .items
        .iter()
        .filter(|i| {
            // autocrlf checkouts hold CRLF where the blob holds LF; compare LF forms.
            let work = std::fs::read(root.join(&i.src)).ok().map(|b| lf_only(&b));
            let at_mb = repo.read_blob_at(&mb, &i.src).ok().flatten();
            let at_base = repo.read_blob_at(base, &i.src).ok().flatten();
            work.is_some() && work == at_mb && at_base.is_some() && at_base != at_mb
        })
        .map(|i| i.src.clone())
        .collect()
}

/// The bytes with every CRLF folded to LF, so a CRLF checkout compares equal to its blob.
fn lf_only(bytes: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(bytes.len());
    for (n, b) in bytes.iter().enumerate() {
        if *b == b'\r' && bytes.get(n + 1) == Some(&b'\n') {
            continue;
        }
        out.push(*b);
    }
    out
}

fn plan(t: &Target, root: &Path, manifest: &Manifest) -> Result<Vec<Planned>, CliError> {
    engine::plan(t.em.as_ref(), root, manifest).map_err(|e| agent_refusal(&e))
}

/// One agent's slice of a report.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PerAgent<R> {
    /// The emitter id.
    pub agent: String,
    /// The directory acted on.
    pub home: String,
    /// What happened there.
    #[serde(flatten)]
    pub report: R,
}

fn per<R>(t: &Target, report: R) -> PerAgent<R> {
    PerAgent {
        agent: t.em.id().to_owned(),
        home: Shown::of(&t.home).to_string(),
        report,
    }
}

/// Output of `agent sync`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct SyncData {
    /// One entry per agent.
    pub agents: Vec<PerAgent<SyncReport>>,
    /// True when `--dry-run` wrote nothing.
    pub dry_run: bool,
}

/// Publish the manifest into each selected agent's home behind a do-not-edit banner and register its hooks.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "agent sync",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct AgentSync {
    agent: String,
    home: Option<PathBuf>,
    allow_stale: bool,
}

impl Command for AgentSync {
    type Data = SyncData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<SyncArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<SyncArgs>(m)?;
        Ok(Self {
            agent: a.target.agent,
            home: a.target.home,
            allow_stale: a.allow_stale,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<SyncData> {
        let (repo, root, cfg, manifest) = setup(ctx)?;
        let targets = targets(&self.agent, self.home.as_deref())?;
        if !self.allow_stale {
            let stale = stale_sources(&repo, &root, &cfg.check.base, &manifest);
            if !stale.is_empty() {
                return Err(Refusal::new(
                    "E-AGENT-STALE",
                    RefusalClass::GuardNeedsAction,
                    format!(
                        "worktree copy is behind {}: {}",
                        cfg.check.base,
                        stale.join(", ")
                    ),
                )
                .with_remedy("rebase onto the base branch, or pass --allow-stale")
                .into());
            }
        }
        let mut agents = Vec::new();
        for t in &targets {
            let planned = plan(t, &root, &manifest)?;
            let report = engine::sync(t.em.as_ref(), &t.home, &manifest, &planned, ctx.dry_run)
                .map_err(|e| agent_refusal(&e))?;
            tracing::info!(
                agent = t.em.id(),
                written = report.written.len(),
                "agent sync done"
            );
            agents.push(per(t, report));
        }
        let already = agents.iter().all(|a| {
            a.report.written.is_empty()
                && a.report.removed.is_empty()
                && !a.report.registration_changed
        });
        Ok(Payload::new(SyncData {
            agents,
            dry_run: ctx.dry_run,
        })
        .with_already(already))
    }
}

/// Output of `agent status`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct StatusData {
    /// One entry per agent.
    pub agents: Vec<PerAgent<StatusReport>>,
    /// True when any agent has drifted.
    pub drift: bool,
}

/// Report drift between the repository manifest and each selected agent's home; exits 1 on drift.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "agent status",
    product = "frob",
    idempotent = true,
    read_only,
    exits(ok, negative, refused, usage, internal)
)]
pub struct AgentStatus {
    agent: String,
    home: Option<PathBuf>,
}

impl Command for AgentStatus {
    type Data = StatusData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<AgentArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AgentArgs>(m)?;
        Ok(Self {
            agent: a.agent,
            home: a.home,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<StatusData> {
        let (_repo, root, _cfg, manifest) = setup(ctx)?;
        let targets = targets(&self.agent, self.home.as_deref())?;
        let mut agents = Vec::new();
        for t in &targets {
            let planned = plan(t, &root, &manifest)?;
            let report = engine::status(t.em.as_ref(), &t.home, &manifest, &planned)
                .map_err(|e| agent_refusal(&e))?;
            agents.push(per(t, report));
        }
        let drift = agents.iter().any(|a| a.report.drift);
        let data = StatusData { agents, drift };
        if drift {
            tracing::warn!("agent drift detected");
            return Err(CliError::Gate {
                message: "an agent home has drifted from the repository; run `frob agent sync`"
                    .to_owned(),
                data: serde_json::to_value(&data).map_err(|e| CliError::Internal(Box::new(e)))?,
                warnings: Vec::new(),
            });
        }
        Ok(Payload::new(data))
    }
}

/// Output of `agent uninstall`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct UninstallData {
    /// One entry per agent.
    pub agents: Vec<PerAgent<UninstallReport>>,
    /// True when `--dry-run` removed nothing.
    pub dry_run: bool,
}

/// Remove only the files and registrations frob installed, leaving user additions alone.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "agent uninstall",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct AgentUninstall {
    agent: String,
    home: Option<PathBuf>,
}

impl Command for AgentUninstall {
    type Data = UninstallData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<AgentArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AgentArgs>(m)?;
        Ok(Self {
            agent: a.agent,
            home: a.home,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<UninstallData> {
        let (_repo, root, _cfg, manifest) = setup(ctx)?;
        let targets = targets(&self.agent, self.home.as_deref())?;
        let mut agents = Vec::new();
        for t in &targets {
            let planned = plan(t, &root, &manifest)?;
            let report =
                engine::uninstall(t.em.as_ref(), &t.home, &manifest, &planned, ctx.dry_run)
                    .map_err(|e| agent_refusal(&e))?;
            tracing::info!(
                agent = t.em.id(),
                removed = report.removed.len(),
                "agent uninstall done"
            );
            agents.push(per(t, report));
        }
        let already = agents
            .iter()
            .all(|a| a.report.removed.is_empty() && a.report.registrations_removed == 0);
        Ok(Payload::new(UninstallData {
            agents,
            dry_run: ctx.dry_run,
        })
        .with_already(already))
    }
}

/// `frob doctor` warnings for every previously synced agent home that has drifted.
pub(crate) fn drift_warnings(root: &Path, cfg: &FrobConfig) -> Vec<String> {
    let Ok(manifest) = Manifest::parse(&cfg.agent.items, &cfg.agent.hooks) else {
        return Vec::new();
    };
    if manifest.is_empty() {
        return Vec::new();
    }
    let mut out = Vec::new();
    for em in agent::emitters() {
        let Some(home) = em.default_home().filter(|h| engine::has_state(h)) else {
            continue;
        };
        let drifted = engine::plan(em.as_ref(), root, &manifest)
            .and_then(|p| engine::status(em.as_ref(), &home, &manifest, &p))
            .is_ok_and(|r| r.drift);
        if drifted {
            out.push(format!(
                "{} ({}) has drifted from the repository's [agent] manifest; fix: frob agent sync --agent {}",
                Shown::of(&home),
                em.id(),
                em.id()
            ));
        }
    }
    out
}

/// The flags of `agent brief`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct BriefArgs {
    #[arg(
        long,
        value_name = "BYTES",
        help = "Cap the brief at this many bytes (default: [agent] brief_max_bytes)"
    )]
    max_bytes: Option<usize>,
}

/// Output of `agent brief`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BriefData {
    /// The facts the brief was rendered from.
    #[serde(flatten)]
    pub input: BriefInput,
    /// The brief as printed, already capped.
    pub text: String,
    /// The byte budget applied.
    pub max_bytes: usize,
    /// True when the text was cut to fit the budget.
    pub truncated: bool,
}

// frob:ticket 01M4P2N1M00A5XSDA8SW5FBRR8
/// Print a bounded summary of the ticket leased from this worktree, its scope, the worktree and the standing rules.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "agent brief",
    product = "frob",
    idempotent = true,
    read_only,
    exits(ok, refused, usage, internal)
)]
pub struct AgentBrief {
    max_bytes: Option<usize>,
}

impl Command for AgentBrief {
    type Data = BriefData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<BriefArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<BriefArgs>(m)?;
        Ok(Self {
            max_bytes: a.max_bytes,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<BriefData> {
        let (_repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let max_bytes = self
            .max_bytes
            .unwrap_or_else(|| usize::try_from(cfg.agent.brief_max_bytes).unwrap_or(usize::MAX));
        let mut warnings = Vec::new();
        let input = gather(ctx, &root, &cfg, &mut warnings)?;
        let (text, truncated) = brief::cap(&brief::lines(&input), max_bytes);
        tracing::info!(
            active = input.ticket.is_some(),
            bytes = text.len(),
            truncated,
            "agent brief"
        );
        let rows = text.lines().map(str::to_owned).collect::<Vec<_>>();
        let mut payload = Payload::new(BriefData {
            input,
            text,
            max_bytes,
            truncated,
        })
        .with_rendered(rows);
        for w in warnings {
            payload = payload.with_warning(w);
        }
        Ok(payload)
    }
}

/// Collect the active ticket (the live lease held from this worktree), scope and rules; a ledger failure degrades to a warning.
fn gather(
    ctx: &Context,
    root: &Path,
    cfg: &FrobConfig,
    warnings: &mut Vec<String>,
) -> Result<BriefInput, CliError> {
    let want = gob_fs::canonical(root).unwrap_or_else(|_| root.to_path_buf());
    let (store, _) = frob_lease::open_store(&ctx.cwd, cfg.lease.clone(), ctx.clock.clone())?;
    let lease = store.list()?.into_iter().find(|l| {
        gob_fs::canonical(&l.holder.worktree).unwrap_or_else(|_| l.holder.worktree.clone()) == want
    });
    let ticket = lease.as_ref().map(|l| {
        let known = crate::ticket::open(ctx)
            .and_then(|ledger| ledger.show(l.ticket).map_err(crate::ticket::cli_err));
        match known {
            Ok(v) => ActiveTicket {
                handle: v.summary.handle,
                title: v.summary.title,
                category: v.summary.category.to_string(),
            },
            Err(e) => {
                tracing::warn!(ticket = %l.ticket, error = %e, "brief: ticket unreadable");
                warnings.push(format!("ticket {} could not be read: {e}", l.ticket));
                ActiveTicket {
                    handle: l.ticket.to_string(),
                    title: String::new(),
                    category: String::new(),
                }
            }
        }
    });
    Ok(BriefInput {
        ticket,
        scope: lease.map(|l| l.scope).unwrap_or_default(),
        worktree: Shown::of(&want).to_string(),
        rules: cfg.agent.brief_rules.clone(),
    })
}

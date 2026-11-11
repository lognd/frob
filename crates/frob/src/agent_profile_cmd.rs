//! `frob agent profile`: derive the committed heavy-command profile from command telemetry.
//!
//! `frob agent heavy` records each command's wall time and disk growth; this verb folds those rows into
//! `heavy-profile.toml` (commands over `[agent] heavy_wall_ms` or `heavy_disk_bytes`). With `--check` it
//! only reports whether the committed profile is stale and exits non-zero when it is.

// frob:ticket 01M4P2N1XMDZAGS1EAZPR6WQMQ

use frob_tests::heavy::{self, PROFILE_FILE, Thresholds};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::workspace::Located;

/// The flags of `agent profile`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ProfileArgs {
    #[arg(
        long,
        help = "Report whether the committed profile is stale; write nothing"
    )]
    check: bool,
}

/// Output of `agent profile`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ProfileData {
    /// The profile file, relative to the repository root.
    pub path: String,
    /// The heavy command keys the profile lists.
    pub commands: Vec<String>,
    /// True when the file was rewritten by this run.
    pub refreshed: bool,
    /// Why the committed profile is stale (`--check` only); absent when current.
    pub stale: Option<String>,
}

/// Refresh `heavy-profile.toml` from command telemetry, or check that it is current.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "agent profile",
    product = "frob",
    exits(ok, negative, usage, internal)
)]
pub struct AgentProfile {
    check: bool,
}

impl Command for AgentProfile {
    type Data = ProfileData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<ProfileArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ProfileArgs>(m)?;
        Ok(Self { check: a.check })
    }

    fn run(&self, ctx: &Context) -> Outcome<ProfileData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(CliError::internal)?;
        let limits = Thresholds {
            wall_ms: cfg.agent.heavy_wall_ms,
            disk_bytes: cfg.agent.heavy_disk_bytes,
        };
        if self.check {
            return Self::check_only(&root, limits);
        }
        let profile = heavy::refresh(&root, limits).map_err(|e| CliError::Usage(e.to_string()))?;
        tracing::info!(
            commands = profile.commands.len(),
            "agent profile: refreshed"
        );
        Ok(Payload::new(ProfileData {
            path: PROFILE_FILE.to_owned(),
            commands: profile.commands.into_keys().collect(),
            refreshed: true,
            stale: None,
        }))
    }
}

impl AgentProfile {
    /// Report staleness of the committed profile against `limits`; a stale profile is a gate failure.
    fn check_only(root: &std::path::Path, limits: Thresholds) -> Outcome<ProfileData> {
        let profile = heavy::load(root).map_err(|e| CliError::Usage(e.to_string()))?;
        let stale = heavy::check(root, Some(limits)).map_err(|e| CliError::Usage(e.to_string()))?;
        let data = ProfileData {
            path: PROFILE_FILE.to_owned(),
            commands: profile.map_or_else(Vec::new, |p| p.commands.into_keys().collect()),
            refreshed: false,
            stale: stale.clone(),
        };
        match stale {
            None => Ok(Payload::new(data)),
            Some(why) => Err(CliError::Gate {
                message: format!("{PROFILE_FILE} is stale: {why}"),
                data: serde_json::to_value(&data).map_err(CliError::internal)?,
                warnings: Vec::new(),
            }),
        }
    }
}

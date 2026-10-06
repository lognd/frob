//! `ticket branch init`: create the orphan ticket branch (`mirror.md` section 1, D79).

use frob_ledger::branch::{BranchError, BranchInit as Init, init_branch};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// Output of `ticket branch init`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BranchInitData {
    /// The branch name (`[tickets] branch`).
    pub branch: String,
    /// The branch tip: the new root commit, or the existing tip when `already`.
    pub tip: String,
}

/// Create the orphan `[tickets] branch` with a README placeholder through gob-git compare-and-swap, leaving the code checkout alone.
#[derive(Debug, Clone, Copy, gob_cli::Command)]
#[command(
    verb = "ticket branch init",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct BranchInit;

impl Command for BranchInit {
    type Data = BranchInitData;

    fn from_matches(_m: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> CliOutcome<BranchInitData> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let branch = cfg.tickets.branch.clone();
        let done = init_branch(&repo, &branch, cfg.git.cas_retries).map_err(branch_err)?;
        let (tip, already) = match done {
            Init::Created(t) => (t, false),
            Init::Already(t) => (t, true),
        };
        tracing::info!(%branch, %tip, already, "ticket branch init");
        Ok(Payload::new(BranchInitData {
            branch,
            tip: tip.to_string(),
        })
        .with_already(already))
    }
}

/// Map a bootstrap failure to a refusal the user can act on, else internal.
fn branch_err(e: BranchError) -> CliError {
    match e {
        BranchError::InvalidName { .. } => Refusal::new(
            "E-TICKET-BRANCH-NAME",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy("set [tickets] branch in frob.toml to a plain branch name")
        .into(),
        BranchError::RemoteOnly { ref branch, .. } => Refusal::new(
            "E-TICKET-BRANCH-REMOTE-ONLY",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy(format!("git branch {branch} origin/{branch}"))
        .into(),
        BranchError::Git(g) => crate::ticket::cli_err(g.into()),
    }
}

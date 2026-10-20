//! `ticket branch init`: create the ticket branch, adopting origin's copy when it has one (`mirror.md` section 1, D79).

use frob_ledger::branch::{BranchError, BranchInit as Init, init_branch};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload, Refusal, RefusalClass};
use gob_git::Repo;
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::{FrobConfig, RefModeKnob};
use crate::workspace::{Located, config_refusal};

/// Output of `ticket branch init`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BranchInitData {
    /// The branch name (`[tickets] branch`).
    pub branch: String,
    /// The branch tip: the new root commit, or the existing tip when `already`.
    pub tip: String,
}

/// Create the local `[tickets] branch` through gob-git compare-and-swap, adopting origin's copy when it has one (else a fresh orphan with a README placeholder), leaving the code checkout alone.
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
            Init::Created(t) | Init::Adopted(t) => (t, false),
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

/// True when `[tickets] ref_mode = "orphan"` but the local ticket branch does not exist yet (a fresh or CI clone).
pub(crate) fn ticket_branch_missing(repo: &Repo, cfg: &FrobConfig) -> bool {
    cfg.tickets.ref_mode == RefModeKnob::Orphan
        && repo
            .rev_parse(&format!("refs/heads/{}", cfg.tickets.branch))
            .is_err()
}

/// Make the local ticket branch exist in orphan mode (adopting origin's copy, else a fresh orphan); `None` outside orphan mode, and in a dry run nothing is written.
///
/// Returns the branch name when it was created (or, in a dry run, would be).
///
/// # Errors
/// The refusal of [`branch_err`].
pub(crate) fn ensure_ticket_branch(
    repo: &Repo,
    cfg: &FrobConfig,
    dry_run: bool,
) -> Result<Option<String>, CliError> {
    if !ticket_branch_missing(repo, cfg) {
        tracing::debug!("ticket branch not needed or already present");
        return Ok(None);
    }
    let branch = cfg.tickets.branch.clone();
    if dry_run {
        tracing::info!(%branch, "dry run: would create the local ticket branch");
        return Ok(Some(branch));
    }
    init_branch(repo, &branch, cfg.git.cas_retries).map_err(branch_err)?;
    Ok(Some(branch))
}

/// Map a bootstrap failure to a refusal the user can act on, else internal.
pub(crate) fn branch_err(e: BranchError) -> CliError {
    match e {
        BranchError::InvalidName { .. } => Refusal::new(
            "E-TICKET-BRANCH-NAME",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy("set [tickets] branch in frob.toml to a plain branch name")
        .into(),
        BranchError::RemoteUnreachable { ref branch, .. } => Refusal::new(
            "E-TICKET-BRANCH-REMOTE-UNREACHABLE",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy(format!(
            "git fetch origin +refs/heads/{branch}:refs/remotes/origin/{branch}, then rerun"
        ))
        .into(),
        BranchError::Git(g) => crate::ticket::cli_err(g.into()),
    }
}

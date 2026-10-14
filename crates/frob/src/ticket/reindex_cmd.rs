//! `ticket reindex`: move ticket files to their computed paths in a reindex commit (`navigation.md` 2.2).
// frob:ticket 01M3ZX85X37W6QSQSJD1WYVKZG

use frob_ledger::r#gen::code_readme::{self, Home, RegionSettings};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::url_cmd::web_base;
use super::{cli_err, open};
use crate::config::{FrobConfig, RefModeKnob};
use crate::workspace::{Located, config_refusal};

/// Most diff lines `--check` prints before summarising the rest.
const DIFF_CAP: usize = 50;

/// One ticket file the reindex moves.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MovedFile {
    /// Old branch-relative path.
    pub from: String,
    /// New branch-relative path.
    pub to: String,
}

/// Output of `ticket reindex`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ReindexData {
    /// Ticket files moved (or, with `--check`, that would move).
    pub moved: Vec<MovedFile>,
    /// Files the reindex commit writes or deletes, moves included.
    pub files: usize,
    /// The reindex commit, when one was written.
    pub commit: Option<String>,
    /// With `--check` on a stale branch, the capped diff (one line per file); empty otherwise.
    pub diff: String,
    /// With `--code-readme`: `current`, `updated` (or, with `--check`, `stale`); absent otherwise.
    // frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
    #[serde(skip_serializing_if = "Option::is_none")]
    pub readme: Option<String>,
}

/// What `--code-readme` found in the code repository's README.
// frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
struct ReadmePlan {
    /// Path of README.md in the work tree.
    path: std::path::PathBuf,
    /// README text with the region regenerated.
    text: String,
    /// True when `text` differs from the file.
    changed: bool,
    /// GEN001 message when the region on disk is missing or edited.
    drift: Option<String>,
}

/// Render the region from the repository's ticket configuration and compare it with README.md.
// frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
fn plan_readme(ctx: &Context) -> Result<ReadmePlan, CliError> {
    let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
    let remote = repo.remote_url("origin");
    let base = remote.as_deref().and_then(web_base);
    let home = match cfg.tickets.ref_mode {
        RefModeKnob::Orphan => Home::Branch(&cfg.tickets.branch),
        RefModeKnob::Trunk | RefModeKnob::Branch => Home::Dir(&cfg.tickets.dir),
    };
    let region = code_readme::render(&RegionSettings {
        home,
        web_base: base.as_deref(),
    });
    let path = root.join("README.md");
    let old = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(e) => return Err(CliError::internal(e)),
    };
    let text = code_readme::apply(&old, &region).map_err(CliError::internal)?;
    let drift = code_readme::check(&old, &region)
        .err()
        .map(|d| d.to_string());
    Ok(ReadmePlan {
        changed: text != old,
        path,
        text,
        drift,
    })
}

/// Move ticket files to the paths their titles and parents imply, in one `tickets(reindex)` commit; `--check` changes nothing and exits 1 with the diff when the branch is stale.
#[derive(Debug, Clone, Copy, gob_cli::Command)]
#[command(
    verb = "ticket reindex",
    product = "frob",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Reindex {
    check: bool,
    // frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
    code_readme: bool,
}

/// The flags of `ticket reindex`, declared once.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ReindexArgs {
    #[arg(
        long,
        help = "Write nothing; print the diff and exit 1 when the ticket branch is not current"
    )]
    check: bool,
    // frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
    #[arg(
        long,
        help = "Also regenerate the marked tickets region of the code repository's README.md; with --check, report GEN001 when it is stale"
    )]
    code_readme: bool,
}

impl Command for Reindex {
    type Data = ReindexData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ReindexArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ReindexArgs>(m)?;
        Ok(Self {
            check: a.check,
            code_readme: a.code_readme,
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<ReindexData> {
        let ledger = open(ctx)?;
        let plan = ledger.reindex_plan().map_err(cli_err)?;
        let moved: Vec<MovedFile> = plan
            .moves
            .iter()
            .map(|m| MovedFile {
                from: m.from.clone(),
                to: m.to.clone(),
            })
            .collect();
        // frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
        let readme = self.code_readme.then(|| plan_readme(ctx)).transpose()?;
        let readme_drifted = readme.as_ref().is_some_and(|r| r.drift.is_some());
        let current = plan.changes.is_empty();
        if self.check && (!current || readme_drifted) {
            let mut diff = plan.diff(DIFF_CAP);
            if let Some(d) = readme.as_ref().and_then(|r| r.drift.as_deref()) {
                diff.push_str(d);
                diff.push('\n');
            }
            let data = ReindexData {
                moved,
                files: plan.changes.len(),
                commit: None,
                diff,
                readme: readme.as_ref().map(|_| "stale".to_owned()),
            };
            return Err(CliError::Gate {
                message: format!("ticket branch is not reindexed:\n{}", data.diff),
                data: serde_json::to_value(&data).map_err(CliError::internal)?,
                warnings: Vec::new(),
            });
        }
        let commit = if self.check || current {
            None
        } else {
            ledger.reindex_commit(None).map_err(cli_err)?
        };
        // frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
        let readme_state = match readme {
            Some(r) if r.changed && !self.check => {
                std::fs::write(&r.path, &r.text).map_err(CliError::internal)?;
                Some("updated")
            }
            Some(_) => Some("current"),
            None => None,
        };
        tracing::info!(
            check = self.check,
            files = plan.changes.len(),
            "ticket reindex"
        );
        Ok(Payload::new(ReindexData {
            moved,
            files: plan.changes.len(),
            commit: commit.map(|c| c.to_string()),
            diff: String::new(),
            readme: readme_state.map(str::to_owned),
        })
        .with_already(current && readme_state != Some("updated")))
    }
}

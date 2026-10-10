//! Opening the repository, ledger, store and `[evidence]` config for a verb.

use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_ledger::{Ledger, LedgerConfig};
use gob_exec::{Limits, Runner};
use gob_git::Repo;

use crate::config::{DotnetTable, EvidenceTable, TestsTable, UnityTable};
use crate::error::{EvidenceError, Result};
use crate::scrub::PathScrub;
use crate::store::BlobStore;

/// Product name and config file stem.
pub const PRODUCT: &str = "frob";

/// Everything an evidence or test verb needs from the repository it runs in.
#[derive(Debug)]
pub struct Workspace {
    /// The ledger (and through it the repository).
    pub ledger: Ledger,
    /// The work tree root.
    pub root: PathBuf,
    /// The effective `[evidence]` table.
    pub evidence: EvidenceTable,
    // frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
    /// The effective `[evidence.dotnet]` table.
    pub dotnet: DotnetTable,
    // frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
    /// The effective `[evidence.unity]` table.
    pub unity: UnityTable,
    // frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
    /// The effective `[tests]` table.
    pub tests: TestsTable,
    /// The blob store built from it.
    pub store: BlobStore,
}

impl Workspace {
    /// Open the repository containing `cwd` with its `frob.toml` settings, stamping from `clock`.
    ///
    /// # Errors
    ///
    /// [`EvidenceError::NotARepo`] outside a work tree, [`EvidenceError::Config`]
    /// for an unreadable or invalid `frob.toml`.
    pub fn open(cwd: &Path, clock: std::sync::Arc<dyn gob_time::Clock>) -> Result<Self> {
        let repo = Repo::discover(cwd).map_err(|e| {
            tracing::debug!(error = %e, "no repository");
            EvidenceError::NotARepo(cwd.display().to_string())
        })?;
        let root = repo
            .work_dir()
            .map(Path::to_path_buf)
            .ok_or_else(|| EvidenceError::NotARepo(cwd.display().to_string()))?;
        let evidence = gob_config::load::<EvidenceTable>(&root, PRODUCT)
            .map_err(|e| EvidenceError::Config(e.to_string()))?
            .value;
        let dotnet = gob_config::load::<DotnetTable>(&root, PRODUCT)
            .map_err(|e| EvidenceError::Config(e.to_string()))?
            .value;
        let unity = gob_config::load::<UnityTable>(&root, PRODUCT)
            .map_err(|e| EvidenceError::Config(e.to_string()))?
            .value;
        let tests = gob_config::load::<TestsTable>(&root, PRODUCT)
            .map_err(|e| EvidenceError::Config(e.to_string()))?
            .value;
        let ledger_cfg = ledger_config(&root)?;
        let store = BlobStore::open(&evidence, &repo)?;
        tracing::debug!(root = %root.display(), "evidence workspace opened");
        Ok(Self {
            ledger: Ledger::open(repo, ledger_cfg, clock),
            root,
            evidence,
            dotnet,
            unity,
            tests,
            store,
        })
    }

    /// A runner whose `Tool` programs are limited to `[evidence] allowed_tools`.
    pub fn runner(&self) -> Runner {
        Runner::new(Limits::default()).allow_tools(self.evidence.allowed_tools.clone())
    }

    // frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
    /// The scrub that rewrites this repository's, worktree's and home's absolute paths in captured text.
    pub fn scrub(&self) -> PathScrub {
        let common = self.ledger.repo().common_dir();
        let repo = if common.file_name().is_some_and(|n| n == ".git") {
            common.parent().unwrap_or(&self.root)
        } else {
            &self.root
        };
        PathScrub::new(repo, &self.root)
    }

    /// The wall-clock limit of one provider process.
    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.evidence.timeout_secs)
    }
}

/// The ledger settings in `<root>/frob.toml`, defaults for anything absent.
///
/// The `[tickets]` and `[git]` tables are owned by the `frob` binary crate,
/// which depends on this one, so the handful of keys the ledger needs are read
/// loosely here; unknown keys are the binary's business, not ours.
///
/// # Errors
///
/// [`EvidenceError::Config`] when the file is unreadable or not TOML, or a
/// known key has the wrong type.
pub fn ledger_config(root: &Path) -> Result<LedgerConfig> {
    frob_ledger::config::load_ledger_config(root).map_err(EvidenceError::Config)
}

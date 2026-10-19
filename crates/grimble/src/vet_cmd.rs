//! `vet [--base REF]`: dependency vetting over `Cargo.lock` (cli.md, boundaries.md 2.3).
//!
//! Inputs: `Cargo.lock` at the root, the allowlist `.grimble/vet.toml` (`allow = ["serde"]`) and an
//! offline RustSec snapshot directory (`--advisory-db`, default `.grimble/advisory-db`). With
//! `--base` only packages new relative to the lockfile at that ref are vetted. `grimble check
//! --base` also reports the same findings as warnings.

// frob:ticket 01M406M2HX6Z6SEGM6HRPQKHAV

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_vet::{Allowlist, Snapshot, VetReport, parse_lockfile, vet};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::locate_root;

const LOCKFILE: &str = "Cargo.lock";
const ALLOWLIST: &str = ".grimble/vet.toml";
const DEFAULT_DB: &str = ".grimble/advisory-db";

/// Vet the locked dependencies: advisories, unvetted additions and duplicate versions.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "vet",
    product = "grimble",
    exits(ok, negative, refused, usage, internal)
)]
pub struct Vet {
    base: Option<String>,
    advisory_db: Option<String>,
}

/// `Vet` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct VetArgs {
    #[arg(
        long,
        help = "Only vet packages that are new relative to Cargo.lock at this ref"
    )]
    base: Option<String>,
    #[arg(
        long,
        help = "Directory of RustSec advisory TOML files (default .grimble/advisory-db)"
    )]
    advisory_db: Option<String>,
}

/// Output of `vet`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct VetData {
    /// The base ref, when delta mode was requested.
    pub base: Option<String>,
    /// Whether an advisory snapshot was available.
    pub advisories_checked: bool,
    /// The vetting report.
    #[serde(flatten)]
    pub report: VetReport,
}

/// Run the vetting pass for `root`; `Ok(None)` when there is no `Cargo.lock`.
///
/// # Errors
/// [`CliError`] for unreadable inputs or an unusable git base.
pub fn run_vet(
    root: &Path,
    base: Option<&str>,
    advisory_db: Option<&str>,
) -> Result<Option<VetData>, CliError> {
    let Ok(head_text) = std::fs::read_to_string(root.join(LOCKFILE)) else {
        tracing::debug!(root = %root.display(), "no Cargo.lock, nothing to vet");
        return Ok(None);
    };
    let bad = |e: grimble_vet::VetError| CliError::Usage(e.to_string());
    let head = parse_lockfile(&head_text).map_err(bad)?;
    let base_pkgs = match base {
        None => None,
        Some(rev) => {
            let repo = gob_git::Repo::discover(root)
                .map_err(|e| CliError::Usage(format!("vet --base needs a git repository: {e}")))?;
            let blob = repo
                .read_blob_at(rev, LOCKFILE)
                .map_err(|e| CliError::Usage(format!("cannot read {LOCKFILE} at {rev}: {e}")))?;
            let text = blob
                .map(|b| String::from_utf8_lossy(&b).into_owned())
                .unwrap_or_default();
            Some(parse_lockfile(&text).map_err(bad)?)
        }
    };
    let allow = match std::fs::read_to_string(root.join(ALLOWLIST)) {
        Ok(t) => Allowlist::parse(&t).map_err(bad)?,
        Err(_) => Allowlist::default(),
    };
    let db_dir = advisory_db.map_or_else(|| root.join(DEFAULT_DB), |d| root.join(d));
    let snapshot = if db_dir.is_dir() {
        Some(Snapshot::load(&db_dir).map_err(bad)?)
    } else if advisory_db.is_some() {
        return Err(CliError::Usage(format!(
            "no advisory snapshot at {}",
            db_dir.display()
        )));
    } else {
        tracing::warn!(dir = %db_dir.display(), "no advisory snapshot; advisories not checked");
        None
    };
    let report = vet(
        &head,
        base_pkgs.as_deref(),
        snapshot.as_ref().unwrap_or(&Snapshot::default()),
        &allow,
    );
    Ok(Some(VetData {
        base: base.map(str::to_owned),
        advisories_checked: snapshot.is_some(),
        report,
    }))
}

impl Command for Vet {
    type Data = VetData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<VetArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<VetArgs>(m)?;
        Ok(Self {
            base: a.base,
            advisory_db: a.advisory_db,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<VetData> {
        let root = locate_root(&ctx.cwd);
        let data = run_vet(&root, self.base.as_deref(), self.advisory_db.as_deref())?
            .ok_or_else(|| CliError::Usage(format!("no {LOCKFILE} at {}", root.display())))?;
        let errors = data.report.errors();
        if errors > 0 {
            let message = format!("{errors} vetting error(s): {}", summary(&data.report));
            let value = serde_json::to_value(&data).map_err(CliError::internal)?;
            return Err(CliError::Gate {
                message,
                data: value,
                warnings: Vec::new(),
            });
        }
        let rows = data
            .report
            .findings
            .iter()
            .map(|f| f.message.clone())
            .collect();
        Ok(Payload::new(data).with_rendered(rows))
    }
}

/// The finding messages joined for a gate message.
fn summary(report: &VetReport) -> String {
    report
        .findings
        .iter()
        .map(|f| format!("{:?} {}", f.rule, f.message))
        .collect::<Vec<_>>()
        .join("; ")
}

/// Finding lines for `grimble check --base`: one warning per finding, empty without a lockfile.
pub fn check_warnings(root: &Path, base: &str) -> Vec<String> {
    match run_vet(root, Some(base), None) {
        Ok(Some(data)) => data
            .report
            .findings
            .iter()
            .map(|f| format!("vet: {}", f.message))
            .collect(),
        Ok(None) => Vec::new(),
        Err(e) => vec![format!("vet: skipped: {e}")],
    }
}

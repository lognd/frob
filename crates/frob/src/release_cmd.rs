//! `release changelog`: compile `changelog.d` fragments into CHANGELOG.md (documentation.md 6).
//!
//! A thin layer over `frob-release`: ticket ULIDs resolve against the ledger, a typed
//! [`ReleaseError`] becomes an exit-3 refusal carrying its teaching message, and
//! an I/O failure is internal.

use frob_ledger::{Ledger, TicketId};
use frob_release::{Mode, Options, ReleaseError};
use gob_cli::clap::{Arg, ArgAction, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::ticket::{get, text_flag};
use crate::workspace::{Located, config_refusal};

/// What `release changelog` did, or with `--check` and `--dry-run` would do.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ChangelogData {
    /// The release version.
    pub version: String,
    /// `write`, `dry-run` or `check`.
    pub mode: String,
    /// The rendered section; absent when there were no fragments.
    pub section: Option<String>,
    /// Fragment file names compiled (or that would be).
    pub fragments: Vec<String>,
    /// True when CHANGELOG.md was written and the fragments removed.
    pub written: bool,
}

/// Compile changelog.d fragments into a new CHANGELOG.md section for a version.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release changelog",
    product = "frob",
    idempotent = true,
    dry_run = true,
    exits(ok, refused, usage, internal)
)]
pub struct ReleaseChangelog {
    version: String,
    date: Option<String>,
    check: bool,
}

impl Command for ReleaseChangelog {
    type Data = ChangelogData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .long("version")
                .required(true)
                .value_name("X")
                .help("Release version, MAJOR.MINOR.PATCH (for example 0.532.0)"),
        )
        .arg(text_flag(
            "date",
            "Section date YYYY-MM-DD (default: today)",
        ))
        .arg(
            Arg::new("check")
                .long("check")
                .action(ArgAction::SetTrue)
                .help("Validate fragments and that older sections are unedited; write nothing"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            date: get(m, "date"),
            check: m.get_flag("check"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ChangelogData> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let ledger = Ledger::open(repo, cfg.ledger());
        let mode = if self.check {
            Mode::Check
        } else if ctx.dry_run {
            Mode::DryRun
        } else {
            Mode::Write
        };
        let date = self
            .date
            .clone()
            .unwrap_or_else(|| jiff::Zoned::now().date().to_string());
        let opts = Options {
            version: self.version.clone(),
            date,
            mode,
        };
        let resolver = |ulid: &str| -> Option<String> {
            let id: TicketId = ulid.parse().ok()?;
            ledger.show(id).ok().map(|v| v.summary.handle)
        };
        let out = frob_release::run(&root, &opts, &resolver).map_err(refuse)?;
        tracing::info!(version = %self.version, ?mode, written = out.written, "release changelog");
        let already = out.section.is_none();
        Ok(Payload::new(ChangelogData {
            version: self.version.clone(),
            mode: format!("{mode:?}").to_lowercase(),
            section: out.section,
            fragments: out.fragments,
            written: out.written,
        })
        .with_already(already))
    }
}

/// Map a release error to its CLI error: refusal (exit 3) unless it is an I/O failure.
fn refuse(e: ReleaseError) -> CliError {
    let (code, remedy) = match &e {
        ReleaseError::Io { .. } => return CliError::internal(e),
        ReleaseError::Fragments(_) => (
            "E-CHANGELOG-FRAGMENT",
            "frob release changelog --check --version <X>",
        ),
        ReleaseError::InvalidVersion(_) | ReleaseError::InvalidDate(_) => {
            ("E-CHANGELOG-ARGS", "frob release changelog --help")
        }
        ReleaseError::VersionExists(_) => (
            "E-CHANGELOG-VERSION-EXISTS",
            "frob release changelog --dry-run --version <next>",
        ),
        ReleaseError::Tampered(_) | ReleaseError::Unmarked(_) => {
            ("E-CHANGELOG-EDITED", "git checkout -- CHANGELOG.md")
        }
    };
    tracing::info!(code, "release changelog refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy(remedy)
        .into()
}

/// Register the `release` verbs on the root.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<ReleaseChangelog>()
}

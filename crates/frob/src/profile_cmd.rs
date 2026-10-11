//! `frob profile [newcomer|experienced]`: the local reader profile (`navigation.md` section 4.1).
//!
//! The profile lives in `.frob/profile.toml`, a local and disposable store. It changes
//! presentation only, never what a check decides and never a gate.

// frob:ticket 01M3ZX87FNRDNXXC2VTYPHN173

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Outcome as TicketOutcome};
use frob_ledger::{Ledger, event::EventBody};
use gob_cli::clap::{Arg, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::workspace::Located;

/// Closed tickets by this actor after which the one-time note suggests switching.
pub const SUGGEST_AFTER: usize = 3;

/// The stored form of `.frob/profile.toml`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
struct Stored {
    /// The chosen profile; absent until the person picks one.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    profile: Option<String>,
    /// True once the switch suggestion has been shown.
    #[serde(default)]
    suggested: bool,
}

/// Output of `frob profile`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ProfileData {
    /// The effective profile: `newcomer` or `experienced`.
    pub profile: String,
    /// True when the person chose it (it is recorded in `profile.toml`), false for the default.
    pub chosen: bool,
    /// Tickets this actor has closed as done in this repository, when it was counted.
    pub closed_by_actor: Option<usize>,
    /// True when this run showed the one-time suggestion to switch.
    pub suggested: bool,
}

/// Show the reader profile, or set it to `newcomer` or `experienced`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "profile",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ProfileVerb {
    set: Option<String>,
}

fn store_path(root: &Path) -> PathBuf {
    root.join(".frob").join("profile.toml")
}

fn load(path: &Path) -> Stored {
    // A missing or unreadable store is the default: the store is disposable.
    std::fs::read_to_string(path)
        .ok()
        .and_then(|t| toml::from_str(&t).ok())
        .unwrap_or_default()
}

fn save(path: &Path, stored: &Stored) -> Result<(), CliError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(CliError::internal)?;
    }
    let text = toml::to_string(stored).map_err(CliError::internal)?;
    std::fs::write(path, text).map_err(CliError::internal)
}

/// Distinct tickets `actor` moved to done with the outcome done.
fn closed_by(ledger: &Ledger, actor: &str) -> Result<usize, frob_ledger::LedgerError> {
    let filter = ListFilter {
        category: Some(Category::Done),
        ..ListFilter::default()
    };
    let mut mine = BTreeSet::new();
    for summary in ledger.list(&filter)? {
        let closed = ledger.events(summary.id)?.iter().any(|e| {
            e.actor == actor
                && matches!(
                    &e.body,
                    EventBody::Transition(t)
                        if t.to == Category::Done && t.outcome == Some(TicketOutcome::Done)
                )
        });
        if closed {
            mine.insert(summary.id);
        }
    }
    Ok(mine.len())
}

impl Command for ProfileVerb {
    type Data = ProfileData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("profile")
                .value_name("PROFILE")
                .value_parser(["newcomer", "experienced"])
                .help("Set the profile; omit to show it"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            set: m.get_one::<String>("profile").cloned(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ProfileData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let path = store_path(&root);
        let mut stored = load(&path);
        let mut already = false;
        if let Some(choice) = &self.set {
            already = stored.profile.as_deref() == Some(choice.as_str());
            if !already {
                stored.profile = Some(choice.clone());
                save(&path, &stored)?;
            }
            tracing::info!(profile = %choice, already, "profile set");
        }
        let mut closed = None;
        let mut suggested = false;
        let mut note = None;
        if stored.profile.is_none() && !stored.suggested {
            // Only a newcomer by default can be nudged, and only once.
            closed = count_closed(ctx);
            if closed.is_some_and(|n| n >= SUGGEST_AFTER) {
                suggested = true;
                stored.suggested = true;
                save(&path, &stored)?;
                note = Some(format!(
                    "you have closed {} tickets here; `frob profile experienced` drops the newcomer hints",
                    closed.unwrap_or_default()
                ));
            }
        }
        let data = ProfileData {
            profile: stored
                .profile
                .clone()
                .unwrap_or_else(|| "newcomer".to_owned()),
            chosen: stored.profile.is_some(),
            closed_by_actor: closed,
            suggested,
        };
        let payload = Payload::new(data).with_already(already);
        Ok(match note {
            Some(n) => payload.with_warning(n),
            None => payload,
        })
    }
}

/// Count tickets the running actor closed; `None` when there is no ledger or identity to count with.
fn count_closed(ctx: &Context) -> Option<usize> {
    let ledger = crate::ticket::open(ctx).ok()?;
    let actor = ledger.actor().ok()?;
    match closed_by(&ledger, &actor) {
        Ok(n) => Some(n),
        Err(e) => {
            tracing::debug!(error = %e, "closed tickets not counted");
            None
        }
    }
}

/// Register the profile verb.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<ProfileVerb>()
}

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
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::workspace::Located;

/// Closed tickets by this actor after which the one-time note suggests switching.
pub const SUGGEST_AFTER: usize = 3;

/// How many of the most recently finished tickets the closed count looks at (it is a lower bound).
const RECENT_DONE: usize = 256;

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

// frob:ticket 01M4MMGDBXRGC9X90CZPPSKN6Z
/// Distinct tickets `actor` moved to done with the outcome done among the [`RECENT_DONE`] most recently
/// finished tickets, counted up to `limit` and no further: a lower bound, which is all the nudge needs,
/// and a cost that does not grow with the ledger.
///
/// Events are read in bulk chunks (`events_many`: one sync and one tree walk per chunk): reading
/// them ticket by ticket re-synced the ledger for each of about 900 done tickets and took seconds.
fn closed_by(
    ledger: &Ledger,
    actor: &str,
    limit: usize,
) -> Result<usize, frob_ledger::LedgerError> {
    const CHUNK: usize = 64;
    let filter = ListFilter {
        category: Some(Category::Done),
        ..ListFilter::default()
    };
    let mut done = ledger.list(&filter)?;
    done.sort_by_key(|s| std::cmp::Reverse(s.updated));
    let ids: Vec<_> = done.into_iter().take(RECENT_DONE).map(|s| s.id).collect();
    let mut mine = BTreeSet::new();
    for chunk in ids.chunks(CHUNK) {
        let want: BTreeSet<_> = chunk.iter().copied().collect();
        for (id, events) in ledger.events_many(&want)? {
            let closed = events.iter().any(|e| {
                e.actor == actor
                    && matches!(
                        &e.body,
                        EventBody::Transition(t)
                            if t.to == Category::Done && t.outcome == Some(TicketOutcome::Done)
                    )
            });
            if closed {
                mine.insert(id);
            }
        }
        if mine.len() >= limit {
            break;
        }
    }
    Ok(mine.len().min(limit))
}

/// `ProfileVerb` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ProfileArgs {
    #[arg(
        value_name = "PROFILE",
        value_parser = ["newcomer", "experienced"],
        help = "Set the profile; omit to show it"
    )]
    profile: Option<String>,
}

impl Command for ProfileVerb {
    type Data = ProfileData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<ProfileArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ProfileArgs>(m)?;
        Ok(Self { set: a.profile })
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
                    "you have closed at least {} tickets here; `frob profile experienced` drops the newcomer hints",
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
    match closed_by(&ledger, &actor, SUGGEST_AFTER) {
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

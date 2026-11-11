//! The `ticket` verbs and `merge-driver`: thin CLI layer over `frob-ledger`.
//!
//! Every verb opens the [`Ledger`] from the repository containing `--cwd`,
//! resolves ticket references (full ULID, `~handle` or alias), calls one
//! ledger operation and renders its result. Verbs: [`mod@write`] (new, update,
//! link, unlink, comment, close, drop, reopen), [`mod@read`] (show, list, doable,
//! brief), [`triage_cmd`] (the inbox verbs), [`doctor_cmd`] and the hidden [`merge_cmd`].

pub mod branch_cmd;
pub mod doctor_cmd;
pub mod fragment_cmd;
pub mod merge_cmd;
pub mod migrate_cmd;
pub mod proposals_accept;
pub mod proposals_cmd;
pub mod read;
pub mod reindex_cmd;
pub mod terminal_lease;
pub mod triage_cmd;
// frob:ticket 01M3ZX88FHDWF9C082QZR1PXXA
pub mod url_cmd;
pub mod usage_cmd;
pub mod write;

use frob_ledger::model::{Category, Class, Outcome, Priority, TicketType};
use frob_ledger::{Applied, Ledger, LedgerError, TicketId};
use gob_cli::{CliError, Context};
use gob_diagnostics::{Refusal, RefusalClass, RemedyCommand};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// Open the ledger of the repository containing `ctx.cwd`.
pub(crate) fn open(ctx: &Context) -> Result<Ledger, CliError> {
    let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
    crate::sync_hook::kick(&repo, &cfg, ctx);
    let ledger =
        Ledger::open(repo, cfg.ledger(), ctx.clock.clone()).with_point_scale(cfg.pm.pm.point_scale);
    // frob:ticket 01M4FG552GZ9FMB000B76AS8XH
    crate::workspace::note_ledger_site(&ledger);
    Ok(ledger)
}

/// Assess the cached ticket view of `ctx.cwd` against `[sync]`; `None` when the repository or its config cannot be read.
// frob:ticket 01M5D9NM6D3DSGD980M52CRMYV
pub(crate) fn view_freshness(ctx: &Context) -> Option<crate::freshness::Freshness> {
    let (repo, root) = Located::discover(&ctx.cwd).into_repo().ok()?;
    let cfg = FrobConfig::load(&root).ok()?;
    Some(crate::freshness::assess_repo(
        &repo,
        &cfg.sync,
        ctx.clock.now().unix(),
    ))
}

/// The envelope `freshness` field for an assessed view.
// frob:ticket 01M5D5PZVVDVE6ZJ2Z9CERYYYA
pub(crate) fn envelope_freshness(
    fresh: Option<&crate::freshness::Freshness>,
) -> Option<gob_diagnostics::EnvelopeFreshness> {
    fresh.map(crate::freshness::Freshness::to_envelope)
}

/// The one-line freshness footer for read verbs; `None` when the view is fresh or local-only.
// frob:ticket 01M5D5PZVVDVE6ZJ2Z9CERYYYA
pub(crate) fn freshness_footer(fresh: Option<&crate::freshness::Freshness>) -> Option<String> {
    use crate::freshness::FreshState;
    let fresh = fresh?;
    let line = match (fresh.state, fresh.age_secs) {
        (FreshState::Fresh | FreshState::LocalOnly, _) => return None,
        (state, Some(age)) => format!(
            "view {state:?} (as of {} ago)",
            frob_ledger::refresh::human_age(age)
        ),
        (state, None) => format!("view {state:?} (never refreshed)"),
    };
    tracing::debug!(%line, "ticket read freshness footer");
    Some(line.to_lowercase())
}

/// Refuse with `E-SYNC-STALE` when `fresh` is too old to claim from, unless automatic sync is disabled (`CI`).
// frob:ticket 01M5D9NM6D3DSGD980M52CRMYV
pub(crate) fn refuse_if_stale(fresh: &crate::freshness::Freshness) -> Result<(), CliError> {
    Ok(crate::freshness::refuse_if_blocked(fresh)?)
}

/// Open the lease store of `ctx.cwd` with the materialized `[lease]` table of `frob.toml`.
pub(crate) fn open_lease_store(
    ctx: &Context,
) -> Result<(frob_lease::LeaseStore, std::path::PathBuf), CliError> {
    let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
    Ok(frob_lease::open_store(
        &ctx.cwd,
        cfg.lease,
        ctx.clock.clone(),
    )?)
}

/// Map a ledger failure to the CLI error: a refusal when the caller can fix it, else internal.
pub(crate) fn cli_err(e: LedgerError) -> CliError {
    match e.to_refusal() {
        Some(r) => r.into(),
        None => CliError::internal(e),
    }
}

/// Resolve a ticket reference given on the command line.
pub(crate) fn resolve(ledger: &Ledger, input: &str) -> Result<TicketId, CliError> {
    if let Some(id) = ticket_file_id(input) {
        // frob:ticket 01M3ZX85H7VX2XFX1T663BD9NG
        if let Ok(view) = ledger.show(id) {
            return Err(Refusal::new(
                "E-TICKET-PATH",
                RefusalClass::UsageError,
                format!("that file is {}; pass the id", view.summary.handle),
            )
            .with_command(
                RemedyCommand::new("frob", "ticket show").arg(view.summary.handle.clone()),
            )
            .into());
        }
    }
    ledger.resolve(input).map_err(cli_err)
}

/// The ticket a path-shaped argument names: a ULID path component (legacy `tickets/<ULID>/ticket.md`) or the frontmatter id of the file it points at.
// frob:ticket 01M3ZX85H7VX2XFX1T663BD9NG
fn ticket_file_id(input: &str) -> Option<TicketId> {
    let input = input.trim();
    if !(input.contains('/')
        || input.contains('\\')
        || std::path::Path::new(input)
            .extension()
            .is_some_and(|ext| ext.eq_ignore_ascii_case("md")))
    {
        return None;
    }
    let by_component = input
        .split(['/', '\\'])
        .find_map(|part| part.parse::<TicketId>().ok());
    by_component.or_else(|| {
        let text = std::fs::read_to_string(input).ok()?;
        frob_ledger::layout::peek_ticket_id(&text)
    })
}

/// The positional ticket argument shared by the ticket verbs, declared once.
#[derive(Debug, Clone, clap::Args)]
pub(crate) struct TicketArg {
    /// The ticket as typed: full ULID, `~handle` or alias.
    #[arg(
        value_name = "TICKET",
        help = "Full ULID, ~handle or alias of the ticket"
    )]
    pub(crate) ticket: String,
}

/// The value parser of a flag restricted to the given spellings.
pub(crate) fn choices(
    names: &'static [&'static str],
) -> gob_cli::clap::builder::PossibleValuesParser {
    gob_cli::clap::builder::PossibleValuesParser::new(names)
}

/// Parse the spelling of the validated choice flag `--flag`, when it was given.
pub(crate) fn parsed<T: std::str::FromStr>(
    flag: &str,
    value: Option<String>,
) -> Result<Option<T>, CliError>
where
    T::Err: std::fmt::Display,
{
    value
        .map(|s| {
            s.parse::<T>()
                .map_err(|e| CliError::Usage(format!("--{flag}: {e}")))
        })
        .transpose()
}

/// The result of a mutating verb.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ChangeData {
    /// Full ULID.
    pub id: TicketId,
    /// Handle with `~`.
    pub handle: String,
    /// Title after the change.
    pub title: String,
    /// Ticket type.
    #[serde(rename = "type")]
    pub ty: TicketType,
    /// Category after the change.
    pub category: Category,
    /// Outcome, when done.
    pub outcome: Option<Outcome>,
    /// Priority.
    pub priority: Priority,
    /// Class of service.
    pub class: Class,
    /// Ids of the events written (empty when `already`).
    pub events: Vec<String>,
    /// The ledger commit, when one was made.
    pub commit: Option<String>,
    /// The reason of the `--no-changelog` exemption this close recorded, when it did.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub changelog_exempt: Option<String>,
}

impl From<&Applied> for ChangeData {
    fn from(a: &Applied) -> Self {
        let f = &a.ticket.front;
        Self {
            id: f.id,
            handle: a.handle.clone(),
            title: f.title.clone(),
            ty: f.ty,
            category: f.category,
            outcome: f.outcome,
            priority: f.priority,
            class: f.class,
            events: Ledger::event_strings(&a.events),
            commit: a.commit.map(|c| c.to_string()),
            changelog_exempt: None,
        }
    }
}

/// Wrap an [`Applied`] as the verb payload, carrying `already`.
pub(crate) fn payload(a: &Applied) -> gob_cli::Payload<ChangeData> {
    a.warnings.iter().cloned().fold(
        gob_cli::Payload::new(ChangeData::from(a)).with_already(a.already),
        gob_cli::Payload::with_warning,
    )
}

// frob:ticket 01M44C546DQRE4D11HHPM0HX6M
/// Verbs of this module, registered on the root in one place.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<write::New>()
        .register::<write::Update>()
        .register::<write::Link>()
        .register::<write::Unlink>()
        .register::<write::Comment>()
        .register::<write::Close>()
        .register::<write::Closeout>()
        .register::<write::DropTicket>()
        .register::<write::Reopen>()
        .register::<read::Show>()
        .register::<read::List>()
        .register::<read::Doable>()
        .register::<read::Brief>()
        .register::<triage_cmd::Accept>()
        .register::<triage_cmd::Decline>()
        .register::<triage_cmd::Snooze>()
        .register::<triage_cmd::Duplicate>()
        .register::<triage_cmd::InboxList>()
        .register::<proposals_cmd::List>()
        .register::<proposals_cmd::Decline>()
        .register::<proposals_accept::Accept>()
        .register::<fragment_cmd::Fragment>()
        .register::<branch_cmd::BranchInit>()
        .register::<migrate_cmd::Migrate>()
        .register::<reindex_cmd::Reindex>()
        // frob:ticket 01M3ZX88FHDWF9C082QZR1PXXA
        .register::<url_cmd::Url>()
        // frob:ticket 01M59VC5Y4HWJYV4KWSM02ESM8
        .register::<usage_cmd::Usage>()
        .register::<doctor_cmd::TicketDoctor>()
        .register::<merge_cmd::MergeDriver>()
}

#[cfg(test)]
mod tests {
    use super::freshness_footer;
    use crate::freshness::{FreshState, Freshness};

    fn view(state: FreshState, age_secs: Option<i64>) -> Freshness {
        Freshness {
            state,
            age_secs,
            notices: Vec::new(),
        }
    }

    // frob:ticket 01M5D5PZVVDVE6ZJ2Z9CERYYYA
    // frob:tests crates/frob/src/ticket/mod.rs::freshness_footer
    #[test]
    fn footer_names_stale_views_and_skips_fresh_ones() {
        assert_eq!(freshness_footer(None), None);
        assert_eq!(
            freshness_footer(Some(&view(FreshState::Fresh, Some(5)))),
            None
        );
        let line = freshness_footer(Some(&view(FreshState::Stale, Some(7200)))).expect("footer");
        assert!(line.starts_with("view stale (as of "), "{line}");
        let line = freshness_footer(Some(&view(FreshState::Unknown, None))).expect("footer");
        assert_eq!(line, "view unknown (never refreshed)");
    }
}

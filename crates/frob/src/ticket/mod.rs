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
pub mod read;
pub mod terminal_lease;
pub mod triage_cmd;
pub mod write;

use frob_ledger::model::{Category, Class, Outcome, Priority, TicketType};
use frob_ledger::{Applied, Ledger, LedgerError, TicketId};
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Context};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::workspace::{Located, config_refusal};

/// Open the ledger of the repository containing `ctx.cwd`.
pub(crate) fn open(ctx: &Context) -> Result<Ledger, CliError> {
    let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
    let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
    let ledger = Ledger::open(repo, cfg.ledger(), ctx.clock.clone());
    // frob:ticket 01M4FG552GZ9FMB000B76AS8XH
    crate::workspace::note_ledger_site(&ledger);
    Ok(ledger)
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
    ledger.resolve(input).map_err(cli_err)
}

/// A required positional ticket argument.
pub(crate) fn ticket_arg() -> Arg {
    Arg::new("ticket")
        .required(true)
        .value_name("TICKET")
        .help("Full ULID, ~handle or alias of the ticket")
}

/// An optional single-valued text flag.
pub(crate) fn text_flag(name: &'static str, help: &'static str) -> Arg {
    Arg::new(name).long(name).value_name("TEXT").help(help)
}

/// A repeatable text flag.
pub(crate) fn many_flag(name: &'static str, help: &'static str) -> Arg {
    text_flag(name, help).action(ArgAction::Append)
}

/// A flag restricted to the given spellings.
pub(crate) fn choice_flag(
    name: &'static str,
    names: &'static [&'static str],
    help: &'static str,
) -> Arg {
    Arg::new(name)
        .long(name)
        .value_name("VALUE")
        .value_parser(gob_cli::clap::builder::PossibleValuesParser::new(names))
        .help(help)
}

/// The text value of flag `name`.
pub(crate) fn get(m: &ArgMatches, name: &str) -> Option<String> {
    m.get_one::<String>(name).cloned()
}

/// Every value of repeatable flag `name`.
pub(crate) fn get_many(m: &ArgMatches, name: &str) -> Vec<String> {
    m.get_many::<String>(name)
        .map(|v| v.cloned().collect())
        .unwrap_or_default()
}

/// Parse the spelling of a validated choice flag.
pub(crate) fn get_parsed<T: std::str::FromStr>(
    m: &ArgMatches,
    name: &str,
) -> Result<Option<T>, CliError>
where
    T::Err: std::fmt::Display,
{
    get(m, name)
        .map(|s| {
            s.parse::<T>()
                .map_err(|e| CliError::Usage(format!("--{name}: {e}")))
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
        .register::<fragment_cmd::Fragment>()
        .register::<branch_cmd::BranchInit>()
        .register::<migrate_cmd::Migrate>()
        .register::<doctor_cmd::TicketDoctor>()
        .register::<merge_cmd::MergeDriver>()
}

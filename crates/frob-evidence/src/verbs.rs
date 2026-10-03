//! The `ticket evidence add`, `ticket evidence list` and `ticket evidence fetch` verbs.

use frob_ledger::TicketId;
use gob_cli::clap::{Arg, ArgAction, ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::EvidenceError;
use crate::events::{self, StoredEvidence};
use crate::provider;
use crate::record::{EvidenceRecord, Provider, Status};
use crate::store::Fetched;
use crate::workspace::Workspace;

fn cli(e: impl Into<EvidenceError>) -> CliError {
    e.into().into_cli()
}

fn resolve(ws: &Workspace, input: &str) -> Result<TicketId, CliError> {
    ws.ledger.resolve(input).map_err(cli)
}

/// Output of `ticket evidence add`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AddData {
    /// Full ULID of the ticket.
    pub id: TicketId,
    /// Its handle with `~`.
    pub handle: String,
    /// The new event's id.
    pub event: String,
    /// The ledger commit holding it.
    pub commit: String,
    /// The record that was written.
    pub record: EvidenceRecord,
}

/// The `add` action: capture evidence with a provider and append it to a ticket.
#[derive(Debug, Clone)]
struct EvidenceAdd {
    ticket: String,
    provider: Provider,
    reference: String,
    accepts: Vec<usize>,
}

impl EvidenceAdd {
    fn run(&self, ctx: &Context) -> Result<Payload<AddData>, CliError> {
        let ws = Workspace::open(&ctx.cwd).map_err(EvidenceError::into_cli)?;
        let id = resolve(&ws, &self.ticket)?;
        let view = ws.ledger.show(id).map_err(cli)?;
        let criteria = view.ticket.front.acceptance.len();
        if let Some(bad) = self.accepts.iter().find(|n| **n == 0 || **n > criteria) {
            return Err(cli(EvidenceError::BadAccepts(format!(
                "--accepts {bad} but {} has {criteria} acceptance criteria (1-based)",
                view.summary.handle
            ))));
        }
        let record =
            provider::capture(&ws, self.provider, &self.reference, &self.accepts).map_err(cli)?;
        let appended = events::append(&ws.ledger, id, &record).map_err(cli)?;
        let payload = Payload::new(AddData {
            id,
            handle: view.summary.handle,
            event: appended.event.to_string(),
            commit: appended.commit.to_string(),
            record: record.clone(),
        });
        Ok(with_record_warnings(payload, &record))
    }
}

/// Attach the warnings a non-binding `record` deserves, for any evidence target.
pub fn with_record_warnings<T>(mut payload: Payload<T>, record: &EvidenceRecord) -> Payload<T> {
    if record.passed == Some(false) {
        payload = payload.with_warning(
            "the measured process failed; this record does not satisfy the close guard",
        );
    }
    if record.status == Status::Unmeasured {
        payload = payload.with_warning("the measurement could not be taken (timeout or signal)");
    }
    payload
}

/// One row of `ticket evidence list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Listed {
    /// 1-based position, the argument of `fetch`.
    pub index: usize,
    /// The status after checking the blob is still there.
    pub effective_status: Status,
    /// The event and record.
    #[serde(flatten)]
    pub stored: StoredEvidence,
}

/// Output of `ticket evidence list`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ListData {
    /// Number of records.
    pub count: usize,
    /// The records, oldest first.
    pub records: Vec<Listed>,
}

/// The `list` action: the evidence records of a ticket with their effective status.
#[derive(Debug, Clone)]
struct EvidenceList {
    ticket: String,
}

impl EvidenceList {
    fn run(&self, ctx: &Context) -> Result<Payload<ListData>, CliError> {
        let ws = Workspace::open(&ctx.cwd).map_err(EvidenceError::into_cli)?;
        let id = resolve(&ws, &self.ticket)?;
        let records: Vec<Listed> = events::list(&ws.ledger, id)
            .map_err(cli)?
            .into_iter()
            .enumerate()
            .map(|(i, stored)| Listed {
                index: i + 1,
                effective_status: stored.record.effective_status(&ws.store),
                stored,
            })
            .collect();
        Ok(Payload::new(ListData {
            count: records.len(),
            records,
        }))
    }
}

/// Output of `ticket evidence fetch`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct FetchData {
    /// 1-based index that was fetched.
    pub index: usize,
    /// Measured when the blob was retrieved and its hash verified, else Unmeasured.
    pub status: Status,
    /// The blob URI, when the transcript is not inline.
    pub uri: Option<String>,
    /// The recorded digest.
    pub digest: String,
    /// The transcript text, when there is one.
    pub content: Option<String>,
    /// Why the record is unmeasured, when it is.
    pub reason: Option<String>,
}

/// The `fetch` action: one evidence blob, hash verified, Unmeasured when it is gone.
#[derive(Debug, Clone)]
struct EvidenceFetch {
    ticket: String,
    index: usize,
}

impl EvidenceFetch {
    fn run(&self, ctx: &Context) -> Result<Payload<FetchData>, CliError> {
        let ws = Workspace::open(&ctx.cwd).map_err(EvidenceError::into_cli)?;
        let id = resolve(&ws, &self.ticket)?;
        let all = events::list(&ws.ledger, id).map_err(cli)?;
        let stored = self
            .index
            .checked_sub(1)
            .and_then(|i| all.get(i))
            .ok_or_else(|| {
                cli(EvidenceError::BadIndex(format!(
                    "{} has {} evidence record(s); index {} is out of range (1-based)",
                    self.ticket,
                    all.len(),
                    self.index
                )))
            })?;
        let r = &stored.record;
        let (status, content, reason) = match (&r.inline, &r.uri) {
            (Some(text), _) => {
                if crate::record::digest_hex(text.as_bytes()) == r.digest {
                    (Status::Measured, Some(text.clone()), None)
                } else {
                    (
                        Status::Unmeasured,
                        None,
                        Some("inline text does not match its digest".to_owned()),
                    )
                }
            }
            (None, Some(uri)) => match ws.store.fetch_verified(uri, &r.digest) {
                Fetched::Found(bytes) => (
                    Status::Measured,
                    Some(String::from_utf8_lossy(&bytes).into_owned()),
                    None,
                ),
                Fetched::Unmeasured { reason, .. } => (Status::Unmeasured, None, Some(reason)),
            },
            (None, None) => (r.status, None, None),
        };
        Ok(Payload::new(FetchData {
            index: self.index,
            status,
            uri: r.uri.clone(),
            digest: r.digest.clone(),
            content,
            reason,
        }))
    }
}

fn flag(m: &ArgMatches, name: &str) -> Option<String> {
    m.get_one::<String>(name).cloned()
}

fn ticket_arg() -> Arg {
    Arg::new("ticket")
        .required(true)
        .value_name("TICKET")
        .help("Full ULID, ~handle or alias of the ticket")
}

/// The `--provider`, `--ref` and `--accepts` flags every evidence-capturing verb shares.
pub fn capture_args(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
    cmd.arg(
        Arg::new("provider")
            .long("provider")
            .required(true)
            .value_name("PROVIDER")
            .value_parser(PossibleValuesParser::new(Provider::NAMES))
            .help("Measurer: nextest, command or file"),
    )
    .arg(
        Arg::new("ref")
            .long("ref")
            .required(true)
            .value_name("REF")
            .help("Nextest filter args, the command line, or the file path"),
    )
    .arg(
        Arg::new("accepts")
            .long("accepts")
            .value_name("N")
            .value_parser(gob_cli::clap::value_parser!(usize))
            .action(ArgAction::Append)
            .help("1-based acceptance criterion this evidence is offered for (repeatable)"),
    )
}

/// The parsed capture flags of [`capture_args`].
#[derive(Debug, Clone)]
pub struct CaptureArgs {
    /// The measurer.
    pub provider: Provider,
    /// Nextest filter args, the command line, or the file path.
    pub reference: String,
    /// 1-based criteria the evidence is offered for.
    pub accepts: Vec<usize>,
}

impl CaptureArgs {
    /// Read the flags of [`capture_args`] from `m`.
    ///
    /// # Errors
    ///
    /// [`CliError::Usage`] when a required flag is missing or the provider is unknown.
    pub fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let provider = flag(m, "provider")
            .ok_or_else(|| CliError::Usage("add needs --provider".to_owned()))?
            .parse::<Provider>()
            .map_err(|e| CliError::Usage(e.to_string()))?;
        let reference =
            flag(m, "ref").ok_or_else(|| CliError::Usage("add needs --ref".to_owned()))?;
        Ok(Self {
            provider,
            reference,
            accepts: m
                .get_many::<usize>("accepts")
                .map(|v| v.copied().collect())
                .unwrap_or_default(),
        })
    }
}

/// Capture evidence with a provider and append it to a ticket: `ticket evidence add <ticket>`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket evidence add",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct AddVerb(EvidenceAdd);

impl Command for AddVerb {
    type Data = AddData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        capture_args(cmd.arg(ticket_arg()))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let CaptureArgs {
            provider,
            reference,
            accepts,
        } = CaptureArgs::from_matches(m)?;
        Ok(Self(EvidenceAdd {
            ticket: flag(m, "ticket").unwrap_or_default(),
            provider,
            reference,
            accepts,
        }))
    }

    fn run(&self, ctx: &Context) -> Outcome<AddData> {
        self.0.run(ctx)
    }
}

/// List the evidence records of a ticket with their effective status: `ticket evidence list <ticket>`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket evidence list",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ListVerb(EvidenceList);

impl Command for ListVerb {
    type Data = ListData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg())
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self(EvidenceList {
            ticket: flag(m, "ticket").unwrap_or_default(),
        }))
    }

    fn run(&self, ctx: &Context) -> Outcome<ListData> {
        self.0.run(ctx)
    }
}

/// Fetch one evidence blob, hash verified: `ticket evidence fetch <ticket> <index>`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ticket evidence fetch",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct FetchVerb(EvidenceFetch);

impl Command for FetchVerb {
    type Data = FetchData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(ticket_arg()).arg(
            Arg::new("index")
                .required(true)
                .value_name("INDEX")
                .value_parser(gob_cli::clap::value_parser!(usize))
                .help("1-based position from `ticket evidence list`"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self(EvidenceFetch {
            ticket: flag(m, "ticket").unwrap_or_default(),
            index: m
                .get_one::<usize>("index")
                .copied()
                .ok_or_else(|| CliError::Usage("fetch needs an INDEX".to_owned()))?,
        }))
    }

    fn run(&self, ctx: &Context) -> Outcome<FetchData> {
        self.0.run(ctx)
    }
}

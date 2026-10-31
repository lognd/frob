//! The `ticket evidence add`, `ticket evidence list` and `ticket evidence fetch` verbs.

use frob_ledger::TicketId;
use gob_cli::clap::{ArgAction, ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::attestation::{self, Presence, Request};
use crate::error::EvidenceError;
use crate::events::{self, StoredEvidence};
use crate::provider;
use crate::record::{CoverageStatus, EvidenceRecord, Provider, Status};
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
    args: CaptureArgs,
}

impl EvidenceAdd {
    fn run(&self, ctx: &Context) -> Result<Payload<AddData>, CliError> {
        let ws = Workspace::open(&ctx.cwd, ctx.clock.clone()).map_err(EvidenceError::into_cli)?;
        frob_lease::heartbeat(&ctx.cwd, ctx.clock.clone());
        let id = resolve(&ws, &self.ticket)?;
        let view = ws.ledger.show(id).map_err(cli)?;
        let criteria = view.ticket.front.acceptance.len();
        if let Some(bad) = self
            .args
            .accepts
            .iter()
            .find(|n| **n == 0 || **n > criteria)
        {
            return Err(cli(EvidenceError::BadAccepts(format!(
                "--accepts {bad} but {} has {criteria} acceptance criteria (1-based)",
                view.summary.handle
            ))));
        }
        let record = self.args.capture(&ws, &Presence::detect()).map_err(cli)?;
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

/// A ref matching more tests than this draws a warning from `evidence add`.
pub const WIDE_REF_TESTS: u64 = 50;

/// Attach the warnings a non-binding `record` deserves, for any evidence target.
pub fn with_record_warnings<T>(mut payload: Payload<T>, record: &EvidenceRecord) -> Payload<T> {
    if record.passed == Some(false) {
        payload = payload.with_warning(
            "the measured process failed; this record does not satisfy the close guard",
        );
    }
    if let Some(label) = record.attestation_label() {
        payload = payload.with_warning(format!(
            "this is an attestation, not a tool measurement: {label}"
        ));
    }
    // frob:ticket 01M4NZCSJWT2XSEZQBVPNMA6HM
    if record.tests_executed() > WIDE_REF_TESTS {
        payload = payload.with_warning(format!(
            "this ref matched {} tests (more than {WIDE_REF_TESTS}); bind the criterion to an exact test name, e.g. -E 'test(=EXACT_TEST_NAME)'",
            record.tests_executed()
        ));
    }
    if record.status == Status::Unmeasured {
        payload = payload.with_warning("the measurement could not be taken (timeout or signal)");
    }
    // frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
    if let Some(cov) = &record.coverage {
        let why = cov.reason.as_deref().unwrap_or("no reason given");
        match cov.status {
            CoverageStatus::Measured => {}
            CoverageStatus::NotRun => {
                payload =
                    payload.with_warning(format!("coverage not run for {}: {why}", cov.language));
            }
            CoverageStatus::MissingReport => {
                payload = payload.with_warning(format!(
                    "coverage report missing for {}: {why}; COV004 will flag it",
                    cov.language
                ));
            }
        }
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
    /// `[attested by X: "statement"]` (escaped) when the record is an attestation, so it never reads as a measurement.
    pub label: Option<String>,
    /// The criteria the record is offered for, renumbered to the ticket's acceptance list now.
    pub current_accepts: Vec<usize>,
    /// The recorded criterion positions whose criteria were since removed.
    pub removed_accepts: Vec<usize>,
    /// The event and record.
    #[serde(flatten)]
    pub stored: StoredEvidence,
}

impl Listed {
    /// Row `index` for `stored` with criteria mapped through `now` (`None` = removed since recorded).
    // frob:ticket 01M4061MSKNEMGBJ7C8AWA71KG
    pub fn new(
        index: usize,
        effective_status: Status,
        stored: StoredEvidence,
        now: &[Option<usize>],
    ) -> Self {
        let current_accepts = now.iter().flatten().copied().collect();
        let removed_accepts = stored
            .record
            .accepts
            .iter()
            .zip(now)
            .filter(|(_, n)| n.is_none())
            .map(|(a, _)| *a)
            .collect();
        Self {
            index,
            effective_status,
            label: stored.record.attestation_label(),
            current_accepts,
            removed_accepts,
            stored,
        }
    }
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
        let ws = Workspace::open(&ctx.cwd, ctx.clock.clone()).map_err(EvidenceError::into_cli)?;
        let id = resolve(&ws, &self.ticket)?;
        let mut records = Vec::new();
        for (i, stored) in events::list(&ws.ledger, id)
            .map_err(cli)?
            .into_iter()
            .enumerate()
        {
            let event: frob_ledger::EventId = stored
                .event
                .parse()
                .map_err(|e: frob_ledger::id::ParseIdError| CliError::internal(e))?;
            let now = ws
                .ledger
                .criteria_now(id, event, &stored.record.accepts)
                .map_err(|e| cli(EvidenceError::from(e)))?;
            let status = stored.record.effective_status(&ws.store);
            tracing::debug!(ticket = %id, evidence = %stored.event, ?now, "evidence criteria mapped");
            records.push(Listed::new(i + 1, status, stored, &now));
        }
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
        let ws = Workspace::open(&ctx.cwd, ctx.clock.clone()).map_err(EvidenceError::into_cli)?;
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

/// The positional ticket handle every evidence verb takes.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct TicketArg {
    #[arg(
        required = true,
        value_name = "TICKET",
        help = "Full ULID, ~handle or alias of the ticket"
    )]
    ticket: String,
}

/// Help text of `--provider`, listing the measurers.
fn provider_help() -> String {
    format!(
        "Measurer: {} (a person's statement; needs a terminal and a listed attester)",
        Provider::expected()
    )
}

/// The `--provider`, `--ref` and `--accepts` flags every evidence-capturing verb shares.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
pub struct CaptureFlags {
    #[arg(
        long,
        required = true,
        value_name = "PROVIDER",
        value_parser = PossibleValuesParser::new(Provider::NAMES),
        help = provider_help()
    )]
    provider: String,
    #[arg(
        long = "ref",
        value_name = "REF",
        allow_hyphen_values = true,
        help = "Nextest filter args, pytest arguments (node ids), vitest or jest arguments (test files), dotnet arguments (fully qualified test ids, an optional project path, and the flags --no-build, --no-restore and -c or --configuration <name>), unity arguments (EditMode or PlayMode, .asmdef paths and fully qualified test ids) or the command line (POSIX shell quoting, no shell run), or the file path (not for attestation)"
    )]
    reference: Option<String>,
    #[arg(
        long,
        value_name = "TEXT",
        allow_hyphen_values = true,
        help = "Attestation only: the statement, taken whole"
    )]
    statement: Option<String>,
    #[arg(
        long = "fact",
        value_name = "FACT",
        action = ArgAction::Append,
        help = "Attestation only: an https URL, commit id or ticket handle the statement rests on (repeatable)"
    )]
    facts: Vec<String>,
    #[arg(
        long,
        value_name = "N",
        action = ArgAction::Append,
        help = "1-based acceptance criterion this evidence is offered for (repeatable)"
    )]
    accepts: Vec<usize>,
    // frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
    #[arg(
        long,
        help = "Also measure coverage with the language's coverage tool and merge it into the [coverage] report (test providers only)"
    )]
    coverage: bool,
}

/// The `--provider`, `--ref` and `--accepts` flags every evidence-capturing verb shares.
pub fn capture_args(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
    gob_cli::augment::<CaptureFlags>(cmd)
}

/// The parsed capture flags of [`capture_args`].
#[derive(Debug, Clone)]
pub struct CaptureArgs {
    /// The measurer.
    pub provider: Provider,
    /// Nextest filter args, pytest arguments, the command line, or the file path (empty for an attestation).
    pub reference: String,
    /// 1-based criteria the evidence is offered for.
    pub accepts: Vec<usize>,
    /// The attestation statement (attestation only).
    pub statement: Option<String>,
    /// The attestation facts (attestation only).
    pub facts: Vec<String>,
    // frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
    /// Measure coverage alongside the tests (test-runner providers only).
    pub coverage: bool,
}

impl CaptureArgs {
    /// Read the flags of [`capture_args`] from `m`.
    ///
    /// # Errors
    ///
    /// [`CliError::Usage`] when a required flag is missing or the provider is unknown.
    pub fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Self::from_flags(gob_cli::parse::<CaptureFlags>(m)?)
    }

    /// Validate parsed capture flags against the provider they select.
    ///
    /// # Errors
    ///
    /// [`CliError::Usage`] when the provider is unknown or the flags do not belong to it.
    pub fn from_flags(flags: CaptureFlags) -> Result<Self, CliError> {
        let provider = flags
            .provider
            .parse::<Provider>()
            .map_err(|e| CliError::Usage(e.to_string()))?;
        let CaptureFlags {
            reference,
            statement,
            facts,
            accepts,
            coverage,
            ..
        } = flags;
        // frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
        if coverage
            && matches!(
                provider,
                Provider::File | Provider::Attestation | Provider::Command
            )
        {
            return Err(CliError::Usage(
                "--coverage belongs to a test provider (nextest, pytest, vitest, jest, dotnet, unity)".to_owned(),
            ));
        }
        let attesting = provider == Provider::Attestation;
        if attesting && reference.is_some() {
            return Err(CliError::Usage(
                "an attestation takes --statement and --fact, not --ref".to_owned(),
            ));
        }
        if !attesting && (statement.is_some() || !facts.is_empty()) {
            return Err(CliError::Usage(
                "--statement and --fact belong to --provider attestation".to_owned(),
            ));
        }
        if !attesting && reference.is_none() {
            return Err(CliError::Usage("add needs --ref".to_owned()));
        }
        Ok(Self {
            provider,
            reference: reference.unwrap_or_default(),
            accepts,
            statement,
            facts,
            coverage,
        })
    }

    /// Capture the evidence these flags ask for; an attestation also needs `presence` to show a person.
    ///
    /// # Errors
    ///
    /// Whatever the provider or [`attestation::attest`] refuses with.
    pub fn capture(
        &self,
        ws: &Workspace,
        presence: &Presence,
    ) -> crate::error::Result<EvidenceRecord> {
        if self.provider == Provider::Attestation {
            // frob:ticket 01M5CW05SGKV3HDVCTTMAQT9TT
            let mut record = attestation::attest(
                ws,
                presence,
                &Request {
                    statement: self.statement.clone().unwrap_or_default(),
                    facts: self.facts.clone(),
                    accepts: self.accepts.clone(),
                },
            )?;
            record.head = crate::guard::head_of(ws.ledger.repo());
            return Ok(record);
        }
        provider::capture_with(
            ws,
            self.provider,
            &self.reference,
            &self.accepts,
            self.coverage,
        )
    }
}

/// The flags of `ticket evidence add`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct AddFlags {
    #[command(flatten)]
    ticket: TicketArg,
    #[command(flatten)]
    capture: CaptureFlags,
}

/// The flags of `ticket evidence fetch`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct FetchFlags {
    #[command(flatten)]
    ticket: TicketArg,
    #[arg(
        required = true,
        value_name = "INDEX",
        help = "1-based position from `ticket evidence list`"
    )]
    index: usize,
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
        gob_cli::augment::<AddFlags>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AddFlags>(m)?;
        Ok(Self(EvidenceAdd {
            ticket: a.ticket.ticket,
            args: CaptureArgs::from_flags(a.capture)?,
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
    read_only,
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ListVerb(EvidenceList);

impl Command for ListVerb {
    type Data = ListData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<TicketArg>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<TicketArg>(m)?;
        Ok(Self(EvidenceList { ticket: a.ticket }))
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
        gob_cli::augment::<FetchFlags>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<FetchFlags>(m)?;
        Ok(Self(EvidenceFetch {
            ticket: a.ticket.ticket,
            index: a.index,
        }))
    }

    fn run(&self, ctx: &Context) -> Outcome<FetchData> {
        self.0.run(ctx)
    }
}

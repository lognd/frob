//! The [`Command`] trait and its type-erased registration.

use clap::ArgMatches;
use gob_rules::Finding;
use schemars::JsonSchema;
use serde::Serialize;

use crate::context::Context;
use crate::error::{CliError, FindingsFailure, Outcome, clear_notes, take_notes};
use crate::meta::{CommandMeta, Described};

/// A verb: parse its flags, run, return typed data.
///
/// Derive [`Described`] with `#[derive(Command)]` for the metadata, implement
/// this trait for the behavior, and register it with
/// [`Cli::register`](crate::Cli::register).
pub trait Command: Described + Sized + 'static {
    /// The `data` payload type; its JSON schema backs `--schema`.
    type Data: Serialize + JsonSchema;

    /// Add this verb's own flags and positionals to its clap command.
    #[must_use]
    fn configure(cmd: clap::Command) -> clap::Command {
        cmd
    }

    /// Build the verb from its parsed flags.
    ///
    /// # Errors
    ///
    /// [`CliError::Usage`] when the flags are inconsistent in a way clap
    /// cannot express.
    fn from_matches(matches: &ArgMatches) -> Result<Self, CliError>;

    /// Execute against the resolved global flags.
    ///
    /// # Errors
    ///
    /// Any [`CliError`]; the root maps it to an exit code and an envelope.
    fn run(&self, ctx: &Context) -> Outcome<Self::Data>;
}

/// A verb result with the data already serialized.
#[derive(Debug)]
pub(crate) struct Erased {
    pub data: serde_json::Value,
    pub findings: Vec<Finding>,
    pub warnings: Vec<String>,
    pub already: bool,
    pub rendered: Option<Vec<String>>,
}

/// One registered verb with its type-erased entry points.
pub(crate) struct Registered {
    pub meta: &'static CommandMeta,
    pub configure: fn(clap::Command) -> clap::Command,
    pub run: fn(&ArgMatches, &Context) -> Result<Erased, CliError>,
    pub schema: fn() -> serde_json::Value,
}

impl Registered {
    /// Erase `C`: its flags, runner and schema become plain function pointers.
    pub(crate) fn of<C: Command>() -> Self {
        Self {
            meta: &<C as Described>::META,
            configure: C::configure,
            run: |matches, ctx| {
                clear_notes();
                let verb = C::from_matches(matches)?;
                let payload = verb.run(ctx)?;
                let data = serde_json::to_value(&payload.data).map_err(CliError::internal)?;
                let mut warnings = payload.warnings;
                warnings.extend(take_notes());
                if data.get("ok") == Some(&serde_json::Value::Bool(false)) {
                    return Err(data_not_ok(C::META.verb, data, &payload.findings, warnings));
                }
                Ok(Erased {
                    data,
                    findings: payload.findings,
                    warnings,
                    already: payload.already,
                    rendered: payload.rendered,
                })
            },
            schema: || {
                serde_json::to_value(schemars::schema_for!(C::Data))
                    .unwrap_or_else(|e| unreachable!("schema values convert to JSON: {e}"))
            },
        }
    }
}

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
/// The failure for a verb whose own `data.ok` is false: the envelope `ok` may not contradict it (cli.md section 2).
///
/// Data, findings and warnings are kept; the exit is 1 like any other gate that found problems.
fn data_not_ok(
    verb: &str,
    data: serde_json::Value,
    findings: &[Finding],
    warnings: Vec<String>,
) -> CliError {
    let sources = gob_diagnostics::MemorySources::new();
    let registry = gob_rules::Registry::global();
    let records: Vec<_> = findings
        .iter()
        .map(|f| gob_diagnostics::FindingRecord::from_finding(f, &sources, registry))
        .collect();
    let detail = findings
        .iter()
        .map(|f| format!("{} {}", f.rule, f.message))
        .collect::<Vec<_>>()
        .join("\n");
    tracing::info!(
        verb,
        findings = records.len(),
        "data.ok is false; envelope ok follows"
    );
    CliError::Findings(Box::new(FindingsFailure {
        summary: format!("{verb} reports ok: false ({} finding(s))", records.len()),
        detail,
        data,
        findings: records,
        warnings,
    }))
}

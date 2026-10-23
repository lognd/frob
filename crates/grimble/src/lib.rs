//! The `grimble` product: a [`gob_product::Product`] impl plus its own verbs.
//!
//! [`cli`] assembles the root; `main` only runs it. The generic `check` (the `gob.sibling/1`
//! document) and `doctor` verbs come from `gob-product`; grimble adds [`ack`] (`grimble.lock`),
//! [`init`], [`fmt_cmd`] and [`exceptions`] and holds its own [`doctor`] rows. The built-in
//! `schema` verb comes from `gob-cli`. The `[compute]`, `[packs]`, `[check]` and `[perf]`
//! config tables register through `grimble-check` and `gob-check`. No frob crate is linked (the
//! boundary test in `tests/boundary.rs`).

// frob:ticket 01M47QSGHYD2EQ4552V1B4EEQZ
pub mod ack;
pub mod compile_cmd;
pub mod config_diff;
pub mod config_for;
pub mod doctor;
pub mod exceptions;
pub mod explain_cmd;
pub mod fmt_cmd;
pub mod init;
pub mod presence;
pub mod rule_cmd;
pub mod serve_mcp;
pub mod shrink_cmd;
pub mod status_cmd;
pub mod vet_cmd;
mod workspace;

use std::path::Path;

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{Cli, Context, Outcome};
use gob_product::{CheckOptions, Product, ProductRun};
use serde_json::Value;

/// Product name, also the config file stem (`grimble.toml`).
pub const PRODUCT: &str = "grimble";

/// The `check --summary` flag id and spelling.
const SUMMARY_FLAG: &str = "summary";

/// Replace the data of a finished `check` with `summary` when one was asked for.
///
/// The gate verdict, the exit code and the warnings are untouched; a gate failure keeps its
/// message and only its data is swapped, so `--summary` is as strict as the full run.
fn with_summary(outcome: Outcome<Value>, summary: Option<Value>) -> Outcome<Value> {
    let Some(summary) = summary else {
        return outcome;
    };
    tracing::debug!("check data replaced by the summary");
    match outcome {
        Ok(mut payload) => {
            payload.data = summary;
            Ok(payload)
        }
        Err(gob_cli::CliError::Gate {
            message, warnings, ..
        }) => Err(gob_cli::CliError::Gate {
            message,
            data: summary,
            warnings,
        }),
        Err(other) => Err(other),
    }
}

/// grimble as a [`Product`]: the generic verbs plus `ack`, `init`, `fmt` and `exceptions list`.
#[derive(Debug, Clone, Copy, Default)]
pub struct GrimbleProduct;

gob_product::register_commands!(GrimbleProduct);

impl Product for GrimbleProduct {
    const NAME: &'static str = PRODUCT;
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");
    const DOCTOR_SUMMARY: &'static str = "Report adapter fidelity per language, how each model file parses and the state of grimble.toml.";
    const REQUIRES_CONFIG: bool = false;

    type CheckData = Value;
    type Doctor = doctor::DoctorData;

    fn check(
        ctx: &Context,
        root: &Path,
        opts: &CheckOptions,
        matches: &ArgMatches,
    ) -> Outcome<Value> {
        // frob:ticket 01M4HEMDB8A1X1RQFNVJB1G32M
        let summarize = matches.get_flag(SUMMARY_FLAG);
        let run = grimble_check::run(
            root,
            &grimble_check::CheckOptions {
                only: opts.only.clone(),
                fail_on: opts.fail_on,
                base: opts.base.clone(),
                ticket_scope: opts.ticket_scope.clone(),
            },
        )
        .map(|run| {
            let document = grimble_check::sibling_document(&run);
            let summary = summarize.then(|| grimble_check::summary_document(&document));
            let mut warnings = run.warnings;
            // frob:ticket 01M406M2HX6Z6SEGM6HRPQKHAV
            if let Some(base) = opts.base.as_deref() {
                warnings.extend(vet_cmd::check_warnings(root, base));
            }
            (
                ProductRun {
                    report: run.report,
                    document,
                    warnings,
                },
                summary,
            )
        });
        let (run, summary) = match run {
            Ok((run, summary)) => (Ok(run), summary),
            Err(e) => (Err(e), None),
        };
        with_summary(gob_product::sibling_check(Self::NAME, ctx, run), summary)
    }

    fn configure_check(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_product::shared_flags(cmd).arg(
            Arg::new(SUMMARY_FLAG)
                .long(SUMMARY_FLAG)
                .action(ArgAction::SetTrue)
                .help("Print a compact summary (under 64 KB) instead of the whole document, in text and JSON mode alike"),
        )
    }

    fn doctor(_ctx: &Context, root: &Path, _matches: &ArgMatches) -> Outcome<doctor::DoctorData> {
        doctor::report(root)
    }

    fn register(cli: Cli) -> Cli {
        cli.register::<ack::Ack>()
            // frob:ticket 01M3ZX7ZD77ZW385N5B992NX3A
            .register::<explain_cmd::Explain>()
            .register::<init::Init>()
            .register::<fmt_cmd::Fmt>()
            .register::<compile_cmd::Compile>()
            // frob:ticket 01M3ZX7K04VN51PGCXT9DCYMWB
            .register::<config_for::ConfigFor>()
            .register::<exceptions::ExceptionsList>()
            // frob:ticket 01M406M2HX6Z6SEGM6HRPQKHAV
            .register::<vet_cmd::Vet>()
            // frob:ticket 01M5A5F8CN6EKHGV1C4QZCQZMP
            .register::<shrink_cmd::Shrink>()
            // frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67
            .register::<status_cmd::Status>()
            .register::<rule_cmd::RuleTest>()
            .register::<rule_cmd::RuleCheck>()
            .register::<rule_cmd::RuleCatalog>()
            .register::<rule_cmd::RuleFmt>()
            // frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
            .register::<rule_cmd::RuleNew>()
    }
}

/// The fully registered `grimble` command-line root.
pub fn cli() -> Cli {
    gob_product::cli::<GrimbleProduct>()
}

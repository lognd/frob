//! A product that declares only some of the shared check flags parses without a clap panic.

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, Context, Outcome, Payload, run_for_test};
use gob_product::{CheckOptions, Product, ProductRun};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

/// A product that borrows crunk's pipeline and adds one extra doctor row.
struct Partial;

#[derive(Serialize, JsonSchema)]
struct PartialDoctor {
    /// Marker row proving the product's own doctor data is rendered.
    demo: bool,
}

gob_product::register_commands!(Partial);

impl Product for Partial {
    const NAME: &'static str = "partial";
    const VERSION: &'static str = "0.0.0";
    const DOCTOR_SUMMARY: &'static str = "Report the demo state.";
    const REQUIRES_CONFIG: bool = true;
    type CheckData = Value;
    type Doctor = PartialDoctor;

    fn configure_check(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(gob_cli::clap::Arg::new("only").long("only"))
    }

    fn check(
        ctx: &Context,
        root: &Path,
        opts: &CheckOptions,
        _matches: &ArgMatches,
    ) -> Outcome<Value> {
        let run = crunk_check::run(
            root,
            &crunk_check::CheckOptions {
                only: opts.only.clone(),
                ..crunk_check::CheckOptions::default()
            },
        )
        .map(|run| {
            let document = crunk_check::sibling_document(&run);
            ProductRun {
                report: run.report,
                document,
                warnings: run.warnings,
            }
        });
        gob_product::sibling_check(Self::NAME, ctx, run)
    }

    fn doctor(_ctx: &Context, _root: &Path, _matches: &ArgMatches) -> Outcome<PartialDoctor> {
        Ok(Payload::new(PartialDoctor { demo: true }))
    }

    fn register(cli: Cli) -> Cli {
        cli
    }
}

// frob:ticket 01M6EZJ8XSWMZXRN5492B94WCN
// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn a_product_declaring_only_some_shared_flags_does_not_panic() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("partial.toml"), "").unwrap();
    let cli = gob_product::cli::<Partial>();
    let (code, out, _) = run_for_test(&cli, &["check", "--json"], dir.path());
    let env: serde_json::Value = serde_json::from_str(&out).unwrap_or_default();
    assert_eq!(code, 0, "{env}");
}

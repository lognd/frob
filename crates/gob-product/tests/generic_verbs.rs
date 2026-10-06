//! A product implemented here gets `check`, `doctor` and the no-config guard with no extra code.

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, Context, Outcome, Payload, run_for_test};
use gob_product::{CheckOptions, Product, ProductRun};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

/// A product that borrows crunk's pipeline and adds one extra doctor row.
struct Demo;

#[derive(Serialize, JsonSchema)]
struct DemoDoctor {
    /// Marker row proving the product's own doctor data is rendered.
    demo: bool,
}

gob_product::register_commands!(Demo);

impl Product for Demo {
    const NAME: &'static str = "demo";
    const VERSION: &'static str = "0.0.0";
    const DOCTOR_SUMMARY: &'static str = "Report the demo state.";
    const REQUIRES_CONFIG: bool = true;
    type CheckData = Value;
    type Doctor = DemoDoctor;

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

    fn doctor(_ctx: &Context, _root: &Path, _matches: &ArgMatches) -> Outcome<DemoDoctor> {
        Ok(Payload::new(DemoDoctor { demo: true }))
    }

    fn register(cli: Cli) -> Cli {
        cli
    }
}

fn run(dir: &Path, args: &[&str]) -> (i32, serde_json::Value) {
    let cli = gob_product::cli::<Demo>();
    let (code, out, _) = run_for_test(&cli, args, dir);
    (code, serde_json::from_str(&out).unwrap_or_default())
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn a_test_product_gets_check_with_no_extra_code() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("demo.toml"), "").unwrap();
    let (code, env) = run(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["data"]["schema_version"], "gob.sibling/1");
}

// frob:tests crates/gob-product/src/doctor.rs::Doctor
#[test]
fn a_test_product_gets_doctor_with_its_own_rows_and_no_config_needed() {
    let dir = tempfile::tempdir().unwrap();
    let (code, env) = run(dir.path(), &["doctor", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["data"]["demo"], true);
}

// frob:tests crates/gob-product/src/workspace.rs::require_config
#[test]
fn the_guard_refuses_check_without_the_product_config_naming_the_file() {
    let dir = tempfile::tempdir().unwrap();
    let (code, env) = run(dir.path(), &["check", "--json"]);
    assert_eq!(code, 3, "{env}");
    assert_eq!(env["error"]["code"], "E-NO-CONFIG");
    assert!(
        env["error"]["remedy"]
            .as_str()
            .unwrap()
            .contains("demo.toml")
    );
}

// frob:tests crates/gob-product/src/lib.rs::register_commands
#[test]
fn registered_commands_list_the_generic_verbs_under_the_product() {
    let verbs: Vec<_> = gob_cli::all_commands()
        .filter(|m| m.product == "demo")
        .map(|m| m.verb)
        .collect();
    assert_eq!(verbs, ["check", "doctor"]);
}

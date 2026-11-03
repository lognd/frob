//! The small public helpers of a product front end: root discovery, error mapping and flag wiring.

use std::path::Path;

use gob_check::CheckError;
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Context, ExitCode, Outcome, Payload, run_for_test};
use gob_config::ConfigError;
use gob_product::workspace::{check_error, config_refusal, locate_root};
use gob_product::{CheckOptions, Product, shared_flags, sibling_check};
use serde_json::Value;

/// A product whose `check` always fails with an unknown `--only` name.
struct Odd;

gob_product::register_commands!(Odd);

impl Product for Odd {
    const NAME: &'static str = "odd";
    const VERSION: &'static str = "0.0.0";
    const DOCTOR_SUMMARY: &'static str = "Report the odd state.";
    const REQUIRES_CONFIG: bool = false;
    type CheckData = Value;
    type Doctor = Value;

    fn check(
        ctx: &Context,
        _root: &Path,
        _opts: &CheckOptions,
        _matches: &ArgMatches,
    ) -> Outcome<Value> {
        sibling_check(
            Self::NAME,
            ctx,
            Err(CheckError::UnknownFamily("zzz".to_owned())),
        )
    }

    fn doctor(_ctx: &Context, _root: &Path, _matches: &ArgMatches) -> Outcome<Value> {
        Ok(Payload::new(Value::Null))
    }
}

#[test]
fn a_root_is_the_nearest_ancestor_with_the_config_or_a_git_dir() {
    // frob:tests crates/gob-product/src/workspace.rs::locate_root
    // frob:tests crates/gob-product/src/product.rs::Product.locate_root
    // frob:tests crates/gob-product/src/product.rs::Product.has_config
    let dir = tempfile::tempdir().unwrap();
    let nested = dir.path().join("a/b");
    std::fs::create_dir_all(&nested).unwrap();
    std::fs::write(dir.path().join("odd.toml"), "").unwrap();
    assert_eq!(locate_root("odd", &nested), dir.path());
    assert_eq!(<Odd as Product>::locate_root(&nested), dir.path());
    assert!(<Odd as Product>::has_config(dir.path()));
    assert!(!<Odd as Product>::has_config(&nested));
    assert_eq!(locate_root("other", &nested), nested);
}

#[test]
fn a_config_failure_is_a_refusal_naming_the_file() {
    // frob:tests crates/gob-product/src/workspace.rs::config_refusal
    let e = ConfigError::Invalid {
        table: "t".to_owned(),
        message: "bad".to_owned(),
    };
    let err = config_refusal("odd", &e);
    assert_eq!(err.exit_code(), ExitCode::Refused);
    assert!(err.to_string().contains("bad"), "{err}");
}

#[test]
fn an_unknown_family_is_a_usage_error() {
    // frob:tests crates/gob-product/src/workspace.rs::check_error
    let usage = check_error("odd", CheckError::UnknownFamily("zzz".to_owned()));
    assert!(matches!(usage, CliError::Usage(_)));
}

#[test]
fn a_config_failure_is_a_refused_exit() {
    // frob:tests crates/gob-product/src/workspace.rs::check_error
    let cfg = check_error(
        "odd",
        CheckError::Config(ConfigError::Invalid {
            table: "t".to_owned(),
            message: "bad".to_owned(),
        }),
    );
    assert_eq!(cfg.exit_code(), ExitCode::Refused);
}

#[test]
fn any_other_pipeline_failure_is_an_internal_exit() {
    // frob:tests crates/gob-product/src/workspace.rs::check_error
    let other = check_error("odd", CheckError::NoLedger("x".to_owned()));
    assert_eq!(other.exit_code(), ExitCode::Internal);
}

#[test]
fn a_failed_pipeline_is_a_usage_exit_through_sibling_check() {
    // frob:tests crates/gob-product/src/check.rs::sibling_check
    let dir = tempfile::tempdir().unwrap();
    let cli = gob_product::cli::<Odd>();
    let (code, out, err) = run_for_test(&cli, &["check", "--only", "zzz"], dir.path());
    assert_eq!(code, 2, "{out}{err}");
    assert!(format!("{out}{err}").contains("zzz"), "{out}{err}");
}

#[test]
fn the_default_flag_hooks_add_the_shared_check_flags_and_leave_doctor_alone() {
    // frob:tests crates/gob-product/src/check.rs::shared_flags
    // frob:tests crates/gob-product/src/product.rs::Product.configure_check
    // frob:tests crates/gob-product/src/product.rs::Product.configure_doctor
    let bare = ClapCommand::new("check");
    let shared = shared_flags(bare.clone());
    assert!(shared.get_arguments().any(|a| a.get_id() == "only"));
    let via_product = <Odd as Product>::configure_check(bare.clone());
    assert_eq!(
        via_product.get_arguments().count(),
        shared.get_arguments().count()
    );
    assert_eq!(
        <Odd as Product>::configure_doctor(bare)
            .get_arguments()
            .count(),
        0
    );
}

#[test]
fn a_product_doctor_is_called_with_its_matches() {
    // frob:tests crates/gob-product/src/product.rs::Product.doctor
    let dir = tempfile::tempdir().unwrap();
    let cli = gob_product::cli::<Odd>();
    let (code, out, err) = run_for_test(&cli, &["doctor", "--json"], dir.path());
    assert_eq!(code, 0, "{err}");
    assert!(out.contains("\"ok\""), "{out}");
}

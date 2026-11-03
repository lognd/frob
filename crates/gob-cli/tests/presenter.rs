//! Presenter hooks and startup failures: text-only extras that never change an exit code.

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, CliError, Command, Context, Outcome, Payload, Presenter, run_for_test};

/// Succeed with a number.
#[derive(Debug, Default, Command)]
#[command(verb = "num", product = "dummy", idempotent = true, exits(ok))]
struct NumCmd;

impl Command for NumCmd {
    type Data = u32;
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, _: &Context) -> Outcome<u32> {
        Ok(Payload::new(7))
    }
}

/// Always fail.
#[derive(Debug, Default, Command)]
#[command(verb = "boom", product = "dummy", exits(ok, internal))]
struct BoomCmd;

impl Command for BoomCmd {
    type Data = ();
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, _: &Context) -> Outcome<()> {
        Err(CliError::internal("boom"))
    }
}

fn cli() -> Cli {
    Cli::new("dummy", "1.0.0")
        .register::<NumCmd>()
        .register::<BoomCmd>()
        .with_presenter(Presenter {
            next_step: |verb, data, _| Some(format!("next after {verb}: {data}")),
            failure_help: |_| Some("see the docs".to_owned()),
        })
}

// frob:tests crates/gob-cli/src/cli.rs::Cli.with_presenter
#[test]
fn the_presenter_adds_a_next_step_to_text_success_only() {
    let cwd = std::env::temp_dir();
    let (exit, out, _) = run_for_test(&cli(), &["--text", "num"], &cwd);
    assert_eq!(exit, 0);
    assert!(out.contains("next after num: 7"), "{out}");
    let (_, json, _) = run_for_test(&cli(), &["--json", "num"], &cwd);
    assert!(!json.contains("next after"), "{json}");
}

// frob:tests crates/gob-cli/src/cli.rs::Cli.with_presenter
#[test]
fn the_presenter_adds_failure_help_without_changing_the_exit_code() {
    let (exit, _, err) = run_for_test(&cli(), &["--text", "boom"], &std::env::temp_dir());
    assert_eq!(exit, 4);
    assert!(err.contains("see the docs"), "{err}");
}

// frob:tests crates/gob-cli/src/cli.rs::Cli.fail_startup
#[test]
fn a_startup_failure_exits_four() {
    assert_eq!(cli().fail_startup("could not start"), 4);
}

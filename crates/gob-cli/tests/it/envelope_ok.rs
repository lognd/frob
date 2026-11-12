//! The envelope `ok` never contradicts a verb's own `data.ok`, and queued notices reach `warnings`.

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, CliError, Command, Context, Outcome, Payload, run_for_test};
use schemars::JsonSchema;
use serde::Serialize;

#[derive(Serialize, JsonSchema)]
struct Report {
    ok: bool,
}

/// Report a failed self-check inside an otherwise normal result.
#[derive(Debug, Command)]
#[command(verb = "bad", product = "dummy", exits(ok, negative))]
struct BadCmd;

impl Command for BadCmd {
    type Data = Report;
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, _: &Context) -> Outcome<Report> {
        Payload::note("queued from a helper");
        Ok(Payload::new(Report { ok: false }).with_warning("direct"))
    }
}

/// Report a passing self-check and queue the same notice twice.
#[derive(Debug, Command)]
#[command(verb = "good", product = "dummy", exits(ok))]
struct GoodCmd;

impl Command for GoodCmd {
    type Data = Report;
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, _: &Context) -> Outcome<Report> {
        Payload::note("twice");
        Payload::note("twice");
        Ok(Payload::new(Report { ok: true }))
    }
}

fn run(args: &[&str]) -> (i32, serde_json::Value, String) {
    let cli = Cli::new("dummy", "1.0.0")
        .register::<BadCmd>()
        .register::<GoodCmd>();
    let (exit, out, err) = run_for_test(&cli, args, &std::env::temp_dir());
    (exit, serde_json::from_str(&out).unwrap_or_default(), err)
}

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
// frob:tests crates/gob-cli/src/command.rs::data_not_ok
#[test]
fn data_ok_false_makes_the_envelope_not_ok_and_exits_one() {
    let (exit, v, _) = run(&["bad"]);
    assert_eq!(exit, 1);
    assert_eq!(v["ok"], false);
    assert_eq!(v["data"]["ok"], false, "data is kept");
    assert_eq!(v["error"]["code"], "E-NEGATIVE");
    assert_eq!(
        v["warnings"],
        serde_json::json!(["direct", "queued from a helper"])
    );
}

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
// frob:tests crates/gob-cli/src/error.rs::note
#[test]
fn data_ok_true_stays_ok_and_notices_are_deduplicated() {
    let (exit, v, _) = run(&["good"]);
    assert_eq!(exit, 0);
    assert_eq!(v["ok"], true);
    assert_eq!(v["warnings"], serde_json::json!(["twice"]));
}

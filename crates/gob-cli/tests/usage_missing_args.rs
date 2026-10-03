//! Usage errors are built from clap's structured error and name every argument involved.

// frob:ticket 01M40FXV4AB47ASH79KJNF3JFH

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{Cli, CliError, Command, Context, Outcome, Payload, run_for_test};

/// Take two required options and a restricted one.
#[derive(Debug, Command)]
#[command(verb = "grp put", product = "usagetest", exits(ok, usage))]
struct PutCmd;

impl Command for PutCmd {
    type Data = ();

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("provider")
                .long("provider")
                .required(true)
                .action(ArgAction::Set),
        )
        .arg(
            Arg::new("ref")
                .long("ref")
                .required(true)
                .action(ArgAction::Set),
        )
        .arg(
            Arg::new("mode")
                .long("mode")
                .action(ArgAction::Set)
                .value_parser(["fast", "slow"]),
        )
    }

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, _: &Context) -> Outcome<()> {
        Ok(Payload::new(()))
    }
}

/// Run the dummy product and return the error object of the envelope.
fn failure(args: &[&str]) -> serde_json::Value {
    let cli = Cli::new("usagetest", "1.0.0").register::<PutCmd>();
    let (exit, out, _) = run_for_test(&cli, args, &std::env::temp_dir());
    assert_eq!(exit, 2, "{out}");
    let v: serde_json::Value = serde_json::from_str(&out).expect("json envelope");
    v["error"].clone()
}

// frob:tests crates/gob-cli/src/cli.rs::usage_parts
#[test]
fn missing_required_arguments_are_all_named() {
    let e = failure(&["grp", "put"]);
    let msg = e["message"].as_str().unwrap();
    assert!(msg.contains("--provider") && msg.contains("--ref"), "{msg}");
    assert!(!msg.contains('\n'), "{msg}");
    let remedy = e["remedy"].as_str().unwrap();
    assert!(remedy.contains("usage: usagetest grp put"), "{remedy}");
}

// frob:tests crates/gob-cli/src/cli.rs::usage_parts
#[test]
fn unknown_flag_carries_a_did_you_mean() {
    let e = failure(&["grp", "put", "--provder", "x"]);
    assert!(e["message"].as_str().unwrap().contains("'--provder'"));
    assert!(
        e["remedy"]
            .as_str()
            .unwrap()
            .contains("did you mean `--provider`")
    );
}

// frob:tests crates/gob-cli/src/cli.rs::usage_parts
#[test]
fn invalid_value_lists_the_valid_values() {
    let e = failure(&[
        "grp",
        "put",
        "--provider",
        "a",
        "--ref",
        "b",
        "--mode",
        "fats",
    ]);
    let msg = e["message"].as_str().unwrap();
    assert!(msg.contains("'fats'") && msg.contains("--mode"), "{msg}");
    assert!(msg.contains("valid values: fast, slow"), "{msg}");
    assert!(
        e["remedy"]
            .as_str()
            .unwrap()
            .contains("did you mean `fast`")
    );
}

// frob:tests crates/gob-cli/src/cli.rs::usage_parts
#[test]
fn missing_subcommand_is_one_complete_line() {
    let e = failure(&["grp"]);
    let msg = e["message"].as_str().unwrap();
    assert!(!msg.is_empty() && !msg.contains('\n'), "{msg}");
    assert!(e["remedy"].as_str().unwrap().contains("usage:"), "{e}");
}

//! The root's contract with a dummy product: exit table, flags, rendering.

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{
    Cli, CliError, Command, Context, ExitCode, Outcome, Payload, Refusal, RefusalClass,
    all_commands, run_for_test,
};
use schemars::JsonSchema;
use serde::Serialize;

#[derive(Serialize, JsonSchema)]
struct Echo {
    cwd: String,
    json: bool,
    dry_run: bool,
    verbosity: u8,
}

/// Echo the resolved context.
#[derive(Debug, Default, Command)]
#[command(
    verb = "echo",
    product = "dummy",
    idempotent = true,
    dry_run,
    exits(ok, usage)
)]
struct EchoCmd;

impl Command for EchoCmd {
    type Data = Echo;
    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }
    fn run(&self, ctx: &Context) -> Outcome<Echo> {
        Ok(Payload::new(Echo {
            cwd: ctx.cwd.display().to_string(),
            json: ctx.json,
            dry_run: ctx.dry_run,
            verbosity: ctx.verbosity,
        })
        .with_already(true)
        .with_warning("careful"))
    }
}

/// Fail with the failure named by the argument.
#[derive(Debug, Command)]
#[command(
    verb = "fail",
    product = "dummy",
    exits(ok, negative, usage, refused, internal)
)]
struct FailCmd {
    kind: String,
}

impl Command for FailCmd {
    type Data = ();

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(Arg::new("kind").required(true).action(ArgAction::Set))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            kind: m.get_one::<String>("kind").cloned().unwrap_or_default(),
        })
    }

    fn run(&self, _: &Context) -> Outcome<()> {
        Err(match self.kind.as_str() {
            "negative" => CliError::Negative("no".into()),
            "usage" => CliError::Usage("bad input".into()),
            "wait" => Refusal::new("E-LEASE-HELD", RefusalClass::GuardRetryByWaiting, "held")
                .with_remedy("retry")
                .into(),
            _ => CliError::internal("boom"),
        })
    }
}

fn cli() -> Cli {
    Cli::new("dummy", "1.2.3")
        .register::<EchoCmd>()
        .register::<FailCmd>()
}

fn run(args: &[&str]) -> (i32, String, String) {
    run_for_test(&cli(), args, &std::env::temp_dir())
}

#[test]
fn success_envelope_carries_already_and_warnings() {
    let (exit, out, err) = run(&["echo", "--dry-run", "-vv"]);
    assert_eq!((exit, err.as_str()), (0, ""));
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert_eq!(v["ok"], true);
    assert_eq!(v["already"], true);
    assert_eq!(v["warnings"][0], "careful");
    assert_eq!(v["data"]["dry_run"], true);
    assert_eq!(v["data"]["verbosity"], 2);
    assert_eq!(
        v["data"]["json"], true,
        "json is forced when stdout is not a tty"
    );
}

#[test]
fn global_flags_work_before_and_after_the_verb() {
    let (e1, o1, _) = run(&["--format", "text", "echo"]);
    let (e2, o2, _) = run(&["echo", "--format", "text"]);
    assert_eq!((e1, e2), (0, 0));
    assert_eq!(o1, o2);
    assert!(o1.starts_with("echo: ok (already)\n"), "{o1}");
    assert!(o1.contains("warning: careful"));
}

#[test]
fn quiet_text_prints_nothing_on_success() {
    let (exit, out, err) = run(&["--text", "-q", "echo"]);
    assert_eq!((exit, out.as_str(), err.as_str()), (0, "", ""));
}

#[test]
fn cwd_flag_is_validated_and_applied() {
    let dir = std::env::temp_dir();
    let (exit, out, _) = run(&["--cwd", dir.to_str().unwrap(), "echo"]);
    assert_eq!(exit, 0);
    assert!(out.contains(dir.to_str().unwrap().trim_end_matches('/')));
    let (exit, _, _) = run(&["--cwd", "/definitely/not/here", "echo"]);
    assert_eq!(exit, 2);
}

#[test]
fn each_error_class_maps_to_its_exit_code() {
    for (kind, code) in [("negative", 1), ("usage", 2), ("wait", 3), ("bug", 4)] {
        let (exit, out, err) = run(&["fail", kind]);
        assert_eq!(exit, code, "{kind}");
        assert_eq!(err, "");
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert_eq!(v["ok"], false);
        assert_eq!(v["verb"], "fail");
    }
    let (_, out, _) = run(&["fail", "wait"]);
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert_eq!(v["error"]["retryable"], true);
    assert_eq!(v["error"]["remedy"], "retry");
}

#[test]
fn text_errors_go_to_stderr() {
    let (exit, out, err) = run(&["--text", "fail", "wait"]);
    assert_eq!(exit, 3);
    assert_eq!(out, "");
    assert!(err.starts_with("error[E-LEASE-HELD]: held"), "{err}");
    assert!(err.contains("remedy: retry"));
}

#[test]
fn missing_argument_and_unknown_flag_are_usage_errors() {
    assert_eq!(run(&["fail"]).0, 2);
    assert_eq!(run(&["echo", "--nope"]).0, 2);
    // No prefix abbreviation of long flags.
    assert_eq!(run(&["echo", "--dry"]).0, 2);
}

#[test]
fn help_and_version_exit_zero() {
    let (exit, out, _) = run(&["--help"]);
    assert_eq!(exit, 0);
    assert!(out.contains("echo"));
    let (exit, out, _) = run(&["--version"]);
    assert_eq!(exit, 0);
    assert!(out.contains("1.2.3"));
}

#[test]
fn schema_flag_describes_the_data_type() {
    let (exit, out, _) = run(&["--schema", "echo"]);
    assert_eq!(exit, 0);
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    assert!(v["properties"]["verbosity"].is_object());
}

#[test]
fn derive_registers_metadata() {
    let m = all_commands()
        .find(|m| m.product == "dummy" && m.verb == "echo")
        .unwrap();
    assert!(m.idempotent && m.dry_run);
    assert_eq!(m.summary, "Echo the resolved context.");
    assert_eq!(m.exits, &[ExitCode::Ok, ExitCode::Usage]);
    let f = all_commands().find(|m| m.verb == "fail").unwrap();
    assert!(!f.idempotent && !f.dry_run);
    assert_eq!(f.exits.len(), 5);
}

//! The `check` verb: flags in, [`grimble_check::run`] out, the sibling document as data.

use gob_check::FailOn;
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, ExitCode, Outcome, Payload};
use grimble_check::{CheckOptions, GrimbleRun, sibling_document};
use serde_json::{Value, json};

use crate::workspace::{check_error, locate_root};

/// Run the rules over the repository and print the `gob.sibling/1` document; exit 1 when the gate fails.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "check",
    product = "grimble",
    exits(ok, negative, usage, refused, internal)
)]
pub struct Check {
    only: Vec<String>,
    fail_on: Option<FailOn>,
    base: Option<String>,
    ticket_scope: Option<Vec<String>>,
}

/// One line per finding: `file:line:col: severity RULE message`.
fn lines_of(doc: &Value) -> Vec<String> {
    let text = |f: &Value, k: &str| f[k].as_str().unwrap_or_default().to_owned();
    doc["findings"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|f| {
            let place = match (f["file"].as_str(), f["line"].as_u64(), f["column"].as_u64()) {
                (Some(file), Some(l), Some(c)) => format!("{file}:{l}:{c}: "),
                (Some(file), _, _) => format!("{file}: "),
                _ => String::new(),
            };
            format!(
                "{place}{} {} {}",
                text(f, "severity"),
                text(f, "rule"),
                text(f, "message")
            )
        })
        .collect()
}

/// The data of a text-mode run: counts and finding lines instead of the whole document.
fn summary(run: &GrimbleRun, doc: &Value) -> Value {
    let c = gob_check::Counts::of(&run.report.findings);
    json!({
        "counts": {"error": c.error, "warn": c.warn, "advisory": c.advisory, "unresolved": c.unresolved},
        "suppressed": run.report.suppressed.len(),
        "lines": lines_of(doc),
    })
}

impl Command for Check {
    type Data = Value;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("only")
                .long("only")
                .value_name("FAMILY")
                .value_delimiter(',')
                .action(ArgAction::Append)
                .help("Keep only these rule families or ids (comma separated)"),
        )
        .arg(
            Arg::new("fail_on")
                .long("fail-on")
                .value_name("SEVERITY")
                .value_parser(["error", "warn", "advisory", "none"])
                .help("Exit 1 at or above this severity (default: [check] fail_on)"),
        )
        .arg(
            Arg::new("base")
                .long("base")
                .value_name("REF")
                .help("Ref diff-scoped rules diff against (echoed; no rule diffs yet)"),
        )
        .arg(
            Arg::new("ticket_scope")
                .long("ticket-scope")
                .value_name("PATH")
                .value_delimiter(',')
                .action(ArgAction::Append)
                .help("Repo-relative paths per-file rules are narrowed to (echoed; no per-file rule yet)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let many = |id: &str| -> Option<Vec<String>> {
            m.get_many::<String>(id).map(|v| v.cloned().collect())
        };
        Ok(Self {
            only: many("only").unwrap_or_default(),
            fail_on: m
                .get_one::<String>("fail_on")
                .and_then(|s| FailOn::parse(s)),
            base: m.get_one::<String>("base").cloned(),
            ticket_scope: many("ticket_scope"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<Value> {
        let root = locate_root(&ctx.cwd);
        let opts = CheckOptions {
            only: self.only.clone(),
            fail_on: self.fail_on,
            base: self.base.clone(),
            ticket_scope: self.ticket_scope.clone(),
        };
        let run = grimble_check::run(&root, &opts).map_err(check_error)?;
        let doc = sibling_document(&run);
        let data = if ctx.json {
            doc.clone()
        } else {
            summary(&run, &doc)
        };
        if run.report.exit_code() == ExitCode::Negative {
            let c = gob_check::Counts::of(&run.report.findings);
            return Err(CliError::Gate {
                message: format!(
                    "{} error(s), {} warning(s), {} advisory, {} unresolved ({} required):\n{}",
                    c.error,
                    c.warn,
                    c.advisory,
                    c.unresolved,
                    run.report.required_unresolved(),
                    lines_of(&doc).join("\n")
                ),
                data,
                warnings: run.warnings,
            });
        }
        let mut payload = Payload::new(data);
        payload.warnings = run.warnings;
        Ok(payload)
    }
}

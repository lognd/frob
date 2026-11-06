//! `why`: why a call site is allowed or denied by the capability model.
//!
//! The answer is read from the CAP001 findings of the `gob.sibling/1` document: a finding names the
//! atom, every call site (`file:line callee`) and the narrowest grant that would allow it, so a
//! target matching a finding's text is denied (error) or unknown (unresolved); a target that no
//! finding names is allowed. CAP001 exceptions are listed beside the verdict.

// frob:ticket 01M5XNNJXHY369P16NZJMQ3SX6

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_check::{CheckOptions, exceptions_json, sibling_document};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::workspace::{check_error, locate_root};

/// Explain why a call site (`file:line`) or symbol (`file::symbol`) is allowed or denied.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "why",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Why {
    target: String,
}

/// `Why` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct WhyArgs {
    #[arg(help = "A call site `file:line` or a symbol `file::symbol`")]
    target: String,
}

/// The verdict on one target.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct WhyData {
    /// The target as given.
    pub target: String,
    /// `allowed`, `denied` or `unknown`.
    pub verdict: String,
    /// The CAP001 findings that name the target: atom, sites and the narrowest grant.
    pub findings: Vec<String>,
    /// CAP001 exceptions in the model (`accept CAP001 ...`), which may silence the atom.
    pub exceptions: Vec<String>,
}

impl Command for Why {
    type Data = WhyData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<WhyArgs>(cmd)
    }

    fn from_matches(matches: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<WhyArgs>(matches)?;
        Ok(Self { target: a.target })
    }

    fn run(&self, ctx: &Context) -> Outcome<WhyData> {
        let root = locate_root(&ctx.cwd);
        // Read-only view: leave no telemetry or precision history behind.
        let options = CheckOptions {
            skip_telemetry: true,
            ..CheckOptions::default()
        };
        let run = grimble_check::run(&root, &options).map_err(check_error)?;
        let data = why_of(
            &sibling_document(&run),
            &exceptions_json(&run),
            &self.target,
        );
        tracing::info!(target = %data.target, verdict = %data.verdict, "why answered");
        let mut lines = vec![format!("{}: {}", data.target, data.verdict)];
        lines.extend(data.findings.iter().map(|f| format!("  finding: {f}")));
        lines.extend(data.exceptions.iter().map(|e| format!("  exception: {e}")));
        Ok(Payload::new(data).with_rendered(lines))
    }
}

/// True when `message` names `target` at a token boundary (`a.py:3` must not match `a.py:30`).
fn names(message: &str, target: &str) -> bool {
    message.match_indices(target).any(|(at, _)| {
        message[at + target.len()..]
            .chars()
            .next()
            .is_none_or(|c| !c.is_alphanumeric() && c != '_')
    })
}

/// The verdict on `target` from the document's CAP001 findings and the model's exceptions.
pub fn why_of(doc: &Value, exceptions: &[Value], target: &str) -> WhyData {
    let mut verdict = "allowed";
    let mut findings = Vec::new();
    for f in doc["findings"].as_array().into_iter().flatten() {
        let message = f["message"].as_str().unwrap_or_default();
        if f["rule"] != "CAP001" || !names(message, target) {
            continue;
        }
        if f["severity"] == "error" {
            verdict = "denied";
        } else if verdict == "allowed" {
            verdict = "unknown";
        }
        findings.push(message.to_owned());
    }
    let exceptions = exceptions
        .iter()
        .filter(|e| e["rule"] == "CAP001")
        .map(|e| {
            format!(
                "{} {} ({}:{})",
                e["kind"].as_str().unwrap_or("accept"),
                e["on"].as_str().unwrap_or_default(),
                e["file"].as_str().unwrap_or_default(),
                e["line"]
            )
        })
        .collect();
    WhyData {
        target: target.to_owned(),
        verdict: verdict.to_owned(),
        findings,
        exceptions,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn doc() -> Value {
        json!({"findings": [
            {"rule": "CAP001", "severity": "error",
             "message": "`node/a` uses `fs.write` with no grant (1 use(s)): src/x.py:3 open; narrowest grant: may fs.write(\"o\") at \"src/x.py::f\";"},
            {"rule": "CAP001", "severity": "unresolved", "message": "`net.connect` may be used: src/y.py:7 get"}
        ]})
    }

    // frob:tests crates/grimble/src/why_cmd.rs::why_of
    #[test]
    fn denied_site_names_the_grant() {
        let d = why_of(&doc(), &[], "src/x.py:3");
        assert_eq!(d.verdict, "denied");
        assert!(d.findings[0].contains("narrowest grant: may fs.write"));
    }

    // frob:tests crates/grimble/src/why_cmd.rs::why_of
    #[test]
    fn unknown_allowed_and_boundary() {
        assert_eq!(why_of(&doc(), &[], "src/y.py:7").verdict, "unknown");
        assert_eq!(why_of(&doc(), &[], "src/x.py:30").verdict, "allowed");
        assert_eq!(why_of(&doc(), &[], "src/z.py:1").verdict, "allowed");
    }
}

//! `frob dismiss RULE FINGERPRINT --reason TEXT`: record a finding as dismissed in the precision history.
//!
//! The dismissal lands in `precision-history.json` in the product's telemetry directory through
//! [`gob_check::dismiss`]. That file is a plain read-modify-write with no lock: two concurrent
//! writers (a check run and a dismissal, or two dismissals) can lose one update. The write itself
//! is not temp-file-plus-rename either, because the writer lives in `gob-rules`.

// frob:ticket 01M68K5GXB2C7G082PGAA9C2BY

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_rules::{HistoryError, RuleId};
use schemars::JsonSchema;
use serde::Serialize;

use crate::pretty::PrettyExt;
use crate::workspace::Located;
use frob_check::Frob;

/// Output of `frob dismiss`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DismissData {
    /// The rule whose finding was dismissed.
    pub rule: String,
    /// The fingerprint of the dismissed finding.
    pub fingerprint: String,
    /// The reason recorded for the dismissal.
    pub reason: String,
}

/// The flags of `dismiss`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DismissArgs {
    #[arg(
        required = true,
        value_name = "RULE",
        help = "Rule id of the finding, such as DOC001"
    )]
    rule: String,
    #[arg(
        required = true,
        value_name = "FINGERPRINT",
        help = "Fingerprint of the finding to dismiss"
    )]
    fingerprint: String,
    #[arg(long, required = true, help = "Why this finding is dismissed")]
    reason: String,
}

/// Record the finding `FINGERPRINT` of `RULE` as dismissed for a stated reason in the precision history.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "dismiss",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct Dismiss {
    rule: String,
    fingerprint: String,
    reason: String,
}

/// Map a history failure to the CLI: a bad reason is the caller's mistake, I/O and format are internal.
fn history_err(e: HistoryError) -> CliError {
    match e {
        HistoryError::Reason(_) => CliError::Usage(e.to_string()),
        other => CliError::internal(other),
    }
}

impl Command for Dismiss {
    type Data = DismissData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<DismissArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DismissArgs>(m)?;
        Ok(Self {
            rule: a.rule,
            fingerprint: a.fingerprint,
            reason: a.reason,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<DismissData> {
        let rule: RuleId = self
            .rule
            .parse()
            .map_err(|e| CliError::Usage(format!("`{}` is not a rule id: {e}", self.rule)))?;
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        gob_check::dismiss(
            &Frob::new(frob_check::CheckOptions::default()),
            &root,
            &rule,
            &self.fingerprint,
            &self.reason,
        )
        .map_err(history_err)?;
        tracing::info!(rule = %rule, fingerprint = %self.fingerprint, "finding dismissed");
        let rows = vec![format!(
            "dismissed {rule} {} ({})",
            self.fingerprint, self.reason
        )];
        Ok(Payload::new(DismissData {
            rule: rule.to_string(),
            fingerprint: self.fingerprint.clone(),
            reason: self.reason.clone(),
        })
        .with_pretty(rows))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob/src/dismiss_cmd.rs::history_err
    #[test]
    fn a_rejected_reason_is_a_usage_error() {
        let err = gob_rules::PrecisionHistory::default()
            .dismiss(&"DOC001".parse().unwrap(), "fp", " ")
            .unwrap_err();
        assert!(matches!(history_err(err), CliError::Usage(_)));
    }
}

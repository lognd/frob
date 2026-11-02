//! The generic `check` verb: flags in, [`Product::check`] out, the sibling document as data.

use std::marker::PhantomData;

use gob_check::{CheckError, FailOn};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, CommandMeta, Context, Described, ExitCode, Outcome, Payload};
use serde_json::{Value, json};

// frob:ticket 01M4K8TMXWK93ZKAAFQE9W4M0D
use crate::workspace::{check_error, require_untracked_state};
use crate::{CheckOptions, Product, ProductRun};

/// Run the rules over the repository and print the `gob.sibling/1` document; exit 1 when the gate fails.
#[derive(Debug, Clone)]
pub struct Check<P: Product> {
    only: Vec<String>,
    fail_on: Option<FailOn>,
    base: Option<String>,
    ticket_scope: Option<Vec<String>>,
    matches: ArgMatches,
    product: PhantomData<fn() -> P>,
}

impl<P: Product> Described for Check<P> {
    const META: CommandMeta = CommandMeta {
        verb: "check",
        product: P::NAME,
        idempotent: false,
        dry_run: false,
        exits: &[
            ExitCode::Ok,
            ExitCode::Negative,
            ExitCode::Usage,
            ExitCode::Refused,
            ExitCode::Internal,
        ],
        summary: P::CHECK_SUMMARY,
        module: module_path!(),
        deprecated: None,
        markdown: false,
        read_only: true,
    };
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
fn summary(run: &ProductRun, doc: &Value) -> Value {
    let c = gob_check::Counts::of(&run.report.findings);
    json!({
        "counts": {"error": c.error, "unresolved": c.unresolved},
        "suppressed": run.report.suppressed.len(),
        "lines": lines_of(doc),
    })
}

/// The check flags every product shares: `--only`, `--fail-on`, `--base`, `--ticket-scope`.
#[derive(Debug, Clone, Default, gob_cli::clap::Args)]
#[command(about = None, long_about = None)]
pub struct SharedFlags {
    /// Keep only these rule families or ids (comma separated)
    #[arg(long, value_name = "FAMILY", value_delimiter = ',')]
    only: Vec<String>,
    /// Exit 1 at or above this severity (default: [check] `fail_on`)
    #[arg(long = "fail-on", value_name = "SEVERITY", value_parser = ["error", "warn", "advisory", "none"])]
    fail_on: Option<String>,
    /// Ref diff-scoped rules diff against (echoed; no rule diffs yet)
    #[arg(long, value_name = "REF")]
    base: Option<String>,
    /// Repo-relative paths per-file rules are narrowed to (echoed; no per-file rule yet)
    #[arg(long = "ticket-scope", value_name = "PATH", value_delimiter = ',')]
    ticket_scope: Option<Vec<String>>,
}

/// Declare the shared check flags on `cmd`.
///
/// The default of [`Product::configure_check`]; a product with its own flag set replaces it.
#[must_use]
pub fn shared_flags(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
    gob_cli::augment::<SharedFlags>(cmd)
}

impl<P: Product> Command for Check<P> {
    type Data = P::CheckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        P::configure_check(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        // A product with its own flag set (frob) does not declare every shared flag; clap
        // panics on an undeclared id, so such a product parses to the defaults.
        let declared = ["only", "fail_on", "base", "ticket_scope"]
            .iter()
            .all(|id| m.try_contains_id(id).is_ok());
        let flags: SharedFlags = if declared {
            gob_cli::parse(m)?
        } else {
            tracing::debug!("shared check flags not declared; using defaults");
            SharedFlags::default()
        };
        Ok(Self {
            only: flags.only,
            fail_on: flags.fail_on.and_then(|s| FailOn::parse(&s)),
            base: flags.base,
            ticket_scope: flags.ticket_scope,
            matches: m.clone(),
            product: PhantomData,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<P::CheckData> {
        let root = P::locate_root(&ctx.cwd);
        require_untracked_state(&root)?;
        let opts = CheckOptions {
            only: self.only.clone(),
            fail_on: self.fail_on,
            base: self.base.clone(),
            ticket_scope: self.ticket_scope.clone(),
        };
        tracing::debug!(product = P::NAME, root = ?root, "check started");
        P::check(ctx, &root, &opts, &self.matches)
    }
}

/// The sibling-document `check` of a product whose pipeline yields a [`ProductRun`].
///
/// Maps a pipeline failure to the exit table, returns the whole document in JSON mode and a
/// counts-plus-lines summary in text mode, and fails the gate (exit 1) when the report says so.
///
/// # Errors
///
/// The mapped [`CheckError`], or [`CliError::Gate`] when the report fails the gate.
pub fn sibling_check(
    product: &str,
    ctx: &Context,
    run: Result<ProductRun, CheckError>,
) -> Outcome<Value> {
    let run = run.map_err(|e| check_error(product, e))?;
    let doc = run.document.clone();
    let data = if ctx.json {
        doc.clone()
    } else {
        summary(&run, &doc)
    };
    if run.report.exit_code() == ExitCode::Negative {
        let c = gob_check::Counts::of(&run.report.findings);
        return Err(CliError::Gate {
            message: format!(
                "{} error(s), {} unresolved ({} required):\n{}",
                c.error,
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

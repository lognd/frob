//! `status ID [ready]`: the handoff gate (crunk.md 4.1, 5, 8).
//!
//! `ready` refuses, naming every reason at once, unless the screen has no open blocking comment
//! (`design/review/*.toml`), no stale export, a code mapping and green lints. On success it
//! records the screen's content hash in `crunk.lock` as a `[[ready]]` row and locks the screen
//! file (`status = "ready"` plus its `content_hash`). Without a target the verb reports where the
//! screen stands and marks a ready screen whose content moved as `changed`. It never writes a
//! `[[review]]` row: human acks stay person-only.

// frob:ticket 01M5XCZ18GTA7MKKF4Z0MD95W3

use std::path::Path;

use crunk_rules::component_files::TokenLookup;
use crunk_rules::handoff::{Facts, Standing, judge, standing};
use crunk_rules::screen_files::{ScreenFacts, content_hash};
use crunk_rules::token_files::TokenFacts;
use crunk_spec::table::ScreenStatus;
use gob_cli::clap::{ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use serde::Serialize;

use crate::PRODUCT;
use crate::edit::match_line_endings;
use crate::stamp::set_content_hash;

/// Report a screen's handoff standing, or hand it off with `ready`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "status",
    product = "crunk",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Status {
    id: String,
    target: Option<String>,
}

/// `Status` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct StatusArgs {
    #[arg(value_name = "ID", help = "The screen id")]
    id: String,
    #[arg(
        value_name = "TARGET",
        value_parser = PossibleValuesParser::new(["ready"]),
        help = "`ready` hands the screen off; omit to report where it stands"
    )]
    target: Option<String>,
}

/// The report of `status`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct StatusData {
    /// The screen id.
    pub id: String,
    /// `draft`, `ready` or `changed`.
    pub status: String,
    /// The content hash now recorded for the handoff, when one is.
    pub content_hash: Option<String>,
    /// Comments anchored to a deleted state; reported, never blocking.
    pub orphaned: Vec<String>,
    /// True when nothing was written.
    pub dry_run: bool,
}

/// Why `status` refused, with a stable code.
#[derive(Debug, thiserror::Error)]
pub enum StatusError {
    /// The spec, a screen file or the lock would not load.
    #[error("{0}")]
    Load(String),
    /// The id names no screen file.
    #[error("no screen with id `{0}` under design/screens")]
    Unknown(String),
    /// The screen is not ready for handoff; each reason is named.
    #[error("screen `{id}` is not ready: {}", .reasons.join("; "))]
    NotReady {
        /// The screen id.
        id: String,
        /// One line per reason.
        reasons: Vec<String>,
    },
    /// A write failed.
    #[error("cannot write {0}: {1}")]
    Write(String, String),
}

impl StatusError {
    /// The stable refusal code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Load(_) => "E-STATUS-LOAD",
            Self::Unknown(_) => "E-STATUS-UNKNOWN",
            Self::NotReady { .. } => "E-STATUS-NOT-READY",
            Self::Write(..) => "E-STATUS-WRITE",
        }
    }
}

impl From<StatusError> for CliError {
    fn from(err: StatusError) -> Self {
        tracing::info!(code = err.code(), error = %err, "status refused");
        let (class, remedy) = match err {
            StatusError::Unknown(_) => (RefusalClass::UsageError, "fix the screen id"),
            _ => (
                RefusalClass::GuardNeedsAction,
                "clear each reason named, then rerun; nothing was recorded",
            ),
        };
        Refusal::new(err.code(), class, err.to_string())
            .with_remedy(remedy)
            .into()
    }
}

/// `text` with its top-level `status` set to `word`; comments and line endings are kept.
fn set_status(text: &str, word: &str) -> Result<String, String> {
    let mut doc: toml_edit::DocumentMut = text.parse().map_err(|e| format!("{e}"))?;
    let decor = doc
        .get("status")
        .and_then(toml_edit::Item::as_value)
        .map(|v| v.decor().clone());
    let mut value = toml_edit::value(word);
    if let (Some(decor), Some(v)) = (decor, value.as_value_mut()) {
        *v.decor_mut() = decor;
    }
    doc["status"] = value;
    Ok(match_line_endings(text, &doc.to_string()))
}

/// Whether every path in `sources` exists under `root` (and there is at least one).
fn has_code_mapping(root: &Path, sources: Option<&[String]>) -> bool {
    sources.is_some_and(|s| !s.is_empty() && s.iter().all(|p| root.join(p).exists()))
}

/// Error-severity lint findings against `file`, as `RULE message`.
fn red_lints(root: &Path, file: &str) -> Result<Vec<String>, StatusError> {
    let opts = crunk_check::CheckOptions {
        only: Vec::new(),
        fail_on: None,
        base: None,
        ticket_scope: None,
        static_tailwind: true,
        gate: gob_rules::Gate::resolve(None, None),
    };
    let run = crunk_check::run_to_tier(root, &opts, crunk_check::Tier::default())
        .map_err(|e| StatusError::Load(e.to_string()))?;
    let doc = crunk_check::sibling_document(&run);
    let found = doc["findings"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or_default();
    Ok(found
        .iter()
        .filter(|f| f["severity"] == "error" && f["file"].as_str().is_some_and(|p| p == file))
        .map(|f| {
            format!(
                "{} {}",
                f["rule"].as_str().unwrap_or("?"),
                f["message"].as_str().unwrap_or("")
            )
        })
        .collect())
}

/// Generated export files that are missing or drifted.
fn stale_exports(root: &Path, spec: &crunk_spec::DesignSpec) -> Result<Vec<String>, StatusError> {
    let report = crunk_tokens::export::check(spec).map_err(|e| StatusError::Load(e.to_string()))?;
    Ok(report
        .dirty()
        .map(|f| gob_path::forward_slashes(f.path.strip_prefix(root).unwrap_or(&f.path)))
        .collect())
}

/// Write `text` to `path` atomically.
fn write(path: &Path, label: &str, text: &str) -> Result<(), StatusError> {
    gob_fs::write_atomic(path, text.as_bytes())
        .map_err(|e| StatusError::Write(label.to_owned(), e.to_string()))
}

impl Command for Status {
    type Data = StatusData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<StatusArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<StatusArgs>(m)?;
        Ok(Self {
            id: a.id,
            target: a.target,
        })
    }

    #[allow(clippy::too_many_lines)] // one linear gather, judge, record flow
    fn run(&self, ctx: &Context) -> Outcome<StatusData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| {
            StatusError::Load(format!("crunk.toml is not a valid design spec: {e}"))
        })?;
        let screens = ScreenFacts::load(&spec);
        if let Some(p) = screens.problems.first() {
            return Err(StatusError::Load(format!("{}: {}", p.path, p.message)).into());
        }
        let file = screens
            .files
            .iter()
            .find(|f| f.screen.id == self.id)
            .ok_or_else(|| StatusError::Unknown(self.id.clone()))?;
        let tokens = TokenLookup::new(Some(&spec), Some(&TokenFacts::load(&spec)));
        let hash = content_hash(&file.screen, &tokens);
        let lock_path = crunk_check::review::lock_path(&root);
        let mut lock =
            gob_lock::LockFile::load(&lock_path).map_err(|e| StatusError::Load(e.to_string()))?;
        let subject = format!("screen/{}", self.id);
        let recorded = lock.ready.get(&subject).map(|e| e.hash.clone());
        let screen_path = root.join(&file.path);
        let states: Vec<&str> = file.screen.states.iter().map(|s| s.id.as_str()).collect();
        let comments = crunk_spec::handoff::load_comments(&root);
        let orphaned = judge(&Facts {
            comments: &comments,
            screen: &self.id,
            states: &states,
            stale_exports: &[],
            has_code_mapping: true,
            red_lints: &[],
        })
        .orphaned;

        if self.target.is_none() {
            let now = standing(recorded.as_deref(), &hash);
            let locked = matches!(
                file.screen.status,
                Some(ScreenStatus::Ready | ScreenStatus::Completed)
            );
            if now == Standing::Changed && locked && !ctx.dry_run {
                write(
                    &screen_path,
                    &file.path,
                    &set_status(&file.text, "changed").map_err(StatusError::Load)?,
                )?;
                tracing::info!(screen = %self.id, "status: marked changed");
            }
            let data = StatusData {
                id: self.id.clone(),
                status: now.word().to_owned(),
                content_hash: recorded,
                orphaned,
                dry_run: ctx.dry_run,
            };
            let line = format!("{}: {}", data.id, data.status);
            return Ok(Payload::new(data).with_rendered(vec![line]));
        }

        let reds = red_lints(&root, &file.path)?;
        let exports = stale_exports(&root, &spec)?;
        let verdict = judge(&Facts {
            comments: &comments,
            screen: &self.id,
            states: &states,
            stale_exports: &exports,
            has_code_mapping: has_code_mapping(&root, file.screen.sources.as_deref()),
            red_lints: &reds,
        });
        if !verdict.reasons.is_empty() {
            return Err(StatusError::NotReady {
                id: self.id.clone(),
                reasons: verdict
                    .reasons
                    .iter()
                    .map(crunk_rules::handoff::Reason::line)
                    .collect(),
            }
            .into());
        }
        let already = recorded.as_deref() == Some(hash.as_str())
            && file.screen.status == Some(ScreenStatus::Ready);
        if !ctx.dry_run && !already {
            lock.ready.insert(
                subject,
                gob_lock::ReadyEntry {
                    hash: hash.clone(),
                    at: ctx.clock.now().to_string(),
                },
            );
            lock.save(&lock_path)
                .map_err(|e| StatusError::Write(lock_path.display().to_string(), e.to_string()))?;
            let mut text = set_content_hash(&file.text, &hash).map_err(StatusError::Load)?;
            if file.screen.status != Some(ScreenStatus::Completed) {
                text = set_status(&text, "ready").map_err(StatusError::Load)?;
            }
            if text != file.text {
                write(&screen_path, &file.path, &text)?;
            }
            tracing::info!(screen = %self.id, %hash, "status: handed off");
        }
        let data = StatusData {
            id: self.id.clone(),
            status: Standing::Ready.word().to_owned(),
            content_hash: Some(hash),
            orphaned: verdict.orphaned,
            dry_run: ctx.dry_run,
        };
        let line = format!("{}: ready", data.id);
        Ok(Payload::new(data)
            .with_rendered(vec![line])
            .with_already(already))
    }
}

//! `stamp [ID...]`: record each locked screen's `content_hash`, folding in the resolved token values.
//!
//! Only `ready` and `completed` screens are stamped (the ones STATE007 judges); the hash is the
//! one STATE007 recomputes, so a stamped screen is clean until its content or a token changes.
//! The edit goes through `toml_edit`, so comments, key order and CRLF line endings are kept.

// frob:ticket 01M5EF4AEM3BG06QWEX6081JS9

use std::path::{Path, PathBuf};

use crunk_rules::component_files::TokenLookup;
use crunk_rules::screen_files::{ScreenFacts, content_hash};
use crunk_rules::token_files::TokenFacts;
use crunk_spec::table::ScreenStatus;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use serde::Serialize;

use crate::PRODUCT;
use crate::edit::match_line_endings;

/// Record the content hash of every locked screen (or the named ones).
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "stamp",
    product = "crunk",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Stamp {
    ids: Vec<String>,
}

/// `Stamp` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct StampArgs {
    #[arg(
        value_name = "ID",
        help = "Screen ids to stamp; every ready or completed screen when none is given"
    )]
    ids: Vec<String>,
}

/// One screen file the stamp looked at.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct Stamped {
    /// The screen file, relative to the project root.
    pub file: String,
    /// The screen id.
    pub id: String,
    /// The hash now recorded (or that would be, on a dry run).
    pub content_hash: String,
    /// True when the file's text changed (false when it was already stamped).
    pub changed: bool,
}

/// The report of `stamp`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct StampData {
    /// The locked screens, in path order.
    pub screens: Vec<Stamped>,
    /// True when nothing was written.
    pub dry_run: bool,
    /// Screens skipped because they are not `ready` or `completed`.
    pub skipped: usize,
}

impl StampData {
    /// The human lines: one per screen and a tally.
    #[must_use]
    pub fn lines(&self) -> Vec<String> {
        let verb = if self.dry_run {
            "would stamp"
        } else {
            "stamped"
        };
        let mut lines: Vec<String> = self
            .screens
            .iter()
            .map(|s| {
                let state = if s.changed { verb } else { "unchanged" };
                format!("{state} {} ({})", s.file, s.id)
            })
            .collect();
        lines.push(format!(
            "{} locked screen(s), {} skipped",
            self.screens.len(),
            self.skipped
        ));
        lines
    }
}

/// Why a stamp was refused, with a stable code.
#[derive(Debug, thiserror::Error)]
pub enum StampError {
    /// The spec or a screen file would not load.
    #[error("{0}")]
    Load(String),
    /// A requested id names no screen file.
    #[error("no screen with id `{0}` under design/screens")]
    Unknown(String),
    /// A screen file's text could not be edited.
    #[error("cannot edit {0}: {1}")]
    Edit(String, String),
    /// A write failed.
    #[error("cannot write {0}: {1}")]
    Write(String, String),
}

impl StampError {
    /// The stable refusal code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Load(_) => "E-STAMP-LOAD",
            Self::Unknown(_) => "E-STAMP-UNKNOWN",
            Self::Edit(..) => "E-STAMP-EDIT",
            Self::Write(..) => "E-STAMP-WRITE",
        }
    }
}

impl From<StampError> for CliError {
    fn from(err: StampError) -> Self {
        tracing::info!(code = err.code(), error = %err, "stamp refused");
        let class = match err {
            StampError::Unknown(_) => RefusalClass::UsageError,
            _ => RefusalClass::GuardNeedsAction,
        };
        Refusal::new(err.code(), class, err.to_string())
            .with_remedy("fix the screen id or file as described; nothing was written")
            .into()
    }
}

/// `text` with its top-level `content_hash` set to `hash`; comments, key order and line endings
/// are kept. A new key lands right after `status` when there is one, else at the end of the
/// top-level keys.
///
/// # Errors
/// The text is not TOML.
pub fn set_content_hash(text: &str, hash: &str) -> Result<String, String> {
    let mut doc: toml_edit::DocumentMut = text.parse().map_err(|e| format!("{e}"))?;
    let existing = doc
        .get("content_hash")
        .and_then(toml_edit::Item::as_value)
        .map(|v| v.decor().clone());
    let mut value = toml_edit::value(hash);
    if let (Some(decor), Some(v)) = (existing, value.as_value_mut()) {
        *v.decor_mut() = decor;
    }
    doc["content_hash"] = value;
    Ok(match_line_endings(text, &doc.to_string()))
}

/// What one stamp run decided for one file.
struct Planned {
    path: PathBuf,
    report: Stamped,
    text: String,
}

/// Compute the stamps for the locked screens of the project at `root`; touches nothing.
fn plan(root: &Path, ids: &[String]) -> Result<(Vec<Planned>, usize), StampError> {
    let spec = crunk_spec::load_spec(root)
        .map_err(|e| StampError::Load(format!("crunk.toml is not a valid design spec: {e}")))?;
    let screens = ScreenFacts::load(&spec);
    if let Some(p) = screens.problems.first() {
        return Err(StampError::Load(format!("{}: {}", p.path, p.message)));
    }
    if let Some(id) = ids
        .iter()
        .find(|id| !screens.files.iter().any(|f| &f.screen.id == *id))
    {
        return Err(StampError::Unknown(id.clone()));
    }
    let tokens = TokenLookup::new(Some(&spec), Some(&TokenFacts::load(&spec)));
    let mut planned = Vec::new();
    let mut skipped = 0;
    for file in &screens.files {
        let wanted = ids.is_empty() || ids.contains(&file.screen.id);
        let locked = matches!(
            file.screen.status,
            Some(ScreenStatus::Ready | ScreenStatus::Completed)
        );
        if !wanted || !locked {
            skipped += 1;
            tracing::debug!(path = %file.path, wanted, locked, "stamp: skipped");
            continue;
        }
        let hash = content_hash(&file.screen, &tokens);
        let text = set_content_hash(&file.text, &hash)
            .map_err(|e| StampError::Edit(file.path.clone(), e))?;
        planned.push(Planned {
            path: root.join(&file.path),
            report: Stamped {
                file: file.path.clone(),
                id: file.screen.id.clone(),
                content_hash: hash,
                changed: text != file.text,
            },
            text,
        });
    }
    Ok((planned, skipped))
}

impl Command for Stamp {
    type Data = StampData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<StampArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<StampArgs>(m)?;
        Ok(Self { ids: a.ids })
    }

    fn run(&self, ctx: &Context) -> Outcome<StampData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let (planned, skipped) = plan(&root, &self.ids)?;
        if ctx.dry_run {
            tracing::info!(screens = planned.len(), "stamp: dry run, nothing written");
        } else {
            for p in planned.iter().filter(|p| p.report.changed) {
                gob_fs::write_atomic(&p.path, p.text.as_bytes())
                    .map_err(|e| StampError::Write(p.report.file.clone(), e.to_string()))?;
                tracing::info!(file = %p.report.file, hash = %p.report.content_hash, "stamp: written");
            }
        }
        let data = StampData {
            screens: planned.into_iter().map(|p| p.report).collect(),
            dry_run: ctx.dry_run,
            skipped,
        };
        let lines = data.lines();
        Ok(Payload::new(data).with_rendered(lines))
    }
}

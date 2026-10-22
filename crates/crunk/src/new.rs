//! `new component|screen|flow|token NAME [--from FILE]`: scaffold one design file.
//!
//! The skeleton (or the `--from` source with its identity key renamed) is built and validated in
//! memory by the file kind's own parser; only then is anything touched on disk. The write refuses
//! an existing target, never creates a directory outside the project root, and removes any
//! directory it created if the write fails, so a refusal leaves the project byte-identical.

// frob:ticket 01M5H8MMN5PXGJG2XGS76STB57

use std::path::{Path, PathBuf};

use gob_cli::clap::ArgMatches;
use gob_cli::clap::builder::PossibleValuesParser;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use serde::Serialize;

use crate::PRODUCT;
use crate::dtcg::relative;
use crate::edit::match_line_endings;

/// The scaffoldable kinds.
pub const KINDS: [&str; 4] = ["component", "screen", "flow", "token"];

/// The longest accepted NAME, so the file name stays portable.
const MAX_NAME: usize = 64;

/// Scaffold a component, screen, flow or token file under `design`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "new",
    product = "crunk",
    idempotent = false,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct New {
    kind: String,
    name: String,
    from: Option<String>,
}

/// `New` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct NewArgs {
    #[arg(
        value_name = "KIND",
        value_parser = PossibleValuesParser::new(KINDS),
        help = "component, screen, flow or token"
    )]
    kind: String,
    #[arg(
        value_name = "NAME",
        help = "Lowercase letters, digits, hyphen and underscore, starting with a letter"
    )]
    name: String,
    #[arg(
        long,
        value_name = "FILE",
        help = "Copy an existing design file of the same kind, renamed to NAME, instead of the skeleton"
    )]
    from: Option<String>,
}

/// The report of `new`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct NewData {
    /// The file, relative to the project root.
    pub file: String,
    /// `component`, `screen`, `flow` or `token`.
    pub kind: String,
    /// The validated NAME.
    pub name: String,
    /// The `--from` source as given, if any.
    pub from: Option<String>,
    /// True when nothing was written.
    pub dry_run: bool,
    /// True when the file was written.
    pub created: bool,
    /// Size of the file text in bytes.
    pub bytes: usize,
}

impl NewData {
    /// The human lines: one headline.
    #[must_use]
    pub fn lines(&self) -> Vec<String> {
        let verb = if self.created {
            "created"
        } else {
            "would create"
        };
        let src = self
            .from
            .as_ref()
            .map_or_else(String::new, |f| format!(" from {f}"));
        vec![format!("{verb} {} ({}){src}", self.file, self.kind)]
    }
}

/// Why a scaffold was refused, with a stable code.
#[derive(Debug, thiserror::Error)]
pub enum NewError {
    /// NAME is not a valid identifier.
    #[error("invalid name `{0}`: {1}")]
    Name(String, &'static str),
    /// The target exists already.
    #[error("{0} already exists; it was not touched")]
    Exists(String),
    /// The `--from` source is missing, unreadable or not a valid file of the kind.
    #[error("--from {0}: {1}")]
    From(String, String),
    /// The target would sit behind a symlink or a non-directory.
    #[error("{0}")]
    Path(String),
    /// The produced text fails the kind's schema.
    #[error("the new file is invalid, nothing written: {0}")]
    Schema(String),
    /// The write failed.
    #[error("cannot write {0}: {1}")]
    Write(String, String),
}

impl NewError {
    /// The stable refusal code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Name(..) => "E-NEW-NAME",
            Self::Exists(_) => "E-NEW-EXISTS",
            Self::From(..) => "E-NEW-FROM",
            Self::Path(_) => "E-NEW-PATH",
            Self::Schema(_) => "E-NEW-SCHEMA",
            Self::Write(..) => "E-NEW-WRITE",
        }
    }
}

impl From<NewError> for CliError {
    fn from(err: NewError) -> Self {
        tracing::info!(code = err.code(), error = %err, "new refused");
        Refusal::new(err.code(), RefusalClass::GuardNeedsAction, err.to_string())
            .with_remedy("fix the name, source or target as described; nothing was written")
            .into()
    }
}

impl Command for New {
    type Data = NewData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<NewArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<NewArgs>(m)?;
        Ok(Self {
            kind: a.kind,
            name: a.name,
            from: a.from,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<NewData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let from = self
            .from
            .as_deref()
            .map(|f| crunk_spec::normalize_join(&ctx.cwd, f));
        let plan = plan(&root, &self.kind, &self.name, from.as_deref())?;
        if ctx.dry_run {
            tracing::info!(kind = %self.kind, "new: dry run, nothing written");
        } else {
            write_new(&plan.path, &plan.text, &root)?;
            tracing::info!(file = %relative(&root, &plan.path), kind = %self.kind, "new: written");
        }
        let data = NewData {
            file: relative(&root, &plan.path),
            kind: self.kind.clone(),
            name: self.name.clone(),
            from: self.from.clone(),
            dry_run: ctx.dry_run,
            created: !ctx.dry_run,
            bytes: plan.text.len(),
        };
        let lines = data.lines();
        Ok(Payload::new(data).with_rendered(lines))
    }
}

/// A validated, not yet written scaffold.
struct Plan {
    path: PathBuf,
    text: String,
}

/// The directory (under `design`), file suffix and identity key of `kind`; a token file has no
/// identity key, its name is the file stem.
fn layout(kind: &str) -> (&'static str, &'static str, Option<&'static str>) {
    match kind {
        "component" => ("components", ".component.toml", Some("name")),
        "screen" => ("screens", ".screen.toml", Some("id")),
        "flow" => ("flows", ".flow.toml", Some("name")),
        _ => ("tokens", ".toml", None),
    }
}

/// Check NAME: a lowercase identifier, so it is a safe file stem on every platform and cannot
/// collide with another name on a case-insensitive file system or climb out of its directory.
fn validate_name(name: &str) -> Result<(), NewError> {
    let bad = |why| Err(NewError::Name(name.to_owned(), why));
    if name.is_empty() {
        return bad("it is empty");
    }
    if name.len() > MAX_NAME {
        return bad("it is longer than 64 characters");
    }
    if !name.starts_with(|c: char| c.is_ascii_lowercase()) {
        return bad("it must start with a lowercase letter");
    }
    if !name
        .chars()
        .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '_')
    {
        return bad("only lowercase letters, digits, hyphen and underscore are allowed");
    }
    Ok(())
}

/// The skeleton text of `kind` named `name`.
fn skeleton(kind: &str, name: &str) -> String {
    match kind {
        "component" => format!(
            "name = \"{name}\"\n\n[anatomy]\nnodes = [\"root\"]\n\n[[states]]\nid = \"default\"\n"
        ),
        "screen" => format!("id = \"{name}\"\nentry = \"\"\n\n[[states]]\nid = \"default\"\n"),
        "flow" => format!("name = \"{name}\"\nnodes = []\nedges = []\n"),
        _ => format!(
            "# Tokens: `path = \"value\"` under a group; a token table may add type, tier and modes.\n[{name}]\n"
        ),
    }
}

/// Check `text` against the schema of `kind`; flows have no schema yet, so they only have to be
/// TOML.
fn validate(kind: &str, text: &str) -> Result<(), String> {
    match kind {
        "screen" => crunk_spec::parse_screen_file(text)
            .map(drop)
            .map_err(|e| e.to_string()),
        "component" => crunk_spec::parse_component_file(text)
            .map(drop)
            .map_err(|e| e.to_string()),
        "token" => crunk_tokens::dialect::parse(text, "new")
            .map(drop)
            .map_err(|e| e.to_string()),
        _ => text
            .parse::<toml_edit::DocumentMut>()
            .map(drop)
            .map_err(|e| e.to_string()),
    }
}

/// `source` with its identity key (if the kind has one) set to `name` and the review state dropped, keeping comments
/// and line endings.
fn rename_source(kind: &str, source: &str, name: &str) -> Result<String, String> {
    let (_, _, key) = layout(kind);
    let Some(key) = key else {
        return Ok(source.to_owned());
    };
    let mut doc: toml_edit::DocumentMut = source.parse().map_err(|e| format!("{e}"))?;
    let decor = doc
        .get(key)
        .and_then(toml_edit::Item::as_value)
        .map(|v| v.decor().clone());
    let mut value = toml_edit::value(name);
    if let (Some(decor), Some(v)) = (decor, value.as_value_mut()) {
        *v.decor_mut() = decor;
    }
    // Assigning through the index keeps the key (and the comments before it) in place.
    doc[key] = value;
    // A copy is a new subject: it carries neither the status nor the hash of the original.
    for stale in ["status", "content_hash"] {
        doc.remove(stale);
    }
    Ok(match_line_endings(source, &doc.to_string()))
}

/// Read and build the text for the new file, validated; touches nothing.
fn build(kind: &str, name: &str, from: Option<&Path>) -> Result<String, NewError> {
    let Some(src) = from else {
        let text = skeleton(kind, name);
        validate(kind, &text).map_err(NewError::Schema)?;
        return Ok(text);
    };
    let shown = gob_path::Shown::of(src).as_str().to_owned();
    let source =
        std::fs::read_to_string(src).map_err(|e| NewError::From(shown.clone(), e.to_string()))?;
    validate(kind, &source)
        .map_err(|e| NewError::From(shown.clone(), format!("not a valid {kind} file: {e}")))?;
    let text = rename_source(kind, &source, name).map_err(|e| NewError::From(shown, e))?;
    validate(kind, &text).map_err(NewError::Schema)?;
    Ok(text)
}

/// Validate every input and compute the target; nothing is written.
fn plan(root: &Path, kind: &str, name: &str, from: Option<&Path>) -> Result<Plan, NewError> {
    validate_name(name)?;
    let (dir, suffix, _) = layout(kind);
    let path = root
        .join("design")
        .join(dir)
        .join(format!("{name}{suffix}"));
    check_target(root, &path)?;
    let text = build(kind, name, from)?;
    tracing::debug!(kind, name, bytes = text.len(), "new planned");
    Ok(Plan { path, text })
}

/// Refuse an existing target (a dangling symlink counts) and any symlink or non-directory on the
/// way from the root to the target.
fn check_target(root: &Path, path: &Path) -> Result<(), NewError> {
    let rel = relative(root, path);
    let mut cur = root.to_path_buf();
    let parent = path.parent().unwrap_or(root);
    let tail = parent.strip_prefix(root).unwrap_or(parent);
    for part in tail.components() {
        cur.push(part);
        match std::fs::symlink_metadata(&cur) {
            Ok(m) if m.file_type().is_symlink() || !m.is_dir() => {
                return Err(NewError::Path(format!(
                    "{} is a symlink or not a directory; refusing to write through it",
                    relative(root, &cur)
                )));
            }
            Ok(_) => {}
            Err(_) => break,
        }
    }
    if std::fs::symlink_metadata(path).is_ok() {
        return Err(NewError::Exists(rel));
    }
    Ok(())
}

/// Create the missing parent directories and write `text` atomically; on failure remove the
/// directories created here.
fn write_new(path: &Path, text: &str, root: &Path) -> Result<(), NewError> {
    let parent = path.parent().unwrap_or(root);
    let mut missing: Vec<&Path> = parent
        .ancestors()
        .take_while(|a| *a != root && !a.exists())
        .collect();
    let fail = |e: std::io::Error| NewError::Write(relative(root, path), e.to_string());
    std::fs::create_dir_all(parent).map_err(fail)?;
    // `check_target` ran before; look again right before the rename so a file that appeared since
    // is not replaced.
    if std::fs::symlink_metadata(path).is_ok() {
        remove_created(&mut missing);
        return Err(NewError::Exists(relative(root, path)));
    }
    if let Err(e) = gob_fs::write_atomic(path, text.as_bytes()) {
        tracing::warn!(error = %e, "new: write failed, removing created directories");
        remove_created(&mut missing);
        return Err(fail(e));
    }
    Ok(())
}

/// Remove the directories in `dirs` (deepest first), ignoring any that are not empty.
fn remove_created(dirs: &mut Vec<&Path>) {
    for d in dirs.drain(..) {
        if let Err(e) = std::fs::remove_dir(d) {
            tracing::debug!(error = %e, "new: created directory kept");
        }
    }
}

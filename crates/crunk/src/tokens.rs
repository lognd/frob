//! `tokens [--target T] [--check]`: write, preview or drift-check the generated token files.
//!
//! Bare `tokens` writes every configured file atomically (`[project] tokens_file`, `[tailwind]
//! tokens_file`, `[tokens] json_file`). `--target css|json|tailwind` previews that one export
//! (rendered text is the output; nothing is written). `--check` compares the files on disk with
//! the render and exits 1 naming every missing or drifted file; it never writes. The Python
//! crunk's `--format` is `--target` here because `--format` is the global output format.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::path::{Path, PathBuf};

use crunk_tokens::export::{self, ExportError, Status, Target};
use gob_cli::clap::{Arg, ArgAction, ArgMatches, builder::PossibleValuesParser};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::PRODUCT;

/// Write, preview (`--target`) or drift-check (`--check`) the generated token files.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "tokens",
    product = "crunk",
    idempotent = true,
    dry_run,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Tokens {
    target: Option<Target>,
    check: bool,
}

/// What `tokens` did.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    /// Files were written.
    Write,
    /// Files were not written because of `--dry-run`.
    DryRun,
    /// One export was rendered to the output.
    Preview,
    /// Files on disk were compared with the render.
    Check,
}

/// One generated file.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct FileRow {
    /// `css`, `json` or `tailwind`.
    pub target: String,
    /// Path relative to the project root.
    pub path: String,
    /// `clean`, `missing` or `drifted` under `--check`; absent otherwise.
    pub status: Option<String>,
    /// True when the file differs only at the GENERATED banner line.
    pub banner_only: bool,
}

/// A Tailwind default theme key an un-namespaced export would redefine.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CollisionRow {
    /// The token whose key collides.
    pub token: String,
    /// The Tailwind theme section.
    pub section: String,
    /// The shared theme key.
    pub key: String,
}

/// Output of `tokens`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TokensData {
    /// What ran.
    pub mode: Mode,
    /// The previewed target, under `--target`.
    pub target: Option<String>,
    /// Worst status of the files, under `--check`.
    pub status: Option<String>,
    /// The generated files (written, previewed or checked).
    pub files: Vec<FileRow>,
    /// The rendered text, under `--target`.
    pub content: Option<String>,
    /// Tailwind default theme keys the un-namespaced export would redefine.
    pub collisions: Vec<CollisionRow>,
}

impl Command for Tokens {
    type Data = TokensData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("target")
                .long("target")
                .value_name("TARGET")
                .value_parser(PossibleValuesParser::new(Target::ALL.map(Target::name)))
                .help("Print this export to the output instead of writing the files"),
        )
        .arg(
            Arg::new("check")
                .long("check")
                .action(ArgAction::SetTrue)
                .help("Compare the files on disk with the render; exit 1 on drift, write nothing"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            target: m
                .get_one::<String>("target")
                .and_then(|name| Target::parse(name)),
            check: m.get_flag("check"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<TokensData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| {
            tracing::info!(error = %e, "tokens: spec did not load");
            refusal(
                "E-SPEC",
                &format!("crunk.toml is not a valid design spec: {e}"),
            )
            .with_remedy("fix crunk.toml as described, then rerun")
        })?;
        if self.check {
            return check(&root, &spec);
        }
        if let Some(target) = self.target {
            return preview(&root, &spec, target);
        }
        write(&root, &spec, ctx.dry_run)
    }
}

fn refusal(code: &str, message: &str) -> Refusal {
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
}

/// Map an export failure onto the exit table: a bad spec or an unreadable file is a refusal.
fn export_error(err: ExportError) -> CliError {
    tracing::info!(error = %err, "tokens failed");
    match err {
        ExportError::Token(e) => refusal("E-TOKENS", &e.to_string())
            .with_remedy("rename one of the colliding entries in crunk.toml")
            .into(),
        ExportError::Read { .. } | ExportError::Write { .. } => {
            refusal("E-TOKENS-IO", &err.to_string())
                .with_remedy("fix the path or its permissions, then rerun")
                .into()
        }
    }
}

fn relative(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn collision_rows(found: &[crunk_tokens::ThemeCollision]) -> Vec<CollisionRow> {
    found
        .iter()
        .map(|c| CollisionRow {
            token: c.token.clone(),
            section: c.section.name().to_owned(),
            key: c.key.clone(),
        })
        .collect()
}

fn collision_warnings(found: &[crunk_tokens::ThemeCollision]) -> Vec<String> {
    found
        .iter()
        .map(|c| {
            format!(
                "theme.extend.{} key `{}` ({}) collides with a Tailwind default; set \
                 [tailwind] namespace_keys = true or rename the scale step",
                c.section.name(),
                c.key,
                c.token
            )
        })
        .collect()
}

fn check(root: &Path, spec: &crunk_spec::DesignSpec) -> Outcome<TokensData> {
    let report = export::check(spec).map_err(export_error)?;
    let worst = report.worst();
    let files: Vec<FileRow> = report
        .files
        .iter()
        .map(|f| FileRow {
            target: f.target.name().to_owned(),
            path: relative(root, &f.path),
            status: Some(f.status.word().to_owned()),
            banner_only: f.banner_only,
        })
        .collect();
    let mut warnings = report.warnings.clone();
    warnings.extend(collision_warnings(&report.collisions));
    let data = TokensData {
        mode: Mode::Check,
        target: None,
        status: Some(worst.word().to_owned()),
        files,
        content: None,
        collisions: collision_rows(&report.collisions),
    };
    if worst == Status::Clean {
        let mut payload = Payload::new(data)
            .with_already(true)
            .with_rendered(vec![format!("tokens: {}", worst.word())]);
        payload.warnings = warnings;
        return Ok(payload);
    }
    let named: Vec<String> = report
        .dirty()
        .map(|f| {
            let note = if f.banner_only {
                " (banner line only)"
            } else {
                ""
            };
            format!("{} ({}{note})", relative(root, &f.path), f.status.word())
        })
        .collect();
    let message = format!(
        "tokens: {}: {}; run `crunk tokens` to regenerate",
        worst.word(),
        named.join(", ")
    );
    let value: Value = serde_json::to_value(&data).map_err(CliError::internal)?;
    Err(CliError::Gate {
        message,
        data: value,
        warnings,
    })
}

fn preview(root: &Path, spec: &crunk_spec::DesignSpec, target: Target) -> Outcome<TokensData> {
    let content =
        export::render_target(spec, target).map_err(|e| export_error(ExportError::Token(e)))?;
    let path: Option<PathBuf> = target.exporter().path(spec);
    tracing::debug!(%target, bytes = content.len(), "tokens preview rendered");
    let rows: Vec<String> = content.split_terminator('\n').map(str::to_owned).collect();
    let data = TokensData {
        mode: Mode::Preview,
        target: Some(target.name().to_owned()),
        status: None,
        files: path
            .iter()
            .map(|p| FileRow {
                target: target.name().to_owned(),
                path: relative(root, p),
                status: None,
                banner_only: false,
            })
            .collect(),
        content: Some(content),
        collisions: Vec::new(),
    };
    Ok(Payload::new(data).with_rendered(rows))
}

fn write(root: &Path, spec: &crunk_spec::DesignSpec, dry_run: bool) -> Outcome<TokensData> {
    let (files, collisions, warnings) = if dry_run {
        let rendered =
            export::render_managed(spec).map_err(|e| export_error(ExportError::Token(e)))?;
        let files = rendered
            .iter()
            .map(|r| (r.target, r.path.clone()))
            .collect::<Vec<_>>();
        (files, Vec::new(), Vec::new())
    } else {
        let report = export::write_all(spec).map_err(export_error)?;
        let files = report
            .written
            .iter()
            .map(|w| (w.target, w.path.clone()))
            .collect();
        (files, report.collisions, report.warnings)
    };
    let rows: Vec<String> = files.iter().map(|(_, p)| relative(root, p)).collect();
    let mut warnings = warnings;
    warnings.extend(collision_warnings(&collisions));
    let data = TokensData {
        mode: if dry_run { Mode::DryRun } else { Mode::Write },
        target: None,
        status: None,
        files: files
            .iter()
            .map(|(t, p)| FileRow {
                target: t.name().to_owned(),
                path: relative(root, p),
                status: None,
                banner_only: false,
            })
            .collect(),
        content: None,
        collisions: collision_rows(&collisions),
    };
    let mut payload = Payload::new(data).with_rendered(rows);
    payload.warnings = warnings;
    Ok(payload)
}

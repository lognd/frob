//! `tokens [--target X] [--check]`: render the design tokens from `crunk.toml`.
//!
//! Bare `tokens` writes every configured file atomically; `--target` previews one target on
//! stdout and writes nothing; `--check` compares the files on disk with the render and exits 1
//! on drift (CSS byte for byte, JSON after parsing).

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use crunk_tokens::TokenSet;
use crunk_tokens::export::{self, Drift, GeneratedFile, Target};
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

/// Render the design tokens; bare writes, `--target` previews, `--check` gates on drift.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "tokens",
    product = "crunk",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Tokens {
    target: Option<Target>,
    check: bool,
}

/// One generated file and what happened to it.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TokenFile {
    /// Target name (`css`, `json`, `tailwind`).
    pub target: String,
    /// Absolute path of the file.
    pub path: String,
    /// `written`, `clean`, `drifted` or `missing`.
    pub status: String,
}

/// Output of `tokens`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TokensData {
    /// True under `--check` (nothing was written).
    pub check: bool,
    /// The previewed target, when `--target` was given without `--check`.
    pub preview: Option<String>,
    /// Files written or compared (empty for a preview).
    pub files: Vec<TokenFile>,
}

impl Command for Tokens {
    type Data = TokensData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("target")
                .long("target")
                .value_name("TARGET")
                .value_parser(["css", "json", "tailwind"])
                .help(
                    "Preview one target on stdout and write nothing (with --check: check only it)",
                ),
        )
        .arg(
            Arg::new("check")
                .long("check")
                .action(ArgAction::SetTrue)
                .help("Compare the files on disk with the render and exit 1 on drift"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let target = match m.get_one::<String>("target") {
            None => None,
            Some(name) => Some(
                Target::parse(name)
                    .ok_or_else(|| CliError::Usage(format!("unknown tokens target `{name}`")))?,
            ),
        };
        Ok(Self {
            target,
            check: m.get_flag("check"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<TokensData> {
        let root = gob_product::workspace::locate_root(crate::PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| CliError::Usage(e.to_string()))?;
        let tokens = TokenSet::from_spec(&spec).map_err(|e| CliError::Usage(e.to_string()))?;
        let warnings = export::warnings(&spec, &tokens);

        if let (Some(target), false) = (self.target, self.check) {
            let text = export::render(&spec, &tokens, target);
            tracing::info!(target = target.name(), "tokens preview, nothing written");
            let data = TokensData {
                check: false,
                preview: Some(target.name().to_owned()),
                files: Vec::new(),
            };
            let row = text.strip_suffix('\n').unwrap_or(&text).to_owned();
            return Ok(with_warnings(
                Payload::new(data).with_rendered(vec![row]),
                warnings,
            ));
        }

        let mut files = export::generated_files(&spec, &tokens);
        if let Some(target) = self.target {
            files.retain(|f| f.target == target);
            if files.is_empty() {
                return Err(CliError::Usage(format!(
                    "crunk.toml configures no file for target `{}`",
                    target.name()
                )));
            }
        }
        if self.check {
            check(&files, warnings)
        } else {
            write(&files, warnings)
        }
    }
}

/// Attach `warnings` to `payload`.
fn with_warnings(mut payload: Payload<TokensData>, warnings: Vec<String>) -> Payload<TokensData> {
    payload.warnings.extend(warnings);
    payload
}

/// Write every file atomically, creating parent directories.
fn write(files: &[GeneratedFile], warnings: Vec<String>) -> Outcome<TokensData> {
    let mut out = Vec::new();
    for f in files {
        if let Some(dir) = f.path.parent() {
            std::fs::create_dir_all(dir)
                .map_err(|e| CliError::internal(format!("cannot create {}: {e}", dir.display())))?;
        }
        gob_fs::write_atomic(&f.path, f.content.as_bytes())
            .map_err(|e| CliError::internal(format!("cannot write {}: {e}", f.path.display())))?;
        tracing::info!(path = %f.path.display(), target = f.target.name(), "token file written");
        out.push(entry(f, "written"));
    }
    let rows = out.iter().map(|e| e.path.clone()).collect();
    let data = TokensData {
        check: false,
        preview: None,
        files: out,
    };
    Ok(with_warnings(
        Payload::new(data).with_rendered(rows),
        warnings,
    ))
}

/// Compare every file with disk; exit 1 naming each drifted or missing file.
fn check(files: &[GeneratedFile], warnings: Vec<String>) -> Outcome<TokensData> {
    let mut out = Vec::new();
    let mut bad = Vec::new();
    for f in files {
        let disk = std::fs::read(&f.path).ok();
        let drift = export::compare(f, disk.as_deref());
        let status = match drift {
            Drift::Clean => "clean",
            Drift::Drifted => "drifted",
            Drift::Missing => "missing",
        };
        tracing::info!(path = %f.path.display(), status, "token file checked");
        if drift != Drift::Clean {
            bad.push(format!("{} ({status})", f.path.display()));
        }
        out.push(entry(f, status));
    }
    let data = TokensData {
        check: true,
        preview: None,
        files: out,
    };
    if bad.is_empty() {
        return Ok(with_warnings(
            Payload::new(data).with_rendered(vec!["tokens: clean".to_owned()]),
            warnings,
        ));
    }
    let value = serde_json::to_value(&data).map_err(CliError::internal)?;
    Err(CliError::Gate {
        message: format!("tokens: drift in {}", bad.join(", ")),
        data: value,
        warnings,
    })
}

/// One [`TokenFile`] row.
fn entry(f: &GeneratedFile, status: &str) -> TokenFile {
    TokenFile {
        target: f.target.name().to_owned(),
        path: f.path.display().to_string(),
        status: status.to_owned(),
    }
}

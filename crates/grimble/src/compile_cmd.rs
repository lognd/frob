//! `compile [PATH...]`: parse and check GRL rule files with the `gob-plan` compiler.

// frob:ticket 01M4M5CQ9529KH526299QXXFVF
// frob:ticket 01M4M5CRRV5A6P5WHHVHXP981B

use std::path::{Path, PathBuf};

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_path::{RelPath, Shown};
use gob_plan::catalog::ConfigSchema;
use gob_plan::check::{Severity, compile_diagnostics_with, compile_report_with};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::locate_root;

/// Directories `compile` never descends into when it searches for `.grl` files.
const SKIPPED_DIRS: [&str; 4] = [".git", "target", "node_modules", ".jj"];

/// The config schema document the binary ships, embedded so `compile` needs no file on disk.
const SHIPPED_CONFIG_SCHEMA: &str = include_str!("../../../docs/schemas/config.json");

// frob:ticket 01M4M5CRRV5A6P5WHHVHXP981B
/// Type the `config.*` relations from a schema document; `None` (checking off) when it is malformed or types nothing.
pub fn schema_from_text(text: &str) -> Option<ConfigSchema> {
    let doc = match serde_json::from_str(text) {
        Ok(doc) => doc,
        Err(e) => {
            tracing::warn!(error = %e, "config schema is not valid JSON; config paths are unchecked");
            return None;
        }
    };
    let schema = ConfigSchema::from_json(&doc);
    if schema.is_empty() {
        tracing::warn!("config schema types nothing; config paths are unchecked");
        return None;
    }
    Some(schema)
}

/// Check GRL rule files and print the compiler report; exits 1 when any file has an error.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "compile",
    product = "grimble",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Compile {
    paths: Vec<String>,
}

/// The result of compiling one rule file.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CompiledFile {
    /// Path as given, or relative to the workspace root when discovered.
    pub path: String,
    /// Number of error diagnostics.
    pub errors: usize,
    /// Number of warning diagnostics.
    pub warnings: usize,
    /// The rendered compiler report; empty when the file has no diagnostics.
    pub report: String,
}

/// Output of `compile`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CompileData {
    /// One entry per rule file, in path order.
    pub files: Vec<CompiledFile>,
}

/// Every `.grl` file under `dir`, as paths relative to `root`, unsorted.
fn discover(root: &Path, dir: &Path, out: &mut Vec<String>) -> std::io::Result<()> {
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name();
        if entry.file_type()?.is_dir() {
            if !SKIPPED_DIRS.iter().any(|s| name == *s) {
                discover(root, &path, out)?;
            }
        } else if path.extension().is_some_and(|e| e == "grl") {
            match RelPath::from_host(root, &path) {
                Ok(rel) => out.push(rel.as_str().to_owned()),
                Err(e) => {
                    tracing::warn!(path = %Shown::of(&path), error = %e, "skipping a path outside the root");
                }
            }
        }
    }
    Ok(())
}

/// `Compile` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct CompileArgs {
    #[arg(
        num_args = 0..,
        value_name = "PATH",
        help = "Rule files to check; default every .grl file under the workspace root"
    )]
    paths: Vec<String>,
}

impl Command for Compile {
    type Data = CompileData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<CompileArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<CompileArgs>(m)?;
        Ok(Self { paths: a.paths })
    }

    fn run(&self, ctx: &Context) -> Outcome<CompileData> {
        let root = locate_root(&ctx.cwd);
        let (base, mut paths): (PathBuf, Vec<String>) = if self.paths.is_empty() {
            let mut found = Vec::new();
            discover(&root, &root, &mut found)
                .map_err(|e| CliError::internal(format!("cannot search for .grl files: {e}")))?;
            (root, found)
        } else {
            (ctx.cwd.clone(), self.paths.clone())
        };
        paths.sort();
        paths.dedup();
        let schema = schema_from_text(SHIPPED_CONFIG_SCHEMA);
        let mut files = Vec::new();
        for path in paths {
            let source = std::fs::read_to_string(base.join(&path))
                .map_err(|e| CliError::Usage(format!("cannot read rule file {path}: {e}")))?;
            let diagnostics = compile_diagnostics_with(&path, &source, schema.as_ref());
            let errors = diagnostics
                .iter()
                .filter(|d| d.severity == Severity::Error)
                .count();
            let report = if diagnostics.is_empty() {
                String::new()
            } else {
                compile_report_with(&path, &source, schema.as_ref())
            };
            tracing::debug!(%path, errors, "compiled GRL file");
            files.push(CompiledFile {
                path,
                errors,
                warnings: diagnostics.len() - errors,
                report,
            });
        }
        let data = CompileData { files };
        let failed = data.files.iter().filter(|f| f.errors > 0).count();
        if failed > 0 {
            let message = data
                .files
                .iter()
                .filter(|f| !f.report.is_empty())
                .map(|f| f.report.trim_end())
                .collect::<Vec<_>>()
                .join("\n\n");
            let value = serde_json::to_value(&data).map_err(CliError::internal)?;
            return Err(CliError::Gate {
                message,
                data: value,
                warnings: Vec::new(),
            });
        }
        let mut payload = Payload::new(data.clone());
        payload.warnings = data
            .files
            .iter()
            .filter(|f| !f.report.is_empty())
            .map(|f| f.report.trim_end().to_owned())
            .collect();
        Ok(payload)
    }
}

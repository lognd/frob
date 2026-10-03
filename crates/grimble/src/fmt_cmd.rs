//! `fmt [--check]`: the `grimble-model` formatter over every `.grmb` file.

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_model::{format_file, parse_file};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{check_error, locate_root};

/// Rewrite every `.grmb` file in alpha-normal form; `--check` only reports and exits 1 on a difference.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "fmt",
    product = "grimble",
    idempotent = true,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Fmt {
    check: bool,
}

/// A file fmt would not rewrite.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Skipped {
    /// Repo-relative path.
    pub path: String,
    /// Why (a hole, an opaque or refused file).
    pub reason: String,
}

/// Output of `fmt`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct FmtData {
    /// True under `--check` (nothing was written).
    pub check: bool,
    /// Files examined.
    pub files: usize,
    /// Files whose text differs from the formatted text (rewritten unless `--check`).
    pub changed: Vec<String>,
    /// Files fmt refused to touch.
    pub skipped: Vec<Skipped>,
}

impl Command for Fmt {
    type Data = FmtData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("check")
                .long("check")
                .action(ArgAction::SetTrue)
                .help("Report unformatted files and exit 1 instead of rewriting them"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            check: m.get_flag("check"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<FmtData> {
        let root = locate_root(&ctx.cwd);
        let paths = grimble_check::survey(&root).map_err(check_error)?.models;
        let mut data = FmtData {
            check: self.check,
            files: paths.len(),
            changed: Vec::new(),
            skipped: Vec::new(),
        };
        for path in &paths {
            let full = root.join(path);
            let bytes = std::fs::read(&full)
                .map_err(|e| CliError::internal(format!("cannot read {path}: {e}")))?;
            let parsed = parse_file(path, &bytes);
            match format_file(&parsed) {
                Err(e) => {
                    tracing::warn!(%path, error = %e, "fmt skipped a damaged file");
                    data.skipped.push(Skipped {
                        path: path.clone(),
                        reason: e.to_string(),
                    });
                }
                Ok(text) if text.as_bytes() == bytes.as_slice() => {
                    tracing::debug!(%path, "already formatted");
                }
                Ok(text) => {
                    data.changed.push(path.clone());
                    if !self.check {
                        std::fs::write(&full, text)
                            .map_err(|e| CliError::internal(format!("cannot write {path}: {e}")))?;
                        tracing::info!(%path, "file formatted");
                    }
                }
            }
        }
        if self.check && (!data.changed.is_empty() || !data.skipped.is_empty()) {
            let message = format!(
                "{} file(s) not formatted, {} file(s) not checkable: {}",
                data.changed.len(),
                data.skipped.len(),
                data.changed
                    .iter()
                    .cloned()
                    .chain(data.skipped.iter().map(|s| s.path.clone()))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            let value = serde_json::to_value(&data).map_err(CliError::internal)?;
            return Err(CliError::Gate {
                message,
                data: value,
                warnings: Vec::new(),
            });
        }
        let mut payload = Payload::new(data.clone()).with_already(data.changed.is_empty());
        payload.warnings = data
            .skipped
            .iter()
            .map(|s| format!("{}: {}", s.path, s.reason))
            .collect();
        Ok(payload)
    }
}

//! `frob doc remap`: rewrite every reference to a moved doc anchor using `docs/MOVED.toml`.
//!
//! The map is validated against HEAD first; a row whose target is not a heading of the new file
//! refuses (exit 3) naming the row and writes nothing. `tickets/` and `notes/` are never touched.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

use gob_path::Shown;

use frob_doc::{MOVED_PATH, MovedMap, RemapError};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::Located;

/// Output of `frob doc remap`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DocRemapData {
    /// Rows in the map.
    pub rows: usize,
    /// Repo-relative files whose references changed.
    pub files: Vec<String>,
    /// Whether the files were written (false under `--dry-run`).
    pub written: bool,
}

/// The flags of `doc remap`: none beyond the global ones.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct Args {}

/// Rewrite markdown links, `frob:doc` targets, `.grmb` refs and prose citations to the anchors named in `docs/MOVED.toml`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "doc remap",
    product = "frob",
    idempotent = true,
    dry_run = true,
    exits(ok, refused, usage, internal)
)]
pub struct DocRemap;

/// The refusal for a failed plan, naming each offending row.
fn refuse(e: &RemapError) -> CliError {
    let (code, message, remedy) = match e {
        RemapError::Refused(rows) => {
            let named: Vec<String> = rows
                .iter()
                .map(|r| {
                    format!(
                        "{MOVED_PATH} row \"{}\" = \"{}\": {}",
                        r.key, r.value, r.reason
                    )
                })
                .collect();
            (
                "E-DOC-REMAP-ROW",
                named.join("; "),
                "fix the row in docs/MOVED.toml so its target is a heading at HEAD",
            )
        }
        RemapError::NoMap => (
            "E-DOC-REMAP-NO-MAP",
            e.to_string(),
            "create docs/MOVED.toml with a [moved] table",
        ),
        RemapError::Moved(_) => (
            "E-DOC-REMAP-MAP",
            e.to_string(),
            "fix docs/MOVED.toml (it must parse and every row must settle)",
        ),
        RemapError::Git(_) | RemapError::Io(_) => {
            return CliError::internal(e.to_string());
        }
    };
    tracing::info!(code, "doc remap refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, message)
        .with_remedy(remedy)
        .into()
}

impl Command for DocRemap {
    type Data = DocRemapData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<Args>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        gob_cli::parse::<Args>(m)?;
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<DocRemapData> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let path = root.join(MOVED_PATH);
        let text = std::fs::read_to_string(&path).map_err(|_| refuse(&RemapError::NoMap))?;
        let map = MovedMap::parse(&text).map_err(|e| refuse(&RemapError::Moved(e)))?;
        let plan = frob_doc::remap(&repo, &root, &map).map_err(|e| refuse(&e))?;
        if !ctx.dry_run {
            for change in &plan.changes {
                let target = root.join(&change.path);
                std::fs::write(&target, &change.new_text).map_err(CliError::internal)?;
                tracing::info!(path = %Shown::of(&target), "doc remap wrote file");
            }
        }
        let files: Vec<String> = plan.changes.iter().map(|c| c.path.clone()).collect();
        let verb = if ctx.dry_run {
            "would rewrite"
        } else {
            "rewrote"
        };
        let mut rows = vec![format!(
            "{verb} {} file(s) from {} map row(s)",
            files.len(),
            plan.rows
        )];
        rows.extend(files.iter().map(|f| format!("  {f}")));
        Ok(Payload::new(DocRemapData {
            rows: plan.rows,
            files,
            written: !ctx.dry_run,
        })
        .with_rendered(rows))
    }
}

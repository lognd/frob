//! `import dtcg` / `export dtcg`: move a W3C DTCG token file into and out of the project losslessly.
//!
//! `import dtcg INPUT` validates INPUT and stores the canonical document (default
//! `design/tokens.dtcg.json`, or `--store`); `export dtcg` reads the store back and prints it, or
//! writes it to `--out`. The two compose to the identity up to key order.

// frob:ticket 01M4CXQYFA9ACDVWF4R62C50FH

use std::path::{Path, PathBuf};

use crunk_tokens::interchange::{Document, DtcgError, Summary};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// Where `import dtcg` keeps the document, relative to the project root.
const DEFAULT_STORE: &str = "design/tokens.dtcg.json";

/// Validate a DTCG file and store it as the project's token interchange document.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "import dtcg",
    product = "crunk",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct ImportDtcg {
    input: PathBuf,
    store: Option<PathBuf>,
}

/// Print the stored DTCG document, or write it to `--out`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "export dtcg",
    product = "crunk",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct ExportDtcg {
    store: Option<PathBuf>,
    out: Option<PathBuf>,
}

/// Output of `import dtcg` and `export dtcg`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DtcgData {
    /// Where the document was read from or stored, relative to the project root when inside it.
    pub path: String,
    /// Where the document was written, when it was.
    pub written: Option<String>,
    /// Tokens in the document.
    pub tokens: usize,
    /// Groups in the document.
    pub groups: usize,
    /// Tokens that are whole-value aliases.
    pub aliases: usize,
    /// The document text, for `export dtcg` without `--out`.
    pub content: Option<String>,
}

/// `ImportDtcg` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ImportArgs {
    #[arg(value_name = "INPUT", help = "The DTCG .tokens.json file to import")]
    input: PathBuf,
    #[arg(
        long,
        value_name = "PATH",
        help = "Where to keep the document (default design/tokens.dtcg.json)"
    )]
    store: Option<PathBuf>,
}

/// `ExportDtcg` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ExportArgs {
    #[arg(
        long,
        value_name = "PATH",
        help = "The stored document (default design/tokens.dtcg.json)"
    )]
    store: Option<PathBuf>,
    #[arg(long, value_name = "PATH", help = "Write here instead of printing")]
    out: Option<PathBuf>,
}

impl Command for ImportDtcg {
    type Data = DtcgData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ImportArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ImportArgs>(m)?;
        Ok(Self {
            input: a.input,
            store: a.store,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<DtcgData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let input = absolute(&ctx.cwd, &self.input);
        let store = store_path(&root, &ctx.cwd, self.store.as_deref());
        let doc = Document::read(&input).map_err(|e| dtcg_error(&e))?;
        if ctx.dry_run {
            tracing::info!(input = %input.to_string_lossy(), "import dtcg: dry run, nothing written");
            return Ok(report(&root, &input, None, &doc, None));
        }
        doc.write(&store).map_err(|e| dtcg_error(&e))?;
        tracing::info!(store = %store.to_string_lossy(), "import dtcg: stored");
        Ok(report(&root, &input, Some(&store), &doc, None))
    }
}

impl Command for ExportDtcg {
    type Data = DtcgData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ExportArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ExportArgs>(m)?;
        Ok(Self {
            store: a.store,
            out: a.out,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<DtcgData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let store = store_path(&root, &ctx.cwd, self.store.as_deref());
        let doc = Document::read(&store).map_err(|e| dtcg_error(&e))?;
        let Some(out) = &self.out else {
            tracing::info!(store = %store.to_string_lossy(), "export dtcg: printed");
            let text = doc.render();
            let lines = text.lines().map(str::to_owned).collect::<Vec<_>>();
            return Ok(report(&root, &store, None, &doc, Some(text)).with_rendered(lines));
        };
        let out = absolute(&ctx.cwd, out);
        if !ctx.dry_run {
            doc.write(&out).map_err(|e| dtcg_error(&e))?;
        }
        Ok(report(&root, &store, Some(&out), &doc, None))
    }
}

fn absolute(cwd: &Path, path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        cwd.join(path)
    }
}

fn store_path(root: &Path, cwd: &Path, store: Option<&Path>) -> PathBuf {
    store.map_or_else(|| root.join(DEFAULT_STORE), |p| absolute(cwd, p))
}

// frob:ticket 01M5PC8M49F53YSPKKT7XXMDFH
/// A path relative to the project root when inside it, as text.
pub(crate) fn relative(root: &Path, path: &Path) -> String {
    // Always `/`-separated so it matches the check report's file table on every platform.
    gob_path::forward_slashes(path.strip_prefix(root).unwrap_or(path))
}

fn report(
    root: &Path,
    source: &Path,
    written: Option<&Path>,
    doc: &Document,
    content: Option<String>,
) -> Payload<DtcgData> {
    let Summary {
        tokens,
        groups,
        aliases,
    } = doc.summary();
    let written = written.map(|p| relative(root, p));
    let summary = format!("{tokens} tokens, {groups} groups, {aliases} aliases");
    let line = match &written {
        Some(w) => format!("{} -> {w}: {summary}", relative(root, source)),
        None => format!("{}: {summary}", relative(root, source)),
    };
    Payload::new(DtcgData {
        path: relative(root, source),
        written,
        tokens,
        groups,
        aliases,
        content,
    })
    .with_rendered(vec![line])
}

/// Map a DTCG failure onto the exit table: an invalid or unreadable file is a refusal.
fn dtcg_error(err: &DtcgError) -> CliError {
    tracing::info!(error = %err, "dtcg verb failed");
    let (code, remedy) = match err {
        DtcgError::Io { .. } => ("E-DTCG-IO", "fix the path or its permissions, then rerun"),
        _ => ("E-DTCG", "fix the DTCG file as described, then rerun"),
    };
    Refusal::new(code, RefusalClass::GuardNeedsAction, err.to_string())
        .with_remedy(remedy)
        .into()
}

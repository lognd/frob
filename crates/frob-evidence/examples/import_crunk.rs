//! Runner of the crunk ticket import (`cargo run -p frob-evidence --example import_crunk`), ~JBTM6EF.
//!
//! A dry run is the default and writes nothing; `--write` is the retirement step and is
//! run by the coordinator, never by the ticket that built this importer.
// frob:ticket 01M43AVMN1DWBVTYW37JBTM6EF

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::Parser;
use frob_evidence::import_crunk;
use frob_evidence::import_v1;

/// Command-line arguments of the crunk import.
#[derive(Debug, Parser)]
#[command(
    name = "import_crunk",
    about = "Selectively import the crunk repository's tickets"
)]
struct Args {
    /// An already extracted crunk `tickets/` directory; without it the tickets are fetched with `gh`.
    #[arg(long)]
    from: Option<PathBuf>,
    /// The git ref to fetch when `--from` is absent.
    #[arg(long, default_value = "main")]
    git_ref: String,
    /// The selection file.
    #[arg(long, default_value = "docs/migration/crunk-selection.toml")]
    selection: PathBuf,
    /// The v2 ledger to merge into (required with `--write`).
    #[arg(long, default_value = "tickets")]
    to: PathBuf,
    /// Really write the tickets; the default is a dry run.
    #[arg(long)]
    write: bool,
}

/// Write `text` and a newline to stdout; a closed pipe is not worth failing the run over.
fn emit(text: &str) {
    let mut out = std::io::stdout().lock();
    if writeln!(out, "{text}").is_err() {
        tracing::debug!("stdout closed while emitting");
    }
}

/// Fetch (or reuse) the tickets, run the import and print the dry-run report.
fn run(args: &Args, work: &Path) -> Result<(), String> {
    let from = match &args.from {
        Some(dir) => dir.clone(),
        None => import_crunk::fetch(import_crunk::REPO, &args.git_ref, work)
            .map_err(|e| format!("error: {e}"))?,
    };
    let opts = import_crunk::options(
        from,
        args.to.clone(),
        args.selection.clone(),
        !args.write,
        gob_git::Repo::discover(".")
            .ok()
            .map(|r| r.common_dir().to_path_buf()),
    );
    let report = import_v1::run(&opts).map_err(|e| format!("error: {e}"))?;
    for line in import_v1::render_selection(&report.dispositions, &report.open, &report.skipped) {
        emit(&line);
    }
    emit("");
    for line in import_crunk::render_dispositions(&report) {
        emit(&line);
    }
    emit("");
    emit(&format!(
        "== redaction: private-term rules loaded: {}; tickets rewritten: {}; blocked: {} ==",
        report.private_rules_loaded,
        report.redactions.len(),
        report.blocked.len()
    ));
    for (id, what) in &report.redactions {
        emit(&format!("{id}: {what}"));
    }
    for id in &report.blocked {
        emit(&format!(
            "{id}: BLOCKED, an absolute home path survived redaction"
        ));
    }
    emit(&format!(
        "{} tickets, {} events (aliases {}<id>){}",
        report.rows.len(),
        report.events,
        import_crunk::ALIAS_PREFIX,
        if opts.dry_run {
            " (dry run, nothing written)"
        } else {
            ""
        }
    ));
    emit(&format!("by type: {:?}", report.by_type));
    emit(&format!("by category: {:?}", report.by_category));
    for warning in &report.warnings {
        emit(&format!("warning: {warning}"));
    }
    Ok(())
}

fn main() -> ExitCode {
    let args = Args::parse();
    if let Err(e) = gob_log::init("import-crunk", 0, false) {
        emit(&format!("warning: logging not initialised: {e}"));
    }
    let work = std::env::temp_dir().join(format!("import-crunk-{}", std::process::id()));
    let result = run(&args, &work);
    if work.exists() {
        std::fs::remove_dir_all(&work).ok();
    }
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(msg) => {
            emit(&msg);
            ExitCode::FAILURE
        }
    }
}

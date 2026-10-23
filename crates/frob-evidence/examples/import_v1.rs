//! One-off converter runner: v1 YAML ledger to v2 ULID tickets (`cargo run -p frob-evidence --example import_v1`).
//!
//! Moved out of `gob-dev` (the substrate must not import frob crates); the conversion itself is
//! [`frob_evidence::import_v1`].
// frob:ticket 01M48NCNDQZ27NP0JQ7M8WETW7

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use clap::Parser;
use frob_evidence::import_v1::{self, ImportOptions};
use frob_ledger::model::Category;

/// Category an imported open v1 ticket is created in.
#[derive(Debug, Clone, Copy, clap::ValueEnum)]
enum OpenCategory {
    /// Ready to start.
    Todo,
    /// Awaiting triage.
    Triage,
}

impl From<OpenCategory> for Category {
    fn from(c: OpenCategory) -> Self {
        match c {
            OpenCategory::Todo => Self::Todo,
            OpenCategory::Triage => Self::Triage,
        }
    }
}

/// Command-line arguments of the v1 import.
#[derive(Debug, Parser)]
#[command(
    name = "import_v1",
    about = "Convert the v1 YAML ledger into v2 ULID tickets"
)]
struct Args {
    /// The v1 ledger directory.
    #[arg(long, default_value = "tickets")]
    from: PathBuf,
    /// Where to write the v2 tree (must be empty or absent).
    #[arg(long)]
    to: PathBuf,
    /// Convert and verify in memory; write nothing.
    #[arg(long)]
    dry_run: bool,
    /// A selection file naming which open v1 tickets import; without one every v1 ticket imports.
    #[arg(long)]
    selection: Option<PathBuf>,
    /// Import every v1 ticket as open work, ignoring any selection.
    #[arg(long)]
    all: bool,
    /// `--to` may be an existing v2 ledger: write only new ticket directories; refuse on any collision.
    #[arg(long)]
    merge: bool,
    /// Category recorded in the create event of imported open tickets.
    #[arg(long, value_enum, default_value = "todo")]
    open_category: OpenCategory,
    /// Also write the `T-NNNN<TAB>ulid` id map to this file.
    #[arg(long)]
    map_out: Option<PathBuf>,
    /// Also write the migration report markdown here.
    #[arg(long)]
    report_md: Option<PathBuf>,
}

/// Write `text` and a newline to stdout; a closed pipe is not worth failing the run over.
fn emit(text: &str) {
    let mut out = std::io::stdout().lock();
    if writeln!(out, "{text}").is_err() {
        tracing::debug!("stdout closed while emitting");
    }
}

/// Write `text` to `path`, naming the path in the failure.
fn write(path: &Path, text: &str) -> Result<(), String> {
    std::fs::write(path, text)
        .map_err(|e| format!("error: {}: {e}", gob_path::Shown::with_home(path, None)))
}

/// Run the import and print its summary table, counts and dropped fields.
fn import_tickets(
    opts: &ImportOptions,
    map_out: Option<&Path>,
    report_md: Option<&Path>,
) -> Result<(), String> {
    let report = import_v1::run(opts).map_err(|e| {
        tracing::error!(error = %e, "import failed");
        format!("error: {e}")
    })?;
    for line in import_v1::render_table(&report.rows) {
        emit(&line);
    }
    emit("");
    for line in import_v1::render_selection(&report.dispositions, &report.open, &report.skipped) {
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
        "{} tickets, {} events{}",
        report.rows.len(),
        report.events,
        if opts.dry_run {
            " (dry run, nothing written)"
        } else {
            ""
        }
    ));
    emit(&format!("by type: {:?}", report.by_type));
    emit(&format!("by category: {:?}", report.by_category));
    for (field, count) in &report.dropped {
        emit(&format!(
            "dropped v1 field {field}: {count} tickets carried a value"
        ));
    }
    for warning in &report.warnings {
        emit(&format!("warning: {warning}"));
    }
    if let Some(path) = map_out {
        write(path, &import_v1::render_id_map(&report.rows))?;
    }
    if let Some(path) = report_md {
        write(path, &import_v1::render_report_md(&report))?;
    }
    Ok(())
}

fn main() -> ExitCode {
    let args = Args::parse();
    if let Err(e) = gob_log::init("import-v1", 0, false) {
        emit(&format!("warning: logging not initialised: {e}"));
    }
    let opts = ImportOptions {
        from: args.from,
        to: args.to,
        dry_run: args.dry_run,
        selection: args.selection.filter(|_| !args.all),
        merge: args.merge,
        open_category: args.open_category.into(),
        alias_prefix: None,
        extra_labels: Vec::new(),
        privacy_dir: gob_git::Repo::discover(".")
            .ok()
            .map(|r| r.common_dir().to_path_buf()),
    };
    match import_tickets(&opts, args.map_out.as_deref(), args.report_md.as_deref()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(msg) => {
            emit(&msg);
            ExitCode::FAILURE
        }
    }
}

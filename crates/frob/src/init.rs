//! `frob init`: materialize config, ignore `.frob/`, install the ledger merge driver.

use std::path::Path;
use std::time::Duration;

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::config_cmd::{SyncData, sync_config};
use crate::workspace::{Located, config_refusal};

/// Merge driver command line (`%O` ancestor, `%A` ours, `%B` theirs, `%P` path).
const DRIVER_COMMAND: &str = "frob merge-driver %O %A %B %P";
/// Human label stored in git config next to the driver.
const DRIVER_NAME: &str = "frob ledger union-and-refold";
/// Attribute name selecting the driver in `.gitattributes`.
const DRIVER_ATTR: &str = "merge=frob-ledger";
/// Lines that already ignore the cache directory.
const IGNORE_FORMS: [&str; 4] = [".frob/", ".frob", "/.frob/", "/.frob"];
/// Time a `git config` call may take.
const GIT_TIMEOUT: Duration = Duration::from_secs(10);

/// Write frob.toml knobs, ignore .frob/, and install the ledger merge driver; safe to repeat.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "init",
    product = "frob",
    idempotent = true,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Init;

/// One file-or-config step of init.
#[derive(Debug, Serialize, JsonSchema)]
pub struct Step {
    /// What the step touches (a path or a git config key).
    pub target: String,
    /// True when the step changed (or, in a dry run, would change) something.
    pub changed: bool,
}

/// Output of `init`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct InitData {
    /// Repository root initialized.
    pub root: String,
    /// The materialized config file.
    pub config: SyncData,
    /// The `.gitignore` entry.
    pub gitignore: Step,
    /// The `merge.frob-ledger.driver` git config.
    pub merge_driver: Step,
    /// The `.gitattributes` line.
    pub gitattributes: Step,
}

/// Ensure `.frob/` is ignored; returns whether the file changed.
fn ensure_gitignore(root: &Path, dry_run: bool) -> Result<Step, CliError> {
    let path = root.join(".gitignore");
    let existing = read_or_empty(&path)?;
    let present = existing.lines().any(|l| IGNORE_FORMS.contains(&l.trim()));
    if !present && !dry_run {
        append_line(&path, &existing, ".frob/")?;
    }
    Ok(Step {
        target: path.display().to_string(),
        changed: !present,
    })
}

/// Ensure the ticket ledger attribute line is in `.gitattributes`.
fn ensure_gitattributes(root: &Path, tickets_dir: &str, dry_run: bool) -> Result<Step, CliError> {
    let path = root.join(".gitattributes");
    let line = format!("{tickets_dir}/**/ticket.md {DRIVER_ATTR}");
    let existing = read_or_empty(&path)?;
    let present = existing
        .lines()
        .any(|l| l.split_whitespace().eq(line.split_whitespace()));
    if !present && !dry_run {
        append_line(&path, &existing, &line)?;
    }
    Ok(Step {
        target: path.display().to_string(),
        changed: !present,
    })
}

fn read_or_empty(path: &Path) -> Result<String, CliError> {
    match std::fs::read_to_string(path) {
        Ok(t) => Ok(t),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(e) => Err(CliError::internal(format!(
            "cannot read {}: {e}",
            path.display()
        ))),
    }
}

fn append_line(path: &Path, existing: &str, line: &str) -> Result<(), CliError> {
    let mut text = existing.to_owned();
    if !text.is_empty() && !text.ends_with('\n') {
        text.push('\n');
    }
    text.push_str(line);
    text.push('\n');
    std::fs::write(path, text)
        .map_err(|e| CliError::internal(format!("cannot write {}: {e}", path.display())))?;
    tracing::info!(path = %path.display(), line, "line appended");
    Ok(())
}

/// Run `git <args>` in `root`, returning its exit code and trimmed stdout.
fn git(runner: &Runner, root: &Path, args: &[&str]) -> Result<(i32, String), CliError> {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: GIT_TIMEOUT,
        capture: true,
    };
    let out = runner.run(&spec).map_err(CliError::internal)?;
    match out.status {
        ExecOutcome::Exited(code) => Ok((code, out.stdout.trim().to_owned())),
        other => Err(CliError::internal(format!(
            "git {args:?} ended abnormally: {other:?}"
        ))),
    }
}

/// Ensure `merge.frob-ledger.driver` (and its name) are set in the local git config.
fn ensure_merge_driver(root: &Path, dry_run: bool) -> Result<Step, CliError> {
    let runner = Runner::new(Limits { jobs: 1 });
    let key = "merge.frob-ledger.driver";
    let (code, current) = git(&runner, root, &["config", "--local", "--get", key])?;
    let present = code == 0 && current == DRIVER_COMMAND;
    if !present && !dry_run {
        for (k, v) in [
            (key, DRIVER_COMMAND),
            ("merge.frob-ledger.name", DRIVER_NAME),
        ] {
            let (code, _) = git(&runner, root, &["config", "--local", k, v])?;
            if code != 0 {
                return Err(CliError::internal(format!("git config {k} exited {code}")));
            }
        }
        tracing::info!(key, "merge driver installed");
    }
    Ok(Step {
        target: key.to_owned(),
        changed: !present,
    })
}

impl Command for Init {
    type Data = InitData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<InitData> {
        let located = Located::discover(&ctx.cwd);
        located.require_repo()?;
        let root = &located.root;
        let cfg = FrobConfig::load(root).map_err(|e| config_refusal(&e))?;
        let config = sync_config(root, ctx.dry_run)?;
        let gitignore = ensure_gitignore(root, ctx.dry_run)?;
        let merge_driver = ensure_merge_driver(root, ctx.dry_run)?;
        let gitattributes = ensure_gitattributes(root, &cfg.tickets.dir, ctx.dry_run)?;
        let already = config.added.is_empty()
            && !gitignore.changed
            && !merge_driver.changed
            && !gitattributes.changed;
        tracing::info!(already, dry_run = ctx.dry_run, "init finished");
        Ok(Payload::new(InitData {
            root: root.display().to_string(),
            config,
            gitignore,
            merge_driver,
            gitattributes,
        })
        .with_already(already))
    }
}

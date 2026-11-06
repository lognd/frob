//! `frob agent digest`: run a command, store its full output as a content-addressed artifact, print a bounded summary.
//!
//! Keeps a coding agent's context small: the whole output is written under `.frob/artifacts/` named
//! by its blake3 address, and only the head, tail, error lines and the artifact path are printed. The
//! wrapped command's exit status is recorded as `exit_code`; a nonzero status fails the verb with exit 1
//! (a verb's own exit codes are the fixed 0-4 set, so the exact status lives in the data).

// frob:ticket 01M4P2N1Q1F8PKS9FY2MRH4QCR

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

use crate::agent::digest::{self, Digest};
use crate::pretty::PrettyExt;
use crate::workspace::Located;

/// Directory, under the repo root, holding digest artifacts.
const ARTIFACT_DIR: &str = ".frob/artifacts";

/// The flags and trailing command of `agent digest`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DigestArgs {
    #[arg(
        long,
        value_name = "N",
        default_value_t = 10,
        help = "Lines to print from the start"
    )]
    head: usize,
    #[arg(
        long,
        value_name = "N",
        default_value_t = 20,
        help = "Lines to print from the end"
    )]
    tail: usize,
    #[arg(
        long,
        value_name = "N",
        default_value_t = 20,
        help = "Most error lines to print"
    )]
    max_errors: usize,
    #[arg(
        long,
        value_name = "SECS",
        default_value_t = 3600,
        help = "Kill the command after this many seconds"
    )]
    timeout: u64,
    #[arg(
        required = true,
        num_args = 1..,
        trailing_var_arg = true,
        allow_hyphen_values = true,
        value_name = "CMD",
        help = "The command and its arguments (put them after `--`)"
    )]
    command: Vec<String>,
}

/// Output of `agent digest`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DigestData {
    /// The command that ran.
    pub command: Vec<String>,
    /// The wrapped command's exit status; -1 when it was signaled or timed out.
    pub exit_code: i32,
    /// True when the command was killed for exceeding the timeout.
    pub timed_out: bool,
    /// Path of the stored full output.
    pub artifact: String,
    /// Content address (blake3 hex) of the stored output.
    pub address: String,
    /// Size of the stored output in bytes.
    pub bytes: usize,
    /// The bounded summary.
    #[serde(flatten)]
    pub digest: Digest,
}

/// Run a command, store its full output content-addressed and print head, tail, error lines and the artifact path.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "agent digest",
    product = "frob",
    exits(ok, negative, refused, usage, internal)
)]
pub struct AgentDigest {
    head: usize,
    tail: usize,
    max_errors: usize,
    timeout: u64,
    command: Vec<String>,
}

/// The program to spawn for `argv0`: a bare name from `PATH`, or a path made absolute against `cwd`.
fn program_for(argv0: &str, cwd: &Path) -> Program {
    if argv0.contains(['/', '\\']) {
        Program::Pack {
            path: cwd.join(argv0),
        }
    } else {
        Program::Tool {
            name: argv0.to_owned(),
        }
    }
}

/// Write `output` to its content-addressed file under `root`, returning the path and address.
fn store(root: &Path, output: &str) -> Result<(PathBuf, String), CliError> {
    let address = digest::address(output.as_bytes());
    let dir = root.join(ARTIFACT_DIR);
    std::fs::create_dir_all(&dir).map_err(CliError::internal)?;
    let path = dir.join(format!("{address}.log"));
    if path.is_file() {
        tracing::debug!(%address, "digest artifact already stored");
    } else {
        gob_fs::write_atomic(&path, output.as_bytes()).map_err(CliError::internal)?;
        tracing::info!(%address, bytes = output.len(), "digest artifact stored");
    }
    Ok((path, address))
}

impl Command for AgentDigest {
    type Data = DigestData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<DigestArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DigestArgs>(m)?;
        Ok(Self {
            head: a.head,
            tail: a.tail,
            max_errors: a.max_errors,
            timeout: a.timeout,
            command: a.command,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<DigestData> {
        let (_repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let (argv0, rest) = self
            .command
            .split_first()
            .ok_or_else(|| CliError::Usage("agent digest needs a command".to_owned()))?;
        let spec = Spec {
            program: program_for(argv0, &ctx.cwd),
            args: rest.to_vec(),
            cwd: Some(ctx.cwd.clone()),
            env: Vec::new(),
            timeout: Duration::from_secs(self.timeout),
            capture: true,
        };
        tracing::info!(command = ?self.command, "agent digest: running");
        let out = Runner::new(Limits { jobs: 1 }).run(&spec).map_err(|e| {
            tracing::error!(error = %e, "agent digest: command could not run");
            CliError::from(
                Refusal::new(
                    "E-DIGEST-SPAWN",
                    RefusalClass::GuardNeedsAction,
                    e.to_string(),
                )
                .with_remedy("check the command name or path"),
            )
        })?;
        let (exit_code, timed_out) = match out.status {
            ExecOutcome::Exited(c) => (c, false),
            ExecOutcome::Signaled => (-1, false),
            ExecOutcome::TimedOut => (-1, true),
        };
        let full = if out.stderr.is_empty() {
            out.stdout.clone()
        } else {
            format!("{}{}", out.stdout, out.stderr)
        };
        let (path, address) = store(&root, &full)?;
        let data = DigestData {
            command: self.command.clone(),
            exit_code,
            timed_out,
            artifact: gob_path::Shown::of(&path).to_string(),
            address,
            bytes: full.len(),
            digest: digest::summarize(&full, self.head, self.tail, self.max_errors),
        };
        tracing::info!(
            exit_code,
            timed_out,
            bytes = data.bytes,
            "agent digest: done"
        );
        let mut rows = vec![format!(
            "exit {exit_code}{}; {} lines, {} bytes",
            if timed_out { " (timed out)" } else { "" },
            data.digest.total_lines,
            data.bytes
        )];
        rows.extend(data.digest.head.iter().map(|l| format!("head| {l}")));
        rows.extend(data.digest.tail.iter().map(|l| format!("tail| {l}")));
        rows.extend(data.digest.errors.iter().map(|l| format!("err | {l}")));
        rows.push(format!("artifact: {}", data.artifact));
        if exit_code != 0 {
            return Err(CliError::Gate {
                message: format!(
                    "the wrapped command exited {exit_code}; full output at {}",
                    data.artifact
                ),
                data: serde_json::to_value(&data).map_err(CliError::internal)?,
                warnings: Vec::new(),
            });
        }
        Ok(Payload::new(data).with_pretty(rows))
    }
}

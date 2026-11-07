//! `frob agent hook <event>`: the coding-agent hook handlers.
//!
//! Reads Claude Code's hook JSON on stdin and prints the reply JSON as the only stdout line (register
//! the hook as `frob --text agent hook <event>`; the default piped format is the verb envelope). The
//! handlers never block the agent by accident: a payload or repository problem is logged as a
//! warning on stderr, and answered with the empty reply `{}`.

// frob:ticket 01M4P2N1D8ZJN8A3EDD9T7ZT21

use std::io::{IsTerminal, Read};

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::agent::brief::{self, BriefInput};
use crate::agent::hook::{self, Event, HookInput, Policy};
use crate::agent::telemetry::{self, Basis};
use crate::config::FrobConfig;
use crate::pretty::PrettyExt;
use crate::workspace::Located;

/// The positional of `agent hook`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct HookArgs {
    #[arg(value_enum, value_name = "EVENT", help = "The hook event to handle")]
    event: Event,
}

/// Output of `agent hook`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct HookData {
    /// The event handled, as its enum name.
    pub event: String,
    /// The reply JSON the agent reads.
    pub reply: Value,
}

/// Answer one coding-agent hook call from the payload on stdin, failing open on any problem.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "agent hook",
    product = "frob",
    idempotent = true,
    read_only,
    exits(ok, usage, internal)
)]
pub struct AgentHook {
    event: Event,
}

impl Command for AgentHook {
    type Data = HookData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<HookArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            event: gob_cli::parse::<HookArgs>(m)?.event,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<HookData> {
        let mut warnings = Vec::new();
        let reply = match read_stdin().and_then(|t| hook::parse(&t).map_err(|e| e.to_string())) {
            Ok(input) => respond(self.event, &input, ctx, &mut warnings),
            Err(e) => {
                tracing::warn!(error = %e, event = ?self.event, "hook payload unusable; failing open");
                warnings.push(format!("hook payload ignored: {e}"));
                hook::allow()
            }
        };
        let name = format!("{:?}", self.event);
        let payload = Payload::new(HookData {
            event: name,
            reply: reply.clone(),
        })
        .with_pretty(vec![reply.to_string()]);
        // Warnings stay on the log (stderr): in text mode a payload warning would land on stdout and
        // corrupt the reply the agent parses.
        for w in &warnings {
            tracing::warn!(warning = %w, "agent hook degraded");
        }
        Ok(payload)
    }
}

/// Read all of stdin; a terminal counts as an empty payload.
fn read_stdin() -> Result<String, String> {
    let mut stdin = std::io::stdin();
    if stdin.is_terminal() {
        return Ok(String::new());
    }
    let mut text = String::new();
    stdin.read_to_string(&mut text).map_err(|e| e.to_string())?;
    Ok(text)
}

/// The command keys `heavy-profile.toml` lists; empty (with a log line) when absent or unreadable.
fn profiled_commands<E>(root: &Result<std::path::PathBuf, E>) -> Vec<String> {
    let Ok(root) = root else {
        return Vec::new();
    };
    match frob_tests::heavy::load(root) {
        Ok(profile) => profile.map_or_else(Vec::new, |p| p.commands.into_keys().collect()),
        Err(e) => {
            tracing::warn!(error = %e, "hook: heavy profile unreadable; ignored");
            Vec::new()
        }
    }
}

/// The reply for `event`; any repository problem degrades to the allow reply and a warning.
fn respond(event: Event, input: &HookInput, ctx: &Context, warnings: &mut Vec<String>) -> Value {
    let root = Located::discover(&ctx.cwd).into_repo().map(|(_, r)| r);
    let cfg = match &root {
        Ok(r) => FrobConfig::load(r).unwrap_or_else(|e| {
            tracing::warn!(error = %e, "hook: frob.toml unreadable; using defaults");
            warnings.push(format!("frob.toml unreadable, hook defaults used: {e}"));
            FrobConfig::default()
        }),
        Err(_) => FrobConfig::default(),
    };
    let policy = Policy {
        read_max_bytes: cfg.agent.hook_read_max_bytes,
        bash_max_lines: cfg.agent.hook_bash_max_lines,
        heavy: cfg.agent.hook_heavy_commands.clone(),
        profiled: profiled_commands(&root),
    };
    tracing::debug!(?event, "handling agent hook");
    match event {
        Event::PreBash => {
            let reply = hook::pre_bash(input, &policy);
            if let Ok(r) = &root
                && let Some(guard) = hook::bash_guard(&reply)
            {
                telemetry::record(r, guard, 0, Basis::Unmeasured);
            }
            reply
        }
        Event::PreRead => {
            let size = std::cell::Cell::new(0_u64);
            let reply = hook::pre_read(input, &policy, |p| {
                let n = std::fs::metadata(p).ok().map(|m| m.len());
                size.set(n.unwrap_or(0));
                n
            });
            if let Ok(r) = &root
                && hook::is_deny(&reply)
            {
                telemetry::record(r, "pre-read", size.get(), Basis::FileSize);
            }
            reply
        }
        Event::SessionStart | Event::PreCompact | Event::UserPrompt | Event::Stop => {
            let Ok(root) = root else {
                return hook::allow();
            };
            match crate::agent_cmd::gather(ctx, &root, &cfg, warnings) {
                Ok(brief_input) => session_reply(event, &brief_input, &cfg, input),
                Err(e) => {
                    tracing::warn!(error = %e, "hook: brief unavailable; failing open");
                    warnings.push(format!("brief unavailable: {e}"));
                    hook::allow()
                }
            }
        }
    }
}

/// The reply for a session-shaped event built from the gathered brief facts.
fn session_reply(event: Event, facts: &BriefInput, cfg: &FrobConfig, input: &HookInput) -> Value {
    let max = usize::try_from(cfg.agent.brief_max_bytes).unwrap_or(usize::MAX);
    let Some(active) = &facts.ticket else {
        return match event {
            Event::SessionStart => {
                hook::context("SessionStart", &brief::cap(&brief::lines(facts), max).0)
            }
            _ => hook::allow(),
        };
    };
    let one_line = format!("frob: working on {} {}", active.handle, active.title);
    match event {
        Event::SessionStart => {
            hook::context("SessionStart", &brief::cap(&brief::lines(facts), max).0)
        }
        Event::PreCompact => hook::message(&brief::cap(&brief::lines(facts), max).0),
        Event::UserPrompt => hook::context("UserPromptSubmit", &one_line),
        Event::Stop if input.stop_hook_active => hook::allow(),
        Event::Stop => hook::message(&format!(
            "{one_line} is still leased; run `frob check --ticket` and `frob land` when done"
        )),
        Event::PreBash | Event::PreRead => hook::allow(),
    }
}

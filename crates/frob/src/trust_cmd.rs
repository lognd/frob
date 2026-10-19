//! `frob trust`: the interactive trust review (security.md 2.3).
//!
//! The verb takes no arguments and no flags: there is no `--yes`, no `--all` and no scope flag, so
//! nothing can pre-decide the answer. It refuses (exit 3) unless stdin and stdout are terminals and
//! no agent marker is set, and the refusal never names a pack or prints a command line a script
//! could act on; the envelope carries `requires_human = true`.

// frob:ticket 01M3ZX7VDVTM9DJCW5228YRZ8Z

use std::io::IsTerminal;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_trust::prompt::{Presence, ReviewFacts, presence};
use schemars::JsonSchema;
use serde::Serialize;

/// Refusal code when the review cannot run in this session.
const CODE_NEEDS_HUMAN: &str = "E-TRUST-NEEDS-HUMAN";

/// Output of `frob trust`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TrustData {
    /// Packs the person approved in this session.
    pub approved: Vec<String>,
    /// Packs the person denied in this session.
    pub denied: Vec<String>,
}

/// Review untrusted packs interactively; needs a terminal and a person, and takes no flags.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(verb = "trust", product = "frob", exits(ok, refused, usage, internal))]
pub struct Trust;

/// The refusal for a session without a person, deliberately free of pack names and commands.
fn needs_human(why: Presence) -> Refusal {
    let message = match why {
        Presence::Agent => {
            "trust is a review a person performs at a terminal; stop and tell the user a pack is untrusted"
        }
        _ => "trust is a review a person performs at a terminal",
    };
    Refusal::new(CODE_NEEDS_HUMAN, RefusalClass::GuardNeedsAction, message)
        .with_remedy("ask the user to run `frob trust` in their own terminal")
        .requiring_human()
}

/// Run the review gate for the given session facts; `Ok` only when a person may be present.
pub fn gate(
    stdin_tty: bool,
    stdout_tty: bool,
    env: impl Fn(&str) -> Option<String>,
) -> Result<(), Refusal> {
    match presence(stdin_tty, stdout_tty, env) {
        Presence::Human => Ok(()),
        other => {
            tracing::warn!(?other, "trust refused: no person at a terminal");
            Err(needs_human(other))
        }
    }
}

/// The packs awaiting review; none are sourced yet (see the follow-up ticket for lock-based discovery).
fn pending() -> Vec<ReviewFacts> {
    Vec::new()
}

impl Command for Trust {
    type Data = TrustData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, _ctx: &Context) -> Outcome<TrustData> {
        gate(
            std::io::stdin().is_terminal(),
            std::io::stdout().is_terminal(),
            |k| std::env::var(k).ok(),
        )?;
        let (mut approved, mut denied) = (Vec::new(), Vec::new());
        for facts in pending() {
            let decision = gob_trust::prompt::review(
                &facts,
                &mut std::io::stdin().lock(),
                &mut std::io::stdout().lock(),
            )
            .map_err(CliError::internal)?;
            match decision {
                gob_trust::prompt::Decision::Approve => approved.push(facts.pack),
                gob_trust::prompt::Decision::Deny => denied.push(facts.pack),
            }
        }
        tracing::info!(
            approved = approved.len(),
            denied = denied.len(),
            "trust session done"
        );
        let rows = if approved.is_empty() && denied.is_empty() {
            vec!["no pack awaits review".to_owned()]
        } else {
            Vec::new()
        };
        Ok(Payload::new(TrustData { approved, denied }).with_rendered(rows))
    }
}

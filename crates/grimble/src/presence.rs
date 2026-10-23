//! Who may acknowledge a capability grant: a person at a terminal who is a listed attester.
//!
//! Mirrors the `frob` attestation guard (`E-ATTEST-NOT-HUMAN`, `E-ATTEST-NOT-ATTESTER`) without
//! linking `frob-evidence`: a grant approval is a person's statement, so an agent never records
//! one. Presence is injected so the refusals are testable without a terminal.

// frob:ticket 01M4GYBNW01DT1MJ6NJN2GX6NN

use std::io::IsTerminal;

use gob_cli::{CliError, Refusal, RefusalClass};

/// Environment variables set by known coding agents; any non-empty value means an agent is present.
pub const AGENT_MARKERS: &[&str] = &[
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CODEX_SANDBOX",
    "CODEX_CI",
    "GEMINI_CLI",
    "CURSOR_AGENT",
    "OPENCODE",
    "FROB_AGENT",
];

/// Whether a person is at the controls: the seam through which TTY and agent detection is injected.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Presence {
    /// Standard input is a terminal.
    pub stdin_tty: bool,
    /// Standard output is a terminal.
    pub stdout_tty: bool,
    /// Names of the agent markers found in the environment.
    pub agent_markers: Vec<String>,
}

impl Presence {
    /// Detect presence from the real standard streams and process environment.
    pub fn detect() -> Self {
        Self::from_parts(
            std::io::stdin().is_terminal(),
            std::io::stdout().is_terminal(),
            |name| std::env::var(name).ok(),
        )
    }

    /// Build presence from stream facts and an environment lookup (the testable core of [`Presence::detect`]).
    pub fn from_parts(
        stdin_tty: bool,
        stdout_tty: bool,
        env: impl Fn(&str) -> Option<String>,
    ) -> Self {
        let agent_markers = AGENT_MARKERS
            .iter()
            .filter(|m| env(m).is_some_and(|v| !v.is_empty()))
            .map(|m| (*m).to_owned())
            .collect();
        Self {
            stdin_tty,
            stdout_tty,
            agent_markers,
        }
    }

    /// A person at an interactive terminal with no agent marker, for callers that simulate presence.
    pub fn interactive() -> Self {
        Self::from_parts(true, true, |_| None)
    }

    /// Why this is not a person at a terminal; empty when it is.
    pub fn reasons(&self) -> Vec<String> {
        let mut out = Vec::new();
        if !self.stdin_tty {
            out.push("standard input is not a terminal".to_owned());
        }
        if !self.stdout_tty {
            out.push("standard output is not a terminal".to_owned());
        }
        for m in &self.agent_markers {
            out.push(format!("agent marker {m} is set"));
        }
        out
    }
}

/// The identity allowed to approve grants, or the refusal that says why nobody here may.
///
/// `identity` is the git `user.email`; `attesters` is frob.toml `[evidence] attesters`.
///
/// # Errors
///
/// `E-ATTEST-NOT-HUMAN` when no person is at a terminal, `E-ATTEST-NOT-ATTESTER` when the
/// identity is missing or not listed.
pub fn authorize(
    presence: &Presence,
    identity: Option<&str>,
    attesters: &[String],
) -> Result<String, CliError> {
    let reasons = presence.reasons();
    if !reasons.is_empty() {
        tracing::warn!(?reasons, "grant approval refused: no person present");
        return Err(Refusal::new(
            "E-ATTEST-NOT-HUMAN",
            RefusalClass::GuardNeedsAction,
            format!(
                "E-ATTEST-NOT-HUMAN: an attestation is a person's statement; refused because {}",
                reasons.join("; ")
            ),
        )
        .with_remedy(
            "stop and tell the user which grants need approval; only a person at an interactive terminal can run `grimble ack --grants`, and an agent never does",
        )
        .requiring_human()
        .into());
    }
    match identity {
        Some(id) if attesters.iter().any(|a| a == id) => Ok(id.to_owned()),
        _ => {
            let who = identity.map_or_else(
                || "no git user.email is set".to_owned(),
                |i| format!("`{i}` is not an attester"),
            );
            let list = if attesters.is_empty() {
                "[evidence] attesters is empty, so nobody may approve grants".to_owned()
            } else {
                format!("[evidence] attesters lists {}", attesters.join(", "))
            };
            tracing::warn!(%who, "grant approval refused: not an attester");
            Err(Refusal::new(
                "E-ATTEST-NOT-ATTESTER",
                RefusalClass::GuardNeedsAction,
                format!("E-ATTEST-NOT-ATTESTER: {who}; {list}"),
            )
            .with_remedy(
                "the repository owner must list the approving identity under [evidence] attesters in frob.toml; an agent must not edit that list",
            )
            .requiring_human()
            .into())
        }
    }
}

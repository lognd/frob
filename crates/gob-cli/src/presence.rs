//! Whether a person is at the controls, and who may attest: shared by frob and grimble.
//!
//! An attestation or grant approval is a person's statement, so an agent never records one.
//! Presence is injected so the refusals are testable without a terminal.

// frob:ticket 01M5N948TQFB9364996468DHJ3

use std::io::IsTerminal;

use crate::audience::AGENT_MARKERS;

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
        let presence = Self::from_parts(
            std::io::stdin().is_terminal(),
            std::io::stdout().is_terminal(),
            |name| std::env::var(name).ok(),
        );
        tracing::debug!(?presence, "presence detected");
        presence
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
            out.push("stdin is not a terminal".to_owned());
        }
        if !self.stdout_tty {
            out.push("stdout is not a terminal".to_owned());
        }
        for m in &self.agent_markers {
            out.push(format!("the agent marker {m} is set in the environment"));
        }
        out
    }
}

/// Whether `identity` (a git `user.email`) is among the `[evidence] attesters`, ignoring case and surrounding space.
pub fn is_listed_attester(identity: &str, attesters: &[String]) -> bool {
    attesters
        .iter()
        .any(|a| a.trim().eq_ignore_ascii_case(identity.trim()))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5N948TQFB9364996468DHJ3
    // frob:tests crates/gob-cli/src/presence.rs::Presence.reasons
    #[test]
    fn presence_needs_both_streams_and_no_marker() {
        assert!(Presence::interactive().reasons().is_empty());
        let piped = Presence::from_parts(true, false, |_| None);
        assert_eq!(piped.reasons(), ["stdout is not a terminal"]);
        let agent = Presence::from_parts(true, true, |n| (n == "CLAUDECODE").then(|| "1".into()));
        assert!(agent.reasons()[0].contains("CLAUDECODE"));
        let empty = Presence::from_parts(true, true, |_| Some(String::new()));
        assert!(empty.reasons().is_empty(), "an empty marker is unset");
    }

    // frob:tests crates/gob-cli/src/presence.rs::is_listed_attester
    #[test]
    fn attesters_match_ignoring_case_and_space() {
        let listed = vec![" Owner@Example.com ".to_owned()];
        assert!(is_listed_attester("owner@example.com", &listed));
        assert!(!is_listed_attester("other@example.com", &listed));
        assert!(!is_listed_attester("owner@example.com", &[]));
    }
}

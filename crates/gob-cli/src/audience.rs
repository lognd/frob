//! Who reads the output: an AI agent or a human, detected from the environment.

use gob_rules::Audience;

/// Environment variables an agent harness sets; any non-empty value marks an agent.
///
/// `FROB_AGENT` is the explicit switch for harnesses that set none of the others.
pub(crate) const AGENT_MARKERS: [&str; 8] = [
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CODEX_SANDBOX",
    "CODEX_CI",
    "GEMINI_CLI",
    "CURSOR_AGENT",
    "OPENCODE",
    "FROB_AGENT",
];

// frob:ticket 01M63B7F02SKSJCQG7TMXQ4HW5
/// The audience given `lookup` for environment variables: an agent when any marker is non-empty, else a human.
///
/// A terminal is never consulted: a piped human is still a human.
pub(crate) fn detect_audience(lookup: impl Fn(&str) -> Option<String>) -> Audience {
    let hit = AGENT_MARKERS
        .iter()
        .find(|k| lookup(k).is_some_and(|v| !v.trim().is_empty()));
    let audience = if hit.is_some() {
        Audience::Agent
    } else {
        Audience::Human
    };
    tracing::debug!(?audience, marker = ?hit, "audience detected");
    audience
}

// frob:ticket 01M63B7F02SKSJCQG7TMXQ4HW5
/// The audience for the running process, read from the real environment.
pub(crate) fn process_audience() -> Audience {
    detect_audience(|k| std::env::var(k).ok())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn env<'a>(pairs: &'a [(&'a str, &'a str)]) -> impl Fn(&str) -> Option<String> + 'a {
        move |k| {
            pairs
                .iter()
                .find(|(n, _)| *n == k)
                .map(|(_, v)| (*v).to_owned())
        }
    }

    // frob:tests crates/gob-cli/src/audience.rs::detect_audience
    #[test]
    fn no_marker_is_human() {
        assert_eq!(detect_audience(env(&[])), Audience::Human);
    }

    // frob:tests crates/gob-cli/src/audience.rs::detect_audience
    #[test]
    fn each_marker_selects_agent() {
        for m in AGENT_MARKERS {
            assert_eq!(detect_audience(env(&[(m, "1")])), Audience::Agent, "{m}");
        }
    }

    // frob:tests crates/gob-cli/src/audience.rs::detect_audience
    #[test]
    fn empty_marker_is_human() {
        assert_eq!(
            detect_audience(env(&[("CLAUDECODE", " ")])),
            Audience::Human
        );
    }
}

//! The `attestation` provider: a person's statement as evidence no tool can measure.
//!
//! An attestation (design: `tickets.md` section 9, `security.md` 2.3 and 2.10)
//! holds the statement, the attesting identity and the facts it rests on. It
//! is recorded as measured and passed only when [`Presence`] shows a person at
//! a terminal with no agent marker and the identity (git `user.email`) is
//! listed in `[evidence] attesters`; otherwise nothing is written. The record
//! is data with origin `ledger`: every text render shows it through
//! [`Attestation::label`], which escapes it and names it an attestation, never
//! a tool measurement.

// frob:ticket 01M40AKKXBN7K30090V7KQSA8Z

use std::fmt::Write as _;
use std::io::IsTerminal;

use frob_ledger::model::Stamp;

use crate::error::{EvidenceError, Result};
use crate::record::{Attestation, EvidenceRecord, Provider, Status, digest_hex};
use crate::workspace::Workspace;

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

/// Longest statement shown in a one-line label before it is cut with `...`.
const LABEL_MAX_CHARS: usize = 300;

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

    /// Require a person at a terminal.
    ///
    /// # Errors
    ///
    /// [`EvidenceError::NotHuman`] naming every reason.
    pub fn require_human(&self) -> Result<()> {
        let reasons = self.reasons();
        if reasons.is_empty() {
            return Ok(());
        }
        tracing::warn!(?reasons, "attestation refused: no person at a terminal");
        Err(EvidenceError::NotHuman { reasons })
    }
}

/// What a person asks to attest.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Request {
    /// The statement text.
    pub statement: String,
    /// URLs, commit ids and ticket handles or ULIDs it rests on.
    pub facts: Vec<String>,
    /// 1-based criteria the attestation is offered for.
    pub accepts: Vec<usize>,
}

/// Escape `text` for one line of terminal output: controls, newlines and every non-ASCII character become `\u{..}`.
///
/// The text of an attestation is ledger data (security.md 2.10); this keeps it from forging output.
pub fn escape_line(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            '\n' => out.push_str("\\n"),
            c if c.is_ascii() && !c.is_ascii_control() => out.push(c),
            c => {
                let _ = write!(out, "\\u{{{:x}}}", u32::from(c));
            }
        }
    }
    out
}

/// Escape every non-ASCII character of `text` as `\u{..}`, keeping ASCII (newlines and tabs included) as is.
///
/// Ledger files must be ASCII; captured tool text goes through this before it is written into an event.
pub fn escape_non_ascii(text: &str) -> String {
    if text.is_ascii() {
        return text.to_owned();
    }
    let mut out = String::with_capacity(text.len() + 16);
    for c in text.chars() {
        if c.is_ascii() {
            out.push(c);
        } else {
            let _ = write!(out, "\\u{{{:x}}}", u32::from(c));
        }
    }
    tracing::debug!("non-ASCII captured text escaped");
    out
}

/// Refuse `text` if it holds a non-ASCII character, naming the first one so the attester can retype it.
///
/// # Errors
///
/// [`EvidenceError::NonAscii`] for the first non-ASCII character of `text`.
fn require_ascii(what: &'static str, text: &str) -> Result<()> {
    match text.chars().enumerate().find(|(_, c)| !c.is_ascii()) {
        None => Ok(()),
        Some((i, c)) => {
            tracing::warn!(
                what,
                position = i + 1,
                "attestation refused: non-ASCII input"
            );
            Err(EvidenceError::NonAscii {
                what,
                position: i + 1,
                escape: format!("\\u{{{:04X}}}", u32::from(c)),
            })
        }
    }
}

impl Attestation {
    /// The visible form: `[attested by X: "statement"]`, escaped and cut to one line.
    pub fn label(&self) -> String {
        let mut statement = escape_line(&self.statement);
        if statement.chars().count() > LABEL_MAX_CHARS {
            statement = statement.chars().take(LABEL_MAX_CHARS).collect::<String>() + "...";
        }
        format!("[attested by {}: \"{}\"]", escape_line(&self.by), statement)
    }
}

impl EvidenceRecord {
    /// The attestation label when this record is one, else `None`.
    pub fn attestation_label(&self) -> Option<String> {
        self.attestation.as_ref().map(Attestation::label)
    }
}

/// The kind of thing a fact names, from its shape alone.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FactKind {
    Url,
    Commit,
    Ticket,
}

fn classify(fact: &str) -> Option<FactKind> {
    let url_rest = fact
        .strip_prefix("https://")
        .or_else(|| fact.strip_prefix("http://"));
    if let Some(rest) = url_rest {
        let host = rest.split(['/', '?', '#']).next().unwrap_or_default();
        let clean = !fact.chars().any(|c| c.is_whitespace() || c.is_control());
        return (!host.is_empty() && clean).then_some(FactKind::Url);
    }
    if let Some(h) = fact.strip_prefix('~') {
        return (h.len() >= 4 && h.chars().all(|c| c.is_ascii_alphanumeric()))
            .then_some(FactKind::Ticket);
    }
    let ulid = fact.len() == 26 && fact.chars().all(|c| c.is_ascii_alphanumeric());
    if ulid {
        return Some(FactKind::Ticket);
    }
    let hex = (7..=40).contains(&fact.len()) && fact.chars().all(|c| c.is_ascii_hexdigit());
    hex.then_some(FactKind::Commit)
}

/// Validate each fact's shape and, for commits and tickets, that it exists; returns them trimmed.
///
/// # Errors
///
/// [`EvidenceError::NonAscii`] for a non-ASCII fact, [`EvidenceError::BadFact`] for a malformed fact, [`EvidenceError::MissingFact`] for a commit or ticket that does not exist.
pub fn validate_facts(ws: &Workspace, facts: &[String]) -> Result<Vec<String>> {
    let mut out = Vec::new();
    for raw in facts {
        require_ascii("fact", raw)?;
        let fact = raw.trim();
        let Some(kind) = classify(fact) else {
            tracing::warn!(fact, "attestation fact has no recognised shape");
            return Err(EvidenceError::BadFact {
                fact: escape_line(fact),
            });
        };
        match kind {
            FactKind::Url => {}
            FactKind::Commit => {
                if ws
                    .ledger
                    .repo()
                    .rev_parse(&format!("{}^{{commit}}", fact.to_ascii_lowercase()))
                    .is_err()
                {
                    tracing::warn!(fact, "attestation names a missing commit");
                    return Err(EvidenceError::MissingFact {
                        kind: "commit",
                        fact: fact.to_owned(),
                    });
                }
            }
            FactKind::Ticket => {
                if ws.ledger.resolve(fact).is_err() {
                    tracing::warn!(fact, "attestation names a missing ticket");
                    return Err(EvidenceError::MissingFact {
                        kind: "ticket",
                        fact: fact.to_owned(),
                    });
                }
            }
        }
        out.push(fact.to_owned());
    }
    Ok(out)
}

/// The attesting identity: git `user.email`, which must be listed in `[evidence] attesters`.
fn attester_of(ws: &Workspace) -> Result<String> {
    let identity = ws.ledger.repo().config_user().map(|(_, email)| email);
    let listed = &ws.evidence.attesters;
    match identity {
        Some(email)
            if listed
                .iter()
                .any(|a| a.trim().eq_ignore_ascii_case(email.trim())) =>
        {
            Ok(email)
        }
        other => {
            tracing::warn!(identity = ?other, listed = ?listed, "attestation refused: not an attester");
            Err(EvidenceError::NotAttester {
                identity: other,
                listed: listed.clone(),
            })
        }
    }
}

/// Record a person's attestation: presence, statement, identity and facts are all checked before a record exists.
///
/// # Errors
///
/// [`EvidenceError::NotHuman`], [`EvidenceError::EmptyStatement`], [`EvidenceError::NonAscii`], [`EvidenceError::NotAttester`], [`EvidenceError::BadFact`] or [`EvidenceError::MissingFact`]; nothing is written for any of them.
pub fn attest(ws: &Workspace, presence: &Presence, req: &Request) -> Result<EvidenceRecord> {
    presence.require_human()?;
    if req.statement.trim().is_empty() {
        tracing::warn!("attestation refused: empty statement");
        return Err(EvidenceError::EmptyStatement);
    }
    require_ascii("statement", &req.statement)?;
    let by = attester_of(ws)?;
    let facts = validate_facts(ws, &req.facts)?;
    let digest = digest_hex(req.statement.as_bytes());
    tracing::info!(by, facts = facts.len(), "attestation accepted");
    Ok(EvidenceRecord {
        provider: Provider::Attestation,
        reference: format!("statement:{}", &digest[..12]),
        digest,
        uri: None,
        status: Status::Measured,
        captured_at: Stamp::now(),
        accepts: req.accepts.clone(),
        passed: Some(true),
        exit_code: None,
        tests: Vec::new(),
        failed_tests: Vec::new(),
        inline: None,
        size: req.statement.len() as u64,
        attestation: Some(Attestation {
            by,
            statement: req.statement.clone(),
            facts,
        }),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn presence_needs_both_streams_and_no_marker() {
        assert!(Presence::interactive().require_human().is_ok());
        let piped = Presence::from_parts(true, false, |_| None);
        assert_eq!(piped.reasons(), ["stdout is not a terminal"]);
        let agent = Presence::from_parts(true, true, |n| (n == "CLAUDECODE").then(|| "1".into()));
        assert!(agent.reasons()[0].contains("CLAUDECODE"));
        let empty = Presence::from_parts(true, true, |_| Some(String::new()));
        assert!(empty.require_human().is_ok(), "an empty marker is unset");
    }

    #[test]
    fn escape_non_ascii_keeps_layout_and_hides_the_rest() {
        assert_eq!(escape_non_ascii("a\n\tb"), "a\n\tb");
        assert_eq!(escape_non_ascii("\u{2500}x\u{e9}\n"), "\\u{2500}x\\u{e9}\n");
    }

    #[test]
    fn escape_line_hides_controls_and_non_ascii() {
        assert_eq!(escape_line("a\nb\u{1b}[31m"), "a\\nb\\u{1b}[31m");
        assert_eq!(escape_line("x\u{202e}y\u{e9}"), "x\\u{202e}y\\u{e9}");
        assert!(escape_line("\u{202e}\u{7}\u{85}").is_ascii());
    }

    #[test]
    fn label_names_an_attestation_and_escapes() {
        let a = Attestation {
            by: "o@example.com".into(),
            statement: "ran two cycles\n[passed by nextest]".into(),
            facts: Vec::new(),
        };
        assert_eq!(
            a.label(),
            "[attested by o@example.com: \"ran two cycles\\n[passed by nextest]\"]"
        );
    }

    #[test]
    fn facts_are_classified_by_shape() {
        assert_eq!(classify("https://example.com/x"), Some(FactKind::Url));
        assert_eq!(classify("https://"), None);
        assert_eq!(classify("ftp://example.com"), None);
        assert_eq!(classify("~7KQSA8Z"), Some(FactKind::Ticket));
        assert_eq!(
            classify("01M40AKKXBN7K30090V7KQSA8Z"),
            Some(FactKind::Ticket)
        );
        assert_eq!(classify("deadbeef"), Some(FactKind::Commit));
        assert_eq!(classify("abc"), None);
        assert_eq!(classify("not a fact"), None);
    }
}

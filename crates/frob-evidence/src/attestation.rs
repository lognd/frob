//! The `attestation` provider: a person's statement as evidence no tool can measure.
//!
//! An attestation (design: `tickets.md` section 6, `security.md` 2.3 and 2.10)
//! holds the statement, the attesting identity and the facts it rests on. It
//! is recorded as measured and passed only when [`Presence`] shows a person at
//! a terminal with no agent marker and the identity (git `user.email`) is
//! listed in `[evidence] attesters`; otherwise nothing is written. The record
//! is data with origin `ledger`: every text render shows it through
//! [`Attestation::label`], which escapes it and names it an attestation, never
//! a tool measurement.

// frob:ticket 01M40AKKXBN7K30090V7KQSA8Z

use std::io::IsTerminal;

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

    // frob:waive DUP004 reason="pre-existing mirror of grimble Presence; cross-crate extraction is outside ticket XZR3S4S scope"
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

    // frob:waive DUP004 reason="pre-existing mirror of grimble Presence; cross-crate extraction is outside ticket XZR3S4S scope"
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

// frob:ticket 01M42JTEMYJH8JJFPTGJQB5FA9

/// Escape `text` for one line of terminal output; delegates to `gob_diagnostics::escape_line`.
///
/// The text of an attestation is ledger data (security.md 2.10); this keeps it from forging output.
pub fn escape_line(text: &str) -> String {
    gob_diagnostics::escape_line(text)
}

/// Escape every non-ASCII character of `text` as `\u{..}`; delegates to `gob_diagnostics::escape_non_ascii`.
///
/// Ledger files must be ASCII; captured tool text goes through this before it is written into an event.
pub fn escape_non_ascii(text: &str) -> String {
    gob_diagnostics::escape_non_ascii(text)
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
    /// A design clause anchor `KIND/NAME/verified_by[i]` (grmb-spec 9.1).
    Anchor,
}

/// The shape of a fact: a URL, a design clause anchor, a `~handle` ticket, a ULID ticket, or a hex commit; `None` when malformed.
fn classify(fact: &str) -> Option<FactKind> {
    if let Some(rest) = fact
        .strip_prefix("https://")
        .or_else(|| fact.strip_prefix("http://"))
    {
        url_kind(fact, rest)
    } else if frob_ledger::design::row_anchor_parts(fact).is_some() {
        Some(FactKind::Anchor)
    } else if let Some(h) = fact.strip_prefix('~') {
        (h.len() >= 4 && h.chars().all(|c| c.is_ascii_alphanumeric())).then_some(FactKind::Ticket)
    } else {
        bare_kind(fact)
    }
}

/// A URL fact (`rest` is the text after the scheme): needs a host and no whitespace or control characters.
fn url_kind(fact: &str, rest: &str) -> Option<FactKind> {
    let host = rest.split(['/', '?', '#']).next().unwrap_or_default();
    let clean = !fact.chars().any(|c| c.is_whitespace() || c.is_control());
    (!host.is_empty() && clean).then_some(FactKind::Url)
}

/// A scheme-less fact: a 26-character ULID is a ticket, 7 to 40 hex digits is a commit.
fn bare_kind(fact: &str) -> Option<FactKind> {
    if fact.len() == 26 && fact.chars().all(|c| c.is_ascii_alphanumeric()) {
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
            // Existence is judged against `grimble graph --json` by the overlay, never on shape alone.
            FactKind::Anchor => tracing::debug!(fact, "design clause anchor accepted on shape"),
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
    let mut record = EvidenceRecord {
        provider: Provider::Attestation,
        reference: format!("statement:{}", &digest[..12]),
        digest,
        uri: None,
        status: Status::Measured,
        captured_at: ws.ledger.clock().now().seconds(),
        accepts: req.accepts.clone(),
        passed: Some(true),
        exit_code: None,
        tests: Vec::new(),
        test_count: None,
        tests_digest: None,
        failed_tests: Vec::new(),
        non_passing: crate::record::NonPassingCounts::default(),
        inline: None,
        size: req.statement.len() as u64,
        attestation: Some(Attestation {
            by,
            statement: req.statement.clone(),
            facts,
        }),
        head: None,
        coverage: None,
        design: Vec::new(),
    };
    stamp_fact_designs(ws, &mut record);
    Ok(record)
}

// frob:ticket 01M6C5CMTKAAN38SR012V265H6

/// Stamp on an attestation the design digests of every ticket its facts name, so milestone attestations carry them like `evidence add`.
fn stamp_fact_designs(ws: &Workspace, record: &mut EvidenceRecord) {
    let tickets: Vec<_> = record
        .attestation
        .iter()
        .flat_map(|a| &a.facts)
        .filter(|f| classify(f) == Some(FactKind::Ticket))
        .filter_map(|f| ws.ledger.resolve(f).ok())
        .collect();
    for id in tickets {
        let mut scratch = record.clone();
        crate::design::stamp(ws, id, &mut scratch);
        for d in scratch.design {
            if !record.design.contains(&d) {
                tracing::debug!(ticket = %id, entity = %d.entity, "design digest stamped from attestation fact");
                record.design.push(d);
            }
        }
    }
}

// frob:ticket 01M6BYM5XMG4WD49JAQXZR3S4S
/// The design clause anchors among a passed attestation's facts: what the overlay reads as manual row verdicts.
pub fn anchor_facts(attestation: &Attestation) -> Vec<String> {
    attestation
        .facts
        .iter()
        .filter(|f| classify(f) == Some(FactKind::Anchor))
        .cloned()
        .collect()
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

    // frob:tests escape_non_ascii
    #[test]
    fn escape_non_ascii_keeps_layout_and_hides_the_rest() {
        assert_eq!(escape_non_ascii("a\n\tb"), "a\n\tb");
        assert_eq!(escape_non_ascii("\u{2500}x\u{e9}\n"), "\\u{2500}x\\u{e9}\n");
    }

    // frob:tests escape_line
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

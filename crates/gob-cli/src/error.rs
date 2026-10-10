//! Verb outcomes: the payload on success and [`CliError`] on failure.

use gob_diagnostics::{ExitCode, FindingRecord, Refusal};
use gob_rules::Finding;

/// Everything a successful verb returns besides process exit state.
#[derive(Debug)]
pub struct Payload<T> {
    /// Verb-specific data, serialized as the envelope `data`.
    pub data: T,
    /// Findings the verb produced; reported, never turned into a failure here.
    pub findings: Vec<Finding>,
    /// Non-fatal notices.
    pub warnings: Vec<String>,
    /// True when the request already held and nothing changed (cli.md section 3).
    pub already: bool,
    /// Pre-rendered text rows: the text view prints them verbatim (JSON ignores them).
    pub rendered: Option<Vec<String>>,
}

impl<T> Payload<T> {
    /// A payload with only data: no findings, no warnings, `already` false.
    pub fn new(data: T) -> Self {
        Self {
            data,
            findings: Vec::new(),
            warnings: Vec::new(),
            already: false,
            rendered: None,
        }
    }

    /// Mark the text view as pre-rendered: rows print raw, with no envelope header, markers or indent.
    #[must_use]
    pub fn with_rendered(mut self, rows: Vec<String>) -> Self {
        self.rendered = Some(rows);
        self
    }

    /// Attach findings.
    #[must_use]
    pub fn with_findings(mut self, findings: Vec<Finding>) -> Self {
        self.findings = findings;
        self
    }

    /// Mark the request as already satisfied (or not).
    #[must_use]
    pub fn with_already(mut self, already: bool) -> Self {
        self.already = already;
        self
    }

    /// Add one warning.
    #[must_use]
    pub fn with_warning(mut self, warning: impl Into<String>) -> Self {
        self.warnings.push(warning.into());
        self
    }
}

thread_local! {
    /// Notices queued by [`Payload::note`] during the running verb.
    static NOTES: std::cell::RefCell<Vec<String>> = const { std::cell::RefCell::new(Vec::new()) };
}

impl Payload<()> {
    /// Queue a warning for the running verb's envelope from anywhere below its handler (a shared helper that opens the ledger, say).
    ///
    /// The root drains the queue into `warnings` when the verb returns, success or failure.
    pub fn note(message: impl Into<String>) {
        let message = message.into();
        tracing::debug!(%message, "verb notice queued");
        NOTES.with(|n| n.borrow_mut().push(message));
    }
}

/// Drop notices left by an earlier verb on this thread (a refused verb never drains its queue).
pub(crate) fn clear_notes() {
    NOTES.with(|n| n.borrow_mut().clear());
}

/// Take the notices queued since [`clear_notes`], oldest first, without duplicates.
pub(crate) fn take_notes() -> Vec<String> {
    let mut notes = NOTES.with(|n| std::mem::take(&mut *n.borrow_mut()));
    let mut seen = std::collections::BTreeSet::new();
    notes.retain(|m| seen.insert(m.clone()));
    notes
}

/// The payload of [`CliError::Findings`], boxed to keep the error small.
#[derive(Debug)]
pub struct FindingsFailure {
    /// One-line summary, the envelope `error.message`.
    pub summary: String,
    /// The finding lines for the text view.
    pub detail: String,
    /// The verb's data, serialized as the envelope `data`.
    pub data: serde_json::Value,
    /// Every finding as a structured record.
    pub findings: Vec<FindingRecord>,
    /// Non-fatal notices.
    pub warnings: Vec<String>,
}

/// Why a verb did not succeed; fixes the exit code (cli.md section 2).
#[derive(Debug, thiserror::Error)]
pub enum CliError {
    /// A guard refused (exit 3, or the code its class implies).
    #[error(transparent)]
    Refusal(#[from] Refusal),
    /// Bad flags or input (exit 2).
    #[error("usage: {0}")]
    Usage(String),
    /// The caller asked for a yes/no answer and it is no (exit 1).
    #[error("negative: {0}")]
    Negative(String),
    /// The run completed and its gate failed (exit 1) but its result is still the answer.
    ///
    /// JSON mode prints a success envelope (`ok` true, `data` kept) so a caller can read the
    /// document on exit 1 (sibling-contract 2); text mode prints `message` on stderr.
    #[error("gate failed: {message}")]
    Gate {
        /// One-paragraph summary of why the gate failed.
        message: String,
        /// The verb's data, serialized as the envelope `data`.
        data: serde_json::Value,
        /// Non-fatal notices.
        warnings: Vec<String>,
    },
    /// The run completed, its gate failed (exit 1), and the findings are the answer.
    ///
    /// JSON mode prints `ok` false with `findings` carrying every record, `data` kept and a
    /// one-line `error.message` (`summary`); text mode prints `summary` then `detail` on stderr.
    #[error("findings gate failed: {}", .0.summary)]
    Findings(Box<FindingsFailure>),
    /// A bug (exit 4).
    #[error("internal: {0}")]
    Internal(Box<dyn std::error::Error + Send + Sync>),
}

impl CliError {
    /// Wrap any error as an internal failure.
    pub fn internal(error: impl Into<Box<dyn std::error::Error + Send + Sync>>) -> Self {
        Self::Internal(error.into())
    }

    /// The process exit code for this error.
    pub fn exit_code(&self) -> ExitCode {
        match self {
            Self::Refusal(r) => r.exit_code(),
            Self::Usage(_) => ExitCode::Usage,
            Self::Negative(_) | Self::Gate { .. } | Self::Findings(_) => ExitCode::Negative,
            Self::Internal(_) => ExitCode::Internal,
        }
    }
}

/// What every verb handler returns.
pub type Outcome<T> = Result<Payload<T>, CliError>;

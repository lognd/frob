//! The consumer-side types of the `gob.sibling/1` document (lenient: unknown keys are ignored).
//!
//! Only the fields frob reads are declared (`sibling-contract.md` sections 3 and 4);
//! the producer's strict schema is `docs/schemas/sibling.json`. A field the contract
//! makes mandatory has no `default`, so its absence is a parse failure (malformed).

use frob_obligations::SiblingException;
use gob_rules::RequiredReason;
use serde::Deserialize;

/// The envelope of `check --json` (`cli.md` section 2); `data` is the sibling document.
#[derive(Debug, Deserialize)]
pub(super) struct Envelope {
    /// True when the product ran to completion.
    pub ok: bool,
    /// The sibling document of an `ok` run.
    #[serde(default)]
    pub data: Option<serde_json::Value>,
    /// The failure body of a not-`ok` run.
    #[serde(default)]
    pub error: Option<ErrorBody>,
}

/// The `error` object of a failure envelope.
#[derive(Debug, Deserialize)]
pub(super) struct ErrorBody {
    /// Human message.
    #[serde(default)]
    pub message: String,
    /// The exact corrected command, when the product knows one.
    #[serde(default)]
    pub remedy: Option<String>,
}

/// The severity spellings of the landed `severity_label`.
#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(super) enum Sev {
    /// An error.
    Error,
    /// A warning.
    Warning,
    /// An advisory note.
    Advisory,
    /// Could not be decided.
    Unresolved,
}

/// A byte range, half-open.
#[derive(Debug, Clone, Copy, Deserialize)]
pub(super) struct Range {
    /// First byte.
    pub start: u32,
    /// One past the last byte.
    pub end: u32,
}

/// Reads the mandatory-but-nullable `required` mark: an absent key is an error.
fn required_mark<'de, D: serde::Deserializer<'de>>(
    d: D,
) -> Result<Option<RequiredReason>, D::Error> {
    Option::<RequiredReason>::deserialize(d)
}

/// One finding (the landed `FindingRecord` plus the sibling's extras, of which frob reads these).
#[derive(Debug, Clone, Deserialize)]
pub(super) struct DocFinding {
    /// Rule id such as `SYS006`.
    pub rule: String,
    /// Severity as printed.
    pub severity: Sev,
    /// Repository-relative path, or null.
    pub file: Option<String>,
    /// Byte range in `file`, or null.
    pub range: Option<Range>,
    /// Human text.
    pub message: String,
    /// 64 lowercase hex digits, not yet namespaced.
    pub fingerprint: String,
    /// The mandatory mark of `cli.md` section 2.
    #[serde(deserialize_with = "required_mark")]
    pub required: Option<RequiredReason>,
}

/// A parked finding and the id of the exception that parked it.
#[derive(Debug, Deserialize)]
pub(super) struct DocSuppressed {
    /// The finding as it would have been reported.
    pub finding: DocFinding,
    /// The `id` of its exception.
    pub exception: String,
}

/// One parsed exception of the sibling.
#[derive(Debug, Deserialize)]
pub(super) struct DocException {
    /// Stable id.
    pub id: String,
    /// `accept`, `defer`, `hotfix` or `baseline`.
    pub kind: String,
    /// The excepted rule id.
    pub rule: String,
    /// Where it is written, or null.
    pub file: Option<String>,
    /// Line where it is written, or null.
    pub line: Option<u32>,
    /// The reason text.
    pub because: String,
    /// The date exit, or null.
    pub until: Option<String>,
    /// The opaque `ticket=` value, or null.
    pub ticket: Option<String>,
}

/// One language's fidelity row.
#[derive(Debug, Deserialize)]
pub(super) struct DocFidelity {
    /// Language id.
    pub language: String,
    /// `F0` to `F4`.
    pub level: String,
    /// Rules whose whole scope is not applicable here.
    pub not_applicable_rules: Vec<String>,
}

/// One rule record, for the vacuous-rule self-check.
#[derive(Debug, Deserialize)]
pub(super) struct DocRule {
    /// Rule id.
    pub rule: String,
    /// Subjects examined over the whole run.
    pub subjects_examined: u64,
    /// Live findings.
    pub findings: u64,
    /// Unresolved findings.
    pub unresolved: u64,
}

/// The sibling document, the `data` of the envelope.
#[derive(Debug, Deserialize)]
pub(super) struct Doc {
    /// The producing product.
    pub product: String,
    /// The producer's own version, when it reports one.
    #[serde(default)]
    pub product_version: Option<String>,
    /// `blake3:` plus 64 hex digits.
    pub compute_digest: String,
    /// Per language fidelity.
    pub fidelity: Vec<DocFidelity>,
    /// Per rule counts.
    pub rules: Vec<DocRule>,
    /// Live findings.
    pub findings: Vec<DocFinding>,
    /// Parked findings.
    pub suppressed: Vec<DocSuppressed>,
    /// Every parsed exception.
    pub exceptions: Vec<DocException>,
}

impl DocException {
    /// The ticket-bound view of this exception, with the findings it parked, or `None` without a ticket.
    pub(super) fn bound(
        &self,
        product: &str,
        suppressed: &[DocSuppressed],
    ) -> Option<SiblingException> {
        let ticket = self.ticket.clone()?;
        let parks = suppressed
            .iter()
            .filter(|s| s.exception == self.id)
            .map(|s| {
                format!(
                    "{} {}",
                    s.finding.rule,
                    s.finding
                        .fingerprint
                        .get(..12)
                        .unwrap_or(&s.finding.fingerprint)
                )
            })
            .collect();
        Some(SiblingException {
            product: product.to_owned(),
            id: self.id.clone(),
            kind: self.kind.clone(),
            rule: self.rule.clone(),
            file: self.file.clone(),
            line: self.line,
            ticket,
            parks,
        })
    }
}

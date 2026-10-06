//! The `gob.sibling/1` document (sibling-contract.md section 3, products.md section 7): the one
//! emitter every product prints with and the one typed reader frob merges through.
//!
//! [`document`] builds the `data` of a `check --json` envelope from a [`SiblingInput`], the
//! product-neutral view of a finished check run; crunk, grimble and frob's own tests all go
//! through it, so the contract has one owner. [`Doc`] and its row types are the lenient reader
//! (unknown keys ignored); a field the contract makes mandatory has no `default`, so its absence
//! is a parse failure (malformed). The producer's strict schema is `docs/schemas/sibling.json`.

use std::collections::HashSet;
use std::path::Path;

use gob_config::ComputeTable;
use gob_diagnostics::{FindingRecord, MemorySources};
use gob_rules::{Finding, Polarity as RulePolarity, Registry, RequiredReason, Severity};
use gob_text::SourceText;
use serde::Deserialize;
use serde_json::Value;
use tracing::debug;

use crate::CheckReport;
use crate::sibling_doc::{
    FindingRow, Invocation, PolarityMark, Range as RowRange, RuleRecord, SiblingDocument,
    SuppressedFinding, Timing,
};

/// The contract name and major this build implements.
pub const SCHEMA_VERSION: &str = "gob.sibling/1";

/// The pack list of a document and the digest of its canonical JSON (both or neither are emitted).
#[derive(Debug, Clone)]
pub struct PacksField {
    /// The `packs` array.
    pub packs: Vec<Value>,
    /// The `packs_digest` string.
    pub digest: String,
}

/// Everything the emitter needs from one finished check run, whatever the product.
pub struct SiblingInput<'a> {
    /// The producing product name (`crunk`, `grimble`).
    pub product: &'a str,
    /// The producer's own version.
    pub product_version: &'a str,
    /// Repository root the report's paths are relative to.
    pub root: &'a Path,
    /// The pipeline report.
    pub report: &'a CheckReport,
    /// The `[compute]` knobs in force.
    pub compute: &'a ComputeTable,
    /// Echo of `--ticket-scope`.
    pub ticket_scope: Option<&'a [String]>,
    /// Echo of `--base`.
    pub base: Option<&'a str>,
    /// Wall time of the run in milliseconds.
    pub elapsed_ms: u64,
    /// The `fidelity` array.
    pub fidelity: Vec<Value>,
    /// Rules left out of the `rules` array (their whole scope is not applicable).
    pub not_applicable: &'a HashSet<String>,
    /// The unresolved reason code of a finding (`None` for a resolved one).
    pub reason: &'a dyn Fn(&Finding) -> Option<String>,
    /// The id of the exception that parked a finding (empty when unknown).
    pub exception_of: &'a dyn Fn(&Finding) -> String,
    /// The `exceptions` array.
    pub exceptions: Vec<Value>,
    /// The `entities` array.
    pub entities: Vec<Value>,
    /// The `bindings` array.
    pub bindings: Vec<Value>,
    /// The optional pack keys.
    pub packs: Option<PacksField>,
}

/// The reason code of an Unresolved finding when the product knows no better: `fidelity`.
pub fn fidelity_reason(f: &Finding) -> Option<String> {
    (f.severity == Severity::Unresolved).then(|| "fidelity".to_owned())
}

/// Polarity of `rule` (`P+` when the registry does not know it).
fn polarity_of(rule: &str) -> PolarityMark {
    Registry::global()
        .by_id(rule)
        .map_or(PolarityMark::Plus, |m| match m.polarity {
            RulePolarity::Pplus => PolarityMark::Plus,
            RulePolarity::Pminus => PolarityMark::Minus,
            RulePolarity::P0 => PolarityMark::P0,
            RulePolarity::Pn => PolarityMark::Pn,
            RulePolarity::Pc => PolarityMark::Pc,
        })
}

/// A resolver of `file:line:column` over the files the findings point into.
fn sources_of(root: &Path, report: &CheckReport) -> MemorySources {
    let mut sources = MemorySources::new();
    let mut seen = HashSet::new();
    let all = report
        .findings
        .iter()
        .chain(report.suppressed.iter().map(|(f, _)| f));
    for f in all {
        let Some(span) = f.span else { continue };
        if !seen.insert(span.file) {
            continue;
        }
        let Some(path) = report.files.path(span.file) else {
            continue;
        };
        // Lossy: an opaque (non-UTF-8) file still needs a path and an approximate line.
        let text = std::fs::read(root.join(path)).map(|b| String::from_utf8_lossy(&b).into_owned());
        if let Ok(text) = text
            && let Ok(src) = SourceText::new(text)
        {
            sources.insert(span.file, path, src);
        }
    }
    sources
}

/// One finding as a sibling row: the landed record plus the sibling's extras.
fn finding_row(input: &SiblingInput<'_>, sources: &MemorySources, f: &Finding) -> FindingRow {
    let rule = f.rule.as_str();
    FindingRow {
        record: FindingRecord::from_finding(f, sources, Registry::global()),
        polarity: polarity_of(rule),
        subjects_examined: input
            .report
            .subjects_examined
            .get(rule)
            .map_or(0, |n| *n as u64),
        reason: (input.reason)(f),
        maybe: Vec::new(),
        anchor: None,
        entity: None,
        remedy: None,
        range: f.span.map(|s| RowRange {
            start: u32::from(s.range.start()),
            end: u32::from(s.range.end()),
        }),
    }
}

/// The `rules` array: per rule that ran, polarity and counts.
fn rules_json(input: &SiblingInput<'_>) -> Vec<RuleRecord> {
    let report = input.report;
    let count = |rule: &str, sev: Option<Severity>| {
        report
            .findings
            .iter()
            .filter(|f| f.rule.as_str() == rule && sev.is_none_or(|s| f.severity == s))
            .count() as u64
    };
    report
        .subjects_examined
        .iter()
        .filter(|(rule, _)| !input.not_applicable.contains(rule.as_str()))
        .map(|(rule, subjects)| RuleRecord {
            rule: rule.clone(),
            polarity: polarity_of(rule),
            subjects_examined: *subjects as u64,
            findings: count(rule, None),
            suppressed: report
                .suppressed
                .iter()
                .filter(|(f, _)| f.rule.as_str() == rule)
                .count() as u64,
            unresolved: count(rule, Some(Severity::Unresolved)),
        })
        .collect()
}

/// The sibling document of `input` (the `data` of the check envelope).
pub fn document(input: &SiblingInput<'_>) -> Value {
    let sources = sources_of(input.root, input.report);
    let findings: Vec<FindingRow> = input
        .report
        .findings
        .iter()
        .map(|f| finding_row(input, &sources, f))
        .collect();
    let suppressed: Vec<SuppressedFinding> = input
        .report
        .suppressed
        .iter()
        .map(|(f, _)| SuppressedFinding {
            finding: finding_row(input, &sources, f),
            exception: (input.exception_of)(f),
        })
        .collect();
    let doc = SiblingDocument {
        schema_version: SCHEMA_VERSION.to_owned(),
        product: input.product.to_owned(),
        product_version: input.product_version.to_owned(),
        compute_digest: gob_config::compute_digest(input.compute),
        compute: input.compute.to_value(),
        invocation: Invocation {
            verb: "check".to_owned(),
            root: ".".to_owned(),
            ticket_scope: input.ticket_scope.map(<[String]>::to_vec),
            base: input.base.map(str::to_owned),
        },
        fidelity: input.fidelity.clone(),
        rules: rules_json(input),
        findings,
        suppressed,
        exceptions: input.exceptions.clone(),
        entities: input.entities.clone(),
        bindings: input.bindings.clone(),
        timing: Timing {
            elapsed_ms: input.elapsed_ms,
        },
        packs: input.packs.as_ref().map(|p| p.packs.clone()),
        packs_digest: input.packs.as_ref().map(|p| p.digest.clone()),
    };
    debug!(
        product = input.product,
        findings = input.report.findings.len(),
        "sibling document built"
    );
    serde_json::to_value(&doc)
        .unwrap_or_else(|e| unreachable!("a sibling document serializes: {e}"))
}

/// The envelope of `check --json` (`cli.md` section 2); `data` is the sibling document.
#[derive(Debug, Deserialize)]
pub struct Envelope {
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
pub struct ErrorBody {
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
pub enum Sev {
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
pub struct Range {
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
pub struct DocFinding {
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
pub struct DocSuppressed {
    /// The finding as it would have been reported.
    pub finding: DocFinding,
    /// The `id` of its exception.
    pub exception: String,
}

/// One parsed exception of the sibling.
#[derive(Debug, Deserialize)]
pub struct DocException {
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
pub struct DocFidelity {
    /// Language id.
    pub language: String,
    /// `F0` to `F4`.
    pub level: String,
    /// Rules whose whole scope is not applicable here.
    pub not_applicable_rules: Vec<String>,
}

/// One rule record, for the vacuous-rule self-check.
#[derive(Debug, Deserialize)]
pub struct DocRule {
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
pub struct Doc {
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

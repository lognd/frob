//! Merging a validated sibling document into frob's report (`sibling-contract.md` section 5).

use std::collections::HashMap;

use frob_obligations::SiblingException;
use gob_check::{External, LanguageFidelity};
use gob_rules::{Exception, ExceptionKind, Finding, Fingerprint, Registry, RuleId, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};

use super::doc::{Doc, DocException, DocFinding, Sev};
use super::spawn::{Failure, Reason};

fn malformed(why: impl Into<String>) -> Failure {
    Failure::new(Reason::Malformed, why)
}

/// A repository-relative path: no leading `/`, drive letter or `..` segment.
fn safe_path(path: &str) -> bool {
    !(path.starts_with('/')
        || path.starts_with('\\')
        || path.as_bytes().get(1) == Some(&b':')
        || path.split(['/', '\\']).any(|s| s == ".."))
}

/// The severity mapping, one to one; frob never re-grades.
fn severity(s: Sev) -> Severity {
    match s {
        Sev::Error => Severity::Error,
        Sev::Warning => Severity::Warn,
        Sev::Advisory => Severity::Advisory,
        Sev::Unresolved => Severity::Unresolved,
    }
}

/// One sibling finding as a frob finding with a namespaced fingerprint recorded in `out`.
fn finding(
    product: &str,
    f: &DocFinding,
    files: &mut FileInterner,
    out: &mut External,
) -> Result<Finding, Failure> {
    let rule: RuleId = f
        .rule
        .parse()
        .map_err(|e| malformed(format!("finding rule: {e}")))?;
    if let Some(path) = &f.file
        && !safe_path(path)
    {
        return Err(malformed(format!(
            "finding file `{path}` is not repository-relative"
        )));
    }
    if f.fingerprint.len() != 64 || !f.fingerprint.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(malformed(format!(
            "finding fingerprint `{}` is not 64 hex digits",
            f.fingerprint
        )));
    }
    if Registry::global()
        .by_id(rule.as_str())
        .is_some_and(|m| m.product == "frob")
    {
        tracing::warn!(product, rule = %rule, "sibling uses a rule id a frob family owns");
        out.warnings.push(format!("{product} emitted {rule}, an id owned by a frob family (contract violation; finding kept)"));
    }
    let span = match (&f.file, f.range) {
        (Some(path), Some(r)) => Some(Span::new(
            files.intern(path),
            TextRange::new(TextSize::new(r.start), TextSize::new(r.end.max(r.start))),
        )),
        _ => None,
    };
    let namespaced = format!("{product}:{}", f.fingerprint);
    let mut finding = Finding::new(
        rule.clone(),
        severity(f.severity),
        span,
        f.message.clone(),
        &namespaced,
    );
    // A stable, message-independent identity derived from the sibling's own fingerprint.
    finding.fingerprint = Fingerprint::compute(&rule, &namespaced, "");
    finding.required.clone_from(&f.required);
    out.namespaces.insert(finding.fingerprint, namespaced);
    Ok(finding)
}

/// The suppression record of `e` as frob's exception type.
fn exception(e: &DocException) -> Result<Exception, Failure> {
    let kind = match e.kind.as_str() {
        "accept" => ExceptionKind::Accept,
        "defer" => ExceptionKind::Defer,
        "hotfix" => ExceptionKind::Hotfix,
        "baseline" => ExceptionKind::Baseline,
        other => return Err(malformed(format!("exception kind `{other}` is unknown"))),
    };
    Ok(Exception {
        kind,
        rule: e
            .rule
            .parse()
            .map_err(|err| malformed(format!("exception rule: {err}")))?,
        reason: e.because.clone(),
        ticket: e.ticket.clone(),
        until: e.until.clone(),
    })
}

/// Merge `doc` into `out`; return the ticket-bound exceptions frob must evaluate.
///
/// # Errors
///
/// A [`Failure`] (malformed) when a finding or exception is unusable; nothing is merged then.
pub(super) fn merge(
    product: &str,
    doc: Doc,
    files: &mut FileInterner,
    out: &mut External,
) -> Result<Vec<SiblingException>, Failure> {
    if !doc.compute_digest.starts_with("blake3:") || doc.compute_digest.len() != 71 {
        return Err(malformed(format!(
            "compute_digest `{}` is not blake3: plus 64 hex digits",
            doc.compute_digest
        )));
    }
    let mut staged = External::default();
    for f in &doc.findings {
        let merged = finding(product, f, files, &mut staged)?;
        staged.findings.push(merged);
    }
    let by_id: HashMap<&str, &DocException> =
        doc.exceptions.iter().map(|e| (e.id.as_str(), e)).collect();
    for s in &doc.suppressed {
        let e = by_id.get(s.exception.as_str()).ok_or_else(|| {
            malformed(format!(
                "suppressed finding names unknown exception `{}`",
                s.exception
            ))
        })?;
        if matches!(s.finding.severity, Sev::Unresolved) && e.kind == "accept" {
            return Err(malformed("an accept parks an Unresolved finding (EXC016)"));
        }
        let merged = finding(product, &s.finding, files, &mut staged)?;
        staged.suppressed.push((merged, exception(e)?));
    }
    for r in &doc.rules {
        if r.subjects_examined == 0 && r.unresolved == 0 && r.findings == 0 {
            tracing::warn!(product, rule = %r.rule, "rule measured nothing");
            staged.warnings.push(format!("{product} rule {} examined no subject and reported nothing (a framework bug, not clean evidence)", r.rule));
        }
    }
    for f in &doc.fidelity {
        let mut row = LanguageFidelity {
            fidelity: f.level.clone(),
            ..LanguageFidelity::default()
        };
        for rule in &f.not_applicable_rules {
            if let Ok(id) = rule.parse::<RuleId>() {
                *row.not_applicable
                    .entry(id.family().to_owned())
                    .or_default() += 1;
            }
        }
        staged
            .languages
            .push((format!("{product}:{}", f.language), row));
    }
    let exceptions = doc
        .exceptions
        .iter()
        .filter_map(|e| e.bound(product, &doc.suppressed))
        .collect();
    out.findings.extend(staged.findings);
    out.suppressed.extend(staged.suppressed);
    out.namespaces.extend(staged.namespaces);
    out.languages.extend(staged.languages);
    out.warnings.extend(staged.warnings);
    Ok(exceptions)
}

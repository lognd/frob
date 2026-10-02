//! Required marks for Unresolved findings (cli.md section 2, the one gate mechanism).

use gob_diagnostics::{RequiredMarks, RequiredReason};
use gob_rules::{Finding, RuleId, Severity};

use crate::report::PendingMark;
use crate::snapshot::Snapshot;

/// Message prefix gob-ir will use for an opaque that needs an annotation.
pub(crate) const ANNOTATION_PREFIX: &str = "annotation-required:";

/// Rules flagged `must_measure`; empty until `RuleMeta` carries the flag (G06).
pub(crate) const MUST_MEASURE: &[&str] = &[];

/// Number of subjects `rule` examined, when the pipeline can tell; `None` when it cannot.
fn subjects_examined(snap: &Snapshot, rule: &str) -> Option<usize> {
    match rule {
        "TICK001" | "TICK003" | "TODO002" | "REF001" => Some(usize::from(snap.ledger.is_some())),
        _ => None,
    }
}

/// One Unresolved finding per `must_measure` rule that examined nothing, with its pending mark.
pub(crate) fn zero_subjects(
    snap: &Snapshot,
    must_measure: &[&str],
) -> (Vec<Finding>, Vec<PendingMark>) {
    let mut findings = Vec::new();
    let mut marks = Vec::new();
    for rule in must_measure {
        let Ok(id) = rule.parse::<RuleId>() else {
            tracing::warn!(rule, "must_measure names an invalid rule id");
            continue;
        };
        match subjects_examined(snap, rule) {
            Some(0) => {
                let message = format!("{rule} examined zero subjects (no ledger present)");
                tracing::warn!(rule, "must_measure rule examined zero subjects");
                findings.push(Finding::new(
                    id,
                    Severity::Unresolved,
                    None,
                    message.clone(),
                    "zero-subjects",
                ));
                marks.push(PendingMark {
                    rule: (*rule).to_owned(),
                    message,
                    reason: RequiredReason::ZeroSubjects {
                        rule: (*rule).to_owned(),
                    },
                });
            }
            Some(_) => {}
            None => tracing::debug!(rule, "subject count not tracked; ZeroSubjects not checked"),
        }
    }
    (findings, marks)
}

/// The stub `AnnotationRequired` mapping from an `annotation-required:` message.
fn annotation_reason(f: &Finding) -> Option<RequiredReason> {
    let rest = f.message.strip_prefix(ANNOTATION_PREFIX)?.trim_start();
    let code = rest.split_whitespace().next().unwrap_or_default();
    Some(RequiredReason::AnnotationRequired {
        code: code.to_owned(),
        public_surface: true,
    })
}

/// Marks for every Unresolved finding: pending marks first, then the annotation stub.
pub(crate) fn build_marks(findings: &[Finding], pending: &[PendingMark]) -> RequiredMarks {
    let mut marks = RequiredMarks::new();
    for f in findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved)
    {
        let reason = pending
            .iter()
            .find(|p| p.rule == f.rule.as_str() && p.message == f.message)
            .map(|p| p.reason.clone())
            .or_else(|| annotation_reason(f));
        if let Some(reason) = reason {
            marks.insert(f, reason);
        }
    }
    marks
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unresolved(msg: &str) -> Finding {
        Finding::new(
            "TOOL001".parse().unwrap(),
            Severity::Unresolved,
            None,
            msg,
            "x",
        )
    }

    #[test]
    fn annotation_prefix_maps_to_a_required_reason() {
        let f = unresolved("annotation-required: opaque-fn at pub fn x");
        let marks = build_marks(std::slice::from_ref(&f), &[]);
        assert_eq!(
            marks.get(&f),
            Some(&RequiredReason::AnnotationRequired {
                code: "opaque-fn".into(),
                public_surface: true
            })
        );
    }

    #[test]
    fn unrelated_unresolved_is_not_marked() {
        let f = unresolved("sample too small");
        assert!(build_marks(&[f], &[]).is_empty());
    }

    #[test]
    fn pending_mark_matches_by_rule_and_message() {
        let f = unresolved("tool missing");
        let pending = [PendingMark {
            rule: "TOOL001".into(),
            message: "tool missing".into(),
            reason: RequiredReason::SiblingMissing {
                product: "crunk".into(),
            },
        }];
        assert_eq!(build_marks(&[f], &pending).len(), 1);
    }
}

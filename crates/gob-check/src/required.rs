//! Required marks for Unresolved findings (cli.md section 2, the one gate mechanism).
//!
//! A finding carries its own [`gob_rules::RequiredReason`]; this module adds the
//! two pipeline-level sources (a typed `annotation-required` reason and a
//! `must_measure` rule that examined nothing); the gate reads `Finding.required`.

use std::collections::BTreeMap;

use gob_rules::{Finding, RequiredReason, RuleId, RuleMeta, Severity, UnresolvedReason};

/// The required Unresolved finding for the `must_measure` rule `id` that examined zero subjects.
pub(crate) fn zero_subject_finding(id: &str) -> Option<Finding> {
    let Ok(rule) = id.parse::<RuleId>() else {
        tracing::warn!(rule = id, "must_measure names an invalid rule id");
        return None;
    };
    tracing::warn!(rule = id, "must_measure rule examined zero subjects");
    Some(
        Finding::new(
            rule,
            Severity::Unresolved,
            None,
            format!(
                "{id} examined zero subjects; it is flagged must_measure, so silence is not a pass"
            ),
            "zero-subjects",
        )
        .with_reason(UnresolvedReason::Vacuous)
        .with_required(RequiredReason::ZeroSubjects {
            rule: id.to_owned(),
        }),
    )
}

/// One Unresolved, required finding per applicable `must_measure` rule that examined zero subjects.
///
/// `subjects` holds the count of every rule that was evaluated this run; a rule
/// absent from it was not evaluated (filtered out, or not tracked) and is
/// skipped. `applicable` decides whether the rule's scope is non-empty here.
pub(crate) fn zero_subjects(
    must_measure: &[&'static RuleMeta],
    subjects: &BTreeMap<String, usize>,
    applicable: &dyn Fn(&RuleMeta) -> bool,
) -> Vec<Finding> {
    let mut out = Vec::new();
    for meta in must_measure {
        match subjects.get(meta.id) {
            Some(0) if applicable(meta) => out.extend(zero_subject_finding(meta.id)),
            Some(0) => {
                tracing::debug!(
                    rule = meta.id,
                    "must_measure rule not applicable here; no finding"
                );
            }
            Some(_) => {}
            None => {
                tracing::debug!(
                    rule = meta.id,
                    "rule not evaluated or not counted; ZeroSubjects not checked"
                );
            }
        }
    }
    out
}

/// The `AnnotationRequired` mark of a finding whose typed reason is an `annotation-required` one.
fn annotation_reason(f: &Finding) -> Option<RequiredReason> {
    if let Some(reason) = f.reason.as_ref().filter(|r| r.is_annotation()) {
        return Some(RequiredReason::AnnotationRequired {
            code: reason
                .code()
                .strip_prefix("annotation-required:")
                .unwrap_or(reason.code())
                .to_owned(),
            public_surface: *reason == UnresolvedReason::AnnotationSignature,
        });
    }
    None
}

/// Give typed annotation Unresolved findings their required reason.
pub(crate) fn mark_annotations(findings: &mut [Finding]) {
    for f in findings
        .iter_mut()
        .filter(|f| f.severity == Severity::Unresolved)
    {
        if f.required.is_none() {
            f.required = annotation_reason(f);
        }
    }
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

    // frob:tests crates/gob-check/src/required.rs::mark_annotations
    #[test]
    fn an_annotation_prefix_in_the_message_alone_marks_nothing() {
        let mut fs = [unresolved("annotation-required: opaque-fn at pub fn x")];
        mark_annotations(&mut fs);
        assert!(fs[0].required.is_none());
        assert!(fs[0].reason.is_none());
    }

    // frob:tests crates/gob-check/src/required.rs::mark_annotations
    #[test]
    fn a_typed_annotation_reason_maps_to_a_required_mark_without_reading_the_message() {
        let f = unresolved("opaque signature at pub fn x")
            .with_reason(UnresolvedReason::AnnotationEffects);
        let mut fs = [f];
        mark_annotations(&mut fs);
        assert_eq!(
            fs[0].required,
            Some(RequiredReason::AnnotationRequired {
                code: "effects".into(),
                public_surface: false
            })
        );
    }

    #[test]
    fn a_zero_subject_finding_is_typed_vacuous() {
        let f = zero_subject_finding("REF001").expect("valid id");
        assert_eq!(f.reason, Some(UnresolvedReason::Vacuous));
    }

    #[test]
    fn unrelated_unresolved_is_not_marked() {
        let mut fs = [unresolved("sample too small")];
        mark_annotations(&mut fs);
        assert!(fs[0].required.is_none());
    }

    #[test]
    fn a_reason_carried_by_the_finding_is_marked() {
        let f = unresolved("tool missing").with_required(RequiredReason::SiblingMissing {
            product: "crunk".into(),
        });
        let mut fs = [f];
        mark_annotations(&mut fs);
        assert!(fs[0].required.is_some());
    }

    static MEASURED: RuleMeta = RuleMeta {
        id: "REF001",
        slug: "measured",
        family: "REF",
        product: "frob",
        severity: Severity::Error,
        summary: "s",
        explanation: "e",
        tier: gob_rules::Tier::Universal,
        scope: gob_rules::Scope::File,
        fix: gob_rules::FixKind::Manual,
        polarity: gob_rules::Polarity::Pplus,
        must_measure: true,
        version: 1,
        since: "2.0.0",
        module: "t",
    };

    // frob:tests crates/gob-check/src/required.rs::zero_subjects
    #[test]
    fn only_an_applicable_rule_with_zero_subjects_is_flagged() {
        let metas = [&MEASURED];
        let zero = BTreeMap::from([("REF001".to_owned(), 0)]);
        let flagged = zero_subjects(&metas, &zero, &|_| true);
        assert_eq!(flagged.len(), 1);
        assert_eq!(flagged[0].severity, Severity::Unresolved);
        assert_eq!(
            flagged[0].required,
            Some(RequiredReason::ZeroSubjects {
                rule: "REF001".into()
            })
        );
        assert!(
            zero_subjects(&metas, &zero, &|_| false).is_empty(),
            "not applicable"
        );
        let some = BTreeMap::from([("REF001".to_owned(), 3)]);
        assert!(
            zero_subjects(&metas, &some, &|_| true).is_empty(),
            "examined"
        );
        assert!(
            zero_subjects(&metas, &BTreeMap::new(), &|_| true).is_empty(),
            "not evaluated"
        );
    }
}

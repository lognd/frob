//! Required marks for Unresolved findings (cli.md section 2, the one gate mechanism).
//!
//! A finding carries its own [`gob_rules::RequiredReason`]; this module adds the
//! two pipeline-level sources (an `annotation-required:` message and a
//! `must_measure` rule that examined nothing) and turns the marks into the
//! [`gob_diagnostics::RequiredMarks`] table the gate reads.

use std::collections::BTreeMap;

use gob_diagnostics::{RequiredMarks, RequiredReason as GateReason};
use gob_rules::{Finding, RequiredReason, RuleId, RuleMeta, Severity};

/// Message prefix gob-ir uses for an opaque that needs an annotation.
pub(crate) const ANNOTATION_PREFIX: &str = "annotation-required:";

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
        let Ok(id) = meta.id.parse::<RuleId>() else {
            tracing::warn!(rule = meta.id, "must_measure names an invalid rule id");
            continue;
        };
        match subjects.get(meta.id) {
            Some(0) if applicable(meta) => {
                tracing::warn!(rule = meta.id, "must_measure rule examined zero subjects");
                out.push(
                    Finding::new(
                        id,
                        Severity::Unresolved,
                        None,
                        format!(
                            "{} examined zero subjects; it is flagged must_measure, so silence is not a pass",
                            meta.id
                        ),
                        "zero-subjects",
                    )
                    .with_required(RequiredReason::ZeroSubjects {
                        rule: meta.id.to_owned(),
                    }),
                );
            }
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

/// The `AnnotationRequired` reason of an `annotation-required:` message, until gob-ir sets it itself.
fn annotation_reason(f: &Finding) -> Option<RequiredReason> {
    let rest = f.message.strip_prefix(ANNOTATION_PREFIX)?.trim_start();
    let code = rest.split_whitespace().next().unwrap_or_default();
    Some(RequiredReason::AnnotationRequired {
        code: code.to_owned(),
        public_surface: true,
    })
}

/// The gate-side form of a finding's required reason.
///
/// `gob-diagnostics` keeps its own copy of the enum until it re-exports
/// `gob_rules::RequiredReason` and drops `RequiredMarks`.
fn gate_reason(reason: &RequiredReason) -> GateReason {
    match reason {
        RequiredReason::SiblingMissing { product } => GateReason::SiblingMissing {
            product: product.clone(),
        },
        RequiredReason::AnnotationRequired {
            code,
            public_surface,
        } => GateReason::AnnotationRequired {
            code: code.clone(),
            public_surface: *public_surface,
        },
        RequiredReason::ZeroSubjects { rule } => GateReason::ZeroSubjects { rule: rule.clone() },
    }
}

/// Give annotation-prefixed Unresolved findings their reason, then collect every mark.
pub(crate) fn build_marks(findings: &mut [Finding]) -> RequiredMarks {
    let mut marks = RequiredMarks::new();
    for f in findings
        .iter_mut()
        .filter(|f| f.severity == Severity::Unresolved)
    {
        if f.required.is_none() {
            f.required = annotation_reason(f);
        }
        if let Some(reason) = &f.required {
            marks.insert(f, gate_reason(reason));
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

    // frob:tests crates/gob-check/src/required.rs::build_marks
    #[test]
    fn annotation_prefix_maps_to_a_required_reason() {
        let mut fs = [unresolved("annotation-required: opaque-fn at pub fn x")];
        let marks = build_marks(&mut fs);
        assert_eq!(
            marks.get(&fs[0]),
            Some(&GateReason::AnnotationRequired {
                code: "opaque-fn".into(),
                public_surface: true
            })
        );
    }

    #[test]
    fn unrelated_unresolved_is_not_marked() {
        let mut fs = [unresolved("sample too small")];
        assert!(build_marks(&mut fs).is_empty());
    }

    #[test]
    fn a_reason_carried_by_the_finding_is_marked() {
        let f = unresolved("tool missing").with_required(RequiredReason::SiblingMissing {
            product: "crunk".into(),
        });
        let mut fs = [f];
        assert_eq!(build_marks(&mut fs).len(), 1);
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

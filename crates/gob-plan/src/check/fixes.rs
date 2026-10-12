//! Fix checks for one rule (GRL015; grl-spec.md section 8, security.md section 2.10).
//!
//! A fix must carry an applicability (there is no default), a plugin fix may edit only inside the
//! finding's own span, and a `fix host` is the standard library's alone.

// frob:ticket 01M3ZX7ECR0R91Q5R2T16R03NG
use gob_text::{Span, TextRange};

use super::{Code, Diagnostic, Tier};
use crate::grl::ast::{ClauseKind, Fix, FixKind, Placement, Rule, ShapeKind, Source};

/// Check the fixes of one rule; diagnostics are in source order.
pub(super) fn check_rule(rule: &Rule, tier: Tier) -> Vec<Diagnostic> {
    let reports: Vec<_> = rule
        .clauses
        .iter()
        .filter_map(|c| match &c.node {
            ClauseKind::Report(r) => Some((c.span, r)),
            _ => None,
        })
        .collect();
    let mut out = Vec::new();
    for cl in &rule.clauses {
        let ClauseKind::Fix(fix) = &cl.node else {
            continue;
        };
        if fix.applicability.is_none() && !matches!(fix.kind, FixKind::Manual { .. }) {
            out.push(
                Diagnostic::new(
                    Code::Grl015,
                    "this fix does not say how safe it is to apply",
                    cl.span,
                    "no applicability",
                )
                .with_note("every fix names its applicability; there is no default")
                .with_help(
                    "add one at the end of the fix: `[machine]`, `[maybe-incorrect]` or `[has-placeholders]`",
                ),
            );
        }
        match (&fix.kind, tier) {
            (FixKind::Host { name, .. }, Tier::Plugin) => out.push(
                Diagnostic::new(
                    Code::Grl015,
                    "a plugin rule cannot use a host fix",
                    cl.span,
                    format!("`fix host {}` is std only", name.text),
                )
                .with_note(
                    "host fixes edit other files and are written by the standard library alone",
                )
                .with_help("fix the finding's own span instead, or use `fix manual \"steps\"`"),
            ),
            (_, Tier::Plugin) => {
                if let Some(d) = outside_span(rule, &reports, fix, cl.span) {
                    out.push(d);
                }
            }
            (_, Tier::Std) => {}
        }
    }
    tracing::debug!(rule = %rule.id.text, diagnostics = out.len(), "checked rule fixes");
    out
}

/// The diagnostic for a plugin fix whose target is not a variable some `report` names.
fn outside_span(
    rule: &Rule,
    reports: &[(Span, &crate::grl::ast::Report)],
    fix: &Fix,
    fix_span: Span,
) -> Option<Diagnostic> {
    let (verb, target) = match &fix.kind {
        FixKind::Replace {
            placement, target, ..
        } => (
            match placement {
                None => "replaces",
                Some(Placement::Before) => "inserts before",
                Some(Placement::After) => "inserts after",
            },
            target,
        ),
        FixKind::Delete { target } => ("deletes", target),
        FixKind::Host { .. } | FixKind::Manual { .. } => return None,
    };
    if reports.iter().any(|(_, r)| r.target.text == target.text) {
        return None;
    }
    let what = rule
        .clauses
        .iter()
        .find_map(|c| match &c.node {
            ClauseKind::Find(b) if b.name.text == target.text => match &b.source {
                Source::Shape(s) => match &s.node {
                    ShapeKind::Kind { kind, .. } => Some(format!("the whole {}", kind.text)),
                    _ => None,
                },
                Source::Side(_) => None,
            },
            _ => None,
        })
        .unwrap_or_else(|| "text outside the finding".to_string());
    let mut d = Diagnostic::new(
        Code::Grl015,
        "this fix edits outside the finding it belongs to",
        fix_span,
        format!("{verb} `{}`, {what}", target.text),
    );
    if let Some((rspan, r)) = reports.first() {
        d = d.with_secondary(
            Span::new(
                rspan.file,
                TextRange::new(rspan.range.start(), r.target.span.range.end()),
            ),
            format!("the finding is reported on `{}`", r.target.text),
        );
        d = d
            .with_note("a pack fix may edit only inside the finding's own span")
            .with_help(format!(
                "fix `{0}` instead: `fix {0} -> `...` [machine]`; a fix elsewhere needs a pack that holds `fix.machine`",
                r.target.text
            ));
    }
    Some(d)
}

//! The `rules list` row of a GRL rule: the same [`RuleRow`] shape a Rust std rule and a pack rule get.

// frob:ticket 01M48R07AYMKWPKZDXW4BKKSMH

use gob_rules::{FixKind, Provenance as RuleProvenance, RuleMeta, RuleRow, Scope, Severity, Tier};

use super::convert::{needed_capabilities, read_names};
use crate::grl::ast::{self, HeaderKind, LangSet, Rule};

/// The release a GRL rule is taken to have shipped in when it has no `since` header.
const DEFAULT_SINCE: &str = "0.0.0";

/// Leak a string for the `&'static` fields of a row; rows are built once per loaded rule.
fn leak(s: impl Into<String>) -> &'static str {
    Box::leak(s.into().into_boxed_str())
}

/// The first prose line of the explain block, or empty when there is none.
fn summary_of(rule: &Rule) -> &str {
    rule.explain
        .as_ref()
        .and_then(|e| {
            e.text
                .value
                .lines()
                .map(str::trim)
                .find(|l| !l.is_empty() && !l.starts_with('#'))
        })
        .unwrap_or_default()
}

/// The `rules list` row of a GRL rule, read from its headers alone (no clause is lowered).
// frob:ticket 01M48R07AYMKWPKZDXW4BKKSMH
pub fn grl_row(rule: &Rule, product: &'static str, provenance: &RuleProvenance) -> RuleRow {
    let id = leak(rule.id.text.clone());
    let family = leak(id.trim_end_matches(|c: char| c.is_ascii_digit()));
    let mut meta = RuleMeta {
        id,
        slug: leak(rule.slug.value.clone()),
        family,
        product,
        severity: Severity::Error,
        summary: leak(summary_of(rule)),
        explanation: "",
        tier: Tier::Universal,
        scope: Scope::File,
        fix: FixKind::Manual,
        polarity: ast::Polarity::Pplus,
        must_measure: false,
        needs: gob_rules::Needs::Structural,
        version: 1,
        since: DEFAULT_SINCE,
        module: "grl",
    };
    let mut fidelity = None;
    for h in &rule.headers {
        match &h.node {
            HeaderKind::Lang(LangSet::One(_) | LangSet::List(_)) => meta.tier = Tier::Lang,
            HeaderKind::Polarity(p) => meta.polarity = *p,
            HeaderKind::Scope(ast::Scope::Repo) => meta.scope = Scope::Repo,
            HeaderKind::MustMeasure => meta.must_measure = true,
            HeaderKind::Since(s) => meta.since = leak(s.value.clone()),
            HeaderKind::Fidelity(f) => fidelity = Some(f.to_string()),
            _ => {}
        }
    }
    let mut row = RuleRow::from_meta(&meta, provenance);
    row.fidelity = fidelity;
    row.needs = needed_capabilities(rule)
        .iter()
        .map(|c| c.name().to_owned())
        .collect();
    row.reads = read_names(rule);
    tracing::debug!(rule = row.id, since = row.since, "built GRL rule row");
    row
}

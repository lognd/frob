//! `[lint]` of `crunk.toml` applied to declared rules and to findings.
//!
//! The spec crate owns the table and the catalog default ([`DesignSpec::severity`]); this module is
//! the one place that maps its three levels (`error`, `warn`, `off`) onto the pipeline's
//! [`Severity`], so a rule body never repeats the mapping (COLOR001 still carries its own copy
//! until its migration, ~6AN9XJY).

// frob:ticket 01M43ATASM383KB9130JY79XVV

use crunk_spec::catalog::is_rule_id;
use crunk_spec::{DesignSpec, Severity as SpecSeverity};
use gob_rules::{Finding, RuleDef, Severity};

/// The severity `def` runs at under `spec`; `None` when `[lint]` turns it `off`.
pub fn severity_of(spec: &DesignSpec, def: &RuleDef) -> Option<Severity> {
    map(spec.severity(def.id))
}

fn map(level: SpecSeverity) -> Option<Severity> {
    match level {
        SpecSeverity::Off => None,
        SpecSeverity::Warn => Some(Severity::Warn),
        SpecSeverity::Error => Some(Severity::Error),
    }
}

/// Apply `[lint]` to `findings` of catalog rules: `off` drops them, `warn` and `error` replace the
/// declared severity. Unresolved findings and findings of rules outside the catalog (the
/// directive scanner's PARSE and DSL findings) pass through untouched.
pub fn apply(spec: &DesignSpec, findings: Vec<Finding>) -> Vec<Finding> {
    findings
        .into_iter()
        .filter_map(|mut f| {
            if f.severity == Severity::Unresolved || !is_rule_id(f.rule.as_str()) {
                return Some(f);
            }
            let Some(level) = map(spec.severity(f.rule.as_str())) else {
                tracing::debug!(rule = %f.rule, "finding dropped: rule is off in [lint]");
                return None;
            };
            if level != f.severity {
                tracing::debug!(rule = %f.rule, from = ?f.severity, to = ?level, "[lint] changes severity");
                f.severity = level;
            }
            Some(f)
        })
        .collect()
}

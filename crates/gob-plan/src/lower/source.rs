//! Source text to plans: the one-call path generators use (parse, then lower every rule), no I/O.

// frob:ticket 01M3ZX7HN0YF3SYGVJRT5H07H5

use gob_text::FileInterner;

use super::{LowerError, lower_rule};
use crate::grl;
use crate::plan::{Plan, Provenance};

/// Why a GRL source could not become plans.
#[derive(Debug, thiserror::Error)]
pub enum SourceError {
    /// The text does not parse; the payload is the compiler's rendered report.
    #[error("{0}")]
    Syntax(String),
    /// A rule could not be lowered.
    #[error("rule {rule}: {source}")]
    Lower {
        /// The rule id.
        rule: String,
        /// Why lowering failed.
        source: LowerError,
    },
}

/// Parse GRL `text` (named `path` in reports) and lower each rule to a std-provenance plan, in source order.
///
/// # Errors
/// [`SourceError`] for a syntax error or the first rule that cannot be lowered.
pub fn lower_source(path: &str, text: &str) -> Result<Vec<Plan>, SourceError> {
    let parsed = grl::parse(FileInterner::new().intern(path), text);
    if !parsed.is_ok() {
        tracing::warn!(
            path,
            errors = parsed.errors.len(),
            "GRL source does not parse"
        );
        return Err(SourceError::Syntax(crate::check::compile_report(
            path, text,
        )));
    }
    parsed
        .file
        .rules
        .iter()
        .map(|rule| {
            lower_rule(rule, Provenance::Std).map_err(|source| SourceError::Lower {
                rule: rule.id.text.clone(),
                source,
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const RULE: &str = "rule DANGER001 \"danger-call\" {\n  lang typescript\n  severity error\n  find c: call where c.callee == \"danger\"\n  report c \"danger\"\n  explain \"\"\"\n    Danger.\n\n    ## Remedy\n    Do not.\n  \"\"\"\n}\n";

    // frob:tests crates/gob-plan/src/lower/source.rs::lower_source
    #[test]
    fn lowers_each_rule_of_a_source() {
        let plans = lower_source("r.grl", RULE).unwrap();
        assert_eq!(plans.len(), 1);
        assert_eq!(plans[0].rule(), "DANGER001");
    }

    // frob:tests crates/gob-plan/src/lower/source.rs::lower_source
    #[test]
    fn a_syntax_error_is_reported_not_lowered() {
        assert!(matches!(
            lower_source("r.grl", "rule {"),
            Err(SourceError::Syntax(_))
        ));
    }
}

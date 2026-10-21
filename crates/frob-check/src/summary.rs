//! The fix-availability line that ends a plain `frob check` summary.
//!
//! A plain check never writes and never prompts (diagnostics.md section 4); when fixes
//! exist it only says how to apply them.
// frob:ticket 01M3ZX81ZPA8J5RXBEZ14SZNSZ

use gob_rules::{Applicability, Finding};

/// The closing line for `fixes` available fixes of which `safe` are machine, or `None` when none.
#[must_use]
pub fn fix_summary_line(fixes: usize, safe: usize) -> Option<String> {
    if fixes == 0 {
        return None;
    }
    let noun = if fixes == 1 { "fix" } else { "fixes" };
    let how = if safe == 0 {
        "run frob fix --interactive to review them".to_owned()
    } else {
        "run frob check --fix, or frob fix --interactive to review the rest".to_owned()
    };
    Some(format!("{fixes} {noun} available ({safe} safe): {how}"))
}

/// The closing line for the fixes attached to `findings`; manual (edit-less) fixes do not count.
#[must_use]
pub fn fix_summary_for(findings: &[Finding]) -> Option<String> {
    let applicabilities: Vec<Applicability> = findings
        .iter()
        .filter_map(|f| f.fix.as_ref().map(|fix| fix.applicability))
        .filter(|a| *a != Applicability::Manual)
        .collect();
    let safe = applicabilities
        .iter()
        .filter(|a| **a == Applicability::Machine)
        .count();
    let line = fix_summary_line(applicabilities.len(), safe);
    tracing::debug!(
        fixes = applicabilities.len(),
        safe,
        "fix availability counted"
    );
    line
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests fix_summary_line
    #[test]
    fn three_fixes_one_safe_ends_with_the_documented_line() {
        assert_eq!(
            fix_summary_line(3, 1).as_deref(),
            Some(
                "3 fixes available (1 safe): run frob check --fix, or frob fix --interactive to review the rest"
            )
        );
    }

    // frob:tests fix_summary_line
    #[test]
    fn no_fixes_print_nothing_and_no_safe_fix_omits_check_fix() {
        assert_eq!(fix_summary_line(0, 0), None);
        let line = fix_summary_line(1, 0).expect("a line");
        assert!(line.starts_with("1 fix available (0 safe)"), "{line}");
        assert!(!line.contains("check --fix"), "{line}");
    }

    // frob:tests fix_summary_for
    #[test]
    fn no_findings_give_no_line() {
        assert_eq!(fix_summary_for(&[]), None);
    }
}

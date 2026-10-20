//! `replaces` as a privilege (security.md 2.9, plugins.md 6.1 override row).
//!
//! A pack may replace a std rule only by declaring it; the replaced rule keeps
//! running as a shadow, and a finding only the shadow produces is Unresolved
//! `replaced-divergence`. Replacing a kernel-integrity rule (PACK, CAP004,
//! GATE) needs `--allow-replace ID` on every invocation. A new `replaces` is a
//! GATE001 weakening.

// frob:ticket 01M3ZX8068R0AEK980CWAGXYRJ

use std::collections::BTreeSet;

use crate::finding_handle::{Finding, Span};

/// Stable code of an Unresolved finding for a shadow-only finding.
pub const REPLACED_DIVERGENCE: &str = "replaced-divergence";

/// One declared override: `pack` replaces the std rule `rule`.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Replacement {
    /// The pack declaring `replaces`.
    pub pack: String,
    /// The std rule id being replaced.
    pub rule: String,
}

/// Why a `replaces` declaration was refused.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ReplaceError {
    /// The target is kernel-integrity and `--allow-replace` was not passed for it.
    #[error(
        "pack `{pack}` replaces kernel-integrity rule {rule}: refused without --allow-replace {rule}"
    )]
    KernelIntegrity {
        /// The declaring pack.
        pack: String,
        /// The kernel-integrity rule id.
        rule: String,
    },
}

/// The ids passed as `--allow-replace ID`, valid for one invocation only.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct AllowReplace {
    ids: BTreeSet<String>,
}

impl AllowReplace {
    /// Builds the set from the flag values of this invocation.
    pub fn new<I: IntoIterator<Item = String>>(ids: I) -> Self {
        Self {
            ids: ids.into_iter().collect(),
        }
    }

    /// True when `rule` was explicitly allowed.
    pub fn allows(&self, rule: &str) -> bool {
        self.ids.contains(rule)
    }
}

/// True for the kernel-integrity rules: the PACK and GATE families and CAP004.
pub fn is_kernel_integrity(rule: &str) -> bool {
    let digits = |p: &str| {
        rule.strip_prefix(p)
            .is_some_and(|d| !d.is_empty() && d.bytes().all(|b| b.is_ascii_digit()))
    };
    digits("PACK") || digits("GATE") || rule == "CAP004"
}

/// Refuses replacing a kernel-integrity rule unless `allow` names it.
///
/// # Errors
///
/// [`ReplaceError::KernelIntegrity`] when the target is PACK, CAP004 or GATE
/// and `allow` does not name it.
pub fn check_replacement(r: &Replacement, allow: &AllowReplace) -> Result<(), ReplaceError> {
    if is_kernel_integrity(&r.rule) && !allow.allows(&r.rule) {
        tracing::warn!(pack = %r.pack, rule = %r.rule, "replaces: kernel-integrity target refused");
        return Err(ReplaceError::KernelIntegrity {
            pack: r.pack.clone(),
            rule: r.rule.clone(),
        });
    }
    tracing::debug!(pack = %r.pack, rule = %r.rule, "replaces: accepted");
    Ok(())
}

/// The replacements in `new` absent from `old`: each is a GATE001 weakening.
pub fn added_replacements(old: &[Replacement], new: &[Replacement]) -> Vec<Replacement> {
    let known: BTreeSet<&Replacement> = old.iter().collect();
    let added: Vec<Replacement> = new.iter().filter(|r| !known.contains(r)).cloned().collect();
    tracing::debug!(count = added.len(), "replaces: new declarations (GATE001)");
    added
}

/// A shadow-only finding: Unresolved `replaced-divergence`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Divergence {
    /// The replaced std rule whose shadow produced the finding.
    pub rule: String,
    /// The pack that replaces it.
    pub pack: String,
    /// Where the shadow found something the replacement did not.
    pub primary: Span,
    /// True when the family is security-relevant, so the Unresolved is required.
    pub required: bool,
}

/// Findings the shadow produced at spans the replacement did not report.
pub fn divergences(
    r: &Replacement,
    replacement: &[Finding],
    shadow: &[Finding],
    security_relevant: bool,
) -> Vec<Divergence> {
    let seen: BTreeSet<(u32, usize, usize)> = replacement.iter().map(span_key).collect();
    let out: Vec<Divergence> = shadow
        .iter()
        .filter(|f| !seen.contains(&span_key(f)))
        .map(|f| Divergence {
            rule: r.rule.clone(),
            pack: r.pack.clone(),
            primary: f.primary,
            required: security_relevant,
        })
        .collect();
    if !out.is_empty() {
        tracing::warn!(rule = %r.rule, pack = %r.pack, count = out.len(), "replaces: replaced-divergence");
    }
    out
}

fn span_key(f: &Finding) -> (u32, usize, usize) {
    (f.primary.file.0, f.primary.start, f.primary.end)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::finding_handle::FileHandle;

    fn rep(rule: &str) -> Replacement {
        Replacement {
            pack: "p".into(),
            rule: rule.into(),
        }
    }

    fn finding(start: usize) -> Finding {
        Finding {
            code: "R".into(),
            primary: Span {
                file: FileHandle(1),
                start,
                end: start + 1,
            },
            secondary: vec![],
        }
    }

    #[test]
    fn shadow_only_finding_is_replaced_divergence() {
        let d = divergences(
            &rep("PY001"),
            &[finding(0)],
            &[finding(0), finding(5)],
            true,
        );
        assert_eq!(d.len(), 1);
        assert_eq!(d[0].primary.start, 5);
        assert!(d[0].required);
        assert_eq!(REPLACED_DIVERGENCE, "replaced-divergence");
    }

    #[test]
    fn agreeing_shadow_reports_nothing() {
        assert!(divergences(&rep("PY001"), &[finding(0)], &[finding(0)], true).is_empty());
    }

    #[test]
    fn replacing_cap004_without_allow_replace_is_refused() {
        let none = AllowReplace::default();
        assert!(check_replacement(&rep("CAP004"), &none).is_err());
        assert!(check_replacement(&rep("PACK004"), &none).is_err());
        assert!(check_replacement(&rep("GATE001"), &none).is_err());
        assert!(check_replacement(&rep("PY001"), &none).is_ok());
        let allow = AllowReplace::new(["CAP004".to_owned()]);
        assert!(check_replacement(&rep("CAP004"), &allow).is_ok());
        assert!(check_replacement(&rep("GATE001"), &allow).is_err());
    }

    #[test]
    fn new_replaces_is_a_weakening() {
        let added = added_replacements(&[rep("A001")], &[rep("A001"), rep("B001")]);
        assert_eq!(added, vec![rep("B001")]);
    }
}

//! "No new unknowns" for `check --base REF` (`security.md` section 2.7, I9).
//!
//! A change must not turn a decided P+ rule into an Unresolved one in a file it
//! touches. Existing Unresolved findings (present at base) stay non-failing so
//! adoption is never blocked. This module is the pure comparison: the caller
//! computes the base and head findings (the base side from a git snapshot, only
//! for changed files) and hands them in.

use std::collections::BTreeSet;
use std::fmt;

use gob_rules::{Finding, Polarity, Severity};

/// One finding located in a repository-relative file.
#[derive(Debug, Clone)]
pub struct LocatedFinding {
    /// Repository-relative path of the file the finding is in.
    pub path: String,
    /// The finding itself.
    pub finding: Finding,
}

/// An Unresolved P+ finding that exists at head but not at base, in a changed file.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct NewUnknown {
    /// The changed file the new Unresolved is in.
    pub path: String,
    /// The P+ rule that became Unresolved.
    pub rule: String,
}

impl fmt::Display for NewUnknown {
    /// Names the file and rule so the failure is actionable.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}: {} is newly Unresolved (decided at base); a change must not add unknowns for P+ rules",
            self.path, self.rule
        )
    }
}

/// Unresolved P+ findings in `changed` files at head that were not Unresolved at base.
///
/// `polarity_of` maps a rule id to its polarity (`None` for an unknown rule,
/// which is skipped). A `(path, rule)` pair already Unresolved at base is not
/// new, however many findings it carries. The result is sorted and deduplicated.
pub fn new_unknowns(
    changed: &[String],
    base: &[LocatedFinding],
    head: &[LocatedFinding],
    polarity_of: &dyn Fn(&str) -> Option<Polarity>,
) -> Vec<NewUnknown> {
    let changed: BTreeSet<&str> = changed.iter().map(String::as_str).collect();
    let unresolved = |lf: &&LocatedFinding| {
        lf.finding.severity == Severity::Unresolved && changed.contains(lf.path.as_str())
    };
    let at_base: BTreeSet<(&str, String)> = base
        .iter()
        .filter(unresolved)
        .map(|lf| (lf.path.as_str(), lf.finding.rule.to_string()))
        .collect();
    let out: BTreeSet<NewUnknown> = head
        .iter()
        .filter(unresolved)
        .filter_map(|lf| {
            let rule = lf.finding.rule.to_string();
            if polarity_of(&rule) != Some(Polarity::Pplus) {
                return None;
            }
            if at_base.contains(&(lf.path.as_str(), rule.clone())) {
                tracing::debug!(path = %lf.path, rule = %rule, "Unresolved existed at base; not new");
                return None;
            }
            tracing::warn!(path = %lf.path, rule = %rule, "new Unresolved for a P+ rule in a changed file");
            Some(NewUnknown {
                path: lf.path.clone(),
                rule,
            })
        })
        .collect();
    out.into_iter().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lf(path: &str, rule: &str, sev: Severity) -> LocatedFinding {
        LocatedFinding {
            path: path.to_owned(),
            finding: Finding::new(rule.parse().unwrap(), sev, None, "m", path),
        }
    }

    fn pol(rule: &str) -> Option<Polarity> {
        match rule {
            "SEC001" => Some(Polarity::Pplus),
            "SEC002" => Some(Polarity::Pminus),
            _ => None,
        }
    }

    fn changed() -> Vec<String> {
        vec!["a.rs".to_owned()]
    }

    // frob:tests crates/gob-check/src/base_unknowns.rs::new_unknowns
    #[test]
    fn new_unresolved_on_pplus_in_changed_file_is_reported() {
        let head = [lf("a.rs", "SEC001", Severity::Unresolved)];
        let got = new_unknowns(&changed(), &[], &head, &pol);
        assert_eq!(got.len(), 1);
        let msg = got[0].to_string();
        assert!(msg.contains("a.rs") && msg.contains("SEC001"));
    }

    // frob:tests crates/gob-check/src/base_unknowns.rs::new_unknowns
    #[test]
    fn unresolved_at_base_is_not_new() {
        let base = [lf("a.rs", "SEC001", Severity::Unresolved)];
        let head = [
            lf("a.rs", "SEC001", Severity::Unresolved),
            lf("a.rs", "SEC001", Severity::Unresolved),
        ];
        assert!(new_unknowns(&changed(), &base, &head, &pol).is_empty());
    }

    // frob:tests crates/gob-check/src/base_unknowns.rs::new_unknowns
    #[test]
    fn untouched_files_non_pplus_and_resolved_are_ignored() {
        let head = [
            lf("b.rs", "SEC001", Severity::Unresolved),
            lf("a.rs", "SEC002", Severity::Unresolved),
            lf("a.rs", "SEC001", Severity::Error),
            lf("a.rs", "ZZZ999", Severity::Unresolved),
        ];
        assert!(new_unknowns(&changed(), &[], &head, &pol).is_empty());
    }
}

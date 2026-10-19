//! The verdict type the architecture pass returns.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use gob_rules::{Finding, RuleId, Severity, UnresolvedReason};
use gob_text::{FileInterner, Span, TextRange, TextSize};

/// One architecture verdict before the product interns its span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArchFinding {
    /// The rule id (`CYCLE001`).
    pub rule: &'static str,
    /// The severity; `Unresolved` when `reason` is set.
    pub severity: Severity,
    /// Repo-relative file the finding points into.
    pub file: String,
    /// Byte range in that file.
    pub range: (usize, usize),
    /// The message.
    pub message: String,
    /// Why an Unresolved finding could not decide; `None` for a resolved finding.
    pub reason: Option<UnresolvedReason>,
    /// The anchor the fingerprint is computed from.
    pub anchor: String,
}

impl ArchFinding {
    /// A resolved finding at `severity`.
    pub(crate) fn fire(
        rule: &'static str,
        severity: Severity,
        site: (&str, (usize, usize)),
        message: String,
        anchor: String,
    ) -> Self {
        Self {
            rule,
            severity,
            file: site.0.to_owned(),
            range: site.1,
            message,
            reason: None,
            anchor,
        }
    }

    /// An Unresolved finding with its `reason`.
    pub(crate) fn unresolved(
        rule: &'static str,
        reason: UnresolvedReason,
        site: (&str, (usize, usize)),
        message: String,
        anchor: String,
    ) -> Self {
        Self {
            rule,
            severity: Severity::Unresolved,
            file: site.0.to_owned(),
            range: site.1,
            message,
            reason: Some(reason),
            anchor,
        }
    }

    /// Intern the span and build the pipeline [`Finding`]; `None` when the rule id is invalid.
    pub fn into_finding(self, files: &mut FileInterner) -> Option<Finding> {
        let id: RuleId = match self.rule.parse() {
            Ok(id) => id,
            Err(err) => {
                tracing::error!(rule = self.rule, %err, "architecture finding names an invalid rule id");
                return None;
            }
        };
        let size = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        let (start, end) = self.range;
        let span = Span::new(
            files.intern(&self.file),
            TextRange::new(size(start), size(end.max(start))),
        );
        let finding = Finding::new(id, self.severity, Some(span), self.message, &self.anchor);
        Some(match self.reason {
            Some(r) => finding.with_reason(r),
            None => finding,
        })
    }
}

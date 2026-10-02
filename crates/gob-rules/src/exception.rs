//! Exception data types and matching (directive parsing and the EXC rules stay with the product).

use std::ops::Range;

use gob_text::FileInterner;
use serde::{Deserialize, Serialize};

use crate::finding::Finding;
use crate::id::RuleId;

/// The four exception kinds from the exceptions design.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExceptionKind {
    /// Does not apply here by design; permanent.
    Accept,
    /// Real debt paid by a ticket.
    Defer,
    /// Quick fix that must be revisited; hard expiry.
    Hotfix,
    /// Mass legacy findings admitted at rule introduction.
    Baseline,
}

/// A recorded exception to one rule.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Exception {
    /// Which kind of exception this is.
    pub kind: ExceptionKind,
    /// The rule excepted.
    pub rule: RuleId,
    /// Why; vetted by `check_reason`.
    pub reason: String,
    /// Ticket that pays the debt, when the kind needs one.
    pub ticket: Option<String>,
    /// Optional ISO date (`YYYY-MM-DD`) after which the exception lapses.
    pub until: Option<String>,
}

/// An exception together with where it applies in the repository.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundException {
    /// The exception itself.
    pub exception: Exception,
    /// Repo-relative path the exception applies to.
    pub path: String,
    /// Byte range inside `path`; `None` means the whole file.
    pub range: Option<Range<usize>>,
}

impl BoundException {
    /// True when `f` is of this exception's rule and lies inside its binding.
    pub fn covers(&self, f: &Finding, ctx: &ExceptionCtx<'_>) -> bool {
        if f.rule != self.exception.rule {
            return false;
        }
        let Some(span) = f.span else {
            return false;
        };
        if ctx.files.path(span.file) != Some(self.path.as_str()) {
            return false;
        }
        self.range.as_ref().is_none_or(|r| {
            r.start <= to_usize(u32::from(span.range.start()))
                && to_usize(u32::from(span.range.end())) <= r.end
        })
    }

    /// Size of the bound region, for choosing the tightest cover.
    pub fn width(&self) -> usize {
        self.range.as_ref().map_or(usize::MAX, |r| r.end - r.start)
    }
}

fn to_usize(n: u32) -> usize {
    usize::try_from(n).unwrap_or(usize::MAX)
}

/// What exception matching needs to know about the repository.
#[derive(Debug, Clone, Copy)]
pub struct ExceptionCtx<'a> {
    /// Resolves the file ids inside finding spans to paths.
    pub files: &'a FileInterner,
}

/// What applying exceptions decided.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Resolved {
    /// Findings left standing.
    pub findings: Vec<Finding>,
    /// Suppressed findings with the exception that suppressed each.
    pub suppressed: Vec<(Finding, Exception)>,
}

/// Split `findings` into those left standing and those a bound exception covers.
///
/// A finding is covered by the tightest exception of its rule whose binding
/// contains its span; spanless findings are never covered. Input order is kept
/// in both halves.
pub fn apply_exceptions(
    findings: Vec<Finding>,
    exceptions: &[BoundException],
    ctx: &ExceptionCtx<'_>,
) -> Resolved {
    let mut kept = Vec::new();
    let mut suppressed = Vec::new();
    for f in findings {
        let best = exceptions
            .iter()
            .filter(|b| b.covers(&f, ctx))
            .min_by_key(|b| b.width());
        match best {
            Some(b) => {
                tracing::debug!(rule = %f.rule, path = %b.path, kind = ?b.exception.kind, "finding suppressed by exception");
                suppressed.push((f, b.exception.clone()));
            }
            None => kept.push(f),
        }
    }
    tracing::debug!(
        kept = kept.len(),
        suppressed = suppressed.len(),
        "exceptions applied"
    );
    Resolved {
        findings: kept,
        suppressed,
    }
}

#[cfg(test)]
mod tests {
    use gob_text::{Span, TextRange, TextSize};

    use super::*;
    use crate::meta::Severity;

    fn finding(files: &mut FileInterner, path: &str, start: u32, end: u32) -> Finding {
        let span = Span::new(
            files.intern(path),
            TextRange::new(TextSize::new(start), TextSize::new(end)),
        );
        Finding::new("COV001".parse().unwrap(), Severity::Warn, Some(span), "m", path)
    }

    fn bound(path: &str, range: Option<Range<usize>>) -> BoundException {
        BoundException {
            exception: Exception {
                kind: ExceptionKind::Accept,
                rule: "COV001".parse().unwrap(),
                reason: "generated code".into(),
                ticket: None,
                until: None,
            },
            path: path.into(),
            range,
        }
    }

    // frob:tests crates/gob-rules/src/exception.rs::apply_exceptions
    #[test]
    fn covered_findings_are_suppressed_and_the_rest_stand() {
        let mut files = FileInterner::new();
        let inside = finding(&mut files, "a.rs", 10, 20);
        let outside = finding(&mut files, "a.rs", 50, 60);
        let other_file = finding(&mut files, "b.rs", 10, 20);
        let spanless = Finding::new("COV001".parse().unwrap(), Severity::Warn, None, "m", "x");
        let ctx = ExceptionCtx { files: &files };
        let r = apply_exceptions(
            vec![inside.clone(), outside.clone(), other_file.clone(), spanless.clone()],
            &[bound("a.rs", Some(0..30))],
            &ctx,
        );
        assert_eq!(r.suppressed.len(), 1);
        assert_eq!(r.suppressed[0].0, inside);
        assert_eq!(r.findings, vec![outside, other_file, spanless]);
    }

    #[test]
    fn the_tightest_binding_wins_and_a_file_binding_covers_everything() {
        let mut files = FileInterner::new();
        let f = finding(&mut files, "a.rs", 10, 20);
        let ctx = ExceptionCtx { files: &files };
        let mut narrow = bound("a.rs", Some(5..25));
        narrow.exception.reason = "narrow one".into();
        let wide = bound("a.rs", None);
        let r = apply_exceptions(vec![f], &[wide, narrow], &ctx);
        assert_eq!(r.suppressed[0].1.reason, "narrow one");
    }
}

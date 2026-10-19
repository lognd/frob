//! Render limits and per-ticket isolation (mirror.md 3.6, MIR-AUD-18, 19).
//!
//! Body size, label count and length and sub-issue count are checked before any write. A ticket
//! that cannot be published is isolated with a reason (MIR001 for that ticket only) and the run
//! carries on with the rest.

// frob:ticket 01M4052TVNPHH7H9Z2M4A453RQ

use tracing::{debug, warn};

use crate::github::render::RenderedIssue;

/// GitHub's body limit, in characters.
pub const MAX_BODY_CHARS: usize = 65_536;
/// Most labels one issue may carry in a single write.
pub const MAX_LABELS: usize = 100;
/// GitHub's label name limit, in characters.
pub const MAX_LABEL_CHARS: usize = 50;
/// Most sub-issues one parent may have.
pub const MAX_SUB_ISSUES: usize = 100;

/// The limits applied to one rendered issue.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    /// Most body characters.
    pub body_chars: usize,
    /// Most labels.
    pub labels: usize,
    /// Most characters in one label.
    pub label_chars: usize,
    /// Most sub-issues under one parent.
    pub sub_issues: usize,
}

impl Default for Limits {
    /// GitHub's documented limits.
    fn default() -> Self {
        Self {
            body_chars: MAX_BODY_CHARS,
            labels: MAX_LABELS,
            label_chars: MAX_LABEL_CHARS,
            sub_issues: MAX_SUB_ISSUES,
        }
    }
}

/// Why one ticket cannot be published; every variant reports MIR001 for that ticket only.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum LimitError {
    /// The rendered body is over the character limit.
    #[error("MIR001 body-too-large: {chars} characters exceeds {max}")]
    BodyTooLarge {
        /// Characters in the body.
        chars: usize,
        /// The limit.
        max: usize,
    },
    /// More labels than one issue may carry.
    #[error("MIR001 too-many-labels: {count} exceeds {max}")]
    TooManyLabels {
        /// Labels requested.
        count: usize,
        /// The limit.
        max: usize,
    },
    /// A label name is over the length limit.
    #[error("MIR001 label-too-long: `{label}` is {chars} characters, limit {max}")]
    LabelTooLong {
        /// The offending label.
        label: String,
        /// Its length in characters.
        chars: usize,
        /// The limit.
        max: usize,
    },
    /// More sub-issues than one parent may have.
    #[error("MIR001 too-many-sub-issues: {count} exceeds {max}")]
    TooManySubIssues {
        /// Sub-issues requested.
        count: usize,
        /// The limit.
        max: usize,
    },
}

/// Check one rendered issue (with its sub-issue count) against `limits`; no write has happened.
///
/// # Errors
///
/// The first [`LimitError`] hit: body size, label count, label length, then sub-issues.
pub fn check(r: &RenderedIssue, sub_issues: usize, limits: &Limits) -> Result<(), LimitError> {
    let chars = r.body.chars().count();
    if chars > limits.body_chars {
        return Err(LimitError::BodyTooLarge {
            chars,
            max: limits.body_chars,
        });
    }
    if r.labels.len() > limits.labels {
        return Err(LimitError::TooManyLabels {
            count: r.labels.len(),
            max: limits.labels,
        });
    }
    if let Some(l) = r
        .labels
        .iter()
        .find(|l| l.chars().count() > limits.label_chars)
    {
        return Err(LimitError::LabelTooLong {
            label: l.clone(),
            chars: l.chars().count(),
            max: limits.label_chars,
        });
    }
    if sub_issues > limits.sub_issues {
        return Err(LimitError::TooManySubIssues {
            count: sub_issues,
            max: limits.sub_issues,
        });
    }
    Ok(())
}

/// A ticket left out of the run, with the reason.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Isolated {
    /// The ticket id.
    pub ticket: String,
    /// Why it cannot be published.
    pub reason: LimitError,
}

/// The outcome of planning a run: tickets safe to write and tickets isolated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Planned {
    /// Tickets (id, rendered issue) within limits, in input order.
    pub publishable: Vec<(String, RenderedIssue)>,
    /// Tickets isolated with a reason; no write is made for these.
    pub isolated: Vec<Isolated>,
}

/// Split `items` (ticket id, rendered issue, sub-issue count) into publishable and isolated.
pub fn plan(items: Vec<(String, RenderedIssue, usize)>, limits: &Limits) -> Planned {
    let mut out = Planned {
        publishable: Vec::new(),
        isolated: Vec::new(),
    };
    for (ticket, r, subs) in items {
        match check(&r, subs, limits) {
            Ok(()) => {
                debug!(%ticket, "limits: within limits");
                out.publishable.push((ticket, r));
            }
            Err(reason) => {
                warn!(%ticket, %reason, "limits: ticket isolated");
                out.isolated.push(Isolated { ticket, reason });
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn issue(body_len: usize, labels: &[&str]) -> RenderedIssue {
        RenderedIssue {
            title: "t".into(),
            body: "a".repeat(body_len),
            labels: labels.iter().map(|s| (*s).to_owned()).collect(),
            digest: "d".into(),
        }
    }

    // frob:tests check
    #[test]
    fn body_over_limit_is_reported_and_exact_limit_passes() {
        let l = Limits::default();
        assert!(check(&issue(65_536, &["frob:managed"]), 0, &l).is_ok());
        let e = check(&issue(65_537, &["frob:managed"]), 0, &l).unwrap_err();
        assert!(matches!(e, LimitError::BodyTooLarge { chars: 65_537, .. }));
        assert!(e.to_string().starts_with("MIR001"));
        let p = plan(vec![("T1".into(), issue(65_537, &[]), 0)], &l);
        assert!(p.publishable.is_empty());
        assert_eq!(p.isolated[0].ticket, "T1");
    }

    // frob:tests plan
    #[test]
    fn one_bad_ticket_among_ten_leaves_nine_publishable() {
        let items: Vec<_> = (0..10)
            .map(|i| {
                let len = if i == 4 { 70_000 } else { 10 };
                (format!("T{i}"), issue(len, &["frob:managed"]), 0)
            })
            .collect();
        let p = plan(items, &Limits::default());
        assert_eq!(p.publishable.len(), 9);
        assert_eq!(p.isolated.len(), 1);
        assert_eq!(p.isolated[0].ticket, "T4");
        assert!(p.publishable.iter().all(|(t, _)| t != "T4"));
    }

    // frob:tests check
    #[test]
    fn label_over_length_is_isolated_with_reason() {
        let long = "x".repeat(51);
        let p = plan(
            vec![("T1".into(), issue(1, &[long.as_str()]), 0)],
            &Limits::default(),
        );
        assert!(p.publishable.is_empty());
        assert!(matches!(
            p.isolated[0].reason,
            LimitError::LabelTooLong {
                chars: 51,
                max: 50,
                ..
            }
        ));
        assert!(p.isolated[0].reason.to_string().contains("label-too-long"));
    }

    // frob:tests check
    #[test]
    fn label_count_and_sub_issue_limits() {
        let l = Limits {
            labels: 1,
            sub_issues: 2,
            ..Limits::default()
        };
        assert!(matches!(
            check(&issue(1, &["a", "b"]), 0, &l),
            Err(LimitError::TooManyLabels { count: 2, max: 1 })
        ));
        assert!(matches!(
            check(&issue(1, &["a"]), 3, &l),
            Err(LimitError::TooManySubIssues { count: 3, max: 2 })
        ));
    }
}

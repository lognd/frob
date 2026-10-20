//! `frob mirror status` report (mirror.md 3.2, 3.3, 3.4): the last successful run, every MIR001
//! reason with its scope, the sweep's visit bound, fidelity gaps, contested fields, create-uncertain
//! and unmirrored tickets. Pure assembly and rendering; callers gather the inputs.

// frob:ticket 01M4052VZ10VRGMVPC1JYHAH7M

use std::fmt::Write as _;

use tracing::debug;

use crate::capture::GapListing;
use crate::mapfile::Shard;
use crate::sweep::visit_bound;

/// A MIR001 reason already rendered for one scope (a ticket ULID, or `run`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReasonLine {
    /// What the reason is about.
    pub scope: String,
    /// The one-line reason message.
    pub message: String,
}

/// A field the mirror stopped reverting (MIR002 Advisory), with its ticket.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ContestedField {
    /// The ticket ULID.
    pub ticket: String,
    /// The contested field.
    pub field: String,
}

/// Everything status reads, gathered by the caller from the map and the run record.
#[derive(Debug, Clone, Default)]
pub struct StatusInput {
    /// When the last successful run finished (RFC 3339), if any.
    pub last_success: Option<String>,
    /// The MIR001 reasons recorded by the latest runs.
    pub reasons: Vec<ReasonLine>,
    /// N: the number of mirrored issues.
    pub issues: u64,
    /// K: issues swept per run.
    pub per_run: u64,
    /// Fidelity gaps accumulated so far.
    pub gaps: GapListing,
    /// Fields in the contested state.
    pub contested: Vec<ContestedField>,
    /// Tickets marked unmirrored (their issue was deleted).
    pub unmirrored: Vec<String>,
    /// Every shard, scanned for create-uncertain tickets.
    pub shards: Vec<Shard>,
}

/// A create-uncertain ticket with the time its create started.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UncertainCreate {
    /// The ticket ULID.
    pub ticket: String,
    /// Create-start time (RFC 3339).
    pub started: String,
}

/// The assembled status, ready to render.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StatusReport {
    /// When the last successful run finished, if any.
    pub last_success: Option<String>,
    /// MIR001 reasons with their scopes.
    pub reasons: Vec<ReasonLine>,
    /// Runs within which every issue is visited; `None` when K is 0.
    pub visit_bound_runs: Option<u64>,
    /// N, for the bound line.
    pub issues: u64,
    /// K, for the bound line.
    pub per_run: u64,
    /// Gaps as `(ticket, field, kind)` lines, in stable order.
    pub gaps: Vec<(String, Option<String>, &'static str)>,
    /// Contested fields, sorted.
    pub contested: Vec<ContestedField>,
    /// Create-uncertain tickets, sorted by ticket.
    pub uncertain: Vec<UncertainCreate>,
    /// Unmirrored tickets, sorted.
    pub unmirrored: Vec<String>,
}

/// Assembles the status report from `input`.
pub fn build(input: &StatusInput) -> StatusReport {
    let mut uncertain: Vec<UncertainCreate> = input
        .shards
        .iter()
        .filter_map(|s| {
            s.create_uncertain.as_ref().map(|u| UncertainCreate {
                ticket: s.ulid.clone(),
                started: u.started.clone(),
            })
        })
        .collect();
    uncertain.sort_by(|a, b| a.ticket.cmp(&b.ticket));
    let mut contested = input.contested.clone();
    contested.sort();
    let mut unmirrored = input.unmirrored.clone();
    unmirrored.sort();
    let gaps = input
        .gaps
        .list()
        .into_iter()
        .map(|g| (g.issue.0.clone(), g.field.clone(), g.kind.as_str()))
        .collect();
    debug!(
        reasons = input.reasons.len(),
        uncertain = uncertain.len(),
        contested = contested.len(),
        "status: assembled"
    );
    StatusReport {
        last_success: input.last_success.clone(),
        reasons: input.reasons.clone(),
        visit_bound_runs: visit_bound(input.issues, input.per_run),
        issues: input.issues,
        per_run: input.per_run,
        gaps,
        contested,
        uncertain,
        unmirrored,
    }
}

impl StatusReport {
    /// Renders the report as plain text, one fact per line.
    pub fn render(&self) -> String {
        let mut out = String::new();
        let _ = writeln!(
            out,
            "last successful run: {}",
            self.last_success.as_deref().unwrap_or("never")
        );
        match self.visit_bound_runs {
            Some(runs) => {
                let _ = writeln!(
                    out,
                    "sweep bound: every issue visited within {runs} runs (ceil({}/{}))",
                    self.issues, self.per_run
                );
            }
            None => out.push_str("sweep bound: none (0 issues per run)\n"),
        }
        section(&mut out, "MIR001 reasons", &self.reasons, |r| {
            format!("{}: {}", r.scope, r.message)
        });
        section(&mut out, "gaps", &self.gaps, |(t, f, k)| match f {
            Some(f) => format!("{t} field {f}: {k}"),
            None => format!("{t}: {k}"),
        });
        section(&mut out, "contested (MIR002)", &self.contested, |c| {
            format!("{} field {}", c.ticket, c.field)
        });
        section(&mut out, "create-uncertain", &self.uncertain, |u| {
            format!("{} create started {}", u.ticket, u.started)
        });
        section(&mut out, "unmirrored", &self.unmirrored, Clone::clone);
        out
    }
}

/// Appends a titled list, or `title: none` when empty.
fn section<T>(out: &mut String, title: &str, items: &[T], line: impl Fn(&T) -> String) {
    if items.is_empty() {
        let _ = writeln!(out, "{title}: none");
        return;
    }
    let _ = writeln!(out, "{title}:");
    for item in items {
        let _ = writeln!(out, "  {}", line(item));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::IssueRef;
    use crate::capture::GapKind;
    use crate::mapfile::CreateUncertain;

    // frob:tests build
    // frob:tests render
    #[test]
    fn states_ceil_n_over_k_as_the_visit_bound() {
        let input = StatusInput {
            issues: 10,
            per_run: 3,
            ..StatusInput::default()
        };
        let report = build(&input);
        assert_eq!(report.visit_bound_runs, Some(4));
        assert!(report.render().contains("within 4 runs (ceil(10/3))"));
        let zero = build(&StatusInput::default());
        assert!(zero.render().contains("sweep bound: none"));
    }

    // frob:tests build
    // frob:tests render
    #[test]
    fn lists_gap_and_contested_field_with_ticket_and_field() {
        let mut gaps = GapListing::new();
        gaps.record_no_history(&IssueRef("42".into()), Some("labels"), GapKind::Unexplained);
        let input = StatusInput {
            gaps,
            contested: vec![ContestedField {
                ticket: "T1".into(),
                field: "priority".into(),
            }],
            reasons: vec![ReasonLine {
                scope: "run".into(),
                message: "rate-limited".into(),
            }],
            ..StatusInput::default()
        };
        let text = build(&input).render();
        assert!(text.contains("42 field labels: unexplained"), "{text}");
        assert!(text.contains("T1 field priority"), "{text}");
        assert!(text.contains("run: rate-limited"), "{text}");
    }

    // frob:tests build
    // frob:tests render
    #[test]
    fn lists_create_uncertain_ticket_with_start_time() {
        let mut shard = Shard::new("T9");
        shard.create_uncertain = Some(CreateUncertain {
            nonce: "n".into(),
            started: "2026-10-20T10:00:00Z".into(),
        });
        let input = StatusInput {
            shards: vec![shard, Shard::new("T8")],
            unmirrored: vec!["T7".into()],
            ..StatusInput::default()
        };
        let report = build(&input);
        assert_eq!(report.uncertain.len(), 1);
        let text = report.render();
        assert!(
            text.contains("T9 create started 2026-10-20T10:00:00Z"),
            "{text}"
        );
        assert!(text.contains("unmirrored:\n  T7"), "{text}");
    }
}

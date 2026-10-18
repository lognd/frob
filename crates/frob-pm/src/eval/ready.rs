//! `PM012`: a cycle member that is not ready fails the definition of ready.
//!
//! The definition is `[pm] ready_requires`; [`failed`] is its single
//! evaluation. Only members still waiting to start (`triage` or `todo`) are
//! judged: work already in progress or done was pulled earlier, and judging it
//! against today's definition would only produce noise. The qualified-story
//! predicate means a story carries persona, capability and outcome text;
//! other ticket types have no value statement to qualify and pass it. The
//! pure core [`pm012`] takes member facts; [`evaluate`] reads them from a
//! ledger.

// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use frob_ledger::Ledger;
use frob_ledger::model::{Category, Frontmatter, TicketType};
use gob_rules::{Finding, RuleId, Severity};

use crate::config::ReadyRequirement;
use crate::cycle::lifecycle::with_state;
use crate::error::Result;
use crate::eval::cycle::cycles;
use crate::eval::id_of;
use crate::eval::membership::Evaluation;
use crate::model::State;
use crate::rules::pm012::Pm012;
use crate::store::PmStore;

fn rule_id() -> RuleId {
    id_of::<Pm012>()
}

/// A cycle member and the `ready_requires` predicates it fails.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NotReady {
    /// The cycle's alias.
    pub cycle: String,
    /// The member's handle.
    pub handle: String,
    /// The predicates it fails, in `ready_requires` order.
    pub failed: Vec<ReadyRequirement>,
}

fn blank(s: Option<&str>) -> bool {
    s.is_none_or(|t| t.trim().is_empty())
}

/// The facts of one ticket that the ready predicates read.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
#[allow(clippy::struct_excessive_bools)]
pub struct ReadyFacts {
    /// True for a story (the only type with a value statement to qualify).
    pub story: bool,
    /// Whether persona, capability and outcome text are all stated.
    pub value_stated: bool,
    /// Whether at least one acceptance criterion exists.
    pub has_criteria: bool,
    /// Whether the ticket is sized.
    pub has_points: bool,
    /// Whether the ticket declares a scope.
    pub has_scope: bool,
    /// Whether the ticket has a parent.
    pub has_parent: bool,
}

impl ReadyFacts {
    /// The facts of the ticket whose frontmatter is `front`.
    pub fn of(front: &Frontmatter) -> Self {
        Self {
            story: front.ty == TicketType::Story,
            value_stated: !(blank(front.persona.as_deref())
                || blank(front.capability.as_deref())
                || blank(front.outcome_text.as_deref())),
            has_criteria: !front.acceptance.is_empty(),
            has_points: front.points.is_some(),
            has_scope: !front.scope.is_empty(),
            has_parent: front.parent.is_some(),
        }
    }
}

/// The predicates of `required` that a ticket with `facts` fails, in `required` order.
pub fn failed(required: &[ReadyRequirement], facts: &ReadyFacts) -> Vec<ReadyRequirement> {
    required
        .iter()
        .copied()
        .filter(|r| match r {
            ReadyRequirement::StoryOrObjectiveQualified => facts.story && !facts.value_stated,
            ReadyRequirement::Criteria => !facts.has_criteria,
            ReadyRequirement::Points => !facts.has_points,
            ReadyRequirement::Scope => !facts.has_scope,
            ReadyRequirement::Parent => !facts.has_parent,
        })
        .collect()
}

/// True for the categories `PM012` judges: not yet started.
pub const fn judged(category: Category) -> bool {
    matches!(category, Category::Triage | Category::Todo)
}

/// Evaluate `PM012` over the failing members; `subjects` is how many members were judged.
pub fn pm012(not_ready: &[NotReady], subjects: usize) -> Evaluation {
    let findings = not_ready
        .iter()
        .map(|n| {
            let names: Vec<&str> = n.failed.iter().map(|r| r.as_str()).collect();
            tracing::debug!(cycle = %n.cycle, ticket = %n.handle, failed = ?names, "PM012: member not ready");
            Finding::new(
                rule_id(),
                Severity::Warn,
                None,
                format!(
                    "{} in cycle {} is not ready: fails {} (fix it with `frob ticket update {}`)",
                    n.handle,
                    n.cycle,
                    names.join(", "),
                    n.handle
                ),
                &format!("cycle:{}:{}", n.cycle, n.handle),
            )
        })
        .collect();
    Evaluation { findings, subjects }
}

/// Read the open cycles' members from `ledger` and run [`pm012`] against `required`.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, required: &[ReadyRequirement]) -> Result<Evaluation> {
    if required.is_empty() {
        tracing::info!("PM012 not applicable: [pm] ready_requires is empty");
        return Ok(Evaluation::default());
    }
    let today = PmStore::new(ledger).today();
    let mut bad = Vec::new();
    let mut subjects = 0;
    for c in cycles(ledger)?
        .into_iter()
        .map(|c| with_state(c, today))
        .filter(|c| c.state != State::Closed)
    {
        for id in &c.tickets {
            let v = match ledger.show(*id) {
                Ok(v) => v,
                Err(e) => {
                    tracing::warn!(ticket = %id, error = %e, "member ticket unreadable; not judged");
                    continue;
                }
            };
            if !judged(v.summary.category) {
                continue;
            }
            subjects += 1;
            let miss = failed(required, &ReadyFacts::of(&v.ticket.front));
            if !miss.is_empty() {
                bad.push(NotReady {
                    cycle: c.alias(),
                    handle: v.summary.handle,
                    failed: miss,
                });
            }
        }
    }
    let out = pm012(&bad, subjects);
    tracing::info!(subjects, findings = out.findings.len(), "PM012 evaluated");
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn full() -> ReadyFacts {
        ReadyFacts {
            story: false,
            value_stated: false,
            has_criteria: true,
            has_points: true,
            has_scope: true,
            has_parent: true,
        }
    }

    #[test]
    fn bare_ticket_fails_everything_but_the_story_predicate() {
        // frob:tests crates/frob-pm/src/eval/ready.rs::failed
        let got = failed(ReadyRequirement::ALL, &ReadyFacts::default());
        assert_eq!(
            got,
            vec![
                ReadyRequirement::Criteria,
                ReadyRequirement::Points,
                ReadyRequirement::Scope,
                ReadyRequirement::Parent
            ]
        );
    }

    #[test]
    fn story_needs_its_value_statement() {
        // frob:tests crates/frob-pm/src/eval/ready.rs::failed
        let req = [ReadyRequirement::StoryOrObjectiveQualified];
        let mut f = ReadyFacts {
            story: true,
            ..full()
        };
        assert_eq!(failed(&req, &f).len(), 1);
        f.value_stated = true;
        assert!(failed(&req, &f).is_empty());
    }

    #[test]
    fn complete_ticket_is_ready() {
        // frob:tests crates/frob-pm/src/eval/ready.rs::failed
        assert!(failed(ReadyRequirement::ALL, &full()).is_empty());
    }

    #[test]
    fn message_names_every_failed_predicate() {
        // frob:tests crates/frob-pm/src/eval/ready.rs::pm012
        let n = NotReady {
            cycle: "2026-10-05..2026-10-11".into(),
            handle: "~ABC1234".into(),
            failed: vec![ReadyRequirement::Points, ReadyRequirement::Scope],
        };
        let f = &pm012(&[n], 1).findings[0];
        assert!(f.message.contains("fails points, scope"), "{}", f.message);
    }
}

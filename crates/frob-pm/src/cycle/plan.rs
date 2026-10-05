//! `cycle plan` as pure rules: fill a cycle from ready work in rank order, never past capacity.
//!
//! The candidates arrive already ranked by `Ledger::doable` (expedite, then
//! fixed-date by due, then the rest). The plan keeps that order, except that
//! among the plain lane tickets of the next milestone go first. Each candidate
//! is then tried through [`plan_assign`], the same rules `cycle assign` applies, so
//! eligibility and the capacity refusal are unchanged and a plan never
//! over-commits. A candidate that cannot be taken is left out with the reason.
//! Without an enforced capacity there is no limit to fill to, so planning is
//! refused rather than committing every ready ticket (pm-enforcement.md section 4).
// frob:ticket 01M4069T2V69X32EP8NZQHJH6H

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::TicketId;
use frob_ledger::model::{Class, TicketType};

use crate::cycle::assign::{AssignError, AssignPlan, TicketFacts, plan_assign};
use crate::cycle::velocity::{Capacity, counts};
use crate::model::{Cycle, Milestone, State};
use crate::rules::membership::{Claimant, claimed_versions, reached};

/// A plan that cannot be made.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum PlanError {
    /// The target cycle cannot take members.
    #[error(transparent)]
    Assign(#[from] AssignError),
    /// No limit is enforced, so there is nothing to fill up to.
    #[error("cannot plan cycle {alias}: {why}")]
    NoCapacity {
        /// Alias of the target cycle.
        alias: String,
        /// The capacity statement.
        why: String,
    },
}

/// A ready ticket offered to the plan, in `doable` rank order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Candidate {
    /// The facts `cycle assign` needs.
    pub facts: TicketFacts,
    /// Its class of service.
    pub class: Class,
    /// True when it belongs to the next milestone.
    pub next_milestone: bool,
}

/// A ticket the plan assigns.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pick {
    /// The ticket.
    pub id: TicketId,
    /// Its handle.
    pub handle: String,
    /// Its points (0 for a type that never counts).
    pub points: u32,
    /// Committed points of the cycle after this pick.
    pub running: u32,
    /// Why it ranks where it does.
    pub why: String,
}

/// A ready ticket the plan does not assign.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LeftOut {
    /// Its handle.
    pub handle: String,
    /// Why it was left out.
    pub reason: String,
}

/// What `cycle plan` proposes for one cycle.
#[derive(Debug, Clone, PartialEq)]
pub struct FillPlan {
    /// Committed points of the cycle before the plan.
    pub committed: u32,
    /// The capacity that applied.
    pub capacity: Capacity,
    /// Tickets to assign, in rank order.
    pub picks: Vec<Pick>,
    /// Ready tickets already members of the cycle (nothing to do).
    pub already: Vec<String>,
    /// Ready tickets not assigned, with reasons.
    pub left_out: Vec<LeftOut>,
}

/// The milestone planning looks at: the open one with the earliest target (undated last), then by version.
pub fn next_milestone(milestones: &[Milestone]) -> Option<&Milestone> {
    milestones
        .iter()
        .filter(|m| m.state == State::Open)
        .min_by(|a, b| {
            (a.target.is_none(), a.target, &a.version).cmp(&(
                b.target.is_none(),
                b.target,
                &b.version,
            ))
        })
}

/// The tickets belonging to `milestone`: under one of its epics, or claiming it by `release:VERSION`.
pub fn milestone_members(milestone: &Milestone, tickets: &[Claimant]) -> BTreeSet<TicketId> {
    let by_id: BTreeMap<TicketId, &Claimant> = tickets.iter().map(|t| (t.id, t)).collect();
    tickets
        .iter()
        .filter(|t| {
            reached(t, &by_id, &milestone.epics)
                || claimed_versions(&t.labels).any(|v| v == milestone.version)
        })
        .map(|t| t.id)
        .collect()
}

/// Lane of the ranking: 0 expedite, 1 fixed-date, 2 the rest (the lanes `doable` sorts by).
const fn lane(class: Class) -> u8 {
    match class {
        Class::Expedite => 0,
        Class::FixedDate => 1,
        Class::Standard | Class::Intangible => 2,
    }
}

/// Reorder `ranked` candidates so next-milestone tickets lead the plain lane, keeping every other order.
fn prefer_milestone(ranked: Vec<Candidate>) -> Vec<Candidate> {
    let mut out = ranked;
    out.sort_by_key(|c| (lane(c.class), lane(c.class) == 2 && !c.next_milestone));
    out
}

/// Plan filling `target` from `ranked` ready tickets up to `capacity`.
///
/// `members` are the `(type, points)` of the target's current members; `all` is every cycle.
/// Tickets held by another open or planned cycle are left out rather than moved.
///
/// # Errors
///
/// [`PlanError::Assign`] for a closed target, [`PlanError::NoCapacity`] when `capacity` is unenforced.
pub fn plan_fill(
    target: &Cycle,
    all: &[Cycle],
    ranked: Vec<Candidate>,
    members: &[(TicketType, u32)],
    capacity: &Capacity,
) -> Result<FillPlan, PlanError> {
    if target.state == State::Closed {
        return Err(AssignError::Closed {
            alias: target.alias(),
        }
        .into());
    }
    if capacity.limit().is_none() {
        tracing::info!(cycle = %target.alias(), "plan refused: capacity not enforced");
        return Err(PlanError::NoCapacity {
            alias: target.alias(),
            why: format!(
                "{} so there is no limit to fill to; set one with `--points N` or `frob cycle new --capacity N`",
                capacity.describe()
            ),
        });
    }
    let mut held: Vec<(TicketType, u32)> = members.to_vec();
    let mut plan = FillPlan {
        committed: crate::cycle::velocity::committed(members),
        capacity: capacity.clone(),
        picks: Vec::new(),
        already: Vec::new(),
        left_out: Vec::new(),
    };
    for c in prefer_milestone(ranked) {
        let f = &c.facts;
        if let Some(other) = all
            .iter()
            .find(|o| o.id != target.id && o.state != State::Closed && o.tickets.contains(&f.id))
        {
            plan.left_out.push(LeftOut {
                handle: f.handle.clone(),
                reason: format!("already in cycle {}", other.alias()),
            });
            continue;
        }
        match plan_assign(target, all, f, &held, capacity.clone(), false) {
            Ok(AssignPlan::Already) => plan.already.push(f.handle.clone()),
            Ok(AssignPlan::Add { committed, .. }) => {
                let points = if counts(f.ty) {
                    f.points.unwrap_or(0)
                } else {
                    0
                };
                held.push((f.ty, f.points.unwrap_or(0)));
                plan.picks.push(Pick {
                    id: f.id,
                    handle: f.handle.clone(),
                    points,
                    running: committed,
                    why: why(&c),
                });
            }
            Err(e) => plan.left_out.push(LeftOut {
                handle: f.handle.clone(),
                reason: e.to_string(),
            }),
        }
    }
    tracing::info!(
        cycle = %target.alias(), picks = plan.picks.len(), left_out = plan.left_out.len(),
        already = plan.already.len(), "cycle plan computed"
    );
    Ok(plan)
}

/// The rank reason shown beside a pick.
fn why(c: &Candidate) -> String {
    let lane = match c.class {
        Class::Expedite => "expedite",
        Class::FixedDate => "fixed-date",
        Class::Standard | Class::Intangible => "standard",
    };
    if c.next_milestone {
        format!("{lane}, next milestone")
    } else {
        lane.to_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Day, ObjectId};
    use crate::rules::membership::CLAIM_PREFIX;
    use frob_ledger::model::Stamp;

    fn day(s: &str) -> Day {
        s.parse().expect("day")
    }

    fn cycle(cap: Option<u32>, state: State) -> Cycle {
        Cycle {
            id: ObjectId::mint(),
            start: day("2026-10-05"),
            end: day("2026-10-11"),
            ended: None,
            goal: "g".to_owned(),
            capacity_points: cap,
            state,
            tickets: Vec::new(),
            created: Stamp::from_unix(1_800_000_000),
            updated: Stamp::from_unix(1_800_000_000),
            ordinal: 1,
        }
    }

    fn cand(handle: &str, points: Option<u32>, class: Class, ms: bool) -> Candidate {
        Candidate {
            facts: TicketFacts {
                id: TicketId::mint(),
                handle: handle.to_owned(),
                ty: TicketType::Task,
                points,
            },
            class,
            next_milestone: ms,
        }
    }

    #[test]
    fn fills_in_rank_order_and_leaves_out_what_does_not_fit() {
        // frob:tests crates/frob-pm/src/cycle/plan.rs::plan_fill
        let t = cycle(Some(8), State::Planned);
        let ranked = vec![
            cand("~A", Some(5), Class::Expedite, false),
            cand("~B", Some(5), Class::Standard, false),
            cand("~C", Some(3), Class::Standard, false),
            cand("~D", None, Class::Standard, false),
        ];
        let p = plan_fill(&t, &[], ranked, &[], &Capacity::Set(8)).expect("plan");
        let picked: Vec<_> = p
            .picks
            .iter()
            .map(|x| (x.handle.as_str(), x.running))
            .collect();
        assert_eq!(picked, vec![("~A", 5), ("~C", 8)]);
        assert_eq!(p.left_out.len(), 2);
        assert!(
            p.left_out[0].reason.contains("over its 8-point limit"),
            "{:?}",
            p.left_out
        );
        assert!(
            p.left_out[1].reason.contains("no story points"),
            "{:?}",
            p.left_out
        );
    }

    #[test]
    fn next_milestone_leads_the_plain_lane_only() {
        // frob:tests crates/frob-pm/src/cycle/plan.rs::plan_fill
        let t = cycle(Some(99), State::Planned);
        let ranked = vec![
            cand("~X", Some(1), Class::Expedite, false),
            cand("~F", Some(1), Class::FixedDate, false),
            cand("~S", Some(1), Class::Standard, false),
            cand("~M", Some(1), Class::Standard, true),
        ];
        let p = plan_fill(&t, &[], ranked, &[], &Capacity::Set(99)).expect("plan");
        let order: Vec<_> = p.picks.iter().map(|x| x.handle.as_str()).collect();
        assert_eq!(order, vec!["~X", "~F", "~M", "~S"]);
    }

    #[test]
    fn members_and_other_cycles_are_not_reassigned_and_replanning_is_stable() {
        // frob:tests crates/frob-pm/src/cycle/plan.rs::plan_fill
        let mut t = cycle(Some(9), State::Planned);
        let mut other = cycle(None, State::Planned);
        let a = cand("~A", Some(4), Class::Standard, false);
        let b = cand("~B", Some(4), Class::Standard, false);
        t.tickets.push(a.facts.id);
        other.tickets.push(b.facts.id);
        let all = vec![t.clone(), other];
        let p = plan_fill(
            &t,
            &all,
            vec![a, b],
            &[(TicketType::Task, 4)],
            &Capacity::Set(9),
        )
        .expect("plan");
        assert!(p.picks.is_empty());
        assert_eq!(p.already, vec!["~A".to_owned()]);
        assert!(p.left_out[0].reason.contains("already in cycle"));
    }

    #[test]
    fn unenforced_capacity_and_closed_cycles_are_refused() {
        // frob:tests crates/frob-pm/src/cycle/plan.rs::plan_fill
        let t = cycle(None, State::Planned);
        let none = Capacity::Unenforced { have: 0, need: 3 };
        assert!(matches!(
            plan_fill(&t, &[], vec![], &[], &none),
            Err(PlanError::NoCapacity { .. })
        ));
        let closed = cycle(Some(5), State::Closed);
        assert!(matches!(
            plan_fill(&closed, &[], vec![], &[], &Capacity::Set(5)),
            Err(PlanError::Assign(AssignError::Closed { .. }))
        ));
    }

    #[test]
    fn next_milestone_is_the_earliest_open_target() {
        // frob:tests crates/frob-pm/src/cycle/plan.rs::next_milestone
        let mk = |v: &str, target: Option<&str>, state| Milestone {
            id: ObjectId::mint(),
            version: v.to_owned(),
            goal: "g".to_owned(),
            target: target.map(day),
            state,
            epics: Vec::new(),
            criteria: Vec::new(),
            created: Stamp::from_unix(1_800_000_000),
            updated: Stamp::from_unix(1_800_000_000),
        };
        let ms = vec![
            mk("3.0", None, State::Open),
            mk("2.0", Some("2026-12-01"), State::Open),
            mk("1.0", Some("2026-01-01"), State::Released),
        ];
        assert_eq!(next_milestone(&ms).map(|m| m.version.as_str()), Some("2.0"));
    }

    #[test]
    fn milestone_members_follow_epics_and_claims() {
        // frob:tests crates/frob-pm/src/cycle/plan.rs::milestone_members
        let epic = TicketId::mint();
        let child = TicketId::mint();
        let claimer = TicketId::mint();
        let stray = TicketId::mint();
        let c = |id, parent, labels: &[&str]| Claimant {
            id,
            title: "t".to_owned(),
            parent,
            labels: labels.iter().map(|s| (*s).to_owned()).collect(),
        };
        let tickets = vec![
            c(epic, None, &[]),
            c(child, Some(epic), &[]),
            c(claimer, None, &[&format!("{CLAIM_PREFIX}2.0")]),
            c(stray, None, &[]),
        ];
        let m = Milestone {
            id: ObjectId::mint(),
            version: "2.0".to_owned(),
            goal: "g".to_owned(),
            target: None,
            state: State::Open,
            epics: vec![epic],
            criteria: Vec::new(),
            created: Stamp::from_unix(1_800_000_000),
            updated: Stamp::from_unix(1_800_000_000),
        };
        let got = milestone_members(&m, &tickets);
        assert!(got.contains(&child) && got.contains(&claimer) && !got.contains(&stray));
    }
}

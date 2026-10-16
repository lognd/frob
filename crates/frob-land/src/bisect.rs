//! Group-testing bisection planner for the land train (frob:ticket 01M4Z1MYF3JKB73KCCX5BPJ7WJ).
//!
//! Pure: no git and no IO. Given an ordered batch of ticket handles and a
//! [`Runner`] that checks any subset, [`plan`] finds which tickets can land and
//! which are culprits using few sequential checks.
//!
//! frob:invariant every check is of `accepted ++ candidates`, where `accepted`
//! is the set already proven green, so each green check is a superset of every
//! earlier green and `Plan::landable` is exactly the last green-tested set: the
//! landed tree is the tested tree. A union is never landed unless checked whole.
//!
//! A runner fault (`Err`) is retried once and then aborts the plan with the
//! remaining tickets in `Plan::unchecked` ("could not check"); a fault never
//! blames a ticket. A culprit inferred red from a green sibling is confirmed
//! together with the other inferred ones in one final check; if that check is
//! green the earlier red was flaky or an interaction, the set is reported in
//! `Plan::interactions`, nobody is blamed and the set lands (it was tested).
//! Cost: one failing ticket of n takes at most 2*ceil(log2 n) checks; k failing
//! take about k*(ceil(log2 n)+1) plus the root, retest and confirm checks.
//! Optional `suspects` (tickets attributed by finding path) are bisected first
//! after one check of the batch without them.

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Result of checking one subset of the batch.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub enum Verdict {
    /// The subset verified.
    Green,
    /// The subset failed, with the evidence (a failure summary).
    Red(String),
}

/// The check could not run (git error, timeout, OOM kill): says nothing about the tickets.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct CheckFault {
    /// What went wrong.
    pub message: String,
}

/// Checks a subset of the batch; a seam so tests can inject failures.
pub trait Runner {
    /// Check the combination of `subset` (handles, in batch order).
    ///
    /// # Errors
    ///
    /// A [`CheckFault`] when the check could not be run at all.
    fn check(&self, subset: &[String]) -> Result<Verdict, CheckFault>;
}

/// A ticket isolated as the reason a batch is red.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Culprit {
    /// The culprit's handle.
    pub handle: String,
    /// The evidence of the red check that isolated it.
    pub evidence: String,
}

/// A set that was red but verified green whole on a later check (flaky or interacting).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Interaction {
    /// The members; none is blamed and all landed with that exact set tested green.
    pub members: Vec<String>,
}

/// What [`plan`] decided.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Plan {
    /// Tickets safe to land, in batch order; exactly the last green-tested set.
    pub landable: Vec<String>,
    /// Tickets that must not land, in batch order.
    pub culprits: Vec<Culprit>,
    /// Red sets whose parts were green and that stayed red on a re-run.
    pub interactions: Vec<Interaction>,
    /// Tickets not resolved because a check faulted twice, in batch order.
    pub unchecked: Vec<String>,
    /// The fault that aborted the plan, when one did.
    pub fault: Option<CheckFault>,
    /// How many subset checks ran (retries included).
    pub checks: u32,
    /// How many sequential rounds ran (one check per round).
    pub rounds: u32,
}

struct Planner<'a, R: Runner> {
    runner: &'a R,
    batch: &'a [String],
    accepted: Vec<String>,
    /// Culprits inferred red (a green sibling) but not yet checked alone.
    unconfirmed: Vec<Culprit>,
    plan: Plan,
}

impl<R: Runner> Planner<'_, R> {
    fn ordered(&self, mut set: Vec<String>) -> Vec<String> {
        set.sort_by_key(|h| self.batch.iter().position(|b| b == h));
        set
    }

    /// Check `accepted ++ extra`, retrying a fault once.
    fn test(&mut self, extra: &[String]) -> Result<Verdict, CheckFault> {
        let set = self.ordered([self.accepted.as_slice(), extra].concat());
        let mut last = None;
        for attempt in 0..2 {
            self.plan.checks += 1;
            self.plan.rounds += 1;
            match self.runner.check(&set) {
                Ok(verdict) => {
                    tracing::info!(
                        round = self.plan.rounds,
                        size = set.len(),
                        green = (verdict == Verdict::Green),
                        "train bisect round"
                    );
                    return Ok(verdict);
                }
                Err(fault) => {
                    tracing::warn!(attempt, fault = %fault.message, "train bisect check faulted");
                    last = Some(fault);
                }
            }
        }
        Err(last.expect("two attempts ran"))
    }

    fn solve(
        &mut self,
        batch: Vec<String>,
        suspects: &dyn Fn() -> Vec<String>,
    ) -> Result<(), CheckFault> {
        let mut pending = batch;
        let mut evidence: Option<String> = None;
        let mut first = true;
        while !pending.is_empty() {
            let ev = match evidence.take() {
                Some(ev) => ev,
                None => match self.test(&pending)? {
                    Verdict::Green => {
                        self.accepted.append(&mut pending);
                        break;
                    }
                    Verdict::Red(ev) => ev,
                },
            };
            let suspects = if first { suspects() } else { Vec::new() };
            if first && !suspects.is_empty() && suspects.len() < pending.len() {
                let rest: Vec<String> = pending
                    .iter()
                    .filter(|h| !suspects.contains(h))
                    .cloned()
                    .collect();
                if self.test(&rest)? == Verdict::Green {
                    tracing::info!(
                        suspects = suspects.len(),
                        "train bisect narrowed to suspects"
                    );
                    self.accepted.extend(rest);
                    pending.clone_from(&suspects);
                }
            }
            first = false;
            pending = self.isolate(pending, ev)?;
        }
        self.confirm()
    }

    /// Check all inferred culprits together: red confirms them, green means flaky or interacting.
    fn confirm(&mut self) -> Result<(), CheckFault> {
        if self.unconfirmed.is_empty() {
            return Ok(());
        }
        let handles: Vec<String> = self.unconfirmed.iter().map(|c| c.handle.clone()).collect();
        match self.test(&handles)? {
            Verdict::Red(e) => {
                for mut c in std::mem::take(&mut self.unconfirmed) {
                    c.evidence.clone_from(&e);
                    self.plan.culprits.push(c);
                }
            }
            Verdict::Green => {
                tracing::warn!(
                    members = handles.len(),
                    "train bisect: red set verified green whole"
                );
                self.unconfirmed.clear();
                self.accepted.extend(handles.iter().cloned());
                self.plan
                    .interactions
                    .push(Interaction { members: handles });
            }
        }
        Ok(())
    }

    /// Isolate one culprit of the red `parent`; returns the still-unknown rest.
    fn isolate(
        &mut self,
        parent: Vec<String>,
        parent_ev: String,
    ) -> Result<Vec<String>, CheckFault> {
        let mut cand = parent;
        let mut ev = parent_ev;
        let mut tested = true;
        let mut dropped: Vec<String> = Vec::new();
        while cand.len() > 1 {
            let (left, right) = cand.split_at(cand.len() / 2);
            let (left, right) = (left.to_vec(), right.to_vec());
            match self.test(&left)? {
                Verdict::Red(e) => {
                    dropped.extend(right);
                    cand = left;
                    ev = e;
                    tested = true;
                }
                Verdict::Green => {
                    self.accepted.extend(left);
                    cand = right;
                    tested = false;
                }
            }
        }
        tracing::info!(culprit = %cand[0], tested, "train bisect culprit isolated");
        let culprit = Culprit {
            handle: cand[0].clone(),
            evidence: ev,
        };
        if tested {
            self.plan.culprits.push(culprit);
        } else {
            self.unconfirmed.push(culprit);
        }
        Ok(dropped)
    }
}

/// Plan which tickets of `batch` (landing order) can land, checking subsets with `runner`.
///
/// `suspects` are tickets already attributed to a failure by path; they are bisected first.
pub fn plan<R: Runner>(batch: &[String], suspects: &[String], runner: &R) -> Plan {
    plan_with(batch, &|| suspects.to_vec(), runner)
}

/// As [`plan`], but `suspects` is asked for once, after the first red check of the batch, so a
/// runner can attribute the failure (to members red on their own rules, or by finding path) first.
pub fn plan_with<R: Runner>(
    batch: &[String],
    suspects: &dyn Fn() -> Vec<String>,
    runner: &R,
) -> Plan {
    let mut planner = Planner {
        runner,
        batch,
        accepted: Vec::new(),
        unconfirmed: Vec::new(),
        plan: Plan::default(),
    };
    if let Err(fault) = planner.solve(batch.to_vec(), suspects) {
        tracing::error!(fault = %fault.message, "train bisect aborted: could not check");
        planner.plan.fault = Some(fault);
    }
    let mut out = std::mem::take(&mut planner.plan);
    out.landable = planner.ordered(planner.accepted.clone());
    out.culprits
        .sort_by_key(|c| batch.iter().position(|b| *b == c.handle));
    if out.fault.is_some() {
        let known =
            |h: &String| out.landable.contains(h) || out.culprits.iter().any(|c| &c.handle == h);
        out.unchecked = batch.iter().filter(|h| !known(h)).cloned().collect();
    }
    tracing::info!(
        landable = out.landable.len(),
        culprits = out.culprits.len(),
        checks = out.checks,
        "train bisect plan done"
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;
    use std::collections::HashSet;

    /// Red when the subset has a bad handle or holds every member of a joint set.
    #[derive(Default)]
    struct Fake {
        bad: HashSet<String>,
        joint: Vec<String>,
        /// Fault on these (1-based) call numbers.
        faults: Vec<u32>,
        calls: Cell<u32>,
        /// Report red on these (1-based) call numbers regardless of content.
        red_calls: Vec<u32>,
    }

    impl Runner for Fake {
        fn check(&self, subset: &[String]) -> Result<Verdict, CheckFault> {
            self.calls.set(self.calls.get() + 1);
            if self.faults.contains(&self.calls.get()) {
                return Err(CheckFault {
                    message: "oom".into(),
                });
            }
            if self.red_calls.contains(&self.calls.get()) {
                return Ok(Verdict::Red("flake".into()));
            }
            if let Some(b) = subset.iter().find(|h| self.bad.contains(*h)) {
                return Ok(Verdict::Red(format!("{b} failed")));
            }
            if !self.joint.is_empty() && self.joint.iter().all(|h| subset.contains(h)) {
                return Ok(Verdict::Red("joint failure".into()));
            }
            Ok(Verdict::Green)
        }
    }

    fn batch(n: usize) -> Vec<String> {
        (0..n).map(|i| format!("t{i}")).collect()
    }

    fn fake(b: &[String], bad: &[usize]) -> Fake {
        Fake {
            bad: bad.iter().map(|&i| b[i].clone()).collect(),
            ..Fake::default()
        }
    }

    // frob:tests plan
    // frob:tests Runner.check
    #[test]
    fn one_failing_of_twelve_is_isolated_within_budget() {
        let b = batch(12);
        for i in 0..12 {
            let p = plan(&b, &[], &fake(&b, &[i]));
            assert_eq!(p.culprits.len(), 1);
            assert_eq!(p.culprits[0].handle, b[i]);
            assert_eq!(p.landable.len(), 11);
            assert!(p.checks <= 8, "culprit {i} took {} checks", p.checks);
        }
    }

    // frob:tests plan
    #[test]
    fn two_failing_of_twelve_are_isolated_within_budget() {
        let b = batch(12);
        for i in 0..12 {
            for j in (i + 1)..12 {
                let p = plan(&b, &[], &fake(&b, &[i, j]));
                let got: Vec<_> = p.culprits.iter().map(|c| c.handle.clone()).collect();
                assert_eq!(got, vec![b[i].clone(), b[j].clone()]);
                assert_eq!(p.landable.len(), 10);
                assert!(p.checks <= 12, "culprits {i},{j} took {} checks", p.checks);
            }
        }
    }

    // frob:tests plan
    #[test]
    fn all_green_costs_one_check() {
        let b = batch(12);
        let p = plan(&b, &[], &fake(&b, &[]));
        assert_eq!(p.checks, 1);
        assert_eq!(p.landable, b);
        assert!(p.culprits.is_empty());
    }

    // frob:tests plan
    #[test]
    fn landed_set_is_always_a_tested_set() {
        // A+C interact, D fails alone: the landable set must not contain both A and C.
        let b = batch(4);
        let f = Fake {
            bad: [b[3].clone()].into(),
            joint: vec![b[0].clone(), b[2].clone()],
            ..Fake::default()
        };
        let p = plan(&b, &[], &f);
        assert!(!(p.landable.contains(&b[0]) && p.landable.contains(&b[2])));
        assert_eq!(f.check(&p.landable).unwrap(), Verdict::Green);
    }

    // frob:tests plan
    #[test]
    fn red_parent_with_green_parts_is_reported_and_terminates() {
        // The full set is red once, every later check is green.
        let b = batch(4);
        let f = Fake {
            red_calls: vec![1],
            ..Fake::default()
        };
        let p = plan(&b, &[], &f);
        assert!(p.culprits.is_empty());
        assert_eq!(p.landable, b);
        assert_eq!(p.interactions.len(), 1);
    }

    // frob:tests plan
    #[test]
    fn single_fault_is_retried_and_double_fault_blames_nobody() {
        let b = batch(4);
        let p = plan(
            &b,
            &[],
            &Fake {
                faults: vec![1],
                ..Fake::default()
            },
        );
        assert_eq!(p.landable, b);
        let p = plan(
            &b,
            &[],
            &Fake {
                faults: vec![1, 2],
                ..Fake::default()
            },
        );
        assert!(p.culprits.is_empty() && p.landable.is_empty());
        assert_eq!(p.unchecked, b);
        assert!(p.fault.is_some());
    }

    // frob:tests plan
    #[test]
    fn suspects_are_bisected_first() {
        let b = batch(12);
        let p = plan(&b, &[b[7].clone()], &fake(&b, &[7]));
        assert_eq!(p.culprits[0].handle, b[7]);
        assert_eq!(p.landable.len(), 11);
        assert_eq!(p.checks, 2);
    }

    // frob:tests plan
    #[test]
    fn empty_batch_runs_no_checks() {
        let p = plan(&[], &[], &fake(&[], &[]));
        assert_eq!(p.checks, 0);
    }
}

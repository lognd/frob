//! Union check of a land-train candidate (frob:ticket 01M4Z1MYXBWTWH9F271FEY3NSE).
//!
//! [`CandidateChecker`] implements the planner's [`Runner`]: for a subset of the batch it runs the
//! cheap per-member ticket rules (one ticket-scoped run per member, tools skipped), then ONE
//! `diff_base`-scoped tool run over the union of the members' cones, ratcheted once against the base
//! findings. A member's cheap-rule result is reused while no other member of the candidate touches
//! its cone. A red verdict carries the failing evidence, attributed to a member where the finding
//! path lies in exactly one member's diff. A fault (git, timeout) is `Err(CheckFault)`, never red.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use frob_check::CheckOptions;
use frob_ledger::LedgerConfig;
use gob_git::Repo;

use crate::bisect::{CheckFault, Runner, Verdict};
use crate::candidate::{CandidateMember, build_candidate, scopes_overlap};
use crate::error::LandError;
use crate::ratchet::{self, FindingNote};

/// What the checker knows about one batch member.
#[derive(Debug, Clone)]
pub struct MemberInfo {
    /// Ticket handle.
    pub handle: String,
    /// Lease scope globs (what the member may touch).
    pub scope: Vec<String>,
    /// Globs of the files the member's bound evidence depends on (its cone; unresolved edges widen it).
    pub cone: Vec<String>,
    /// Paths of the member's own diff against the base, for attributing findings.
    pub paths: Vec<String>,
}

/// The checks a [`CandidateChecker`] composes; a seam so tests can inject findings and faults.
pub trait CandidateBackend {
    /// Cheap ticket rules of one member (tools skipped); the blocking findings new against the base.
    ///
    /// # Errors
    ///
    /// The rules could not run.
    fn member_rules(&self, handle: &str) -> Result<Vec<FindingNote>, CheckFault>;

    /// ONE `diff_base`-scoped tool run over the candidate of `subset`, ratcheted once against the base.
    ///
    /// # Errors
    ///
    /// The candidate could not be built or the run could not complete.
    fn union_run(&self, subset: &[String]) -> Result<Vec<FindingNote>, CheckFault>;
}

/// Counters of the work a checker did, for logs and tests.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CheckStats {
    /// Member rule runs executed.
    pub rules_run: u32,
    /// Member rule results reused from an earlier check.
    pub rules_reused: u32,
    /// Union tool runs executed.
    pub union_runs: u32,
}

/// The planner [`Runner`] over a land-train candidate.
pub struct CandidateChecker<B: CandidateBackend> {
    backend: B,
    members: Vec<MemberInfo>,
    cache: Mutex<HashMap<String, Vec<FindingNote>>>,
    /// Members the last red union run attributed by finding path.
    attributed: Mutex<Vec<String>>,
    stats: Mutex<CheckStats>,
}

impl<B: CandidateBackend> CandidateChecker<B> {
    /// A checker over `members` using `backend`.
    pub fn new(backend: B, members: Vec<MemberInfo>) -> Self {
        Self {
            backend,
            members,
            cache: Mutex::new(HashMap::new()),
            attributed: Mutex::new(Vec::new()),
            stats: Mutex::new(CheckStats::default()),
        }
    }

    /// What the checker has run and reused so far.
    pub fn stats(&self) -> CheckStats {
        *self
            .stats
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }

    /// Members known to be behind a red verdict without another check: red on their own rules, or
    /// named by path in the last red union run, in batch order (the planner bisects these first).
    pub fn suspects(&self) -> Vec<String> {
        let cache = self
            .cache
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let attributed = self
            .attributed
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let out: Vec<String> = self
            .members
            .iter()
            .filter(|m| {
                cache.get(&m.handle).is_some_and(|f| !f.is_empty())
                    || attributed.contains(&m.handle)
            })
            .map(|m| m.handle.clone())
            .collect();
        tracing::info!(suspects = out.len(), "train suspects attributed");
        out
    }

    fn bump(&self, f: impl FnOnce(&mut CheckStats)) {
        f(&mut self
            .stats
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner));
    }

    fn info(&self, handle: &str) -> Option<&MemberInfo> {
        self.members.iter().find(|m| m.handle == handle)
    }

    /// True when no other member of `subset` has scope in `member`'s cone, so its evidence stands.
    fn evidence_fresh(&self, member: &MemberInfo, subset: &[String]) -> Result<bool, CheckFault> {
        for other in subset.iter().filter(|h| **h != member.handle) {
            let Some(o) = self.info(other) else { continue };
            if scopes_overlap(&member.cone, &o.scope).map_err(fault)? {
                return Ok(false);
            }
        }
        Ok(true)
    }

    /// Member rule findings of `handle`, reused when the cached result is still fresh in `subset`.
    fn rules_for(
        &self,
        member: &MemberInfo,
        subset: &[String],
    ) -> Result<Vec<FindingNote>, CheckFault> {
        let fresh = self.evidence_fresh(member, subset)?;
        let cached = self
            .cache
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .get(&member.handle)
            .cloned();
        if let (true, Some(found)) = (fresh, cached) {
            tracing::info!(handle = %member.handle, "train member rules reused");
            self.bump(|s| s.rules_reused += 1);
            return Ok(found);
        }
        let found = self.backend.member_rules(&member.handle)?;
        tracing::info!(handle = %member.handle, findings = found.len(), "train member rules ran");
        self.bump(|s| s.rules_run += 1);
        self.cache
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .insert(member.handle.clone(), found.clone());
        Ok(found)
    }

    /// The member whose diff alone contains the finding's path, if exactly one does.
    fn attribute(&self, subset: &[String], note: &FindingNote) -> Option<String> {
        let path = note.path.as_ref()?;
        let mut hits = subset
            .iter()
            .filter_map(|h| self.info(h))
            .filter(|m| m.paths.contains(path));
        let first = hits.next()?;
        hits.next().is_none().then(|| first.handle.clone())
    }
}

/// Turn any displayable failure into a [`CheckFault`].
fn fault(e: impl std::fmt::Display) -> CheckFault {
    CheckFault {
        message: e.to_string(),
    }
}

/// One evidence line: `[owner] rule path: message`.
fn line(owner: &str, n: &FindingNote) -> String {
    format!(
        "[{owner}] {} {}: {}",
        n.rule,
        n.path.as_deref().unwrap_or("-"),
        n.message
    )
}

impl<B: CandidateBackend> Runner for CandidateChecker<B> {
    fn check(&self, subset: &[String]) -> Result<Verdict, CheckFault> {
        let mut evidence = Vec::new();
        for handle in subset {
            let Some(member) = self.info(handle) else {
                return Err(fault(format!("unknown train member {handle}")));
            };
            evidence.extend(
                self.rules_for(member, subset)?
                    .iter()
                    .map(|n| line(handle, n)),
            );
        }
        if !evidence.is_empty() {
            tracing::warn!(red = evidence.len(), "train candidate red on member rules");
            return Ok(Verdict::Red(evidence.join("; ")));
        }
        self.bump(|s| s.union_runs += 1);
        let found = self.backend.union_run(subset)?;
        if found.is_empty() {
            tracing::info!(members = subset.len(), "train candidate green");
            return Ok(Verdict::Green);
        }
        tracing::warn!(red = found.len(), "train candidate red on the union run");
        *self
            .attributed
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = found
            .iter()
            .filter_map(|n| self.attribute(subset, n))
            .collect();
        let lines: Vec<String> = found
            .iter()
            .map(|n| {
                line(
                    &self
                        .attribute(subset, n)
                        .unwrap_or_else(|| "union".to_owned()),
                    n,
                )
            })
            .collect();
        Ok(Verdict::Red(lines.join("; ")))
    }
}

/// The real backend: member worktrees for the cheap rules, a built candidate for the union run.
pub struct GitBackend {
    /// The primary checkout of the repository.
    pub primary: PathBuf,
    /// The base commit the candidate is built on and the ratchet compares with.
    pub base_oid: String,
    /// Ledger settings handed to every check.
    pub ledger: LedgerConfig,
    /// Members as the candidate builder takes them.
    pub members: Vec<CandidateMember>,
    /// Each member's worktree, by handle (where its cheap ticket rules run).
    pub worktrees: HashMap<String, PathBuf>,
    /// Counter naming the temp refs of successive candidates.
    pub round: Mutex<u32>,
    /// Raw rule findings stored at enqueue, by handle; a member listed here is re-ratcheted, not re-run.
    pub stored: HashMap<String, Vec<FindingNote>>,
}

/// Run the cheap ticket rules (tools skipped) of `handle` in `dir` and return the raw blocking findings.
///
/// Used at enqueue, in the agent's process outside the land lock; the driver re-ratchets the result
/// against the base findings instead of running the rules again.
///
/// # Errors
///
/// The check could not run.
pub fn run_member_rules(
    dir: &Path,
    handle: &str,
    base_oid: &str,
    ledger: &LedgerConfig,
) -> Result<Vec<FindingNote>, LandError> {
    let report = frob_check::run(
        dir,
        &CheckOptions {
            ledger: Some(ledger.clone()),
            skip_telemetry: true,
            ticket: Some(handle.to_owned()),
            base: Some(base_oid.to_owned()),
            skip_tools: true,
            ..CheckOptions::default()
        },
    )
    .map_err(|e| LandError::Config(e.to_string()))?;
    Ok(ratchet::blocking(&report))
}

impl GitBackend {
    fn options(&self) -> CheckOptions {
        CheckOptions {
            ledger: Some(self.ledger.clone()),
            skip_telemetry: true,
            ..CheckOptions::default()
        }
    }

    fn base(&self, at: &Path) -> Result<(Repo, Vec<FindingNote>), LandError> {
        let repo = Repo::discover(&self.primary).map_err(|e| LandError::Config(e.to_string()))?;
        let set = ratchet::base_findings(&repo, at, &self.base_oid, &self.ledger)?;
        Ok((repo, set))
    }
}

impl CandidateBackend for GitBackend {
    fn member_rules(&self, handle: &str) -> Result<Vec<FindingNote>, CheckFault> {
        let dir = self
            .worktrees
            .get(handle)
            .ok_or_else(|| fault(format!("no worktree for {handle}")))?;
        let (_, base) = self.base(dir).map_err(fault)?;
        let raw = match self.stored.get(handle) {
            Some(found) => {
                tracing::info!(%handle, "train member rules taken from enqueue");
                found.clone()
            }
            None => run_member_rules(dir, handle, &self.base_oid, &self.ledger).map_err(fault)?,
        };
        Ok(ratchet::without_base(raw, &base))
    }

    fn union_run(&self, subset: &[String]) -> Result<Vec<FindingNote>, CheckFault> {
        let members: Vec<CandidateMember> = self
            .members
            .iter()
            .filter(|m| subset.contains(&m.handle))
            .cloned()
            .collect();
        let id = {
            let mut n = self
                .round
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            *n += 1;
            format!("check-{}-{n}", std::process::id())
        };
        let repo = Repo::discover(&self.primary).map_err(fault)?;
        let cand =
            build_candidate(&repo, &self.primary, &id, &self.base_oid, &members).map_err(fault)?;
        if let Some(s) = cand.skipped.first() {
            return Err(fault(format!(
                "{} did not merge into the candidate: {}",
                s.handle, s.reason
            )));
        }
        let dir = cand.checkout();
        ratchet::share_build_dir(repo.common_dir(), dir);
        let (_, base) = self.base(dir).map_err(fault)?;
        let report = frob_check::run(
            dir,
            &CheckOptions {
                diff_base: Some(self.base_oid.clone()),
                ..self.options()
            },
        )
        .map_err(fault)?;
        Ok(ratchet::new_blocking(&report, &base))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    fn note(path: Option<&str>) -> FindingNote {
        FindingNote {
            fingerprint: "ab".into(),
            rule: "R1".into(),
            path: path.map(str::to_owned),
            message: "bad".into(),
        }
    }

    fn info(h: &str, scope: &str, paths: &[&str]) -> MemberInfo {
        MemberInfo {
            handle: h.into(),
            scope: vec![scope.into()],
            cone: vec![scope.into()],
            paths: paths.iter().map(|p| (*p).to_owned()).collect(),
        }
    }

    #[derive(Default)]
    struct Fake {
        rules: HashMap<String, Vec<FindingNote>>,
        union: Vec<FindingNote>,
        fail_union: bool,
        union_calls: RefCell<Vec<Vec<String>>>,
        rule_calls: RefCell<Vec<String>>,
    }

    impl CandidateBackend for &Fake {
        fn member_rules(&self, handle: &str) -> Result<Vec<FindingNote>, CheckFault> {
            self.rule_calls.borrow_mut().push(handle.into());
            Ok(self.rules.get(handle).cloned().unwrap_or_default())
        }
        fn union_run(&self, subset: &[String]) -> Result<Vec<FindingNote>, CheckFault> {
            self.union_calls.borrow_mut().push(subset.to_vec());
            if self.fail_union {
                return Err(CheckFault {
                    message: "oom".into(),
                });
            }
            Ok(self.union.clone())
        }
    }

    fn members() -> Vec<MemberInfo> {
        vec![
            info("A", "a/**", &["a/x.rs"]),
            info("B", "b/**", &["b/y.rs"]),
        ]
    }

    fn set(hs: &[&str]) -> Vec<String> {
        hs.iter().map(|h| (*h).to_owned()).collect()
    }

    // frob:tests crates/frob-land/src/train_check.rs::check
    #[test]
    fn one_union_run_covers_all_members() {
        let fake = Fake::default();
        let c = CandidateChecker::new(&fake, members());
        assert_eq!(c.check(&set(&["A", "B"])), Ok(Verdict::Green));
        assert_eq!(fake.union_calls.borrow().len(), 1);
        assert_eq!(fake.union_calls.borrow()[0], set(&["A", "B"]));
        assert_eq!(c.stats().rules_run, 2);
    }

    // frob:tests crates/frob-land/src/train_check.rs::check
    #[test]
    fn disjoint_member_rules_are_reused() {
        let fake = Fake::default();
        let c = CandidateChecker::new(&fake, members());
        c.check(&set(&["A"])).unwrap();
        c.check(&set(&["A", "B"])).unwrap();
        assert_eq!(*fake.rule_calls.borrow(), set(&["A", "B"]));
        assert_eq!(c.stats().rules_reused, 1);
    }

    // frob:tests crates/frob-land/src/train_check.rs::check
    #[test]
    fn touched_cone_reruns_member_rules() {
        let fake = Fake::default();
        let mut ms = members();
        ms[0].cone.push("b/**".into());
        let c = CandidateChecker::new(&fake, ms);
        c.check(&set(&["A"])).unwrap();
        c.check(&set(&["A", "B"])).unwrap();
        assert_eq!(
            fake.rule_calls
                .borrow()
                .iter()
                .filter(|h| *h == "A")
                .count(),
            2
        );
    }

    // frob:tests crates/frob-land/src/train_check.rs::check
    #[test]
    fn red_union_attributes_by_path() {
        let fake = Fake {
            union: vec![note(Some("b/y.rs")), note(None)],
            ..Fake::default()
        };
        let c = CandidateChecker::new(&fake, members());
        let Ok(Verdict::Red(ev)) = c.check(&set(&["A", "B"])) else {
            panic!("expected red")
        };
        assert!(ev.contains("[B] R1 b/y.rs: bad"), "{ev}");
        assert!(ev.contains("[union] R1 -: bad"), "{ev}");
    }

    // frob:tests crates/frob-land/src/train_check.rs::check
    #[test]
    fn red_member_rules_skip_the_union_run() {
        let mut fake = Fake::default();
        fake.rules.insert("A".into(), vec![note(Some("a/x.rs"))]);
        let c = CandidateChecker::new(&fake, members());
        assert!(matches!(c.check(&set(&["A", "B"])), Ok(Verdict::Red(e)) if e.contains("[A]")));
        assert!(fake.union_calls.borrow().is_empty());
    }

    // frob:tests crates/frob-land/src/train_check.rs::check
    #[test]
    fn fault_is_not_red() {
        let fake = Fake {
            fail_union: true,
            ..Fake::default()
        };
        let c = CandidateChecker::new(&fake, members());
        assert_eq!(
            c.check(&set(&["A"])),
            Err(CheckFault {
                message: "oom".into()
            })
        );
    }

    // frob:tests crates/frob-land/src/train_check.rs::suspects
    #[test]
    fn member_red_on_own_rules_is_a_suspect() {
        let mut fake = Fake::default();
        fake.rules.insert("B".into(), vec![note(Some("b/y.rs"))]);
        let c = CandidateChecker::new(&fake, members());
        assert!(matches!(c.check(&set(&["A", "B"])), Ok(Verdict::Red(_))));
        assert_eq!(c.suspects(), set(&["B"]));
    }

    // frob:tests crates/frob-land/src/train_check.rs::suspects
    #[test]
    fn path_attributed_union_finding_is_a_suspect() {
        let fake = Fake {
            union: vec![note(Some("a/x.rs")), note(None)],
            ..Fake::default()
        };
        let c = CandidateChecker::new(&fake, members());
        assert!(matches!(c.check(&set(&["A", "B"])), Ok(Verdict::Red(_))));
        assert_eq!(c.suspects(), set(&["A"]));
    }

    // frob:tests crates/frob-land/src/train_check.rs::suspects
    // frob:tests crates/frob-land/src/bisect.rs::plan_with
    #[test]
    fn own_rule_red_member_costs_one_union_run() {
        let mut fake = Fake::default();
        fake.rules.insert("B".into(), vec![note(Some("b/y.rs"))]);
        let c = CandidateChecker::new(&fake, members());
        let plan = crate::bisect::plan_with(&set(&["A", "B"]), &|| c.suspects(), &c);
        assert_eq!(plan.landable, set(&["A"]));
        assert_eq!(plan.culprits.len(), 1);
        assert_eq!(c.stats().union_runs, 1);
    }
}

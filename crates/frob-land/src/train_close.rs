//! Publish a green land-train candidate: fast-forward the base, then close every member in one ledger commit.
//!
//! The base moves first (compare-and-swap, with the same bounded retry as a
//! single land), then the members close together through
//! [`Ledger::close_batch`]. The run is saved as [`Phase::Closing`] before any
//! close, and a member that cannot close stays [`MemberStatus::Green`] with
//! its reason: it is pending-close in the train state, never lost. Calling
//! [`TrainCloser::close_run`] again (after a crash, or later) closes only the
//! members that are still pending.

use gob_path::Shown;
use std::path::Path;
use std::time::{Duration, Instant};

use frob_evidence::{DoneGuard, EvidenceGuard};
use frob_ledger::event::{CommentData, EventBody, LandData};
use frob_ledger::guards::{CloseGuard, default_close_guards};
use frob_ledger::model::CommentSubtype;
use frob_ledger::ops::BatchClose;
use frob_ledger::{Ledger, LedgerError, TicketId};
use gob_diagnostics::{Refusal, RefusalClass};
use gob_git::{Oid, Repo, TreeRef};

use crate::error::LandError;
use crate::events::{LandEvent, land_recorded};
use crate::git::git;
use crate::land::{base_ref, jitter};
use crate::plan::LandOptions;
use crate::train_state::{MemberStatus, Phase, TrainRun, TrainStore, resume_phase};

/// Stable code of the refusal when the base moved and could not be folded in.
const CODE_STALE: &str = "E-LAND-STALE";

/// Stable code of the refusal when git declined to advance the base.
const CODE_ADVANCE: &str = "E-LAND-ADVANCE";

/// One member to close: its ticket, branch and the guards built for it.
pub struct CloseMember {
    /// The ticket.
    pub id: TicketId,
    /// The ticket branch the candidate contains.
    pub branch: String,
    /// The evidence guard for the ticket.
    pub evidence: EvidenceGuard,
    /// The done guard (criteria, changelog) for the ticket.
    pub done: DoneGuard,
}

/// What a [`TrainCloser::close_run`] did.
#[derive(Debug, Clone)]
pub struct CloseReport {
    /// Members closed by this call.
    pub landed: Vec<TicketId>,
    /// Members still pending-close, with why.
    pub pending: Vec<(TicketId, String)>,
    /// The base tip after the call.
    pub advanced_to: Oid,
    /// The ledger commit that closed the members, when this call wrote one.
    pub ledger_commit: Option<Oid>,
    /// True when the base had already advanced before this call (a resume).
    pub resumed: bool,
}

/// Everything [`TrainCloser::close_run`] needs besides the run and its members.
pub struct TrainCloser<'a> {
    /// The repository.
    pub repo: &'a Repo,
    /// The primary checkout (cwd for ref updates).
    pub primary: &'a Path,
    /// The ledger the members close in.
    pub ledger: &'a Ledger,
    /// Where the run is saved.
    pub store: &'a TrainStore,
    /// The base branch short name.
    pub base: &'a str,
    /// Outcome, reason, retry policy and wait budget.
    pub opts: &'a LandOptions,
    /// The base-CI override note to audit on every member, when set.
    pub ci_override: Option<&'a str>,
}

impl TrainCloser<'_> {
    /// Advance the base to the run's candidate and close every pending member; safe to call again after a crash.
    ///
    /// # Errors
    ///
    /// `E-LAND-STALE` when the base moved and could not be folded in within the
    /// `--wait` budget, `E-LAND-ADVANCE` when git refuses the fast-forward, and
    /// ledger, git and state-store failures. The run is saved before every
    /// step, so an error leaves it resumable.
    pub fn close_run(
        &self,
        run: &mut TrainRun,
        members: &[CloseMember],
    ) -> Result<CloseReport, LandError> {
        // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
        let candidate = self.candidate(run)?;
        let in_base = self.in_base(candidate)?;
        let phase = resume_phase(run, in_base);
        let mut resumed = in_base;
        match phase {
            Phase::Building => {
                return Err(LandError::Config(format!(
                    "run {} has no built candidate to publish",
                    run.id
                )));
            }
            Phase::Checking => {
                self.advance_base(run)?;
                resumed = false;
                run.phase = Phase::Advanced;
                self.store.save_run(run)?;
                tracing::info!(run = %run.id, "base advanced to the candidate");
            }
            Phase::Advanced | Phase::Closing | Phase::Done => {
                tracing::info!(run = %run.id, ?phase, "base already advanced; closing the rest");
            }
        }
        let candidate_hex = run
            .candidate_oid
            .clone()
            .ok_or_else(|| LandError::Config("run lost its candidate".to_owned()))?;
        run.phase = Phase::Closing;
        self.store.save_run(run)?;
        let before: Vec<TicketId> = run
            .members
            .iter()
            .filter(|m| m.status == MemberStatus::Landed)
            .map(|m| m.id)
            .collect();
        let ledger_commit = self.close_pending(run, members, &candidate_hex)?;
        let landed_now = run
            .members
            .iter()
            .filter(|m| m.status == MemberStatus::Landed && !before.contains(&m.id))
            .map(|m| m.id)
            .collect::<Vec<_>>();
        let pending: Vec<(TicketId, String)> = run
            .members
            .iter()
            .filter(|m| m.status == MemberStatus::Green)
            .map(|m| {
                (
                    m.id,
                    m.reason
                        .clone()
                        .unwrap_or_else(|| "close not attempted".to_owned()),
                )
            })
            .collect();
        if pending.is_empty() {
            run.phase = Phase::Done;
            self.store.save_run(run)?;
            self.store.clear_run()?;
            tracing::info!(run = %run.id, "train run complete; state cleared");
        } else {
            tracing::warn!(run = %run.id, pending = pending.len(), "members left pending-close in the train state");
        }
        Ok(CloseReport {
            landed: landed_now,
            pending,
            advanced_to: self.repo.rev_parse(&base_ref(self.base))?,
            ledger_commit,
            resumed,
        })
    }

    /// The run's candidate oid.
    fn candidate(&self, run: &TrainRun) -> Result<Oid, LandError> {
        let hex = run.candidate_oid.as_deref().ok_or_else(|| {
            LandError::Config(format!("run {} has no candidate to publish", run.id))
        })?;
        Ok(self.repo.rev_parse(hex)?)
    }

    /// True when `candidate` is an ancestor of (or equal to) the base tip.
    fn in_base(&self, candidate: Oid) -> Result<bool, LandError> {
        Ok(self
            .repo
            .merge_base(&base_ref(self.base), &candidate.to_string())?
            == Some(candidate))
    }

    /// Fast-forward the base to the candidate, folding in ledger-only moves while `--wait` allows.
    fn advance_base(&self, run: &mut TrainRun) -> Result<(), LandError> {
        let opts = self.opts;
        let retrying = opts.wait_secs > 0;
        let budget = opts
            .retry
            .budget
            .unwrap_or_else(|| Duration::from_secs(opts.wait_secs));
        let started = Instant::now();
        let full = base_ref(self.base);
        let mut attempt = 0_u32;
        loop {
            attempt += 1;
            if let Some(hook) = &opts.retry.before_attempt {
                hook(attempt);
            }
            let base_oid = self.repo.rev_parse(&full)?;
            let candidate = self.candidate(run)?;
            if self.in_base(candidate)? {
                tracing::info!(attempt, "candidate already in the base");
                return Ok(());
            }
            if self.repo.merge_base(&full, &candidate.to_string())? == Some(base_oid) {
                if self.fast_forward(candidate, base_oid)? {
                    tracing::info!(attempt, to = %candidate, "base fast-forwarded");
                    return Ok(());
                }
                tracing::warn!(attempt, "base moved during the fast-forward");
            } else if retrying && self.fold_ledger_move(run, base_oid)? {
                continue;
            } else if !retrying {
                return Err(stale(self.base, None));
            }
            if started.elapsed() >= budget {
                return Err(stale(self.base, Some(attempt)));
            }
            let pause =
                jitter(&opts.retry, attempt, &run.id).min(budget.saturating_sub(started.elapsed()));
            tracing::info!(attempt, ?pause, "base moved; backing off before retrying");
            std::thread::sleep(pause);
        }
    }

    /// Move the base from `old` to `candidate`; false when it changed underneath (retry), an error when git refuses.
    fn fast_forward(&self, candidate: Oid, old: Oid) -> Result<bool, LandError> {
        let hex = candidate.to_string();
        let full = base_ref(self.base);
        let checked_out = self
            .repo
            .list_worktrees()?
            .into_iter()
            .find(|w| w.branch.as_deref() == Some(self.base));
        let outcome = if let Some(w) = &checked_out {
            tracing::info!(at = %Shown::of(&w.path), "fast-forwarding the checked-out base");
            git(self.repo, &w.path, &["merge", "--ff-only", &hex])?
        } else {
            tracing::info!("updating the base ref by compare-and-swap");
            git(
                self.repo,
                self.primary,
                &[
                    "update-ref",
                    "-m",
                    "frob land",
                    &full,
                    &hex,
                    &old.to_string(),
                ],
            )?
        };
        if outcome.ok() {
            return Ok(true);
        }
        if self.repo.rev_parse(&full)? != old {
            return Ok(false);
        }
        Err(LandError::Refused(
            Refusal::new(
                CODE_ADVANCE,
                RefusalClass::GuardNeedsAction,
                format!(
                    "could not advance {} to the train candidate: {}",
                    self.base, outcome.text
                ),
            )
            .with_remedy(format!(
                "commit or stash local changes in the checkout of {}, then rerun the train",
                self.base
            )),
        ))
    }

    /// When the base moved only by ledger commits, merge it into the candidate (a clean merge cannot change the verdict); true when folded.
    fn fold_ledger_move(&self, run: &mut TrainRun, base_oid: Oid) -> Result<bool, LandError> {
        let prefix = format!("{}/", self.ledger.config().dir);
        let old = self.repo.rev_parse(&run.base_oid)?;
        if self.repo.merge_base(&run.base_oid, &base_oid.to_string())? != Some(old) {
            return Ok(false);
        }
        let changed = self
            .repo
            .diff_names(&TreeRef::Oid(old), &TreeRef::Oid(base_oid))?;
        if changed.iter().any(|c| !c.path.starts_with(&prefix)) {
            tracing::info!("base moved in code; the candidate must be rebuilt");
            return Ok(false);
        }
        let candidate = self.candidate(run)?.to_string();
        let base_hex = base_oid.to_string();
        let merged = git(
            self.repo,
            self.primary,
            &["merge-tree", "--write-tree", &candidate, &base_hex],
        )?;
        let Some(tree) = merged
            .text
            .lines()
            .next()
            .filter(|_| merged.ok())
            .map(str::to_owned)
        else {
            tracing::warn!("ledger-only base move does not merge cleanly");
            return Ok(false);
        };
        let commit = git(
            self.repo,
            self.primary,
            &[
                "commit-tree",
                &tree,
                "-p",
                &candidate,
                "-p",
                &base_hex,
                "-m",
                "tickets(merge): fold the moved ledger into the train candidate",
            ],
        )?;
        if !commit.ok() {
            return Err(LandError::Config(format!(
                "git commit-tree failed: {}",
                commit.text
            )));
        }
        let folded = commit.text.trim().to_owned();
        tracing::info!(
            from = candidate,
            to = folded,
            "folded a ledger-only base move into the candidate"
        );
        run.candidate_oid = Some(folded);
        run.base_oid = base_hex;
        self.store.save_run(run)?;
        Ok(true)
    }

    /// Close the members still `Green` in one ledger commit, falling back to one by one when the batch is refused.
    fn close_pending(
        &self,
        run: &mut TrainRun,
        members: &[CloseMember],
        candidate_hex: &str,
    ) -> Result<Option<Oid>, LandError> {
        let mut todo: Vec<&CloseMember> = Vec::new();
        for m in run
            .members
            .iter()
            .filter(|m| m.status == MemberStatus::Green)
        {
            let cm = members.iter().find(|c| c.id == m.id).ok_or_else(|| {
                LandError::Config(format!("no close inputs for pending member {}", m.id))
            })?;
            todo.push(cm);
        }
        if todo.is_empty() {
            return Ok(None);
        }
        for m in &todo {
            let exempt = m.done.record_exemption(self.ledger, m.id)?;
            tracing::info!(ticket = %m.id, exempt = exempt.is_some(), "changelog exemption audited before closing");
        }
        let defaults = default_close_guards();
        let mut commit = None;
        let batch = self.items(&todo, &defaults, candidate_hex)?;
        match self.ledger.close_batch(&batch) {
            Ok(applied) => {
                for (m, a) in todo.iter().zip(&applied) {
                    self.landed(run, m, a.already)?;
                    commit = commit.or(a.commit);
                }
                tracing::info!(
                    count = todo.len(),
                    "closed the train members in one ledger commit"
                );
            }
            Err(LedgerError::GuardRefused { .. } | LedgerError::Terminal { .. }) => {
                tracing::warn!("batch close refused; closing members one at a time");
                for m in &todo {
                    let one = self.items(&[m], &defaults, candidate_hex)?;
                    match self.ledger.close_batch(&one) {
                        Ok(applied) => {
                            let a = &applied[0];
                            self.landed(run, m, a.already)?;
                            commit = commit.or(a.commit);
                        }
                        Err(
                            e @ (LedgerError::GuardRefused { .. } | LedgerError::Terminal { .. }),
                        ) => {
                            tracing::warn!(ticket = %m.id, error = %e, "member left pending-close");
                            self.pend(run, m.id, e.to_string())?;
                        }
                        Err(e) => return Err(e.into()),
                    }
                }
            }
            Err(e) => return Err(e.into()),
        }
        Ok(commit)
    }

    /// The close request for each of `members`: land event, optional CI-override note, guards.
    fn items<'g>(
        &self,
        members: &[&'g CloseMember],
        defaults: &'g [Box<dyn CloseGuard>],
        candidate_hex: &str,
    ) -> Result<Vec<BatchClose<'g>>, LandError> {
        let base_full = base_ref(self.base);
        let mut out = Vec::new();
        for m in members {
            let mut before = Vec::new();
            let land = LandEvent {
                base_ref: &base_full,
                commit: candidate_hex,
                branch: &m.branch,
                pushed: false,
            };
            if !land_recorded(self.ledger, m.id, &land)? {
                before.push(EventBody::Land(LandData {
                    base_ref: base_full.clone(),
                    commit: candidate_hex.to_owned(),
                    branch: m.branch.clone(),
                    pushed: false,
                }));
            }
            if let Some(note) = self.ci_override {
                let seen = self.ledger.events(m.id)?.iter().any(|e| {
                    matches!(&e.body, EventBody::Comment(c)
                        if c.subtype == CommentSubtype::Decision && c.body == note)
                });
                if !seen {
                    tracing::warn!(ticket = %m.id, note, "base CI override recorded");
                    before.push(EventBody::Comment(CommentData {
                        subtype: CommentSubtype::Decision,
                        body: note.to_owned(),
                    }));
                }
            }
            let mut guards: Vec<&dyn CloseGuard> = defaults.iter().map(|g| &**g).collect();
            guards.push(&m.evidence);
            guards.push(&m.done);
            out.push(BatchClose {
                id: m.id,
                before,
                outcome: self.opts.outcome,
                reason: self
                    .opts
                    .reason
                    .clone()
                    .or_else(|| self.opts.no_evidence_reason.clone())
                    .or_else(|| self.opts.no_changelog_reason.clone()),
                guards,
            });
        }
        Ok(out)
    }

    /// Mark `m` landed, audit an evidence bypass when it was newly closed, and save the run.
    fn landed(&self, run: &mut TrainRun, m: &CloseMember, already: bool) -> Result<(), LandError> {
        if !already {
            let recorded = m.evidence.record_bypass(self.ledger, m.id)?;
            tracing::info!(ticket = %m.id, bypass = recorded.is_some(), "train closed the ticket");
        }
        if let Some(member) = run.members.iter_mut().find(|x| x.id == m.id) {
            member.status = MemberStatus::Landed;
            member.reason = None;
        }
        self.store.save_run(run)
    }

    /// Record why `id` stays pending-close and save the run.
    fn pend(&self, run: &mut TrainRun, id: TicketId, why: String) -> Result<(), LandError> {
        if let Some(member) = run.members.iter_mut().find(|x| x.id == id) {
            member.reason = Some(why);
        }
        self.store.save_run(run)
    }
}

/// The stale-base refusal; `gave_up_after` is the attempt count when the `--wait` budget ran out.
fn stale(base: &str, gave_up_after: Option<u32>) -> LandError {
    let message = match gave_up_after {
        None => format!("{base} moved while the train was publishing"),
        Some(n) => format!(
            "{base} moved while the train was publishing; gave up after {n} attempt(s) because the --wait budget is spent"
        ),
    };
    LandError::Refused(
        Refusal::new(CODE_STALE, RefusalClass::GuardRetryByWaiting, message)
            .with_remedy("rerun with frob land --wait <secs> so the train can retry a moved base"),
    )
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;
    use std::sync::Arc;

    use frob_ledger::LedgerConfig;
    use frob_ledger::model::{Category, TicketType};
    use frob_ledger::ops::NewTicket;

    use super::*;
    use crate::train_state::Member;

    const MAIN: &str = "refs/heads/main";

    /// A repository with `main` unchecked-out, an open ledger and an empty train store.
    struct Fix {
        _tmp: tempfile::TempDir,
        root: PathBuf,
        repo: Repo,
        ledger: Ledger,
        store: TrainStore,
    }

    impl Fix {
        fn new() -> Self {
            let tmp = tempfile::tempdir().expect("tempdir");
            let root = tmp.path().join("repo");
            std::fs::create_dir(&root).expect("mkdir");
            let repo = Repo::init(&root).expect("init");
            std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/scratch\n").expect("head");
            let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
            std::fs::write(
                repo.git_dir().join("config"),
                format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
            )
            .expect("identity");
            drop(repo);
            let repo = Repo::discover(&root).expect("discover");
            commit(&repo, MAIN, "README.md", "hello\n");
            std::fs::write(root.join("frob.toml"), "[pm]\ndone_requires = []\n")
                .expect("frob.toml");
            let ledger = open_ledger(&root);
            let store = TrainStore::new(repo.common_dir());
            Self {
                _tmp: tmp,
                root,
                repo,
                ledger,
                store,
            }
        }

        fn ticket(&self, title: &str, ty: TicketType) -> TicketId {
            self.ledger
                .new_ticket(NewTicket::new(title, ty))
                .expect("new ticket")
                .ticket
                .front
                .id
        }

        /// A candidate branch one code commit ahead of the current base.
        fn candidate(&self) -> String {
            let cwd = &self.root;
            let r = git(&self.repo, cwd, &["update-ref", "refs/heads/cand", MAIN]).expect("git");
            assert!(r.ok(), "{}", r.text);
            commit(&self.repo, "refs/heads/cand", "feature.txt", "feature\n");
            self.repo
                .rev_parse("refs/heads/cand")
                .expect("cand")
                .to_string()
        }

        fn run(&self, cand: &str, ids: &[TicketId]) -> TrainRun {
            let base = self.repo.rev_parse(MAIN).expect("main").to_string();
            let members = ids
                .iter()
                .map(|id| Member {
                    id: *id,
                    head_oid: cand.to_owned(),
                    status: MemberStatus::Green,
                    reason: None,
                })
                .collect();
            let mut run = TrainRun::new("RUN1", base, members);
            run.phase = Phase::Checking;
            run.candidate_oid = Some(cand.to_owned());
            self.store.save_run(&mut run).expect("save");
            run
        }

        fn members(&self, ids: &[TicketId]) -> Vec<CloseMember> {
            ids.iter()
                .map(|id| CloseMember {
                    id: *id,
                    branch: format!("ticket/{id}"),
                    evidence: EvidenceGuard::default(),
                    done: DoneGuard::for_ticket(&self.ledger, *id, &self.root).expect("done guard"),
                })
                .collect()
        }

        fn closer<'a>(&'a self, opts: &'a LandOptions) -> TrainCloser<'a> {
            TrainCloser {
                repo: &self.repo,
                primary: &self.root,
                ledger: &self.ledger,
                store: &self.store,
                base: "main",
                opts,
                ci_override: None,
            }
        }

        fn close_commits(&self) -> usize {
            let r = git(&self.repo, &self.root, &["log", "--format=%s", MAIN]).expect("log");
            r.text
                .lines()
                .filter(|l| l.starts_with("tickets(close)"))
                .count()
        }

        fn done(&self, id: TicketId) -> bool {
            self.ledger.show(id).expect("show").ticket.front.category == Category::Done
        }
    }

    fn open_ledger(root: &Path) -> Ledger {
        Ledger::open(
            Repo::discover(root).expect("discover"),
            LedgerConfig::default(),
            Arc::new(gob_time::SystemClock),
        )
    }

    /// Commit `path` = `body` on top of ref `name` with plumbing and a throwaway work tree.
    fn commit(repo: &Repo, name: &str, path: &str, body: &str) {
        let gd = repo.git_dir().to_path_buf();
        let gd_s = Shown::with_home(&gd, None).to_string();
        let tmp = tempfile::tempdir().expect("tempdir");
        let wt = Shown::with_home(tmp.path(), None).to_string();
        let run = |args: &[&str]| -> String {
            let mut full = vec!["--git-dir", gd_s.as_str(), "--work-tree", wt.as_str()];
            full.extend_from_slice(args);
            let r = git(repo, tmp.path(), &full).expect("git");
            assert!(r.ok(), "git {args:?}: {}", r.text);
            r.text.trim().to_owned()
        };
        let parent = repo.rev_parse(name).ok().map(|o| o.to_string());
        let index = gd.join("index");
        let _ = std::fs::remove_file(&index);
        if let Some(p) = &parent {
            run(&["read-tree", p]);
        }
        let file = tmp.path().join(path);
        std::fs::write(&file, body).expect("write");
        run(&["add", path]);
        let tree = run(&["write-tree"]);
        let mut args = vec!["commit-tree", tree.as_str(), "-m", "change"];
        if let Some(p) = &parent {
            args.extend(["-p", p.as_str()]);
        }
        let c = run(&args);
        run(&["update-ref", name, &c]);
        let _ = std::fs::remove_file(&index);
    }

    fn refusal_code(e: LandError) -> String {
        match e {
            LandError::Refused(r) => r.code.clone(),
            other => panic!("expected a refusal, got {other}"),
        }
    }

    // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
    // frob:tests crates/frob-land/src/train_close.rs::TrainCloser.close_run
    #[test]
    fn green_batch_lands_and_closes_in_one_ledger_commit() {
        let f = Fix::new();
        let ids: Vec<_> = (0..3)
            .map(|i| f.ticket(&format!("t{i}"), TicketType::Docs))
            .collect();
        let cand = f.candidate();
        let mut run = f.run(&cand, &ids);
        let opts = LandOptions::default();
        let before = f.close_commits();
        let report = f
            .closer(&opts)
            .close_run(&mut run, &f.members(&ids))
            .expect("close");
        assert_eq!(report.landed.len(), 3, "{:?}", report.pending);
        assert!(report.pending.is_empty());
        assert!(!report.resumed);
        assert_eq!(
            f.repo.merge_base(MAIN, &cand).expect("mb"),
            Some(f.repo.rev_parse(&cand).expect("c"))
        );
        assert!(ids.iter().all(|id| f.done(*id)));
        assert_eq!(
            f.close_commits() - before,
            1,
            "one ledger commit closes every member"
        );
        assert!(f.store.load_run().expect("load").is_none(), "state cleared");
    }

    // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
    // frob:tests crates/frob-land/src/train_close.rs::TrainCloser.close_run
    #[test]
    fn ledger_only_base_move_is_folded_when_waiting() {
        let f = Fix::new();
        let id = f.ticket("t", TicketType::Docs);
        let cand = f.candidate();
        let mut run = f.run(&cand, &[id]);
        let root = f.root.clone();
        let mut opts = LandOptions {
            wait_secs: 5,
            ..LandOptions::default()
        };
        opts.retry.before_attempt = Some(Arc::new(move |attempt| {
            if attempt == 1 {
                open_ledger(&root)
                    .new_ticket(NewTicket::new("racer", TicketType::Docs))
                    .expect("racing ledger write");
            }
        }));
        let report = f
            .closer(&opts)
            .close_run(&mut run, &f.members(&[id]))
            .expect("close");
        assert_eq!(report.landed, vec![id]);
        assert!(f.done(id));
        let tip = f.repo.rev_parse(MAIN).expect("main");
        assert!(
            f.repo.merge_base(MAIN, &cand).expect("mb")
                == Some(f.repo.rev_parse(&cand).expect("cand")),
            "the original candidate is in the base after the fold, tip {tip}"
        );
    }

    // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
    // frob:tests crates/frob-land/src/train_close.rs::TrainCloser.close_run
    #[test]
    fn moved_base_without_wait_is_stale() {
        let f = Fix::new();
        let id = f.ticket("t", TicketType::Docs);
        let cand = f.candidate();
        let mut run = f.run(&cand, &[id]);
        let root = f.root.clone();
        let mut opts = LandOptions::default();
        opts.retry.before_attempt = Some(Arc::new(move |_| {
            commit(
                &Repo::discover(&root).expect("repo"),
                MAIN,
                "other.txt",
                "x\n",
            );
        }));
        let err = f
            .closer(&opts)
            .close_run(&mut run, &f.members(&[id]))
            .expect_err("stale");
        assert_eq!(refusal_code(err), CODE_STALE);
        assert!(!f.done(id));
        assert_eq!(
            f.store.load_run().expect("load").expect("kept").phase,
            Phase::Checking
        );
    }

    // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
    // frob:tests crates/frob-land/src/train_close.rs::TrainCloser.close_run
    #[test]
    fn code_move_gives_up_when_the_budget_is_spent() {
        let f = Fix::new();
        let id = f.ticket("t", TicketType::Docs);
        let cand = f.candidate();
        let mut run = f.run(&cand, &[id]);
        let root = f.root.clone();
        let mut opts = LandOptions {
            wait_secs: 1,
            ..LandOptions::default()
        };
        opts.retry.budget = Some(Duration::from_millis(100));
        opts.retry.backoff_base = Duration::from_millis(5);
        opts.retry.before_attempt = Some(Arc::new(move |attempt| {
            if attempt == 1 {
                commit(
                    &Repo::discover(&root).expect("repo"),
                    MAIN,
                    "other.txt",
                    "x\n",
                );
            }
        }));
        let err = f
            .closer(&opts)
            .close_run(&mut run, &f.members(&[id]))
            .expect_err("stale");
        assert_eq!(refusal_code(err), CODE_STALE);
    }

    // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
    // frob:tests crates/frob-land/src/train_close.rs::TrainCloser.close_run
    #[test]
    fn resume_after_the_fast_forward_closes_only_the_remaining_members() {
        let f = Fix::new();
        let ids: Vec<_> = (0..3)
            .map(|i| f.ticket(&format!("t{i}"), TicketType::Docs))
            .collect();
        let cand = f.candidate();
        let mut run = f.run(&cand, &ids);
        // The crash: the base advanced, the first member was already closed, the rest were not.
        let r = git(&f.repo, &f.root, &["update-ref", MAIN, &cand]).expect("git");
        assert!(r.ok(), "{}", r.text);
        let opts = LandOptions::default();
        let first = f.members(&ids[..1]);
        f.ledger
            .close_batch(&[BatchClose {
                id: ids[0],
                before: Vec::new(),
                outcome: opts.outcome,
                reason: None,
                guards: Vec::new(),
            }])
            .expect("first close");
        drop(first);
        run.members[0].status = MemberStatus::Landed;
        run.phase = Phase::Advanced;
        f.store.save_run(&mut run).expect("save");
        let loaded = f.store.load_run().expect("load").expect("run");
        let mut run = loaded;
        let before = f.close_commits();
        let report = f
            .closer(&opts)
            .close_run(&mut run, &f.members(&ids))
            .expect("resume");
        assert!(report.resumed);
        assert_eq!(report.landed, vec![ids[1], ids[2]]);
        assert!(ids.iter().all(|id| f.done(*id)));
        assert_eq!(f.close_commits() - before, 1);
        assert!(f.store.load_run().expect("load").is_none());
    }

    // frob:ticket 01M4Z1N93S11HX3DGGKBJF5WGP
    // frob:tests crates/frob-land/src/train_close.rs::TrainCloser.close_run
    #[test]
    fn a_member_that_cannot_close_stays_pending_in_the_train_state() {
        let f = Fix::new();
        let good = f.ticket("good", TicketType::Docs);
        let bad = f.ticket("bad", TicketType::Task);
        let cand = f.candidate();
        let ids = [good, bad];
        let mut run = f.run(&cand, &ids);
        let opts = LandOptions::default();
        let report = f
            .closer(&opts)
            .close_run(&mut run, &f.members(&ids))
            .expect("close");
        assert_eq!(report.landed, vec![good]);
        assert_eq!(report.pending.len(), 1);
        assert_eq!(report.pending[0].0, bad);
        assert!(f.done(good) && !f.done(bad));
        let kept = f.store.load_run().expect("load").expect("kept");
        assert_eq!(kept.phase, Phase::Closing);
        let m = kept.members.iter().find(|m| m.id == bad).expect("member");
        assert_eq!(m.status, MemberStatus::Green);
        assert!(m.reason.is_some());
        assert_eq!(
            f.repo.merge_base(MAIN, &cand).expect("mb"),
            Some(f.repo.rev_parse(&cand).expect("cand")),
            "the base stays advanced"
        );
    }
}

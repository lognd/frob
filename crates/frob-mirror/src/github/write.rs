//! GitHub writes (mirror.md 3.2 serial writes, 3.3 never recreate, 3.4 additive endpoints).
//!
//! The HTTP client is not part of this module: a [`WriteTransport`] performs the raw calls (live
//! through `frob-gh`, or recorded offline). The trait has no delete and no replace-the-set call,
//! so the mirror cannot express either. Mutations are sent one at a time, at least
//! [`WRITE_SPACING`] apart by an injected [`Clock`]. A failed write is recorded as failed with no
//! effect assumed; every operation is a set-to-value diff against the issue as read, so the next
//! run recomputes and retries it.

// frob:ticket 01M4052R88Y0A9HQHDB86ERMEM

use std::time::Duration;

use tracing::{debug, info, trace, warn};

use crate::adapter::{AdapterResult, IssueRef, IssueState, RelationRouting};
use crate::fields::MANAGED_LABEL_PREFIX;
use crate::github::render::RenderedIssue;
use crate::projection::{Outcome, Relation, RelationKind};

/// Minimum gap between two mutations (mirror.md 3.2).
pub const WRITE_SPACING: Duration = Duration::from_secs(1);

/// Time source for write spacing; a fake makes spacing testable without sleeping.
pub trait Clock {
    /// Monotonic time since an arbitrary epoch.
    fn now(&self) -> Duration;
    /// Block for `d`.
    fn sleep(&self, d: Duration);
}

/// The raw GitHub mutations the mirror may make; there is deliberately no delete.
pub trait WriteTransport {
    /// PATCH the issue title and body.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the call fails.
    fn patch_issue(&mut self, issue: &IssueRef, title: &str, body: &str) -> AdapterResult<()>;
    /// Close the issue with a `state_reason` (`completed`, `not_planned` or `duplicate`).
    ///
    /// # Errors
    /// Returns an `AdapterError` when the call fails.
    fn close_issue(
        &mut self,
        issue: &IssueRef,
        state_reason: &str,
        reason: &str,
    ) -> AdapterResult<()>;
    /// POST one label onto the issue.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the call fails.
    fn add_label(&mut self, issue: &IssueRef, label: &str) -> AdapterResult<()>;
    /// DELETE one label from the issue.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the call fails.
    fn remove_label(&mut self, issue: &IssueRef, label: &str) -> AdapterResult<()>;
    /// Add `child` as a native sub-issue of `parent`.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the call fails.
    fn add_sub_issue(&mut self, parent: &IssueRef, child: &IssueRef) -> AdapterResult<()>;
    /// Create a native non-hierarchical link from `issue` to `target`.
    ///
    /// # Errors
    /// Returns an `AdapterError` when the call fails.
    fn add_link(
        &mut self,
        issue: &IssueRef,
        kind: RelationKind,
        target: &IssueRef,
    ) -> AdapterResult<()>;
}

/// How one attempted write ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WriteStatus {
    /// The tracker accepted the write.
    Sent,
    /// The write failed (5xx, throttle, transport); no effect is assumed and it is retried
    /// next run.
    Failed(String),
}

/// One attempted write.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WriteRecord {
    /// The issue written.
    pub issue: IssueRef,
    /// What was attempted, for example `add_label frob:managed`.
    pub op: String,
    /// How it ended.
    pub status: WriteStatus,
}

/// Records of every write attempted in a run.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct WriteReport {
    /// Attempts in order.
    pub records: Vec<WriteRecord>,
}

impl WriteReport {
    /// The failed writes, which the next run recomputes and retries.
    pub fn retry_next_run(&self) -> impl Iterator<Item = &WriteRecord> {
        self.records
            .iter()
            .filter(|r| matches!(r.status, WriteStatus::Failed(_)))
    }
}

/// The GitHub `state_reason` for an outcome.
pub fn state_reason(outcome: Outcome) -> &'static str {
    match outcome {
        Outcome::Done => "completed",
        Outcome::Dropped | Outcome::Superseded => "not_planned",
        Outcome::Duplicate => "duplicate",
    }
}

/// Serial, spaced, additive writer over a transport.
pub struct GithubWriter<'a, T: WriteTransport, C: Clock> {
    transport: T,
    clock: &'a C,
    spacing: Duration,
    last_sent: Option<Duration>,
    report: WriteReport,
}

impl<'a, T: WriteTransport, C: Clock> GithubWriter<'a, T, C> {
    /// A writer spacing mutations by [`WRITE_SPACING`].
    pub fn new(transport: T, clock: &'a C) -> Self {
        Self::with_spacing(transport, clock, WRITE_SPACING)
    }

    /// A writer with an explicit spacing.
    pub fn with_spacing(transport: T, clock: &'a C, spacing: Duration) -> Self {
        Self {
            transport,
            clock,
            spacing,
            last_sent: None,
            report: WriteReport::default(),
        }
    }

    /// Everything attempted so far.
    pub fn report(&self) -> &WriteReport {
        &self.report
    }

    /// Wait out the spacing, run `call`, and record the attempt; returns whether it was sent.
    fn send(
        &mut self,
        issue: &IssueRef,
        op: String,
        call: impl FnOnce(&mut T) -> AdapterResult<()>,
    ) -> bool {
        if let Some(last) = self.last_sent {
            let elapsed = self.clock.now().saturating_sub(last);
            if elapsed < self.spacing {
                let wait = self.spacing - elapsed;
                trace!(?wait, "write: spacing mutations");
                self.clock.sleep(wait);
            }
        }
        let result = call(&mut self.transport);
        self.last_sent = Some(self.clock.now());
        let (status, ok) = match result {
            Ok(()) => {
                debug!(issue = %issue.0, %op, "write sent");
                (WriteStatus::Sent, true)
            }
            Err(e) => {
                warn!(issue = %issue.0, %op, error = %e, "write failed; no effect assumed");
                (WriteStatus::Failed(e.to_string()), false)
            }
        };
        self.report.records.push(WriteRecord {
            issue: issue.clone(),
            op,
            status,
        });
        ok
    }

    /// Bring `current` to `rendered`: title and body, then `frob:` labels, then close.
    ///
    /// Only the diff is sent. Labels outside the `frob:` namespace are never added or removed,
    /// and the label set is never replaced. Stops at the first failed write; the rest is
    /// recomputed next run. A `closing` outcome closes an open issue with its reason; an issue is
    /// never deleted. Returns whether every needed write was sent.
    pub fn publish(
        &mut self,
        issue: &IssueRef,
        current: &IssueState,
        rendered: &RenderedIssue,
        closing: Option<(Outcome, &str)>,
    ) -> bool {
        if (current.title != rendered.title || current.body != rendered.body)
            && !self.send(issue, "patch_issue".into(), |t| {
                t.patch_issue(issue, &rendered.title, &rendered.body)
            })
        {
            return false;
        }
        for label in rendered
            .labels
            .iter()
            .filter(|l| l.starts_with(MANAGED_LABEL_PREFIX) && !current.labels.contains(l))
        {
            if !self.send(issue, format!("add_label {label}"), |t| {
                t.add_label(issue, label)
            }) {
                return false;
            }
        }
        for label in current
            .labels
            .iter()
            .filter(|l| l.starts_with(MANAGED_LABEL_PREFIX) && !rendered.labels.contains(l))
        {
            if !self.send(issue, format!("remove_label {label}"), |t| {
                t.remove_label(issue, label)
            }) {
                return false;
            }
        }
        if let Some((outcome, reason)) = closing
            && !current.closed
        {
            let sr = state_reason(outcome);
            if !self.send(issue, format!("close_issue {sr}"), |t| {
                t.close_issue(issue, sr, reason)
            }) {
                return false;
            }
        }
        info!(issue = %issue.0, "write: issue published");
        true
    }

    /// Send native relations of `routing` for `issue`; body-link relations need no call because
    /// they are already in the rendered body. `resolve` maps a relation to its issue, skipping
    /// ones not yet mirrored. Returns whether every needed write was sent.
    pub fn publish_relations(
        &mut self,
        issue: &IssueRef,
        routing: &RelationRouting,
        resolve: impl Fn(&Relation) -> Option<IssueRef>,
    ) -> bool {
        for r in &routing.native {
            let Some(target) = resolve(r) else {
                debug!(handle = %r.handle, "write: relation target not mirrored yet");
                continue;
            };
            let op = format!("{:?} {}", r.kind, target.0);
            let sent = match r.kind {
                RelationKind::Parent => self.send(issue, op, |t| t.add_sub_issue(&target, issue)),
                RelationKind::Child => self.send(issue, op, |t| t.add_sub_issue(issue, &target)),
                kind => self.send(issue, op, |t| t.add_link(issue, kind, &target)),
            };
            if !sent {
                return false;
            }
        }
        true
    }
}

#[cfg(test)]
mod tests {
    use std::cell::{Cell, RefCell};
    use std::rc::Rc;

    use super::*;
    use crate::adapter::AdapterError;

    /// Fake clock: `sleep` advances time, so spacing is exact and instant.
    #[derive(Default)]
    struct FakeClock(Cell<Duration>);

    impl Clock for FakeClock {
        fn now(&self) -> Duration {
            self.0.get()
        }
        fn sleep(&self, d: Duration) {
            self.0.set(self.0.get() + d);
        }
    }

    /// Records calls with the clock time they were made; can fail one op with a 5xx.
    struct Rec<'a> {
        log: Rc<RefCell<Vec<(Duration, String)>>>,
        clock: &'a FakeClock,
        fail_on: Option<&'static str>,
    }

    impl Rec<'_> {
        fn rec(&self, call: String) -> AdapterResult<()> {
            let fail = self.fail_on.is_some_and(|f| call.starts_with(f));
            self.log.borrow_mut().push((self.clock.now(), call));
            if fail {
                Err(AdapterError::Other("http 502".into()))
            } else {
                Ok(())
            }
        }
    }

    impl WriteTransport for Rec<'_> {
        fn patch_issue(&mut self, i: &IssueRef, _: &str, _: &str) -> AdapterResult<()> {
            self.rec(format!("patch {}", i.0))
        }
        fn close_issue(&mut self, i: &IssueRef, sr: &str, why: &str) -> AdapterResult<()> {
            self.rec(format!("close {} {sr} {why}", i.0))
        }
        fn add_label(&mut self, i: &IssueRef, l: &str) -> AdapterResult<()> {
            self.rec(format!("add_label {} {l}", i.0))
        }
        fn remove_label(&mut self, i: &IssueRef, l: &str) -> AdapterResult<()> {
            self.rec(format!("remove_label {} {l}", i.0))
        }
        fn add_sub_issue(&mut self, p: &IssueRef, c: &IssueRef) -> AdapterResult<()> {
            self.rec(format!("sub {} {}", p.0, c.0))
        }
        fn add_link(&mut self, i: &IssueRef, k: RelationKind, t: &IssueRef) -> AdapterResult<()> {
            self.rec(format!("link {} {k:?} {}", i.0, t.0))
        }
    }

    type Log = Rc<RefCell<Vec<(Duration, String)>>>;

    fn setup<'a>(clock: &'a FakeClock, fail_on: Option<&'static str>) -> (Rec<'a>, Log) {
        let log = Log::default();
        (
            Rec {
                log: log.clone(),
                clock,
                fail_on,
            },
            log,
        )
    }

    fn rendered(labels: &[&str]) -> RenderedIssue {
        RenderedIssue {
            title: "T".into(),
            body: "B".into(),
            labels: labels.iter().map(|s| (*s).to_owned()).collect(),
            digest: "d".into(),
        }
    }

    fn state(labels: &[&str], closed: bool) -> IssueState {
        IssueState {
            issue: IssueRef("5".into()),
            title: "T".into(),
            body: "B".into(),
            labels: labels.iter().map(|s| (*s).to_owned()).collect(),
            assignees: vec![],
            closed,
        }
    }

    fn ops(log: &Log) -> Vec<String> {
        log.borrow().iter().map(|(_, c)| c.clone()).collect()
    }

    // frob:tests publish
    #[test]
    fn label_change_uses_only_add_and_remove_and_keeps_tracker_labels() {
        let clock = FakeClock::default();
        let (t, log) = setup(&clock, None);
        let mut w = GithubWriter::new(t, &clock);
        let cur = state(&["bug", "frob:old", "frob:keep"], false);
        let ok = w.publish(
            &IssueRef("5".into()),
            &cur,
            &rendered(&["frob:keep", "frob:new"]),
            None,
        );
        assert!(ok);
        assert_eq!(
            ops(&log),
            ["add_label 5 frob:new", "remove_label 5 frob:old"]
        );
    }

    // frob:tests publish
    // frob:tests state_reason
    #[test]
    fn dropped_ticket_closes_with_reason_and_is_never_deleted() {
        let clock = FakeClock::default();
        let (t, log) = setup(&clock, None);
        let mut w = GithubWriter::new(t, &clock);
        let ok = w.publish(
            &IssueRef("5".into()),
            &state(&[], false),
            &rendered(&[]),
            Some((Outcome::Dropped, "cut from scope")),
        );
        assert!(ok);
        assert_eq!(ops(&log), ["close 5 not_planned cut from scope"]);
        assert!(!ops(&log).iter().any(|o| o.contains("delete")));
        assert_eq!(state_reason(Outcome::Done), "completed");
        assert_eq!(state_reason(Outcome::Duplicate), "duplicate");
    }

    // frob:tests publish
    #[test]
    fn two_mutations_are_at_least_one_second_apart() {
        let clock = FakeClock::default();
        let (t, log) = setup(&clock, None);
        let mut w = GithubWriter::new(t, &clock);
        let mut cur = state(&[], false);
        cur.title = "old".into();
        w.publish(
            &IssueRef("5".into()),
            &cur,
            &rendered(&["frob:managed"]),
            None,
        );
        let times: Vec<_> = log.borrow().iter().map(|(t, _)| *t).collect();
        assert_eq!(times.len(), 2);
        assert!(times[1].saturating_sub(times[0]) >= Duration::from_secs(1));
    }

    // frob:tests publish
    #[test]
    fn a_5xx_is_recorded_failed_and_retried_next_run() {
        let clock = FakeClock::default();
        let (t, log) = setup(&clock, Some("patch"));
        let mut w = GithubWriter::new(t, &clock);
        let mut cur = state(&[], false);
        cur.title = "old".into();
        let ok = w.publish(
            &IssueRef("5".into()),
            &cur,
            &rendered(&["frob:managed"]),
            None,
        );
        assert!(!ok);
        // Stopped at the failure; nothing after it was assumed or sent.
        assert_eq!(ops(&log), ["patch 5"]);
        let failed: Vec<_> = w.report().retry_next_run().collect();
        assert_eq!(failed.len(), 1);
        assert!(matches!(&failed[0].status, WriteStatus::Failed(m) if m.contains("502")));
        // Next run re-reads the unchanged issue and recomputes the same writes.
        let (t2, log2) = setup(&clock, None);
        let mut w2 = GithubWriter::new(t2, &clock);
        assert!(w2.publish(
            &IssueRef("5".into()),
            &cur,
            &rendered(&["frob:managed"]),
            None
        ));
        assert_eq!(ops(&log2), ["patch 5", "add_label 5 frob:managed"]);
    }

    // frob:tests publish_relations
    #[test]
    fn native_relations_use_sub_issue_and_link_calls() {
        let clock = FakeClock::default();
        let (t, log) = setup(&clock, None);
        let mut w = GithubWriter::new(t, &clock);
        let rel = |kind, h: &str| Relation {
            kind,
            ulid: format!("U{h}"),
            handle: h.into(),
        };
        let routing = RelationRouting {
            native: vec![
                rel(RelationKind::Parent, "~P"),
                rel(RelationKind::BlockedBy, "~B"),
            ],
            body_links: vec![rel(RelationKind::Relates, "~R")],
        };
        let ok = w.publish_relations(&IssueRef("5".into()), &routing, |r| {
            Some(IssueRef(r.handle.trim_start_matches('~').to_owned()))
        });
        assert!(ok);
        assert_eq!(ops(&log), ["sub P 5", "link 5 BlockedBy B"]);
    }
}

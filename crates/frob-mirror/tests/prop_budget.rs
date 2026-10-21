//! Property tests for the run budget and starvation freedom (mirror.md 3.7; model README 5, 6.3).
//!
//! A test-local `RunHost` drives the real `run::run` against the fake GitHub with seeded
//! randomness. Sweep writes are counted only against the call bound, because `plan::select`
//! does not treat the sweep as a mutating class.

// frob:ticket 01M4052WNB3X3G61P84VR8VGH2
#![allow(dead_code)]

#[path = "support/fake_github.rs"]
mod fake_github;

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::time::Duration;

use fake_github::{BOT_ID, FakeGithub, HUMAN_ID, Rng};
use frob_mirror::adapter::{AdapterError, CreateOutcome, EventId, IssueRef, TrackerAdapter};
use frob_mirror::budget::{self, BudgetConfig, BudgetError, RateLimit};
use frob_mirror::lock::LOCK_KEY;
use frob_mirror::mapfile::{MapError, Shard, ShardStore, content_hash};
use frob_mirror::plan::{Cursors, WorkClass, WorkItem, select};
use frob_mirror::projection::{
    Category, Classification, Identity, IssueProjection, People, State, TicketFacts, project,
};
use frob_mirror::run::{ItemError, RunConfig, RunHost, RunOutcome, run};

#[derive(Default)]
struct Mem(HashMap<String, Vec<u8>>);

impl ShardStore for Mem {
    fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.0.get(key).cloned()
    }
    fn put_if(&mut self, key: &str, exp: Option<&str>, bytes: Vec<u8>) -> Result<(), MapError> {
        let found = self.get(key).map(|b| content_hash(&b));
        if found.as_deref() != exp {
            return Err(MapError::Conflict {
                key: key.into(),
                expected: exp.map(String::from),
                found,
            });
        }
        self.0.insert(key.into(), bytes);
        Ok(())
    }
}

/// The projection of ticket `ulid` carrying `title`.
fn projection(ulid: &str, title: &str) -> IssueProjection {
    let facts = TicketFacts {
        identity: Identity {
            ulid: ulid.into(),
            handle: format!("~{ulid}"),
            aliases: vec![],
            repository: "https://example.invalid/r".into(),
            ledger_path: format!("tickets/{ulid}.md"),
        },
        title: title.into(),
        summary: "s".into(),
        acceptance: vec![],
        scope: vec![],
        evidence: vec![],
        classification: Classification::default(),
        state: State {
            category: Category::Todo,
            outcome: None,
            reason: None,
        },
        relations: vec![],
        people: People::default(),
        last_event: "01EV".into(),
    };
    project(&facts, &BTreeSet::new(), "test")
}

fn default_title(ulid: &str) -> String {
    format!("title {ulid}")
}

/// Ticket ULIDs `T1..Tn`, sorted.
fn ulids(n: usize) -> Vec<String> {
    (1..=n).map(|i| format!("T{i}")).collect()
}

/// A model host: the ledger side is a title map, the tracker side is the shared fake.
struct ModelHost {
    /// Tracker issue per ticket, once created.
    issues: BTreeMap<String, IssueRef>,
    /// Ledger title per ticket.
    titles: BTreeMap<String, String>,
    /// Title last written to the tracker per ticket.
    written: BTreeMap<String, String>,
    /// Tickets whose issue is yet to be created (the Create class).
    uncreated: Vec<String>,
    /// Rate-limit headers served this run.
    remaining: u64,
    /// Emit Update items for tickets whose written title is stale.
    updates: bool,
    /// Whether a sweep reverts a drifted title.
    sweep_revert: bool,
    /// Per-ticket history cursor.
    history: HashMap<String, Option<EventId>>,
    /// Every non-bot event id the sweep has recorded.
    recorded: HashSet<String>,
    /// Counters reset before each run.
    calls: u64,
    creates: u64,
    mutations: u64,
}

impl ModelHost {
    fn new(tickets: &[String], remaining: u64) -> Self {
        Self {
            issues: BTreeMap::new(),
            titles: tickets
                .iter()
                .map(|t| (t.clone(), default_title(t)))
                .collect(),
            written: BTreeMap::new(),
            uncreated: tickets.to_vec(),
            remaining,
            updates: false,
            sweep_revert: true,
            history: HashMap::new(),
            recorded: HashSet::new(),
            calls: 0,
            creates: 0,
            mutations: 0,
        }
    }

    /// Create the issue of `ulid` directly (setup, outside any run).
    fn precreate(&mut self, fake: &mut FakeGithub, ulid: &str) {
        let title = self.titles[ulid].clone();
        let CreateOutcome::Created(issue) =
            fake.create(&projection(ulid, &title), &format!("n-{ulid}"))
        else {
            panic!("setup create must succeed");
        };
        self.issues.insert(ulid.into(), issue);
        self.written.insert(ulid.into(), title);
        self.uncreated.retain(|t| t != ulid);
    }

    fn reset_counters(&mut self) {
        self.calls = 0;
        self.creates = 0;
        self.mutations = 0;
    }

    fn map_err(e: AdapterError) -> ItemError {
        match e {
            AdapterError::RateLimited => ItemError::RateLimited { reset: None },
            other => ItemError::Failed(other.to_string()),
        }
    }

    fn sweep(&mut self, ulid: &str, adapter: &mut dyn TrackerAdapter) -> Result<(), ItemError> {
        let issue = self.issues[ulid].clone();
        self.calls += 1;
        let state = adapter.read(&issue).map_err(Self::map_err)?;
        self.calls += 1;
        let cursor = self.history.get(ulid).cloned().flatten();
        let entries = adapter
            .history_after(&issue, cursor.as_ref())
            .map_err(Self::map_err)?;
        for e in &entries {
            if e.actor_id != BOT_ID {
                self.recorded.insert(e.event.0.clone());
            }
        }
        if let Some(last) = entries.last() {
            self.history.insert(ulid.into(), Some(last.event.clone()));
        }
        let want = self.titles[ulid].clone();
        if self.sweep_revert && state.title != want {
            self.calls += 1;
            adapter
                .update(&issue, &projection(ulid, &want))
                .map_err(Self::map_err)?;
            self.written.insert(ulid.into(), want);
        }
        Ok(())
    }
}

impl RunHost for ModelHost {
    fn rate_limit(&self) -> RateLimit {
        RateLimit {
            remaining: Some(self.remaining),
            reset: Some(0),
        }
    }

    fn pending<S: ShardStore>(&self, _store: &S) -> Vec<WorkItem> {
        let mut out: Vec<WorkItem> = self
            .uncreated
            .iter()
            .enumerate()
            .map(|(i, t)| WorkItem {
                class: WorkClass::Create,
                age: i as u64,
                ticket: t.clone(),
            })
            .collect();
        if self.updates {
            for (i, (t, w)) in self.written.iter().enumerate() {
                if self.titles[t] != *w {
                    out.push(WorkItem {
                        class: WorkClass::Update,
                        age: i as u64,
                        ticket: t.clone(),
                    });
                }
            }
        }
        out
    }

    fn sweep_universe(&self) -> Vec<String> {
        self.issues.keys().cloned().collect()
    }

    fn execute<S: ShardStore>(
        &mut self,
        item: &WorkItem,
        _store: &mut S,
        adapter: &mut dyn TrackerAdapter,
    ) -> Result<Option<Shard>, ItemError> {
        let ulid = item.ticket.as_str();
        match item.class {
            WorkClass::Create => {
                self.calls += 1;
                self.creates += 1;
                self.mutations += 1;
                let title = self.titles[ulid].clone();
                match adapter.create(&projection(ulid, &title), &format!("n-{ulid}")) {
                    CreateOutcome::Created(issue) => {
                        self.issues.insert(ulid.into(), issue);
                        self.written.insert(ulid.into(), title);
                        self.uncreated.retain(|t| t != ulid);
                    }
                    CreateOutcome::Failed(m) => return Err(ItemError::Failed(m)),
                    CreateOutcome::Unknown => return Err(ItemError::Failed("unknown".into())),
                }
            }
            WorkClass::Update => {
                self.calls += 1;
                self.mutations += 1;
                let title = self.titles[ulid].clone();
                let issue = self.issues[ulid].clone();
                adapter
                    .update(&issue, &projection(ulid, &title))
                    .map_err(Self::map_err)?;
                self.written.insert(ulid.into(), title);
            }
            WorkClass::Sweep => self.sweep(ulid, adapter)?,
            WorkClass::Recovery | WorkClass::Reconcile => {}
        }
        Ok(Some(Shard::new(ulid)))
    }
}

fn config(round: u64) -> RunConfig {
    RunConfig {
        run_id: format!("run-{round}"),
        now: 1_000 + round,
        lock_ttl_secs: 3600,
        commit_every: 2,
        sweep_k: 1,
        bot_id: BOT_ID,
        budget: BudgetConfig {
            share_percent: 100,
            spacing: Duration::ZERO,
            ..BudgetConfig::default()
        },
    }
}

/// Uniform `usize` in `0..n`.
fn below(rng: &mut Rng, n: usize) -> usize {
    usize::try_from(rng.below(u64::try_from(n).expect("fits"))).expect("fits")
}

fn cost(cfg: &RunConfig) -> u64 {
    cfg.budget.reads_per_ticket + 1
}

fn ran(outcome: RunOutcome) -> frob_mirror::run::RunSummary {
    match outcome {
        RunOutcome::Ran(s) => s,
        other => panic!("expected a completed run, got {other:?}"),
    }
}

/// Every ticket completes in every rotation and no human edit is lost (L3, S7).
// frob:tests run
// frob:tests next_batch
#[test]
fn round_robin_completes_every_ticket_under_unbounded_edits() {
    for seed in 0..24u64 {
        let mut rng = Rng::new(seed);
        let n = 2 + below(&mut rng, 4);
        let tickets = ulids(n);
        let mut fake = FakeGithub::new(seed);
        // One ticket's reads plus one write, with 0..2 spare calls (budget 3, 4 or 5).
        let remaining = cost(&config(0)) + rng.below(3);
        let mut host = ModelHost::new(&tickets, remaining);
        for t in &tickets {
            host.precreate(&mut fake, t);
        }
        let mut store = Mem::default();
        let rounds = (n * 8) as u64;
        let mut window: BTreeSet<String> = BTreeSet::new();
        for round in 0..rounds {
            let victim = tickets[below(&mut rng, n)].clone();
            fake.human_edit_title(&host.issues[&victim].clone(), &format!("edit {round}"));
            host.reset_counters();
            let summary = ran(run(&mut store, &mut fake, &mut host, &config(round)).expect("run"));
            for (_, t) in &summary.executed {
                window.insert(t.clone());
                // The executed ticket matches the ledger title again (InfOften).
                let state = fake.read(&host.issues[t]).expect("read");
                assert_eq!(state.title, host.titles[t], "seed {seed} round {round}");
                // No edit lost: every human event on it so far is recorded.
                for e in fake.history_after(&host.issues[t], None).expect("history") {
                    if e.actor_id == HUMAN_ID {
                        assert!(
                            host.recorded.contains(&e.event.0),
                            "seed {seed} round {round}: edit {} lost on {t}",
                            e.event.0
                        );
                    }
                }
            }
            if (round + 1) % n as u64 == 0 {
                assert_eq!(
                    window,
                    tickets.iter().cloned().collect::<BTreeSet<_>>(),
                    "seed {seed}: a ticket missed a rotation ending at round {round}"
                );
                window.clear();
            }
        }
    }
}

/// A budget below one ticket's reads plus one write stops with MIR001 and writes nothing (B3).
// frob:tests run
// frob:tests plan
#[test]
fn budget_below_one_ticket_reports_mir001_and_writes_nothing() {
    let tickets = ulids(2);
    for remaining in 0..=5u64 {
        let mut fake = FakeGithub::new(remaining);
        let mut host = ModelHost::new(&tickets, remaining);
        // share 50% of 0..=5 gives at most 2 calls, below the 3 one ticket needs.
        let mut cfg = config(0);
        cfg.budget.share_percent = 50;
        for t in &tickets {
            host.precreate(&mut fake, t);
        }
        let before = fake.snapshot();
        let mut store = Mem::default();
        let allowed = remaining * 50 / 100;
        assert_eq!(
            budget::plan(host.rate_limit(), &cfg.budget),
            Err(BudgetError::TooSmall {
                allowed,
                needed: cost(&cfg)
            })
        );
        host.reset_counters();
        let out = run(&mut store, &mut fake, &mut host, &cfg).expect("run");
        let RunOutcome::Stopped { mir001 } = out else {
            panic!("expected Stopped, got {out:?}");
        };
        assert!(mir001.contains("MIR001") && mir001.contains("budget-too-small"));
        assert_eq!(host.calls, 0, "no item may execute");
        let after = fake.snapshot();
        assert_eq!(before.issues, after.issues, "no issue may change");
        assert_eq!(before.log, after.log, "no event may be written");
        assert!(
            store.0.keys().all(|k| k == LOCK_KEY),
            "only the lock may be written: {:?}",
            store.0.keys().collect::<Vec<_>>()
        );
    }
}

/// Missing rate-limit headers are also MIR001 and write nothing.
// frob:tests plan
#[test]
fn missing_headers_are_budget_unknown() {
    let limit = RateLimit {
        remaining: None,
        reset: Some(0),
    };
    let err = budget::plan(limit, &BudgetConfig::default()).expect_err("unknown");
    assert!(err.to_string().contains("MIR001"));
}

/// Calls, creates and mutations of a run stay within the plan and the C and M caps.
// frob:tests run
// frob:tests plan
// frob:tests select
#[test]
fn run_stays_within_budget_and_caps() {
    for seed in 0..32u64 {
        let mut rng = Rng::new(1_000 + seed);
        let n = 3 + below(&mut rng, 6);
        let tickets = ulids(n);
        let existing = below(&mut rng, n / 2 + 1);
        let mut fake = FakeGithub::new(seed);
        let remaining = cost(&config(0)) + rng.below(30);
        let mut host = ModelHost::new(&tickets, remaining);
        host.updates = true;
        host.sweep_revert = false;
        for t in tickets.iter().take(existing) {
            host.precreate(&mut fake, t);
        }
        let mut cfg = config(0);
        cfg.budget.max_creates = 1 + rng.below(3);
        cfg.budget.max_mutations = 1 + rng.below(4);
        let mut store = Mem::default();
        let rounds = 8 * n as u64;
        for round in 0..rounds {
            // The ledger keeps changing for the first half, then settles.
            if round < rounds / 2 {
                let t = &tickets[below(&mut rng, n)];
                host.titles.insert(t.clone(), format!("ledger {round}"));
            }
            cfg.run_id = format!("run-{round}");
            cfg.now = 1_000 + round;
            let plan = budget::plan(host.rate_limit(), &cfg.budget).expect("plan");
            host.reset_counters();
            ran(run(&mut store, &mut fake, &mut host, &cfg).expect("run"));
            assert!(host.calls <= plan.calls, "seed {seed} round {round}: calls");
            assert!(host.creates <= plan.creates && plan.creates <= cfg.budget.max_creates);
            assert!(host.mutations <= plan.mutations && plan.mutations <= cfg.budget.max_mutations);
        }
        assert!(host.uncreated.is_empty(), "seed {seed}: creates starved");
        for (t, title) in &host.titles {
            assert_eq!(host.written[t], *title, "seed {seed}: {t} never converged");
        }
    }
}

/// Fixed order starves the second ticket; round robin serves both (F8, the `MC_Race` fixed-order case).
// frob:tests select
#[test]
fn fixed_order_starves_but_round_robin_does_not() {
    let item = |t: &str| WorkItem {
        class: WorkClass::Update,
        age: 0,
        ticket: t.into(),
    };
    let plan = budget::Plan {
        calls: 3,
        creates: 50,
        mutations: 300,
        spacing: Duration::ZERO,
    };
    let pending = || vec![item("T1"), item("T2")];

    // Expected failure: a fresh cursor every round keeps choosing T1.
    let mut served_fixed = BTreeSet::new();
    for _ in 0..20 {
        for i in select(pending(), &Cursors::default(), &plan, 3) {
            served_fixed.insert(i.ticket);
        }
    }
    assert_eq!(served_fixed, BTreeSet::from(["T1".to_string()]));

    // Round robin: the cursor persists, so each ticket is served every two rounds.
    let mut cursors = Cursors::default();
    let mut served = Vec::new();
    for _ in 0..20 {
        for i in select(pending(), &cursors, &plan, 3) {
            cursors.complete(&i);
            served.push(i.ticket);
        }
    }
    for pair in served.chunks(2) {
        let set: BTreeSet<_> = pair.iter().cloned().collect();
        assert_eq!(set.len(), 2, "a rotation missed a ticket: {pair:?}");
    }
}

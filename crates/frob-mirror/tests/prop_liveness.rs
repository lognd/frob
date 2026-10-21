//! Property tests for convergence and no loss (mirror.md 3.7; model README 5, L1 and L2, F1).
//!
//! A test-local `RunHost` drives the real `run::run` against the fake GitHub. Human edits,
//! ledger commits and faults are finite and happen first; runs then repeat on their own.

// frob:ticket 01M4052WHPPDKMCBA9Y1BM06W5
#![allow(dead_code)]

#[path = "support/fake_github.rs"]
mod fake_github;

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::time::Duration;

use fake_github::{BOT_ID, CrashPoint, FakeGithub, HUMAN_ID, Rng};
use frob_mirror::adapter::{AdapterError, CreateOutcome, EventId, IssueRef, TrackerAdapter};
use frob_mirror::budget::{BudgetConfig, RateLimit};
use frob_mirror::mapfile::{MapError, Shard, ShardStore, content_hash};
use frob_mirror::plan::{WorkClass, WorkItem};
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

/// A model host: the ledger side is a title map, the tracker side is the shared fake.
struct ModelHost {
    /// Tracker issue per ticket, once created.
    issues: BTreeMap<String, IssueRef>,
    /// Ledger title per ticket.
    titles: BTreeMap<String, String>,
    /// Title last written to the tracker per ticket.
    written: BTreeMap<String, String>,
    /// Tickets whose issue is yet to be created.
    uncreated: Vec<String>,
    /// Rate-limit headers served each run.
    remaining: u64,
    /// Per-ticket history cursor.
    history: HashMap<String, Option<EventId>>,
    /// Every non-bot event id the sweep has recorded.
    recorded: HashSet<String>,
}

impl ModelHost {
    fn new(tickets: &[String], remaining: u64) -> Self {
        Self {
            issues: BTreeMap::new(),
            titles: tickets
                .iter()
                .map(|t| (t.clone(), format!("title {t}")))
                .collect(),
            written: BTreeMap::new(),
            uncreated: tickets.to_vec(),
            remaining,
            history: HashMap::new(),
            recorded: HashSet::new(),
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

    fn map_err(e: AdapterError) -> ItemError {
        match e {
            AdapterError::RateLimited => ItemError::RateLimited { reset: None },
            other => ItemError::Failed(other.to_string()),
        }
    }

    /// Read, record new human events, and revert a drifted title.
    fn sweep(&mut self, ulid: &str, adapter: &mut dyn TrackerAdapter) -> Result<(), ItemError> {
        let issue = self.issues[ulid].clone();
        let state = adapter.read(&issue).map_err(Self::map_err)?;
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
        if state.title != want {
            adapter
                .update(&issue, &projection(ulid, &want))
                .map_err(Self::map_err)?;
            self.written.insert(ulid.into(), want);
        }
        Ok(())
    }

    /// Whether every ticket has an issue whose tracker title equals the ledger.
    fn converged(&self, fake: &FakeGithub) -> bool {
        self.uncreated.is_empty()
            && self
                .issues
                .iter()
                .all(|(t, i)| fake.read(i).is_ok_and(|s| s.title == self.titles[t]))
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
        for (i, (t, w)) in self.written.iter().enumerate() {
            if self.titles[t] != *w {
                out.push(WorkItem {
                    class: WorkClass::Update,
                    age: i as u64,
                    ticket: t.clone(),
                });
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
        let title = self.titles[ulid].clone();
        match item.class {
            WorkClass::Create => {
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

/// Run once and demand a completed run (the budget always covers one ticket, no fault pending).
fn step(store: &mut Mem, fake: &mut FakeGithub, host: &mut ModelHost, round: u64) {
    match run(store, fake, host, &config(round)).expect("run") {
        RunOutcome::Ran(_) => {}
        other => panic!("expected a completed run, got {other:?}"),
    }
}

/// Run once while faults may be live: a crash in the blindness checks stops the run (MIR001).
fn noisy_step(store: &mut Mem, fake: &mut FakeGithub, host: &mut ModelHost, round: u64) {
    match run(store, fake, host, &config(round)).expect("run") {
        RunOutcome::Ran(_) => {}
        RunOutcome::Stopped { mir001 } => assert!(mir001.contains("MIR001"), "{mir001}"),
        other @ RunOutcome::Busy { .. } => panic!("unexpected outcome {other:?}"),
    }
}

/// A finished scenario: the fake, the host and the store after the quiet phase.
struct Outcome {
    fake: FakeGithub,
    host: ModelHost,
    store: Mem,
    /// Rounds run so far.
    round: u64,
    tickets: Vec<String>,
}

/// Finite human edits, ledger commits and faults, then enough quiet runs to settle.
fn scenario(seed: u64) -> Outcome {
    let mut rng = Rng::new(seed);
    let n = 1 + below(&mut rng, 4);
    let tickets: Vec<String> = (1..=n).map(|i| format!("T{i}")).collect();
    let mut fake = FakeGithub::new(seed);
    // One ticket's reads plus one write, with 0..2 spare calls.
    let cost = config(0).budget.reads_per_ticket + 1;
    let mut host = ModelHost::new(&tickets, cost + rng.below(3));
    let existing = below(&mut rng, n + 1);
    for t in tickets.iter().take(existing) {
        host.precreate(&mut fake, t);
    }
    let mut store = Mem::default();
    let noisy = 4 + below(&mut rng, 8) as u64;
    for round in 0..noisy {
        let t = tickets[below(&mut rng, n)].clone();
        match rng.below(6) {
            0 | 1 => {
                if let Some(i) = host.issues.get(&t) {
                    fake.human_edit_title(&i.clone(), &format!("edit {round}"));
                }
            }
            2 => {
                if let Some(i) = host.issues.get(&t) {
                    fake.human_add_label(&i.clone(), &format!("l{round}"));
                }
            }
            3 => {
                host.titles.insert(t, format!("ledger {round}"));
            }
            4 => fake.lose_next_create(),
            _ => {
                let point = if rng.below(2) == 0 {
                    CrashPoint::Before
                } else {
                    CrashPoint::After
                };
                fake.crash_at(fake.calls() + 1 + rng.below(10), point);
            }
        }
        noisy_step(&mut store, &mut fake, &mut host, round);
    }
    // Quiet phase: no edits, no faults, runs only. A pending fault is spent first.
    let quiet = 12 * n as u64 + 12;
    for round in noisy..noisy + 6 {
        noisy_step(&mut store, &mut fake, &mut host, round);
    }
    for round in noisy + 6..noisy + quiet {
        step(&mut store, &mut fake, &mut host, round);
    }
    Outcome {
        fake,
        host,
        store,
        round: noisy + quiet,
        tickets,
    }
}

/// Every repository-owned field eventually equals the ledger and stays so (L1).
// frob:tests run
#[test]
fn finite_edits_and_faults_converge_and_stay_converged() {
    for seed in 0..40u64 {
        let mut o = scenario(seed);
        assert!(o.host.converged(&o.fake), "seed {seed}: never converged");
        for extra in 0..o.tickets.len() as u64 * 2 {
            step(&mut o.store, &mut o.fake, &mut o.host, o.round + extra);
            assert!(o.host.converged(&o.fake), "seed {seed}: left convergence");
        }
    }
}

/// A human edit with no further ledger push is reverted and recorded by scheduled runs alone (F1).
// frob:tests run
#[test]
fn scheduled_runs_alone_revert_and_record_a_human_edit() {
    for seed in 0..24u64 {
        let mut rng = Rng::new(500 + seed);
        let n = 1 + below(&mut rng, 4);
        let tickets: Vec<String> = (1..=n).map(|i| format!("T{i}")).collect();
        let mut fake = FakeGithub::new(seed);
        let cost = config(0).budget.reads_per_ticket + 1;
        let mut host = ModelHost::new(&tickets, cost + rng.below(3));
        for t in &tickets {
            host.precreate(&mut fake, t);
        }
        let mut store = Mem::default();
        // A first rotation records nothing and changes nothing.
        for round in 0..n as u64 {
            step(&mut store, &mut fake, &mut host, round);
        }
        let victim = tickets[below(&mut rng, n)].clone();
        fake.human_edit_title(&host.issues[&victim].clone(), "hand edit");
        assert!(
            !host.converged(&fake),
            "setup: the edit must drift the title"
        );
        // No push: titles are untouched. One rotation of scheduled runs suffices.
        for round in 0..n as u64 {
            step(&mut store, &mut fake, &mut host, 100 + round);
        }
        assert!(host.converged(&fake), "seed {seed}: edit not reverted");
        let human: Vec<_> = fake
            .history_after(&host.issues[&victim], None)
            .expect("history")
            .into_iter()
            .filter(|e| e.actor_id == HUMAN_ID)
            .collect();
        assert_eq!(human.len(), 1);
        assert!(
            host.recorded.contains(&human[0].event.0),
            "seed {seed}: not recorded"
        );
    }
}

/// Every human edit within retained history ends up recorded (L2).
// frob:tests run
#[test]
fn every_human_edit_is_recorded_once_runs_finish() {
    for seed in 100..140u64 {
        let o = scenario(seed);
        for (t, issue) in &o.host.issues {
            for e in o.fake.history_after(issue, None).expect("history") {
                if e.actor_id != BOT_ID {
                    assert!(
                        o.host.recorded.contains(&e.event.0),
                        "seed {seed}: edit {} on {t} lost",
                        e.event.0
                    );
                }
            }
        }
    }
}

/// A lost or crashed create under the minimum budget still converges with no edit lost.
// frob:tests run
#[test]
fn lost_creates_at_minimum_budget_still_converge() {
    for seed in 0..24u64 {
        let tickets: Vec<String> = (1..=3).map(|i| format!("T{i}")).collect();
        let mut fake = FakeGithub::new(seed);
        let cost = config(0).budget.reads_per_ticket + 1;
        let mut host = ModelHost::new(&tickets, cost);
        let mut store = Mem::default();
        let mut rng = Rng::new(900 + seed);
        for round in 0..4u64 {
            if rng.below(2) == 0 {
                fake.lose_next_create();
            } else {
                fake.crash_at(fake.calls() + 1, CrashPoint::After);
            }
            noisy_step(&mut store, &mut fake, &mut host, round);
        }
        // A crash scheduled further out may still be pending: let it spend itself.
        for round in 4..10u64 {
            noisy_step(&mut store, &mut fake, &mut host, round);
        }
        for round in 10..70u64 {
            step(&mut store, &mut fake, &mut host, round);
        }
        assert!(host.converged(&fake), "seed {seed}: never converged");
    }
}

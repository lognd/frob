//! Integration tests: milestones and cycles against temporary git repositories.
// frob:ticket 01M4069QWSJEH5KW8K0YR8CA0D

use std::path::Path;
use std::process::Command;

use frob_ledger::event::EvidenceData;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use frob_pm::event::Op;
use frob_pm::{Day, NewObject, Object, ObjectKind, PmStore, State, fold, merge};
use gob_git::{CommitOptions, RelPath, Repo};

const MAIN: &str = "refs/heads/main";

fn open(dir: &Path, ref_name: &str) -> Ledger {
    let repo = Repo::discover(dir).expect("discover");
    Ledger::open(
        repo,
        LedgerConfig {
            ref_name: ref_name.to_owned(),
            ..LedgerConfig::default()
        },
        std::sync::Arc::new(gob_time::SystemClock),
    )
}

/// A repository on `main` with a root commit, an identity and an open ledger.
fn fixture() -> (tempfile::TempDir, Ledger) {
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = Repo::init(dir.path()).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir.path()).expect("discover");
    repo.commit_paths(
        MAIN,
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hello\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    drop(repo);
    let ledger = open(dir.path(), MAIN);
    (dir, ledger)
}

fn day(s: &str) -> Day {
    s.parse().expect("day")
}

fn milestone(version: &str, criteria: &[&str]) -> NewObject {
    NewObject::Milestone {
        version: version.to_owned(),
        goal: "ship it".to_owned(),
        target: Some(day("2026-11-01")),
        criteria: criteria.iter().map(|c| (*c).to_owned()).collect(),
    }
}

fn ticket(ledger: &Ledger, title: &str) -> TicketId {
    ledger
        .new_ticket(NewTicket::new(title, TicketType::Task))
        .expect("ticket")
        .ticket
        .front
        .id
}

fn evidence(reference: &str, accepts: &[usize], passed: bool) -> EvidenceData {
    EvidenceData {
        accepts: accepts.to_vec(),
        record: format!(
            "provider = \"command\"\nref = \"{reference}\"\nstatus = \"measured\"\npassed = {passed}\n"
        )
        .parse()
        .expect("table"),
    }
}

fn as_milestone(o: &Object) -> &frob_pm::Milestone {
    match o {
        Object::Milestone(m) => m,
        Object::Cycle(_) => panic!("expected a milestone"),
    }
}

/// Acceptance 1 of ~YR8CA0D: re-folding from events gives the written state.
#[test]
fn fold_from_events_equals_the_written_state() {
    let (dir, ledger) = fixture();
    let t = ticket(&ledger, "An epic");
    let tickets_before = ledger.show(t).expect("show").ticket;
    let pm = PmStore::new(&ledger);
    let made = pm
        .create(milestone("0.532.0", &["installs", "two repos"]))
        .expect("create");
    let id = made.object.id();
    pm.set_field(ObjectKind::Milestone, id, "goal", Some("ship 0.532".into()))
        .expect("goal");
    pm.set_member(ObjectKind::Milestone, id, t, Op::Add)
        .expect("member");
    pm.transition(ObjectKind::Milestone, id, State::Released, None)
        .expect("transition");
    let cyc = pm
        .create(NewObject::Cycle {
            start: day("2026-10-05"),
            end: day("2026-10-18"),
            goal: "land pm".into(),
            capacity_points: Some(20),
        })
        .expect("cycle");
    pm.set_member(ObjectKind::Cycle, cyc.object.id(), t, Op::Add)
        .expect("cycle member");

    // A fresh store over a re-opened ledger folds the same state the files hold.
    let again = open(dir.path(), MAIN);
    let pm2 = PmStore::new(&again);
    let tip = again.tip_hex().expect("tip").expect("some");
    for kind in ObjectKind::ALL {
        for oid in pm2.ids_at(&tip, kind).expect("ids") {
            let events = pm2.read_events_at(&tip, kind, oid).expect("events");
            let folded = fold::fold(kind, oid, &events).expect("fold");
            let stored = pm2
                .read_stored_at(&tip, kind, oid)
                .expect("stored")
                .expect("file");
            assert_eq!(folded.object, stored, "{kind} {oid}");
            assert!(folded.conflicts.is_empty());
        }
    }
    let m = pm2
        .resolve(ObjectKind::Milestone, "0.532.0")
        .expect("by version");
    let m = as_milestone(&m);
    assert_eq!(m.goal, "ship 0.532");
    assert_eq!(m.state, State::Released);
    assert_eq!(m.epics, vec![t]);
    assert_eq!(m.criteria.len(), 2);
    assert_eq!(made.object.id(), m.id);
    let c = pm2
        .resolve(ObjectKind::Cycle, "2026-10-05..2026-10-18")
        .expect("by dates");
    assert_eq!(c.members(), &[t]);
    assert!(pm2.resolve(ObjectKind::Milestone, &id.handle()).is_ok());
    assert!(pm2.doctor(false).expect("doctor").is_clean());
    // The ticket ledger is untouched: same ticket, clean doctor, one ticket.
    assert_eq!(again.show(t).expect("show").ticket, tickets_before);
    assert!(again.doctor(false).expect("ticket doctor").is_clean());
    assert_eq!(again.ticket_ids_at(&tip).expect("ids"), vec![t]);
}

fn git(dir: &Path, args: &[&str]) -> std::process::Output {
    Command::new("git")
        .args(["-c", "user.name=T", "-c", "user.email=t@example.com"])
        .args(args)
        .current_dir(dir)
        .output()
        .expect("git runs")
}

/// Acceptance 2 of ~YR8CA0D: concurrent edits on two branches merge with no event lost.
#[test]
fn concurrent_edits_on_two_branches_merge_without_losing_an_event() {
    let (dir, ledger) = fixture();
    let t = ticket(&ledger, "An epic");
    let id = PmStore::new(&ledger)
        .create(milestone("0.532.0", &["a"]))
        .expect("create")
        .object
        .id();
    let base = ledger.repo().rev_parse(MAIN).expect("main");
    let git_dir = ledger.repo().git_dir().to_path_buf();
    for b in ["a", "b"] {
        std::fs::write(git_dir.join(format!("refs/heads/{b}")), format!("{base}\n"))
            .expect("branch");
    }
    let (la, lb) = (
        open(dir.path(), "refs/heads/a"),
        open(dir.path(), "refs/heads/b"),
    );
    let ea = PmStore::new(&la)
        .set_field(
            ObjectKind::Milestone,
            id,
            "goal",
            Some("goal from a".into()),
        )
        .expect("a edit");
    let sb = PmStore::new(&lb);
    let eb1 = sb
        .set_member(ObjectKind::Milestone, id, t, Op::Add)
        .expect("b member")
        .expect("written");
    let eb2 = sb.add_criterion(id, "from b").expect("b criterion");

    assert!(git(dir.path(), &["checkout", "-q", "a"]).status.success());
    let merged = git(dir.path(), &["merge", "--no-commit", "--no-ff", "b"]);
    let rel = format!("tickets/_milestones/{id}/milestone.md");
    // Only the cached frontmatter can conflict; the pm merge re-folds it from the union of events.
    let ours = dir.path().join(&rel);
    let report = merge::resolve(dir.path(), &rel, &ours).expect("resolve");
    assert!(git(dir.path(), &["add", "-A"]).status.success());
    let commit = git(dir.path(), &["commit", "-q", "--no-edit"]);
    assert!(commit.status.success(), "{merged:?} {commit:?}");

    let after = open(dir.path(), "refs/heads/a");
    let pm = PmStore::new(&after);
    let tip = after.tip_hex().expect("tip").expect("some");
    let events = pm
        .read_events_at(&tip, ObjectKind::Milestone, id)
        .expect("events");
    assert_eq!(
        events.len(),
        1 + ea.events.len() + eb1.events.len() + eb2.events.len()
    );
    assert_eq!(report.events, events.len());
    for e in ea.events.iter().chain(&eb1.events).chain(&eb2.events) {
        assert!(events.iter().any(|x| x.id == *e), "event {e} lost");
    }
    let m = pm
        .get(ObjectKind::Milestone, id)
        .expect("get")
        .expect("some");
    let m = as_milestone(&m.object);
    assert_eq!(m.goal, "goal from a");
    assert_eq!(m.epics, vec![t]);
    assert_eq!(m.criteria.len(), 2);
    assert!(pm.doctor(false).expect("doctor").is_clean());
}

#[test]
fn membership_is_an_event_on_the_object_and_idempotent() {
    let (_dir, ledger) = fixture();
    let (t1, t2) = (ticket(&ledger, "one"), ticket(&ledger, "two"));
    let pm = PmStore::new(&ledger);
    let id = pm
        .create(milestone("0.1.0", &[]))
        .expect("create")
        .object
        .id();
    let k = ObjectKind::Milestone;
    assert!(pm.set_member(k, id, t2, Op::Add).expect("add").is_some());
    assert!(pm.set_member(k, id, t1, Op::Add).expect("add").is_some());
    assert!(pm.set_member(k, id, t1, Op::Add).expect("again").is_none());
    let m = pm.get(k, id).expect("get").expect("some");
    let mut want = vec![t1, t2];
    want.sort();
    assert_eq!(m.object.members(), want.as_slice());
    assert!(pm.set_member(k, id, t1, Op::Remove).expect("rm").is_some());
    assert!(
        pm.set_member(k, id, t1, Op::Remove)
            .expect("rm again")
            .is_none()
    );
    let m = pm.get(k, id).expect("get").expect("some");
    assert_eq!(m.object.members(), &[t2]);
    // Moving a ticket between cycles is one append on each cycle and nothing on the ticket.
    let before = ledger.show(t2).expect("show").ticket;
    let mk = |s: &str, e: &str| NewObject::Cycle {
        start: day(s),
        end: day(e),
        goal: "g".into(),
        capacity_points: None,
    };
    let c1 = pm
        .create(mk("2026-10-05", "2026-10-18"))
        .expect("c1")
        .object
        .id();
    let c2 = pm
        .create(mk("2026-10-19", "2026-11-01"))
        .expect("c2")
        .object
        .id();
    pm.set_member(ObjectKind::Cycle, c1, t2, Op::Add)
        .expect("in c1");
    pm.set_member(ObjectKind::Cycle, c1, t2, Op::Remove)
        .expect("out c1");
    pm.set_member(ObjectKind::Cycle, c2, t2, Op::Add)
        .expect("in c2");
    assert_eq!(ledger.show(t2).expect("show").ticket, before);
    assert!(
        pm.get(ObjectKind::Cycle, c1)
            .expect("c1")
            .expect("some")
            .object
            .members()
            .is_empty()
    );
    assert_eq!(
        pm.get(ObjectKind::Cycle, c2)
            .expect("c2")
            .expect("some")
            .object
            .members(),
        &[t2]
    );
}

#[test]
fn criteria_bind_through_measured_passing_evidence_and_remap() {
    let (_dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    let id = pm
        .create(milestone("0.532.0", &["one", "two", "three"]))
        .expect("create")
        .object
        .id();
    let bound = |pm: &PmStore<'_>| -> Vec<(String, bool)> {
        let o = pm
            .get(ObjectKind::Milestone, id)
            .expect("get")
            .expect("some")
            .object;
        as_milestone(&o)
            .criteria
            .iter()
            .map(|c| (c.text.clone(), c.bound))
            .collect()
    };
    pm.add_evidence(id, evidence("cargo test", &[2, 3], true))
        .expect("ev");
    assert_eq!(
        bound(&pm),
        vec![
            ("one".into(), false),
            ("two".into(), true),
            ("three".into(), true)
        ]
    );
    // Removing criterion 1 renumbers: the evidence follows its criteria.
    pm.remove_criterion(id, 1).expect("rm 1");
    assert_eq!(
        bound(&pm),
        vec![("two".into(), true), ("three".into(), true)]
    );
    // Removing a bound criterion leaves its evidence counting for nothing.
    pm.remove_criterion(id, 2).expect("rm three");
    assert_eq!(bound(&pm), vec![("two".into(), true)]);
    // A later failing run of the same provider and ref supersedes the pass.
    pm.add_evidence(id, evidence("cargo test", &[1], false))
        .expect("fail");
    assert_eq!(bound(&pm), vec![("two".into(), false)]);
    // Unmeasured records never bind.
    let mut unmeasured = evidence("other", &[1], true);
    unmeasured.record.insert("status".into(), "pending".into());
    pm.add_evidence(id, unmeasured).expect("pending");
    assert_eq!(bound(&pm), vec![("two".into(), false)]);
    pm.add_evidence(id, evidence("cargo test", &[1], true))
        .expect("pass again");
    assert_eq!(bound(&pm), vec![("two".into(), true)]);
    assert!(
        pm.remove_criterion(id, 9).is_err(),
        "a criterion that does not exist is refused"
    );
    assert!(pm.doctor(false).expect("doctor").is_clean());
}

#[test]
fn doctor_reports_malformed_drifting_and_dangling_objects() {
    let (_dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    let good = pm
        .create(milestone("0.1.0", &[]))
        .expect("create")
        .object
        .id();
    assert!(pm.doctor(false).expect("clean").is_clean());

    let put = |path: String, text: &str| {
        ledger
            .commit_files("test: corrupt", &[(path, Some(text.as_bytes().to_vec()))])
            .expect("commit");
    };
    // A milestone directory whose only event is garbage, and a non-ULID directory.
    let bad = frob_pm::ObjectId::mint();
    put(
        format!("tickets/_milestones/{bad}/milestone.md"),
        "not a document",
    );
    put(
        format!(
            "tickets/_milestones/{bad}/events/{}.toml",
            frob_ledger::EventId::mint()
        ),
        "kind = \n",
    );
    put(
        "tickets/_milestones/not-a-ulid/milestone.md".into(),
        "+++\n+++\n",
    );
    // Drift: a hand-edited frontmatter.
    let tip = ledger.tip_hex().expect("tip").expect("some");
    let Some(Object::Milestone(mut m)) = pm
        .read_stored_at(&tip, ObjectKind::Milestone, good)
        .expect("stored")
    else {
        panic!("milestone")
    };
    m.goal = "tampered".into();
    put(
        format!("tickets/_milestones/{good}/milestone.md"),
        &Object::Milestone(m).render().expect("render"),
    );
    // A member that is not a ticket.
    pm.set_member(ObjectKind::Milestone, good, TicketId::mint(), Op::Add)
        .expect("dangling");

    let report = pm.doctor(false).expect("doctor");
    let codes: Vec<&str> = report.issues.iter().map(|i| i.code).collect();
    for want in ["E-PM-UNREADABLE", "E-PM-ID", "E-PM-MEMBER"] {
        assert!(codes.contains(&want), "{want} missing from {codes:?}");
    }
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.subject == bad.to_string() && i.code == "E-PM-UNREADABLE")
    );
    // set_member re-folded the frontmatter, repairing the tamper; tamper again to see drift.
    let tip = ledger.tip_hex().expect("tip").expect("some");
    let Some(Object::Milestone(mut m)) = pm
        .read_stored_at(&tip, ObjectKind::Milestone, good)
        .expect("stored")
    else {
        panic!("milestone")
    };
    m.goal = "tampered again".into();
    put(
        format!("tickets/_milestones/{good}/milestone.md"),
        &Object::Milestone(m).render().expect("render"),
    );
    let report = pm.doctor(false).expect("doctor");
    assert!(report.issues.iter().any(|i| i.code == "E-PM-DRIFT"));
    let fixed = pm.doctor(true).expect("fix");
    assert_eq!(fixed.fixed, vec![good]);
    assert!(
        !pm.doctor(false)
            .expect("after")
            .issues
            .iter()
            .any(|i| i.code == "E-PM-DRIFT")
    );
    // The ticket doctor never sees any of this.
    assert!(ledger.doctor(false).expect("ticket doctor").is_clean());
}

#[test]
fn creation_rules_and_unscheduled_milestones() {
    let (_dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    let unscheduled = pm
        .create(NewObject::Milestone {
            version: "0.9.0".into(),
            goal: "later".into(),
            target: None,
            criteria: vec![],
        })
        .expect("create");
    assert_eq!(as_milestone(&unscheduled.object).target, None);
    assert!(
        pm.create(milestone("0.9.0", &[])).is_err(),
        "duplicate version"
    );
    let backwards = NewObject::Cycle {
        start: day("2026-10-18"),
        end: day("2026-10-05"),
        goal: "g".into(),
        capacity_points: None,
    };
    assert!(pm.create(backwards).is_err(), "end before start");
    let id = unscheduled.object.id();
    pm.set_field(
        ObjectKind::Milestone,
        id,
        "target",
        Some("2026-12-01".into()),
    )
    .expect("schedule");
    pm.set_field(ObjectKind::Milestone, id, "target", None)
        .expect("unschedule");
    assert_eq!(
        as_milestone(
            &pm.get(ObjectKind::Milestone, id)
                .expect("get")
                .expect("some")
                .object
        )
        .target,
        None
    );
    assert!(
        pm.transition(ObjectKind::Milestone, id, State::Closed, None)
            .is_err(),
        "closed is not a milestone state"
    );
    assert!(
        pm.set_field(ObjectKind::Milestone, id, "nonsense", Some("x".into()))
            .is_err()
    );
}

#[test]
fn spellings_ordering_and_store_accessors() {
    let (_dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    assert_eq!(pm.ledger().config().dir, "tickets");
    assert_eq!(ObjectKind::Milestone.as_str(), "milestone");
    assert_eq!(State::Released.as_str(), "released");
    let id = pm
        .create(milestone("0.1.0", &[]))
        .expect("create")
        .object
        .id();
    let tip = ledger.tip_hex().expect("tip").expect("some");
    let events = pm
        .read_events_at(&tip, ObjectKind::Milestone, id)
        .expect("events");
    assert!(
        events
            .windows(2)
            .all(|w| w[0].order_key() <= w[1].order_key())
    );
}

// frob:ticket 01M4069RACAQ8Z2C8APK0YKGNK
#[test]
fn bindings_name_the_deciding_event_and_removal_records_the_moved_map() {
    // frob:tests crates/frob-pm/src/milestone/criteria.rs::bindings
    let (_dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    let id = pm
        .create(milestone("0.532.0", &["a", "b", "c"]))
        .expect("create")
        .object
        .id();
    let first = pm
        .add_evidence(id, evidence("t", &[3], false))
        .expect("fail")
        .events[0];
    assert!(
        pm.criterion_bindings(id, 3).expect("b")[2].is_empty(),
        "a failing record binds nothing"
    );
    let second = pm
        .add_evidence(id, evidence("t", &[3], true))
        .expect("pass")
        .events[0];
    let b = pm.criterion_bindings(id, 3).expect("b");
    assert_eq!(b[2].len(), 1);
    assert_eq!(b[2][0].event, second);
    assert_ne!(b[2][0].event, first);
    pm.remove_criterion(id, 2).expect("rm");
    let b = pm.criterion_bindings(id, 2).expect("b");
    assert_eq!(b[1][0].event, second, "c is now criterion 2");
    let events = pm.evidence_events(id).expect("events");
    assert_eq!(events.len(), 2);
    let tip = ledger.tip_hex().expect("tip").expect("some");
    let moved = pm
        .read_events_at(&tip, ObjectKind::Milestone, id)
        .expect("read")
        .into_iter()
        .find_map(|e| match e.body {
            frob_pm::event::PmBody::Criterion(c) => c.moved,
            _ => None,
        });
    assert_eq!(moved, Some(vec![1, 0, 2]));
}

/// Events of a cycle `2026-10-03..2026-10-09` created that morning, then one `transition` body at 13:32.
fn cycle_events(transition: &str) -> Vec<frob_pm::event::PmEvent> {
    use frob_pm::event::PmEvent;
    let create = "kind = \"create\"\nobject = \"cycle\"\ngoal = \"g\"\nstart = \"2026-10-03\"\nend = \"2026-10-09\"\nat = \"2026-10-03T11:34:47Z\"\nactor = \"a\"\nrev = 1\n";
    let close = format!(
        "kind = \"transition\"\n{transition}at = \"2026-10-03T13:32:45Z\"\nactor = \"a\"\nrev = 1\n"
    );
    vec![
        PmEvent::parse("01M40RQ5772BQBYHSPJY7Z8QK0".parse().expect("id"), create).expect("create"),
        PmEvent::parse("01M40ZF55YA2ZS64T1AKXSSZ42".parse().expect("id"), &close).expect("close"),
    ]
}

#[test]
fn a_legacy_close_recorded_from_planned_on_a_started_day_folds_cleanly() {
    // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
    // frob:tests crates/frob-pm/src/fold.rs::apply_transition
    let id = "01M40RQ5772BQBYHSPJY7Z8QJZ".parse().expect("id");
    let legacy = cycle_events("from = \"planned\"\nto = \"closed\"\nended = \"2026-10-03\"\n");
    let folded = fold::fold(ObjectKind::Cycle, id, &legacy).expect("fold");
    assert!(folded.conflicts.is_empty(), "{:?}", folded.conflicts);
    let current = cycle_events("from = \"active\"\nto = \"closed\"\n");
    assert!(
        fold::fold(ObjectKind::Cycle, id, &current)
            .expect("fold")
            .conflicts
            .is_empty()
    );
}

#[test]
fn a_genuinely_wrong_from_is_still_a_conflict() {
    // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
    // frob:tests crates/frob-pm/src/fold.rs::apply_transition
    let id = "01M40RQ5772BQBYHSPJY7Z8QJZ".parse().expect("id");
    let wrong = cycle_events("from = \"closed\"\nto = \"closed\"\n");
    let folded = fold::fold(ObjectKind::Cycle, id, &wrong).expect("fold");
    assert_eq!(folded.conflicts.len(), 1);
    // `planned` is tolerated only while the cycle is still open: a second close from planned conflicts.
    let mut twice = cycle_events("from = \"planned\"\nto = \"closed\"\n");
    let again = "kind = \"transition\"\nfrom = \"planned\"\nto = \"closed\"\nat = \"2026-10-03T14:00:00Z\"\nactor = \"a\"\nrev = 1\n";
    twice.push(
        frob_pm::event::PmEvent::parse("01M40ZF55YA2ZS64T1AKXSSZ43".parse().expect("id"), again)
            .expect("again"),
    );
    assert_eq!(
        fold::fold(ObjectKind::Cycle, id, &twice)
            .expect("fold")
            .conflicts
            .len(),
        1
    );
}

/// Counts tracing events whose message is `events walked once`, the one-batch read of `events_many`.
struct BatchCounter(std::sync::Arc<std::sync::atomic::AtomicUsize>);

struct MessageProbe(bool);

impl tracing::field::Visit for MessageProbe {
    fn record_debug(&mut self, field: &tracing::field::Field, value: &dyn std::fmt::Debug) {
        if field.name() == "message" && format!("{value:?}") == "events walked once" {
            self.0 = true;
        }
    }
}

impl tracing::Subscriber for BatchCounter {
    fn enabled(&self, _: &tracing::Metadata<'_>) -> bool {
        true
    }
    fn new_span(&self, _: &tracing::span::Attributes<'_>) -> tracing::span::Id {
        tracing::span::Id::from_u64(1)
    }
    fn record(&self, _: &tracing::span::Id, _: &tracing::span::Record<'_>) {}
    fn record_follows_from(&self, _: &tracing::span::Id, _: &tracing::span::Id) {}
    fn event(&self, event: &tracing::Event<'_>) {
        let mut probe = MessageProbe(false);
        event.record(&mut probe);
        if probe.0 {
            self.0.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        }
    }
    fn enter(&self, _: &tracing::span::Id) {}
    fn exit(&self, _: &tracing::span::Id) {}
}

// frob:ticket 01M4D6NB00MBEV0PRHN15CXZP8
// frob:tests crates/frob-pm/src/cycle/velocity.rs::done_facts
#[test]
fn done_facts_reads_every_tickets_events_in_one_batch() {
    let (_dir, ledger) = fixture();
    for n in 0..4 {
        let id = ticket(&ledger, &format!("done {n}"));
        ledger
            .transition(
                id,
                frob_ledger::model::Category::Done,
                Some(frob_ledger::model::Outcome::Fixed),
                Some("test".to_owned()),
            )
            .expect("done");
    }
    let walks = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let facts = tracing::subscriber::with_default(BatchCounter(walks.clone()), || {
        frob_pm::cycle::velocity::done_facts(&ledger).expect("facts")
    });
    assert_eq!(facts.len(), 4);
    assert_eq!(
        walks.load(std::sync::atomic::Ordering::SeqCst),
        1,
        "one batched events walk for four tickets"
    );
}

/// Commits on `main` in `dir`.
fn commit_count(dir: &Path) -> usize {
    let out = Command::new("git")
        .args(["rev-list", "--count", "main"])
        .current_dir(dir)
        .output()
        .expect("git");
    String::from_utf8_lossy(&out.stdout)
        .trim()
        .parse()
        .expect("count")
}

/// Assigning N tickets (some moved out of another cycle) writes exactly one ledger commit.
// frob:ticket 01M4DPJJ8J8C8VP9H6EDJG6B4Z
// frob:tests crates/frob-pm/src/store.rs::PmStore.assign_many
#[test]
fn assigning_many_tickets_is_one_commit() {
    let (dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    let mk = |s: &str, e: &str| NewObject::Cycle {
        start: day(s),
        end: day(e),
        goal: "g".into(),
        capacity_points: None,
    };
    let old = pm.create(mk("2026-10-05", "2026-10-11")).expect("old");
    let new = pm.create(mk("2026-10-12", "2026-10-18")).expect("new");
    let (old, new) = (old.object.id(), new.object.id());
    let tickets: Vec<TicketId> = (0..4).map(|i| ticket(&ledger, &format!("T{i}"))).collect();
    pm.set_member(ObjectKind::Cycle, old, tickets[0], Op::Add)
        .expect("seed");
    pm.set_member(ObjectKind::Cycle, old, tickets[1], Op::Add)
        .expect("seed");
    let before = commit_count(dir.path());
    let moves = [
        (tickets[0], Some(old)),
        (tickets[1], Some(old)),
        (tickets[2], None),
        (tickets[3], None),
    ];
    let applied = pm.assign_many(new, &moves, Vec::new()).expect("assign");
    assert_eq!(
        commit_count(dir.path()),
        before + 1,
        "one commit for four tickets"
    );
    assert_eq!(applied.len(), 2, "the old cycle and the target");
    let members = |id| {
        pm.get(ObjectKind::Cycle, id)
            .expect("get")
            .expect("cycle")
            .object
            .members()
            .to_vec()
    };
    assert_eq!(members(new), tickets);
    assert!(members(old).is_empty(), "both moved out");
    assert!(pm.assign_many(new, &[], Vec::new()).is_err());
}

/// Rewrite the `at` of an object's only event to `ulid_secs + delta` and report whether doctor flags it.
fn order_fires(ledger: &Ledger, kind: ObjectKind, id: frob_pm::ObjectId, delta: i64) -> bool {
    let pm = PmStore::new(ledger);
    let tip = ledger.tip_hex().expect("tip").expect("some");
    let ev = pm.read_events_at(&tip, kind, id).expect("events").remove(0);
    let ulid_secs = i64::try_from(ev.id.timestamp_ms() / 1000).expect("secs");
    let path = format!("{}/events/{}.toml", pm.object_dir(kind, id), ev.id);
    let text = ledger
        .read_text_at(&tip, &path)
        .expect("read")
        .expect("exists");
    let at = gob_time::Stamp::from_unix(ulid_secs + delta);
    let rewritten: String = text
        .lines()
        .map(|l| {
            if l.starts_with("at = ") {
                format!("at = \"{at}\"")
            } else {
                l.to_owned()
            }
        })
        .collect::<Vec<_>>()
        .join("\n");
    ledger
        .commit_files(
            "test: skew",
            &[(path, Some(format!("{rewritten}\n").into_bytes()))],
        )
        .expect("commit");
    pm.doctor(false)
        .expect("doctor")
        .issues
        .iter()
        .any(|i| i.code == "E-PM-ORDER" && i.subject == id.to_string())
}

// frob:ticket 01M4HTPMAS5TVK9S8Q47KD8R04
// frob:tests crates/frob-pm/src/doctor.rs::PmStore.doctor
#[test]
fn doctor_order_tolerates_command_clock_lag_but_not_an_at_ahead_of_its_ulid() {
    const SIX_HOURS: i64 = 6 * 3600;
    let (_dir, ledger) = fixture();
    let pm = PmStore::new(&ledger);
    let m = pm.create(milestone("0.1.0", &[])).expect("m").object.id();
    let c = pm
        .create(NewObject::Cycle {
            start: day("2026-10-05"),
            end: day("2026-10-18"),
            goal: "g".into(),
            capacity_points: None,
        })
        .expect("c")
        .object
        .id();
    for (kind, id) in [(ObjectKind::Milestone, m), (ObjectKind::Cycle, c)] {
        // ULID minted up to six hours after `at`: fine, including exactly at the boundary.
        assert!(
            !order_fires(&ledger, kind, id, -5 * 3600),
            "{kind:?} 5h lag"
        );
        assert!(
            !order_fires(&ledger, kind, id, -SIX_HOURS),
            "{kind:?} 6h lag"
        );
        assert!(
            order_fires(&ledger, kind, id, -SIX_HOURS - 1),
            "{kind:?} beyond lag"
        );
        // `at` ahead of its ULID: only the small clock-skew allowance.
        assert!(!order_fires(&ledger, kind, id, 600), "{kind:?} 600s ahead");
        assert!(order_fires(&ledger, kind, id, 601), "{kind:?} 601s ahead");
        assert!(order_fires(&ledger, kind, id, 3600), "{kind:?} 1h ahead");
    }
}

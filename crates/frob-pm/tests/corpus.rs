//! `PM034`, `PM001`, `PM002`, `PM010`-`PM013`, `PM033` and `PM036` markdown corpus: each block is a small ledger built from a line DSL.
// frob:ticket 01M4069RJJ4C73Z6GKKSV1E7PS
// frob:ticket 01M4069TBHQ2YTFEEWHED96MPY
// frob:ticket 01M4069TJA7YJTYSZCATV5ZYFS
// frob:ticket 01M416Z11V5GR012FR47HWFTBP
// frob:ticket 01M4069REJDB8FFVZFMJWAAVRY
// frob:ticket 01M4CSZFC0QF9PH544ARF60RCZ
// frob:ticket 01M4CT036SCVJMN2E3GHDTYDAJ

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::guards::NoLeases;
use frob_ledger::model::{Category, Outcome, TicketType};
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig, TicketId};
use frob_pm::rules::{cycle, cycle_plan, membership::evaluate, milestone, replenish, wip};
use frob_pm::{NewObject, ObjectKind, PmStore, State, event::Op};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_mdtest::Case;
use gob_rules::Finding;

/// A repository on `main` with a root commit, an identity and an open ledger.
fn ledger(dir: &std::path::Path) -> Ledger {
    let repo = Repo::init(dir).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(dir).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new("README.md").expect("path"),
            Some(b"hi\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
}

/// `key=value` words of a DSL line.
fn opts<'a>(words: &[&'a str]) -> BTreeMap<&'a str, &'a str> {
    words.iter().filter_map(|w| w.split_once('=')).collect()
}

/// Create the cycle of a `cycle KEY start=N end=M [closed]` line; `N` and `M` are day offsets from the UTC today (the clock is never pinned).
fn add_cycle(ledger: &Ledger, o: &BTreeMap<&str, &str>, closed: bool) -> frob_pm::ObjectId {
    let store = PmStore::new(ledger);
    let today = store.today();
    let at = |k: &str| {
        today
            .plus_days(o[k].parse().expect("day offset"))
            .expect("in range")
    };
    let applied = store
        .create(NewObject::Cycle {
            start: at("start"),
            end: at("end"),
            goal: match o.get("goal") {
                Some(&"none") => String::new(),
                _ => "goal".to_owned(),
            },
            capacity_points: o.get("capacity").map(|c| c.parse().expect("capacity")),
        })
        .expect("cycle");
    let id = applied.object.id();
    if closed {
        store
            .transition(ObjectKind::Cycle, applied.object.id(), State::Closed, None)
            .expect("close");
    }
    id
}

/// `PM036` over the ledger's cycles.
fn pm036_findings(ledger: &Ledger) -> Vec<Finding> {
    // frob:tests crates/frob-pm/src/rules/cycle.rs::pm036
    // frob:tests crates/frob-pm/src/rules/cycle.rs::evaluate
    // frob:tests crates/frob-pm/src/rules/cycle.rs::overdue
    // frob:tests crates/frob-pm/src/rules/cycle.rs::active
    // frob:tests crates/frob-pm/src/rules/cycle.rs::cycles
    cycle::evaluate(ledger).expect("evaluate").findings
}

/// Create the milestone of a `milestone VERSION [goal=none] [criteria=none] [epics=a,b]` line.
fn add_milestone(
    ledger: &Ledger,
    w: &[&str],
    o: &BTreeMap<&str, &str>,
    keys: &BTreeMap<String, TicketId>,
) {
    let applied = PmStore::new(ledger)
        .create(NewObject::Milestone {
            version: w[1].to_owned(),
            goal: match o.get("goal") {
                Some(&"none") => String::new(),
                _ => "goal".to_owned(),
            },
            target: None,
            criteria: if o.get("criteria") == Some(&"none") {
                Vec::new()
            } else {
                vec!["criterion".to_owned()]
            },
        })
        .expect("milestone");
    for k in o
        .get("epics")
        .copied()
        .unwrap_or("")
        .split(',')
        .filter(|k| !k.is_empty())
    {
        PmStore::new(ledger)
            .set_member(ObjectKind::Milestone, applied.object.id(), keys[k], Op::Add)
            .expect("member");
    }
}

/// The ticket a `epic|task|story KEY [parent= points= scope= criteria= labels= class= value=none]` line describes.
fn new_ticket(
    w: &[&str],
    o: &BTreeMap<&str, &str>,
    keys: &BTreeMap<String, TicketId>,
) -> NewTicket {
    let ty = match w[0] {
        "epic" => TicketType::Epic,
        "story" => TicketType::Story,
        _ => TicketType::Task,
    };
    let list = |k: &str| -> Vec<String> {
        o.get(k)
            .map(|l| l.split(',').map(str::to_owned).collect())
            .unwrap_or_default()
    };
    let mut t = NewTicket::new(w[1], ty);
    t.parent = o.get("parent").map(|k| keys[*k]);
    t.points = o.get("points").map(|p| p.parse().expect("points"));
    t.scope = list("scope");
    t.labels = list("labels");
    t.acceptance = (0..o
        .get("criteria")
        .map_or(0, |n| n.parse().expect("criteria")))
        .map(|i| format!("criterion {i}"))
        .collect();
    if ty == TicketType::Story && o.get("value") != Some(&"none") {
        t.persona = Some("maintainer".to_owned());
        t.capability = Some("see the plan".to_owned());
        t.outcome_text = Some("work is clear".to_owned());
    }
    if let Some(class) = o.get("class") {
        t.class = class.parse().expect("class");
    }
    t
}

/// Build the ledger a block describes and evaluate the block's rule (`PM034`, `PM001`, `PM002`, `PM010`-`PM013`, `PM033` or `PM036`) over it.
fn runner(case: &Case) -> Vec<Finding> {
    // frob:tests crates/frob-pm/src/rules/membership.rs::pm034
    // frob:tests crates/frob-pm/src/rules/membership.rs::evaluate
    // frob:tests crates/frob-pm/src/rules/membership.rs::milestones
    let dir = tempfile::tempdir().expect("tempdir");
    let ledger = ledger(dir.path());
    let mut keys: BTreeMap<String, TicketId> = BTreeMap::new();
    let mut limit = 0_u32;
    let mut ready_min = 0_u32;
    let mut expedite_max = 1_u32;
    let mut live: BTreeSet<TicketId> = BTreeSet::new();
    let mut pm = frob_pm::PmConfig::load(dir.path()).expect("defaults").pm;
    for line in case.text.lines().filter(|l| !l.trim().is_empty()) {
        let w: Vec<&str> = line.split_whitespace().collect();
        let o = opts(&w);
        match w[0] {
            "epic" | "task" | "story" => {
                let t = new_ticket(&w, &o, &keys);
                let id = ledger.new_ticket(t).expect("ticket").ticket.front.id;
                if o.get("state") == Some(&"done") {
                    ledger
                        .transition(id, Category::Done, Some(Outcome::Fixed), None)
                        .expect("done");
                }
                if o.get("state") == Some(&"in_progress") {
                    ledger
                        .transition(id, Category::InProgress, None, None)
                        .expect("transition");
                    if !w.contains(&"stale") {
                        live.insert(id);
                    }
                }
                keys.insert(w[1].to_owned(), id);
            }
            "limit" => limit = w[1].parse().expect("limit"),
            "ready_min" => ready_min = w[1].parse().expect("ready_min"),
            "expedite_max" => expedite_max = w[1].parse().expect("expedite_max"),
            "ready_requires" => {
                pm.ready_requires = w[1]
                    .split(',')
                    .map(|r| r.parse().expect("ready requirement"))
                    .collect();
            }
            "min_history" => pm.min_history = w[1].parse().expect("min_history"),
            "cycle" => {
                let id = add_cycle(&ledger, &o, w.contains(&"closed"));
                for k in o
                    .get("members")
                    .copied()
                    .unwrap_or("")
                    .split(',')
                    .filter(|k| !k.is_empty())
                {
                    PmStore::new(&ledger)
                        .set_member(ObjectKind::Cycle, id, keys[k], Op::Add)
                        .expect("member");
                }
            }
            "milestone" => add_milestone(&ledger, &w, &o, &keys),
            other => unreachable!("unknown DSL verb {other}"),
        }
    }
    if matches!(case.rule.to_string().as_str(), "PM001" | "PM002") {
        // frob:tests crates/frob-pm/src/rules/milestone.rs::pm001
        // frob:tests crates/frob-pm/src/rules/milestone.rs::pm002
        // frob:tests crates/frob-pm/src/rules/milestone.rs::evaluate
        return milestone::evaluate(&ledger)
            .expect("evaluate")
            .findings
            .into_iter()
            .filter(|f| f.rule == case.rule)
            .collect();
    }
    if matches!(case.rule.to_string().as_str(), "PM010" | "PM011" | "PM012") {
        // frob:tests crates/frob-pm/src/rules/cycle_plan.rs::pm010
        // frob:tests crates/frob-pm/src/rules/cycle_plan.rs::pm011
        // frob:tests crates/frob-pm/src/rules/cycle_plan.rs::pm012
        // frob:tests crates/frob-pm/src/rules/cycle_plan.rs::evaluate
        // frob:tests crates/frob-pm/src/rules/cycle_plan.rs::ready_failures
        // frob:tests crates/frob-pm/src/cycle/history.rs::deliveries
        // frob:tests crates/frob-pm/src/cycle/history.rs::done_points
        // frob:tests crates/frob-pm/src/cycle/history.rs::cycle_events
        // frob:tests crates/frob-pm/src/cycle/history.rs::member_status
        return cycle_plan::evaluate(&ledger, &pm)
            .expect("evaluate")
            .findings
            .into_iter()
            .filter(|f| f.rule == case.rule)
            .collect();
    }
    if case.rule.to_string() == "PM036" {
        return pm036_findings(&ledger);
    }
    if case.rule.to_string() == "PM033" {
        // frob:tests crates/frob-pm/src/rules/replenish.rs::pm033
        // frob:tests crates/frob-pm/src/rules/replenish.rs::evaluate
        return replenish::evaluate(&ledger, &NoLeases, ready_min)
            .expect("evaluate")
            .findings;
    }
    if case.rule.to_string() == "PM013" {
        // frob:tests crates/frob-pm/src/rules/wip.rs::pm013
        // frob:tests crates/frob-pm/src/rules/wip.rs::evaluate_with
        // frob:tests crates/frob-pm/src/rules/wip.rs::in_progress
        let limits = wip::WipLimits {
            in_progress: limit,
            expedite_max,
        };
        return wip::evaluate_with(&ledger, limits, Some(&live))
            .expect("evaluate")
            .findings;
    }
    evaluate(&ledger).expect("evaluate").findings
}

/// One `#[test]` per corpus file so nextest runs the five files in parallel (~2E4H9EG: the single
/// `mdtest_corpus` case ran them serially, 8.6 s cold and past the 120 s guard under load).
macro_rules! corpus_file {
    ($name:ident, $file:literal) => {
        // frob:ticket 01M4957V84TB1V6TRPR2E4H9EG
        #[test]
        fn $name() {
            let dir = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR")).join("tests/mdtest");
            let report = gob_mdtest::run_file(&dir.join($file), &gob_mdtest::Runner::new(runner));
            assert!(
                report.passed(),
                "mdtest corpus failed:\n{}",
                report.render_failures()
            );
            assert!(!report.cases.is_empty(), "no cases in {}", $file);
        }
    };
}

corpus_file!(pm001, "pm001.md");
corpus_file!(pm002, "pm002.md");
corpus_file!(pm010, "pm010.md");
corpus_file!(pm011, "pm011.md");
corpus_file!(pm012, "pm012.md");
corpus_file!(pm013, "pm013.md");
corpus_file!(pm033, "pm033.md");
corpus_file!(pm034, "pm034.md");
corpus_file!(pm036, "pm036.md");

/// Guards the per-file split: a new markdown file must get its own `corpus_file!` line above.
// frob:ticket 01M4957V84TB1V6TRPR2E4H9EG
#[test]
fn every_corpus_file_has_a_test() {
    let dir = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR")).join("tests/mdtest");
    let mut files: Vec<String> = std::fs::read_dir(&dir)
        .expect("read corpus dir")
        .filter_map(Result::ok)
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    files.sort();
    assert_eq!(
        files,
        [
            "pm001.md", "pm002.md", "pm010.md", "pm011.md", "pm012.md", "pm013.md", "pm033.md",
            "pm034.md", "pm036.md"
        ],
        "corpus files and corpus_file! lines must match"
    );
}

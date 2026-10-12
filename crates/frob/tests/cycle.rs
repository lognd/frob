//! `cycle new`, `show`, `list` and `close`: defaults, overlap, idempotency, carry-over and refusals.
// frob:ticket 01M4069RPPQE1ES1914K6V6Y0D
// frob:ticket 01M4069T2V69X32EP8NZQHJH6H

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use frob_lease::{Holder, LeaseConfig, LeaseStore};
use frob_pm::event::Op;
use frob_pm::{ObjectId, ObjectKind, PmStore};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

mod common;

/// A trunk-mode repository with `frob init` run and one commit.
struct Repo {
    dir: tempfile::TempDir,
}

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

impl Repo {
    fn new() -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
        git(dir.path(), &["config", "user.name", "Test User"]);
        git(dir.path(), &["config", "user.email", "test@example.com"]);
        git(dir.path(), &["config", "core.autocrlf", "false"]);
        let repo = Self { dir };
        assert_eq!(code(&repo.run(&["--json", "init"])), 0);
        common::set_done_requires(repo.dir.path(), &["no_open_children"]);
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn run(&self, args: &[&str]) -> Output {
        common::frob_command()
            .current_dir(self.dir.path())
            .env_remove("FROB_LOG")
            .args(args)
            .output()
            .expect("run frob")
    }

    fn frob(&self, args: &[&str]) -> Output {
        let mut a = vec!["--json"];
        a.extend_from_slice(args);
        self.run(&a)
    }

    fn ok(&self, args: &[&str]) -> Value {
        let out = self.frob(args);
        assert_eq!(
            code(&out),
            0,
            "{args:?}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        json(&out)
    }

    fn path(&self) -> &Path {
        self.dir.path()
    }

    fn ledger(&self) -> frob_ledger::Ledger {
        let repo = gob_git::Repo::discover(self.path()).expect("discover");
        let cfg = frob_cli::config::FrobConfig::load(self.path()).expect("config");
        frob_ledger::Ledger::open(
            repo,
            cfg.ledger(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
    }

    /// A ticket with `points` story points, started when `category` is `in-progress`; returns its ULID.
    fn ticket(&self, category: &str, points: &str) -> String {
        let id = self.ok(&[
            "ticket", "new", "--title", "t", "--type", "task", "--points", points,
        ])["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned();
        if category == "in-progress" {
            self.ledger()
                .transition(
                    id.parse().expect("ulid"),
                    frob_ledger::model::Category::InProgress,
                    None,
                    None,
                )
                .expect("start");
        }
        id
    }

    /// A done (fixed) ticket with `points`.
    fn done_ticket(&self, points: &str) -> String {
        let id = self.ticket("todo", points);
        self.ok(&[
            "ticket",
            "close",
            &id,
            "--outcome",
            "fixed",
            "--no-evidence",
            "--reason",
            "test",
        ]);
        id
    }

    /// Put ticket `t` into the cycle with ULID `cycle`.
    fn assign(&self, cycle: &str, t: &str) {
        let ledger = self.ledger();
        PmStore::new(&ledger)
            .set_member(
                ObjectKind::Cycle,
                cycle.parse::<ObjectId>().expect("cycle id"),
                t.parse().expect("ticket id"),
                Op::Add,
            )
            .expect("member");
    }

    /// Hold a live lease on `t` as someone else.
    fn lease(&self, t: &str) {
        let repo = gob_git::Repo::discover(self.path()).expect("discover");
        let store = LeaseStore::open(
            &repo,
            LeaseConfig::default(),
            std::sync::Arc::new(gob_time::SystemClock),
        )
        .expect("store");
        let holder = Holder {
            actor: "Someone Else".to_owned(),
            worktree: std::path::PathBuf::from("/wt/other"),
        };
        store
            .acquire(t.parse().expect("ticket id"), &holder, &["x/**".to_owned()])
            .expect("acquire");
    }

    fn new_cycle(&self, start: &str, goal: &str) -> Value {
        self.ok(&["cycle", "new", "--start", start, "--goal", goal])["data"]["cycle"].clone()
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn id(c: &Value) -> &str {
    c["id"].as_str().expect("id")
}

#[test]
fn new_takes_its_end_from_cycle_days_and_a_repeat_is_already() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleNew
    let repo = Repo::new();
    let v = repo.ok(&[
        "cycle",
        "new",
        "--start",
        d(0),
        "--goal",
        "Ship PM",
        "--capacity",
        "13",
    ]);
    assert_eq!(v["verb"], "cycle.new");
    assert_eq!(v["already"], false);
    let c = &v["data"]["cycle"];
    assert_eq!(c["end"], d(6));
    assert_eq!(c["alias"], span(0, 6));
    assert_eq!(c["capacity_points"], 13);
    assert_eq!(c["state"], "planned");
    let again = repo.ok(&[
        "cycle",
        "new",
        "--start",
        d(0),
        "--goal",
        "Ship PM",
        "--capacity",
        "13",
    ]);
    assert_eq!(again["already"], true);
    assert_eq!(again["data"]["commit"], Value::Null);
    let explicit = repo.ok(&[
        "cycle",
        "new",
        "--start",
        d(0),
        "--end",
        d(6),
        "--goal",
        "Ship PM",
        "--capacity-points",
        "13",
    ]);
    assert_eq!(explicit["already"], true);
    let out = repo.frob(&["cycle", "new", "--start", d(0), "--goal", "Other"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-EXISTS");
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 1);
}

#[test]
fn overlapping_an_open_cycle_is_refused_with_a_remedy() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleNew
    let repo = Repo::new();
    repo.new_cycle(d(0), "first");
    let out = repo.frob(&["cycle", "new", "--start", d(6), "--goal", "second"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-OVERLAP");
    assert!(
        e["remedy"]
            .as_str()
            .expect("remedy")
            .contains(&format!("--start {}", d(7)))
    );
    let out = repo.frob(&[
        "cycle",
        "new",
        "--start",
        d(7),
        "--end",
        d(-4),
        "--goal",
        "g",
    ]);
    assert_eq!(code(&out), 2);
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-WINDOW");
    repo.new_cycle(d(7), "second");
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 2);
}

#[test]
fn close_is_refused_while_a_member_is_in_progress_with_a_live_lease() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    let repo = Repo::new();
    let c = repo.new_cycle(d(0), "first");
    repo.new_cycle(d(7), "second");
    let busy = repo.ticket("in-progress", "3");
    repo.assign(id(&c), &busy);
    repo.lease(&busy);
    let handle = format!("~{}", &busy[19..]);
    let out = repo.frob(&["cycle", "close", span(0, 6)]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-LEASE");
    assert!(e["message"].as_str().expect("message").contains(&handle));
    let shown = repo.ok(&["cycle", "show", id(&c)]);
    assert_eq!(shown["data"]["cycle"]["state"], "planned");
}

#[test]
fn close_carries_incomplete_members_and_records_the_ratio_and_retro() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    // frob:tests crates/frob-pm/src/store.rs::PmStore.append_many
    let repo = Repo::new();
    let c = repo.new_cycle(d(0), "first");
    let next = repo.new_cycle(d(7), "second");
    let done = repo.done_ticket("5");
    let todo = repo.ticket("todo", "3");
    let idle = repo.ticket("in-progress", "2");
    for t in [&done, &todo, &idle] {
        repo.assign(id(&c), t);
    }
    let v = repo.ok(&[
        "cycle",
        "close",
        c["handle"].as_str().expect("handle"),
        "--retro",
        "went fine, scope crept",
    ]);
    assert_eq!(v["already"], false);
    let closed = &v["data"]["cycle"];
    assert_eq!(closed["state"], "closed");
    assert_eq!(closed["tickets"].as_array().expect("tickets").len(), 1);
    assert_eq!(closed["tickets"][0]["id"], done.as_str());
    assert_eq!(closed["commitment"]["committed"], 10);
    assert_eq!(closed["commitment"]["done"], 5);
    assert_eq!(closed["commitment"]["ratio"], 0.5);
    assert_eq!(closed["retro"], "went fine, scope crept");
    let carried = closed["carried"].as_array().expect("carried");
    assert_eq!(carried.len(), 2);
    assert!(carried.iter().all(|x| x["to"] == next["id"]));
    let target = repo.ok(&["cycle", "show", span(7, 13)]);
    let members: Vec<&str> = target["data"]["cycle"]["tickets"]
        .as_array()
        .expect("tickets")
        .iter()
        .map(|t| t["id"].as_str().expect("id"))
        .collect();
    assert_eq!(members.len(), 2);
    assert!(members.contains(&todo.as_str()) && members.contains(&idle.as_str()));
    let again = repo.ok(&["cycle", "close", id(&c)]);
    assert_eq!(again["already"], true);
}

#[test]
fn close_without_a_next_cycle_is_refused_unless_carry_to_names_one() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    let repo = Repo::new();
    // Already over, so the planned end is the effective end and the remedy starts the day after it.
    let c = window(&repo, -10, -4, None);
    let todo = repo.ticket("todo", "3");
    repo.assign(id(&c), &todo);
    let out = repo.frob(&["cycle", "close", id(&c)]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-NO-NEXT");
    let remedy = e["remedy"].as_str().expect("remedy");
    assert!(
        remedy.contains(&format!("cycle new --start {}", rel(-3))) && remedy.contains("--carry-to")
    );
    assert_eq!(
        repo.ok(&["cycle", "show", id(&c)])["data"]["cycle"]["state"],
        // Started in the past and never closed: active, as the refused close left it.
        "active"
    );
    let far = repo.new_cycle(d(100), "far");
    let skipped = repo.new_cycle(d(60), "mid");
    let v = repo.ok(&["cycle", "close", id(&c), "--carry-to", id(&far)]);
    assert_eq!(v["data"]["cycle"]["carried"][0]["to"], far["id"]);
    assert_ne!(far["id"], skipped["id"]);
    let all_done = repo.new_cycle(d(200), "empty");
    let v = repo.ok(&["cycle", "close", id(&all_done)]);
    assert_eq!(v["data"]["cycle"]["commitment"]["ratio"], Value::Null);
}

#[test]
fn show_and_list_report_cycles_and_unknown_references_suggest() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleShow
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleList
    // frob:tests crates/gob-time/src/clock.rs::Clock.today
    let repo = Repo::new();
    let a = repo.new_cycle(d(7), "second");
    repo.new_cycle(d(0), "first");
    let list = repo.ok(&["cycle", "list"]);
    assert_eq!(list["data"]["count"], 2);
    assert_eq!(list["data"]["cycles"][0]["goal"], "first");
    for r in [id(&a), a["handle"].as_str().expect("handle"), span(7, 13)] {
        assert_eq!(
            repo.ok(&["cycle", "show", r])["data"]["cycle"]["goal"],
            "second",
            "{r}"
        );
    }
    assert!(repo.ok(&["cycle", "show"])["data"]["cycle"]["goal"].is_string());
    let out = repo.frob(&["cycle", "show", span(7, 14)]);
    assert_eq!(code(&out), 3);
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-NOT-FOUND");
    assert_eq!(e["remedy"], format!("frob cycle show {}", span(7, 13)));
}

/// The UTC day `days` from now, as `YYYY-MM-DD`: the one zone and clock `frob cycle` derives states from.
fn rel(days: i64) -> String {
    gob_time::Clock::today(&gob_time::SystemClock)
        .plus_days(days)
        .expect("in range")
        .to_string()
}

/// A fixture date `offset` days after a point 40 days ahead of the UTC today, so a cycle starting there is `planned` whenever the test runs (leaked: test-only, lets dates sit in `&str` arg arrays).
fn d(offset: i64) -> &'static str {
    Box::leak(rel(40 + offset).into_boxed_str())
}

/// The alias `d(a)..d(b)`.
fn span(a: i64, b: i64) -> &'static str {
    Box::leak(format!("{}..{}", d(a), d(b)).into_boxed_str())
}

/// A cycle from `start` to `end` days relative to today, with an optional capacity.
fn window(repo: &Repo, start: i64, end: i64, capacity: Option<&str>) -> Value {
    let (s, e) = (rel(start), rel(end));
    let mut args = vec!["cycle", "new", "--start", &s, "--end", &e, "--goal", "g"];
    if let Some(c) = capacity {
        args.extend(["--capacity", c]);
    }
    repo.ok(&args)["data"]["cycle"].clone()
}

#[test]
fn assign_and_unassign_are_idempotent_and_say_capacity_is_not_enforced_yet() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleAssign
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleUnassign
    let repo = Repo::new();
    let c = window(&repo, -1, 5, None);
    let t = repo.ticket("todo", "3");
    let v = repo.ok(&["cycle", "assign", &t, id(&c)]);
    assert_eq!(v["already"], false);
    assert_eq!(v["data"]["committed"], 3);
    assert_eq!(v["data"]["over_committed"], false);
    assert_eq!(
        v["data"]["capacity"],
        "capacity not enforced yet: 0 of 3 cycles of history"
    );
    assert_eq!(v["data"]["cycle"]["tickets"][0]["id"], t.as_str());
    let again = repo.ok(&["cycle", "assign", &t, id(&c)]);
    assert_eq!(again["already"], true);
    let off = repo.ok(&["cycle", "unassign", &t, id(&c)]);
    assert_eq!(off["already"], false);
    assert_eq!(off["data"]["committed"], 0);
    assert_eq!(
        off["data"]["cycle"]["tickets"].as_array().expect("t").len(),
        0
    );
    let off_again = repo.ok(&["cycle", "unassign", &t, id(&c)]);
    assert_eq!(off_again["already"], true);
}

#[test]
fn assign_defaults_to_the_open_cycle_holding_today_else_the_next_planned() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleAssign
    // frob:tests crates/frob-pm/src/cycle/assign.rs::default_cycle
    let repo = Repo::new();
    let t = repo.ticket("todo", "2");
    let none = repo.frob(&["cycle", "assign", &t]);
    assert_eq!(code(&none), 3);
    assert_eq!(json(&none)["error"]["code"], "E-CYCLE-NONE");
    assert!(
        json(&none)["error"]["remedy"]
            .as_str()
            .expect("remedy")
            .contains("frob cycle new")
    );
    let future = window(&repo, 14, 20, None);
    let v = repo.ok(&["cycle", "assign", &t]);
    assert_eq!(v["data"]["cycle"]["id"], future["id"]);
    let current = window(&repo, -1, 5, None);
    let u = repo.ticket("todo", "2");
    let v = repo.ok(&["cycle", "assign", &u]);
    assert_eq!(v["data"]["cycle"]["id"], current["id"]);
}

#[test]
fn assign_refuses_epics_and_tickets_without_points_with_remedies() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleAssign
    // frob:tests crates/frob-pm/src/cycle/assign.rs::plan_assign
    let repo = Repo::new();
    let c = window(&repo, -1, 5, None);
    let epic = repo.ok(&["ticket", "new", "--title", "e", "--type", "epic"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let out = repo.frob(&["cycle", "assign", &epic, id(&c)]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-NOT-ASSIGNABLE");
    let bare = repo.ok(&["ticket", "new", "--title", "b", "--type", "task"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let out = repo.frob(&["cycle", "assign", &bare, id(&c)]);
    assert_eq!(code(&out), 3);
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-NO-POINTS");
    assert!(
        e["remedy"]
            .as_str()
            .expect("remedy")
            .contains("ticket update")
    );
    assert!(e["remedy"].as_str().expect("remedy").contains("--points"));
}

#[test]
fn explicit_capacity_is_enforced_and_over_commit_records_the_reason() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleAssign
    // frob:tests crates/frob-pm/src/cycle/assign.rs::plan_assign
    let repo = Repo::new();
    let c = window(&repo, -1, 5, Some("5"));
    let first = repo.ticket("todo", "3");
    let second = repo.ticket("todo", "3");
    repo.ok(&["cycle", "assign", &first, id(&c)]);
    let out = repo.frob(&["cycle", "assign", &second, id(&c)]);
    assert_eq!(code(&out), 3);
    let err = &json(&out)["error"];
    assert_eq!(err["code"], "E-CYCLE-OVER-CAPACITY");
    assert!(err["message"].as_str().expect("m").contains("6 points"));
    assert!(
        err["message"]
            .as_str()
            .expect("m")
            .contains("5-point limit")
    );
    assert!(
        err["remedy"]
            .as_str()
            .expect("r")
            .contains("--over-commit --reason")
    );
    let no_reason = repo.frob(&["cycle", "assign", &second, id(&c), "--over-commit"]);
    assert_eq!(code(&no_reason), 2);
    let v = repo.ok(&[
        "cycle",
        "assign",
        &second,
        id(&c),
        "--over-commit",
        "--reason",
        "customer escalation",
    ]);
    assert_eq!(v["data"]["over_committed"], true);
    assert_eq!(v["data"]["committed"], 6);
    let oc = &v["data"]["cycle"]["over_commits"][0];
    assert_eq!(oc["reason"], "customer escalation");
    assert_eq!(oc["ticket"], second.as_str());
    assert_eq!(oc["capacity"], 5);
    assert_eq!(oc["committed"], 6);
    let shown = repo.ok(&["cycle", "show", id(&c)]);
    assert_eq!(
        shown["data"]["cycle"]["over_commits"][0]["reason"],
        "customer escalation"
    );
}

#[test]
fn computed_capacity_applies_once_min_history_cycles_have_closed() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleAssign
    // frob:tests crates/frob-pm/src/cycle/velocity.rs::capacity
    let repo = Repo::new();
    // Three closed cycles, each committed 10 points and finished them: velocity 10, 10, 10.
    for (s, e) in [(-3, 3), (-2, 4), (-1, 5)] {
        let c = window(&repo, s, e, None);
        repo.assign(id(&c), &repo.done_ticket("8"));
        repo.assign(id(&c), &repo.done_ticket("2"));
        repo.ok(&["cycle", "close", id(&c)]);
    }
    let open = window(&repo, 10, 16, None);
    let a = repo.ticket("todo", "8");
    let b = repo.ticket("todo", "5");
    let v = repo.ok(&["cycle", "assign", &a, id(&open)]);
    assert_eq!(v["data"]["capacity_limit"], 10);
    assert!(
        v["data"]["capacity"]
            .as_str()
            .expect("c")
            .starts_with("capacity 10 points")
    );
    let out = repo.frob(&["cycle", "assign", &b, id(&open)]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-OVER-CAPACITY");
}

#[test]
fn assigning_to_another_cycle_moves_the_ticket() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleAssign
    // frob:tests crates/frob-pm/src/cycle/assign.rs::plan_assign
    let repo = Repo::new();
    let first = window(&repo, -1, 5, None);
    let second = window(&repo, 10, 16, None);
    let t = repo.ticket("todo", "2");
    repo.ok(&["cycle", "assign", &t, id(&first)]);
    let v = repo.ok(&["cycle", "assign", &t, id(&second)]);
    assert_eq!(v["already"], false);
    assert_eq!(v["data"]["moved_from"], first["alias"]);
    let old = repo.ok(&["cycle", "show", id(&first)]);
    assert_eq!(
        old["data"]["cycle"]["tickets"].as_array().expect("t").len(),
        0
    );
    let new = repo.ok(&["cycle", "show", id(&second)]);
    assert_eq!(new["data"]["cycle"]["tickets"][0]["id"], t.as_str());
}

/// The UTC day `days` from now, as `YYYY-MM-DD` (the day an early close records).
fn utc(days: i64) -> String {
    rel(days)
}

/// A cycle from `start` to `end` days from the UTC today.
fn utc_window(repo: &Repo, start: i64, end: i64) -> Value {
    let (s, e) = (utc(start), utc(end));
    repo.ok(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "g"])["data"]["cycle"].clone()
}

/// Every folded cycle, earliest start first.
fn folded(repo: &Repo) -> Vec<frob_pm::Cycle> {
    let ledger = repo.ledger();
    let mut all: Vec<frob_pm::Cycle> = PmStore::new(&ledger)
        .list(ObjectKind::Cycle)
        .expect("list")
        .into_iter()
        .filter_map(|o| match o {
            frob_pm::Object::Cycle(c) => Some(c),
            frob_pm::Object::Milestone(_) => None,
        })
        .collect();
    all.sort_by_key(|c| c.start);
    all
}

#[test]
fn closing_on_the_first_day_frees_the_next_day_and_shows_both_ends() {
    // frob:ticket 01M40SMB58CSHSFV8FTD5W8ERW
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleShow
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleList
    // frob:tests crates/frob-pm/src/fold.rs::fold
    let repo = Repo::new();
    let c = utc_window(&repo, 0, 6);
    assert_eq!(c["ended"], Value::Null);
    let closed = repo.ok(&["cycle", "close", id(&c)])["data"]["cycle"].clone();
    assert_eq!(closed["end"], utc(6).as_str());
    assert_eq!(closed["ended"], utc(0).as_str());
    // The remainder of the planned week is free: a cycle from tomorrow is accepted.
    let next = utc_window(&repo, 1, 2);
    assert_eq!(next["state"], "planned");
    let shown = repo.ok(&["cycle", "show", id(&c)])["data"]["cycle"].clone();
    assert_eq!(
        (&shown["end"], &shown["ended"]),
        (&closed["end"], &closed["ended"])
    );
    let list = repo.ok(&["cycle", "list"]);
    assert_eq!(list["data"]["cycles"][0]["end"], utc(6).as_str());
    assert_eq!(list["data"]["cycles"][0]["ended"], utc(0).as_str());
    assert_eq!(list["data"]["cycles"][1]["ended"], Value::Null);
}

#[test]
fn closing_on_the_last_day_or_a_legacy_close_keeps_the_planned_end() {
    // frob:ticket 01M40SMB58CSHSFV8FTD5W8ERW
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    // frob:tests crates/frob-pm/src/store.rs::PmStore.transition
    let repo = Repo::new();
    let last = utc_window(&repo, -6, 0);
    let v = repo.ok(&["cycle", "close", id(&last)])["data"]["cycle"].clone();
    assert_eq!(v["state"], "closed");
    assert_eq!(v["ended"], Value::Null);
    assert_eq!(v["end"], utc(0).as_str());
    // A close event with no effective end (written before this field existed) folds as before.
    let old = utc_window(&repo, -20, -14);
    let ledger = repo.ledger();
    PmStore::new(&ledger)
        .transition(
            ObjectKind::Cycle,
            id(&old).parse::<ObjectId>().expect("id"),
            frob_pm::State::Closed,
            None,
        )
        .expect("legacy close");
    let cycles = folded(&repo);
    let legacy = cycles
        .iter()
        .find(|c| c.alias().starts_with(&utc(-20)))
        .expect("legacy");
    assert_eq!(legacy.state, frob_pm::State::Closed);
    assert_eq!(legacy.ended, None);
    assert_eq!(legacy.effective_end(), legacy.end);
    assert_eq!(
        repo.ok(&["cycle", "show", id(&old)])["data"]["cycle"]["ended"],
        Value::Null
    );
}

#[test]
fn velocity_and_ratio_stop_at_the_close_day_and_later_work_counts_once() {
    // frob:ticket 01M40SMB58CSHSFV8FTD5W8ERW
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    // frob:tests crates/frob-pm/src/cycle/velocity.rs::delivered
    // frob:tests crates/frob-pm/src/cycle/velocity.rs::velocity
    let repo = Repo::new();
    let a = utc_window(&repo, 0, 6);
    let b = utc_window(&repo, 7, 8);
    let done = repo.done_ticket("5");
    let todo = repo.ticket("todo", "3");
    repo.assign(id(&a), &done);
    repo.assign(id(&a), &todo);
    let closed = repo.ok(&["cycle", "close", id(&a)])["data"]["cycle"].clone();
    assert_eq!(closed["commitment"]["committed"], 8);
    assert_eq!(closed["commitment"]["done"], 5);
    assert_eq!(closed["carried"][0]["to"], b["id"]);
    // Work after the early close and inside A's planned week counts in no cycle; work
    // in B's window counts there once.
    let on = |days: i64| {
        gob_time::Clock::today(&gob_time::SystemClock)
            .plus_days(days)
            .expect("day")
    };
    let fact = |points, done_on| frob_pm::cycle::velocity::DoneFact {
        ty: frob_ledger::model::TicketType::Task,
        points,
        done_on,
    };
    let facts = [fact(5, on(0)), fact(2, on(2)), fact(3, on(7))];
    let cycles = folded(&repo);
    let delivered = |i: usize| frob_pm::cycle::velocity::delivered(&cycles[i], &facts);
    assert_eq!(
        delivered(0),
        5,
        "the early-closed cycle counts up to the close day"
    );
    assert_eq!(delivered(1), 3, "later work counts in the next cycle");
    assert_eq!(delivered(0) + delivered(1), 8, "nothing is counted twice");
}

/// Handles of the member tickets in a `cycle show` view.
fn member_ids(view: &Value) -> Vec<String> {
    view["tickets"]
        .as_array()
        .expect("tickets")
        .iter()
        .map(|t| t["id"].as_str().expect("id").to_owned())
        .collect()
}

#[test]
fn close_early_with_next_goal_creates_the_next_cycle_carries_members_and_counts_them() {
    // frob:ticket 01M40VQWCV38B2JCABYNNNA877
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    // frob:tests crates/frob-pm/src/cycle/lifecycle.rs::plan_next
    let repo = Repo::new();
    let c = utc_window(&repo, 0, 6);
    let done = repo.done_ticket("2");
    let todo = repo.ticket("todo", "3");
    for t in [&done, &todo] {
        repo.assign(id(&c), t);
    }
    let v = repo.ok(&[
        "cycle",
        "close",
        id(&c),
        "--next-goal",
        "follow up",
        "--next-days",
        "2",
    ]);
    let closed = &v["data"]["cycle"];
    assert_eq!(closed["state"], "closed");
    assert_eq!(closed["ended"], utc(0).as_str());
    assert_eq!(closed["commitment"]["committed"], 5);
    assert_eq!(closed["commitment"]["done"], 2);
    assert_eq!(closed["commitment"]["ratio"], 0.4);
    let next = &v["data"]["next"];
    assert_eq!(next["start"], utc(1).as_str());
    assert_eq!(next["end"], utc(2).as_str());
    assert_eq!(next["goal"], "follow up");
    assert_eq!(closed["carried"][0]["to"], next["id"]);
    let shown = repo.ok(&["cycle", "show", id(next)])["data"]["cycle"].clone();
    assert_eq!(member_ids(&shown), vec![todo.clone()]);
    assert_eq!(member_ids(closed), vec![done]);
    // A repeat of the close changes nothing.
    assert_eq!(repo.ok(&["cycle", "close", id(&c)])["already"], true);
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 2);
}

#[test]
fn close_next_days_defaults_to_cycle_days() {
    // frob:ticket 01M40VQWCV38B2JCABYNNNA877
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    let repo = Repo::new();
    let c = utc_window(&repo, 0, 6);
    let todo = repo.ticket("todo", "1");
    repo.assign(id(&c), &todo);
    let v = repo.ok(&["cycle", "close", id(&c), "--next-goal", "g2"]);
    assert_eq!(v["data"]["next"]["start"], utc(1).as_str());
    assert_eq!(v["data"]["next"]["end"], utc(7).as_str());
    // Nothing unfinished: the flags are still honoured, never dropped (frob:ticket 01M4CT13C64KEVBP74G6VCQP1Q).
    let c2 = utc_window(&repo, 8, 9);
    let v = repo.ok(&["cycle", "close", id(&c2), "--next-goal", "unused"]);
    assert_eq!(v["data"]["next"]["goal"], "unused");
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 4);
}

#[test]
fn close_early_without_next_goal_refuses_and_the_remedy_names_it() {
    // frob:ticket 01M40VQWCV38B2JCABYNNNA877
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    let repo = Repo::new();
    let c = utc_window(&repo, 0, 6);
    let todo = repo.ticket("todo", "3");
    repo.assign(id(&c), &todo);
    let out = repo.frob(&["cycle", "close", id(&c)]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-NO-NEXT");
    assert!(
        e["remedy"]
            .as_str()
            .expect("remedy")
            .contains("--next-goal")
    );
    assert_eq!(
        repo.ok(&["cycle", "show", id(&c)])["data"]["cycle"]["state"],
        // Started in the past and never closed: active, as the refused close left it.
        "active"
    );
}

#[test]
fn close_retries_after_a_failure_between_the_create_and_the_carry() {
    // frob:ticket 01M40VQWCV38B2JCABYNNNA877
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    let repo = Repo::new();
    let c = utc_window(&repo, 0, 6);
    let todo = repo.ticket("todo", "3");
    repo.assign(id(&c), &todo);
    // The state a crash right after the create leaves: the next cycle exists, nothing carried.
    // `cycle new` would refuse (the open cycle still covers those days), so write it as the close does.
    let ledger = repo.ledger();
    let made = PmStore::new(&ledger)
        .create(frob_pm::NewObject::Cycle {
            start: utc(1).parse().expect("day"),
            end: utc(2).parse().expect("day"),
            goal: "follow up".to_owned(),
            capacity_points: None,
        })
        .expect("create")
        .object;
    let made = serde_json::json!({ "id": made.id().to_string() });
    // Or after part of the carry: the target already holds the ticket, the source still does too.
    repo.assign(id(&made), &todo);
    let v = repo.ok(&[
        "cycle",
        "close",
        id(&c),
        "--next-goal",
        "follow up",
        "--next-days",
        "2",
    ]);
    assert_eq!(v["data"]["cycle"]["state"], "closed");
    assert_eq!(v["data"]["cycle"]["carried"][0]["to"], made["id"]);
    assert_eq!(v["data"]["cycle"]["commitment"]["committed"], 3);
    let shown = repo.ok(&["cycle", "show", id(&made)])["data"]["cycle"].clone();
    assert_eq!(member_ids(&shown), vec![todo]);
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 2);
}

#[test]
fn a_closed_cycle_does_not_block_the_same_dates_and_the_new_alias_is_suffixed() {
    // frob:ticket 01M40VQWCV38B2JCABYNNNA877
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleNew
    // frob:tests crates/frob-pm/src/store.rs::PmStore.resolve
    // frob:tests crates/frob-pm/src/cycle/lifecycle.rs::plan_new
    let repo = Repo::new();
    let (s, e) = (utc(0), utc(1));
    let first = utc_window(&repo, 0, 1);
    let bare = format!("{s}..{e}");
    assert_eq!(first["alias"], bare.as_str());
    repo.ok(&["cycle", "close", id(&first)]);
    // A different goal on the same dates is no conflict with a closed cycle.
    let out = repo.ok(&[
        "cycle", "new", "--start", &s, "--end", &e, "--goal", "again",
    ]);
    assert_eq!(out["already"], false);
    let second = &out["data"]["cycle"];
    let suffixed = format!("{bare}.2");
    assert_eq!(second["alias"], suffixed.as_str());
    // Even the identical goal is a fresh cycle after a close, and a repeat of the open one is `already`.
    assert_eq!(
        repo.ok(&[
            "cycle", "new", "--start", &s, "--end", &e, "--goal", "again"
        ])["already"],
        true
    );
    for r in [
        suffixed.as_str(),
        id(second),
        second["handle"].as_str().expect("handle"),
    ] {
        assert_eq!(
            repo.ok(&["cycle", "show", r])["data"]["cycle"]["id"],
            second["id"]
        );
    }
    for r in [bare.as_str(), id(&first)] {
        assert_eq!(
            repo.ok(&["cycle", "show", r])["data"]["cycle"]["id"],
            first["id"]
        );
    }
    let list = repo.ok(&["cycle", "list"]);
    let aliases: Vec<&str> = list["data"]["cycles"]
        .as_array()
        .expect("cycles")
        .iter()
        .map(|c| c["alias"].as_str().expect("alias"))
        .collect();
    assert_eq!(aliases, vec![bare.as_str(), suffixed.as_str()]);
    // Overlap with an open cycle is still refused.
    let out = repo.frob(&["cycle", "new", "--start", &e, "--goal", "x"]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-OVERLAP");
    // A third on the same dates after closing the second gets .3.
    repo.ok(&["cycle", "close", id(second)]);
    let third = repo.ok(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "c"]);
    assert_eq!(
        third["data"]["cycle"]["alias"],
        format!("{bare}.3").as_str()
    );
}

#[test]
fn velocity_with_no_closed_cycles_says_so_and_exits_zero() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleVelocity
    let repo = Repo::new();
    window(&repo, -1, 5, None);
    let v = repo.ok(&["cycle", "velocity"]);
    assert_eq!(v["data"]["cycles"].as_array().expect("cycles").len(), 0);
    assert_eq!(v["data"]["samples"], 0);
    assert!(
        v["data"]["message"]
            .as_str()
            .expect("message")
            .contains("no closed cycles")
    );
    assert!(v["data"]["capacity_limit"].is_null());
    assert!(
        v["data"]["capacity"]
            .as_str()
            .expect("capacity")
            .starts_with("capacity not enforced yet: 0 of 3")
    );
}

#[test]
fn velocity_lists_closed_cycles_and_its_capacity_is_what_assign_reports() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleVelocity
    // frob:tests crates/frob-pm/src/cycle/velocity.rs::history_capacity
    let repo = Repo::new();
    for (s, e) in [(-3, 3), (-2, 4)] {
        let c = window(&repo, s, e, None);
        repo.assign(id(&c), &repo.done_ticket("8"));
        repo.assign(id(&c), &repo.done_ticket("2"));
        repo.ok(&["cycle", "close", id(&c)]);
    }
    // Fewer than min_history (3) closed cycles: samples shown, no capacity derived.
    let v = repo.ok(&["cycle", "velocity", "--last", "5"]);
    assert_eq!(v["data"]["samples"], 2);
    assert_eq!(v["data"]["last"], 5);
    assert!(v["data"]["capacity_limit"].is_null());
    assert!(
        v["data"]["capacity"]
            .as_str()
            .expect("capacity")
            .contains("2 of 3")
    );
    let first = &v["data"]["cycles"][0];
    assert_eq!(first["committed"], 10);
    assert_eq!(first["done"], 10);
    assert!((first["ratio"].as_f64().expect("ratio") - 1.0).abs() < 1e-9);
    let third = window(&repo, -1, 5, None);
    repo.assign(id(&third), &repo.done_ticket("8"));
    repo.assign(id(&third), &repo.done_ticket("2"));
    repo.ok(&["cycle", "close", id(&third)]);
    let open = window(&repo, 10, 16, None);
    let a = repo.ticket("todo", "1");
    let assigned = repo.ok(&["cycle", "assign", &a, id(&open)]);
    let v = repo.ok(&["cycle", "velocity"]);
    assert_eq!(v["data"]["cycles"].as_array().expect("cycles").len(), 3);
    assert!((v["data"]["mean"].as_f64().expect("mean") - 10.0).abs() < 1e-9);
    assert!(v["data"]["stddev"].as_f64().expect("stddev").abs() < 1e-9);
    assert_eq!(v["data"]["capacity"], assigned["data"]["capacity"]);
    assert_eq!(
        v["data"]["capacity_limit"],
        assigned["data"]["capacity_limit"]
    );
    assert_eq!(v["data"]["capacity_limit"], 10);
}

#[test]
fn velocity_truncates_an_early_closed_cycle_window_and_rejects_last_zero() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleVelocity
    let repo = Repo::new();
    let a = utc_window(&repo, 0, 6);
    utc_window(&repo, 7, 8);
    repo.ok(&["cycle", "close", id(&a)]);
    let v = repo.ok(&["cycle", "velocity"]);
    let c = &v["data"]["cycles"][0];
    assert_eq!(c["end"], utc(0), "effective end is the close day");
    assert_ne!(c["end"], utc(6));
    let out = repo.frob(&["cycle", "velocity", "--last", "0"]);
    assert_eq!(code(&out), 2);
}

#[test]
fn velocity_agrees_with_the_close_record_and_ignores_unassigned_done_work() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleVelocity
    // frob:tests crates/frob-pm/src/cycle/velocity.rs::delivery
    let repo = Repo::new();
    let a = utc_window(&repo, 0, 6);
    utc_window(&repo, 7, 8);
    let done = repo.done_ticket("3");
    let todo = repo.ticket("todo", "5");
    repo.assign(id(&a), &done);
    repo.assign(id(&a), &todo);
    // Done today inside A's window but never committed to it.
    repo.done_ticket("13");
    let closed = repo.ok(&["cycle", "close", id(&a)])["data"]["cycle"].clone();
    assert_eq!(closed["commitment"]["committed"], 8);
    assert_eq!(closed["commitment"]["done"], 3);
    let v = repo.ok(&["cycle", "velocity"]);
    let c = &v["data"]["cycles"][0];
    assert_eq!(c["committed"], closed["commitment"]["committed"]);
    assert_eq!(c["done"], closed["commitment"]["done"]);
    assert_eq!(c["ratio"], closed["commitment"]["ratio"]);
    assert_eq!(c["unplanned_done"], 13);
    assert!((v["data"]["mean"].as_f64().expect("mean") - 3.0).abs() < 1e-9);
}

#[test]
fn state_is_derived_from_the_clock_in_show_list_and_assign() {
    // frob:ticket 01M413V82EXMRXXVWZN0MQNY3G
    let repo = Repo::new();
    let today = utc_window(&repo, 0, 6);
    let tomorrow = utc_window(&repo, 7, 13);
    assert_eq!(today["state"], "active");
    assert_eq!(tomorrow["state"], "planned");
    assert_eq!(
        repo.ok(&["cycle", "show", id(&today)])["data"]["cycle"]["state"],
        "active"
    );
    let list = repo.ok(&["cycle", "list"]);
    let states: Vec<&str> = list["data"]["cycles"]
        .as_array()
        .expect("cycles")
        .iter()
        .map(|c| c["state"].as_str().expect("state"))
        .collect();
    assert_eq!(states, ["active", "planned"]);
    // The overlap refusal and assign see the same derived state.
    let (s, e) = (utc(3), utc(4));
    let out = repo.frob(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "g"]);
    assert!(String::from_utf8_lossy(&out.stdout).contains("(active)"));
}

#[test]
fn a_cycle_starting_tomorrow_is_planned_and_a_closed_cycle_stays_closed() {
    // frob:ticket 01M413V82EXMRXXVWZN0MQNY3G
    let repo = Repo::new();
    let c = utc_window(&repo, 0, 6);
    let closed = repo.ok(&["cycle", "close", id(&c)])["data"]["cycle"].clone();
    assert_eq!(closed["state"], "closed");
    assert_eq!(
        repo.ok(&["cycle", "show", id(&c)])["data"]["cycle"]["state"],
        "closed"
    );
    let later = utc_window(&repo, 8, 14);
    assert_eq!(later["state"], "planned");
}

#[test]
fn plan_proposes_a_fill_to_capacity_and_apply_assigns_idempotently() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CyclePlan
    // frob:tests crates/frob-pm/src/cycle/plan.rs::plan_fill
    let repo = Repo::new();
    let c = window(&repo, -1, 5, Some("5"));
    repo.ticket("todo", "3");
    repo.ticket("todo", "3");
    repo.ticket("todo", "2");
    let dry = repo.ok(&["cycle", "plan", id(&c)]);
    assert_eq!(dry["data"]["applied"], false);
    assert_eq!(dry["data"]["committed_after"], 5);
    assert_eq!(dry["data"]["picks"].as_array().expect("picks").len(), 2);
    let left = dry["data"]["left_out"].as_array().expect("left");
    assert_eq!(left.len(), 1);
    assert!(
        left[0]["reason"]
            .as_str()
            .expect("r")
            .contains("5-point limit")
    );
    let shown = repo.ok(&["cycle", "show", id(&c)]);
    assert!(
        member_ids(&shown["data"]["cycle"]).is_empty(),
        "a dry run writes nothing"
    );
    let applied = repo.ok(&["cycle", "plan", id(&c), "--apply"]);
    assert_eq!(applied["data"]["applied"], true);
    assert_eq!(applied["data"]["committed_after"], 5);
    let shown = repo.ok(&["cycle", "show", id(&c)]);
    assert_eq!(member_ids(&shown["data"]["cycle"]).len(), 2);
    let again = repo.ok(&["cycle", "plan", id(&c), "--apply"]);
    assert_eq!(again["already"], true);
    assert!(again["data"]["picks"].as_array().expect("picks").is_empty());
    assert_eq!(
        again["data"]["already_in_cycle"]
            .as_array()
            .expect("a")
            .len(),
        2
    );
}

#[test]
fn plan_without_enforced_capacity_is_refused_unless_points_is_given() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CyclePlan
    let repo = Repo::new();
    let c = window(&repo, -1, 5, None);
    repo.ticket("todo", "3");
    repo.ticket("todo", "3");
    let out = repo.frob(&["cycle", "plan", id(&c)]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-NO-CAPACITY");
    let v = repo.ok(&["cycle", "plan", id(&c), "--points", "4"]);
    assert_eq!(v["data"]["picks"].as_array().expect("picks").len(), 1);
    assert_eq!(v["data"]["capacity_limit"], 4);
}

/// The issue codes `ticket doctor` reports for cycles, with `--fix` when asked.
fn pm_codes(repo: &Repo, fix: bool) -> Vec<String> {
    let mut args = vec!["ticket", "doctor"];
    if fix {
        args.push("--fix");
    }
    let out = repo.frob(&args);
    json(&out)["data"]["pm_issues"]
        .as_array()
        .expect("pm_issues")
        .iter()
        .map(|i| i["code"].as_str().expect("code").to_owned())
        .collect()
}

#[test]
fn doctor_is_clean_after_an_early_close_and_a_same_day_recreate() {
    // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
    // frob:tests crates/frob-pm/src/fold.rs::apply_transition
    // frob:tests crates/frob-pm/src/store.rs::PmStore.create
    let repo = Repo::new();
    let (s, e) = (utc(0), utc(1));
    let first = utc_window(&repo, 0, 1);
    repo.ok(&["cycle", "close", id(&first)]);
    assert_eq!(pm_codes(&repo, false), Vec::<String>::new());
    let second = repo.ok(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "c"]);
    let (a, b) = (
        first["alias"].as_str().expect("alias"),
        second["data"]["cycle"]["alias"].as_str().expect("alias"),
    );
    assert_ne!(a, b);
    assert_eq!(b, format!("{a}.2"));
    assert_eq!(pm_codes(&repo, false), Vec::<String>::new());
    // The suffix is stored, so the event and the frontmatter both carry it.
    let stored = folded(&repo);
    assert_eq!(stored.iter().map(|c| c.ordinal).collect::<Vec<_>>(), [1, 2]);
}

#[test]
fn close_with_next_goal_on_a_reused_range_gets_a_unique_alias() {
    // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
    // frob:tests crates/frob/src/cycle_cmd.rs::create_next
    let repo = Repo::new();
    let first = utc_window(&repo, -2, -1);
    repo.ok(&["cycle", "close", id(&first)]);
    let (s, e) = (utc(-2), utc(-1));
    // Same range as the closed one, then closing it creates a following cycle with a unique alias.
    let again = repo.ok(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "x"]);
    assert_eq!(
        again["data"]["cycle"]["alias"],
        format!("{s}..{e}.2").as_str()
    );
    repo.ok(&[
        "cycle",
        "close",
        id(&again["data"]["cycle"]),
        "--next-goal",
        "n",
        "--next-days",
        "2",
    ]);
    assert_eq!(pm_codes(&repo, false), Vec::<String>::new());
}

#[test]
fn doctor_fix_numbers_existing_duplicate_aliases_in_creation_order() {
    // frob:ticket 01M41KS5P8EGFFGBQSMRFBAJ8P
    // frob:tests crates/frob-pm/src/doctor.rs::PmStore.renumber_duplicates
    let repo = Repo::new();
    let (s, e) = (utc(0), utc(1));
    let first = utc_window(&repo, 0, 1);
    repo.ok(&["cycle", "close", id(&first)]);
    let second = repo.ok(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "b"]);
    repo.ok(&["cycle", "close", id(&second["data"]["cycle"])]);
    let third = repo.ok(&["cycle", "new", "--start", &s, "--end", &e, "--goal", "c"]);
    // A ledger written before suffixes were stored: every cycle of the range claims ordinal 1.
    let ledger = repo.ledger();
    let store = PmStore::new(&ledger);
    for c in folded(&repo).iter().filter(|c| c.ordinal > 1) {
        store
            .set_field(ObjectKind::Cycle, c.id, "ordinal", Some(1.into()))
            .expect("legacy ordinal");
    }
    let before = pm_codes(&repo, false);
    assert_eq!(before, vec!["E-PM-ALIAS".to_owned()]);
    pm_codes(&repo, true);
    assert_eq!(pm_codes(&repo, false), Vec::<String>::new());
    let ids: Vec<String> = [&first, &second["data"]["cycle"], &third["data"]["cycle"]]
        .iter()
        .map(|c| id(c).to_owned())
        .collect();
    let mut cycles = folded(&repo);
    cycles.sort_by_key(|c| c.id);
    assert_eq!(
        cycles.iter().map(|c| c.id.to_string()).collect::<Vec<_>>(),
        ids
    );
    assert_eq!(
        cycles.iter().map(|c| c.ordinal).collect::<Vec<_>>(),
        [1, 2, 3]
    );
}

// frob:ticket 01M4FDQFHJKT30DHZEEA6GWB4R
// frob:tests crates/frob-pm/src/cycle/velocity.rs::done_facts
#[test]
fn a_retroactive_closeout_is_not_delivered_work_of_the_current_cycle() {
    let repo = Repo::new();
    repo.done_ticket("5");
    let late = repo.ticket("todo", "3");
    repo.ok(&[
        "ticket",
        "evidence",
        "add",
        &late,
        "--provider",
        "file",
        "--ref",
        "frob.toml",
    ]);
    repo.ok(&[
        "ticket",
        "closeout",
        &late,
        "--reason",
        "finished in a closed cycle",
    ]);
    let facts = frob_pm::cycle::velocity::done_facts(&repo.ledger()).expect("facts");
    assert_eq!(facts.len(), 1, "only the ordinary close counts: {facts:?}");
    assert_eq!(facts[0].points, 5);
}

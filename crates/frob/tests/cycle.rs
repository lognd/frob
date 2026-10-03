//! `cycle new`, `show`, `list` and `close`: defaults, overlap, idempotency, carry-over and refusals.
// frob:ticket 01M4069RPPQE1ES1914K6V6Y0D

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
use frob_lease::{Holder, LeaseConfig, LeaseStore};
use frob_pm::event::Op;
use frob_pm::{ObjectId, ObjectKind, PmStore};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

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
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn run(&self, args: &[&str]) -> Output {
        Command::cargo_bin("frob")
            .expect("frob binary")
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
        frob_ledger::Ledger::open(repo, cfg.ledger())
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
        let store = LeaseStore::open(&repo, LeaseConfig::default()).expect("store");
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
        "2026-10-05",
        "--goal",
        "Ship PM",
        "--capacity",
        "13",
    ]);
    assert_eq!(v["verb"], "cycle.new");
    assert_eq!(v["already"], false);
    let c = &v["data"]["cycle"];
    assert_eq!(c["end"], "2026-10-11");
    assert_eq!(c["alias"], "2026-10-05..2026-10-11");
    assert_eq!(c["capacity_points"], 13);
    assert_eq!(c["state"], "planned");
    let again = repo.ok(&[
        "cycle",
        "new",
        "--start",
        "2026-10-05",
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
        "2026-10-05",
        "--end",
        "2026-10-11",
        "--goal",
        "Ship PM",
        "--capacity-points",
        "13",
    ]);
    assert_eq!(explicit["already"], true);
    let out = repo.frob(&["cycle", "new", "--start", "2026-10-05", "--goal", "Other"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-EXISTS");
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 1);
}

#[test]
fn overlapping_an_open_cycle_is_refused_with_a_remedy() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleNew
    let repo = Repo::new();
    repo.new_cycle("2026-10-05", "first");
    let out = repo.frob(&["cycle", "new", "--start", "2026-10-11", "--goal", "second"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-OVERLAP");
    assert!(
        e["remedy"]
            .as_str()
            .expect("remedy")
            .contains("--start 2026-10-12")
    );
    let out = repo.frob(&[
        "cycle",
        "new",
        "--start",
        "2026-10-12",
        "--end",
        "2026-10-01",
        "--goal",
        "g",
    ]);
    assert_eq!(code(&out), 2);
    assert_eq!(json(&out)["error"]["code"], "E-CYCLE-WINDOW");
    repo.new_cycle("2026-10-12", "second");
    assert_eq!(repo.ok(&["cycle", "list"])["data"]["count"], 2);
}

#[test]
fn close_is_refused_while_a_member_is_in_progress_with_a_live_lease() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleClose
    let repo = Repo::new();
    let c = repo.new_cycle("2026-10-05", "first");
    repo.new_cycle("2026-10-12", "second");
    let busy = repo.ticket("in-progress", "3");
    repo.assign(id(&c), &busy);
    repo.lease(&busy);
    let handle = format!("~{}", &busy[19..]);
    let out = repo.frob(&["cycle", "close", "2026-10-05..2026-10-11"]);
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
    let repo = Repo::new();
    let c = repo.new_cycle("2026-10-05", "first");
    let next = repo.new_cycle("2026-10-12", "second");
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
    let target = repo.ok(&["cycle", "show", "2026-10-12..2026-10-18"]);
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
    let c = repo.new_cycle("2026-10-05", "first");
    let todo = repo.ticket("todo", "3");
    repo.assign(id(&c), &todo);
    let out = repo.frob(&["cycle", "close", id(&c)]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-NO-NEXT");
    let remedy = e["remedy"].as_str().expect("remedy");
    assert!(remedy.contains("cycle new --start 2026-10-12") && remedy.contains("--carry-to"));
    assert_eq!(
        repo.ok(&["cycle", "show", id(&c)])["data"]["cycle"]["state"],
        "planned"
    );
    let far = repo.new_cycle("2026-12-01", "far");
    let skipped = repo.new_cycle("2026-11-01", "mid");
    let v = repo.ok(&["cycle", "close", id(&c), "--carry-to", id(&far)]);
    assert_eq!(v["data"]["cycle"]["carried"][0]["to"], far["id"]);
    assert_ne!(far["id"], skipped["id"]);
    let all_done = repo.new_cycle("2027-01-01", "empty");
    let v = repo.ok(&["cycle", "close", id(&all_done)]);
    assert_eq!(v["data"]["cycle"]["commitment"]["ratio"], Value::Null);
}

#[test]
fn show_and_list_report_cycles_and_unknown_references_suggest() {
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleShow
    // frob:tests crates/frob/src/cycle_cmd.rs::CycleList
    let repo = Repo::new();
    let a = repo.new_cycle("2026-10-12", "second");
    repo.new_cycle("2026-10-05", "first");
    let list = repo.ok(&["cycle", "list"]);
    assert_eq!(list["data"]["count"], 2);
    assert_eq!(list["data"]["cycles"][0]["goal"], "first");
    for r in [
        id(&a),
        a["handle"].as_str().expect("handle"),
        "2026-10-12..2026-10-18",
    ] {
        assert_eq!(
            repo.ok(&["cycle", "show", r])["data"]["cycle"]["goal"],
            "second",
            "{r}"
        );
    }
    assert!(repo.ok(&["cycle", "show"])["data"]["cycle"]["goal"].is_string());
    let out = repo.frob(&["cycle", "show", "2026-10-12..2026-10-19"]);
    assert_eq!(code(&out), 3);
    let e = &json(&out)["error"];
    assert_eq!(e["code"], "E-CYCLE-NOT-FOUND");
    assert_eq!(e["remedy"], "frob cycle show 2026-10-12..2026-10-18");
}

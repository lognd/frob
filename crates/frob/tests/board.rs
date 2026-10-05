//! `frob board`: the text snapshot at a fixed width and clock, card age from events, and the JSON shape.
// frob:ticket 01M4069W45P08YPC4YH4XZVMNC

mod common;

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::process::Output;
use std::time::Duration;

use frob_cli::board_cmd::{FALLBACK_WIDTH, resolve_width};
use frob_ledger::TicketId;
use frob_ledger::event::{Event, EventBody, TransitionData};
use frob_ledger::index::Summary;
use frob_ledger::model::{Category, Stamp};
use frob_pm::board::{self, Input, RenderOptions};
use frob_pm::rules::wip::{self, WipLimits};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use insta::assert_snapshot;
use serde_json::Value;

/// The fixed clock of the snapshot: 2026-10-10T12:00:00Z.
fn now() -> Stamp {
    "2026-10-10T12:00:00Z".parse().expect("stamp")
}

fn at(days_ago: i64, extra_secs: i64) -> Stamp {
    Stamp::from_unix(now().unix() - days_ago * 86_400 - extra_secs)
}

/// A summary with the given category, class and blocked flag, last touched `updated`.
fn summary(
    n: u8,
    title: &str,
    category: &str,
    class: &str,
    blocked: bool,
    created: Stamp,
) -> Summary {
    let id: TicketId = format!("01M4069W45P08YPC4YH4XZVM{n:02}")
        .parse()
        .expect("ulid");
    Summary {
        id,
        handle: format!("~4XZVM{n:02}"),
        title: title.to_owned(),
        ty: "task".parse().expect("type"),
        category: category.parse().expect("category"),
        outcome: (category == "done").then(|| "fixed".parse().expect("outcome")),
        priority: "medium".parse().expect("priority"),
        class: class.parse().expect("class"),
        due: None,
        points: Some(3),
        parent: None,
        created,
        updated: created,
        blocked,
    }
}

fn transition(to: &str, when: Stamp) -> Event {
    let mut e = Event::new(
        gob_time::Clock::now(&gob_time::SystemClock),
        "lognd",
        EventBody::Transition(TransitionData {
            from: Category::Todo,
            to: to.parse().expect("category"),
            outcome: None,
            reason: None,
        }),
    );
    e.at = when;
    e
}

/// A board with every feature: a lane card, an over-limit in-progress column, a stale holder, a blocked, a triage and a done card.
fn fixture() -> Input {
    let tickets = vec![
        summary(
            1,
            "Fix the release",
            "in-progress",
            "expedite",
            false,
            at(9, 0),
        ),
        summary(
            2,
            "Cycle planning",
            "in-progress",
            "standard",
            false,
            at(9, 0),
        ),
        summary(
            3,
            "Board verb with a very long title that needs wrapping",
            "in-progress",
            "standard",
            false,
            at(9, 0),
        ),
        summary(
            4,
            "Lockfiles serialize",
            "in-progress",
            "standard",
            false,
            at(9, 0),
        ),
        summary(5, "Queued work", "todo", "standard", false, at(2, 0)),
        summary(6, "Waits on a blocker", "todo", "standard", true, at(2, 0)),
        summary(7, "Needs a decision", "triage", "standard", false, at(1, 0)),
        summary(8, "Caf\u{e9} shipped", "done", "standard", false, at(9, 0)),
        summary(9, "Hot fix queued", "todo", "expedite", false, at(1, 0)),
    ];
    let id = |n: usize| tickets[n].id;
    let live: BTreeSet<TicketId> = [id(0), id(1), id(2)].into_iter().collect();
    let limits = WipLimits {
        in_progress: 1,
        expedite_max: 1,
    };
    let in_progress: Vec<Summary> = tickets[..4].to_vec();
    let wip = wip::count(in_progress, Some(&live), limits.expedite_max);
    let entered: BTreeMap<TicketId, Stamp> = [
        (id(0), at(0, 5 * 3_600)),
        (id(1), at(3, 100)),
        (id(2), at(0, 20 * 60)),
        (id(3), at(6, 0)),
        (id(7), at(1, 0)),
    ]
    .into_iter()
    .collect();
    let holders: BTreeMap<TicketId, String> = [
        (id(0), "lognd".to_owned()),
        (id(1), "agent-b".to_owned()),
        (id(2), "agent-c".to_owned()),
    ]
    .into_iter()
    .collect();
    Input {
        tickets,
        wip,
        limits,
        entered,
        holders,
        doable_order: Vec::new(),
        now: now(),
        show: board::DEFAULT_SHOWN,
    }
}

#[test]
fn text_board_at_a_fixed_width_and_clock() {
    // frob:tests crates/frob-pm/src/board.rs::render
    let b = board::build(&fixture());
    let wide = board::render(
        &b,
        &RenderOptions {
            width: 100,
            color: false,
        },
    );
    assert!(wide.iter().all(|l| l.is_ascii()), "ASCII only");
    assert!(wide.iter().all(|l| l.len() <= 100), "fits the width");
    assert_snapshot!("board_text_100", wide.join("\n"));
    let narrow = board::render(
        &b,
        &RenderOptions {
            width: 50,
            color: false,
        },
    );
    assert!(narrow.iter().all(|l| l.len() <= 50), "stacked fits too");
    assert_snapshot!("board_text_50_stacked", narrow.join("\n"));
}

#[test]
fn over_limit_header_is_red_only_with_color() {
    // frob:tests crates/frob-pm/src/board.rs::render
    let b = board::build(&fixture());
    let plain = board::render(
        &b,
        &RenderOptions {
            width: 100,
            color: false,
        },
    )
    .join("\n");
    let red = board::render(
        &b,
        &RenderOptions {
            width: 100,
            color: true,
        },
    )
    .join("\n");
    assert!(plain.contains("in-progress 2/1 !"));
    assert!(!plain.contains('\u{1b}'));
    assert!(red.contains("\u{1b}[31min-progress 2/1 !"));
}

#[test]
fn counts_and_limits_come_from_the_shared_wip_count() {
    // frob:tests crates/frob-pm/src/board.rs::build
    let input = fixture();
    let b = board::build(&input);
    let col = &b.columns[2];
    assert_eq!(col.count, input.wip.standard.len());
    assert_eq!(col.limit, Some(1));
    assert!(col.over);
    // The stale holder is listed, marked and not counted.
    assert_eq!(col.cards.len(), 3);
    assert!(col.cards.iter().any(|c| c.stale && c.handle == "~4XZVM04"));
    let lane = b.expedite.expect("lane");
    assert_eq!((lane.count, lane.limit, lane.over), (1, Some(1), false));
    assert_eq!(lane.cards[0].handle, "~4XZVM01");
    assert_eq!(lane.cards.len(), 2, "queued expedite sits in the lane too");
}

#[test]
fn a_ticket_in_progress_for_three_days_reads_3d() {
    // frob:tests crates/frob-pm/src/board.rs::entered
    let s = summary(1, "t", "in-progress", "standard", false, at(9, 0));
    let events = [
        transition("in-progress", at(8, 0)),
        transition("todo", at(5, 0)),
        transition("in-progress", at(3, 120)),
    ];
    assert_eq!(board::entered(&events, &s), at(3, 120));
    let mut input = fixture();
    input.tickets = vec![s.clone()];
    input.entered = BTreeMap::from([(s.id, board::entered(&events, &s))]);
    input.wip = wip::count(vec![s], None, 1);
    let b = board::build(&input);
    let card = &b
        .expedite
        .as_ref()
        .map_or(&b.columns[2], |_| &b.columns[2])
        .cards[0];
    assert_eq!(card.age, "3d");
    assert_eq!(card.age_secs, 3 * 86_400 + 120);
}

#[test]
fn entered_falls_back_to_creation() {
    // frob:tests crates/frob-pm/src/board.rs::entered
    let s = summary(1, "t", "todo", "standard", false, at(4, 0));
    assert_eq!(board::entered(&[], &s), at(4, 0));
}

#[test]
fn old_done_tickets_leave_the_board_and_epics_are_left_off() {
    // frob:tests crates/frob-pm/src/board.rs::shown
    let s = summary(1, "t", "done", "standard", false, at(30, 0));
    assert!(!board::shown(&s, at(8, 0), now()));
    assert!(board::shown(&s, at(6, 0), now()));
    let mut epic = summary(2, "e", "todo", "standard", false, at(1, 0));
    epic.ty = "epic".parse().expect("type");
    assert!(!board::shown(&epic, at(1, 0), now()));
}

#[test]
fn width_prefers_the_flag_then_terminal_columns_then_the_fallback() {
    // frob:tests crates/frob/src/board_cmd.rs::resolve_width
    assert_eq!(resolve_width(Some(72), Some("200"), true), 72);
    assert_eq!(resolve_width(None, Some("132"), true), 132);
    assert_eq!(resolve_width(None, Some("132"), false), FALLBACK_WIDTH);
    assert_eq!(resolve_width(None, Some("junk"), true), FALLBACK_WIDTH);
    assert_eq!(resolve_width(Some(0), None, false), FALLBACK_WIDTH);
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

fn frob(dir: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .env_remove("COLUMNS")
        .args(args)
        .output()
        .expect("run frob")
}

fn ok(dir: &Path, args: &[&str]) -> Value {
    let out = frob(dir, args);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{args:?}: {}",
        String::from_utf8_lossy(&out.stdout)
    );
    serde_json::from_slice(&out.stdout).expect("json")
}

/// A repository with a triage, a todo and a stale in-progress ticket.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    ok(p, &["--json", "init"]);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    ok(
        p,
        &[
            "--json",
            "ticket",
            "new",
            "--title",
            "queued",
            "--type",
            "task",
            "--category",
            "todo",
        ],
    );
    ok(
        p,
        &[
            "--json",
            "ticket",
            "new",
            "--title",
            "unsorted",
            "--type",
            "task",
            "--category",
            "triage",
        ],
    );
    let id = ok(
        p,
        &[
            "--json",
            "ticket",
            "new",
            "--title",
            "abandoned",
            "--type",
            "task",
            "--category",
            "todo",
        ],
    )["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let repo = gob_git::Repo::discover(p).expect("discover");
    let cfg = frob_cli::config::FrobConfig::load(p).expect("config");
    frob_ledger::Ledger::open(
        repo,
        cfg.ledger(),
        std::sync::Arc::new(gob_time::SystemClock),
    )
    .transition(id.parse().expect("ulid"), Category::InProgress, None, None)
    .expect("start");
    dir
}

#[test]
fn json_shape_carries_the_lane_and_the_five_columns() {
    // frob:tests crates/frob/src/board_cmd.rs::BoardVerb
    let dir = repo();
    let v = ok(dir.path(), &["--json", "board"]);
    assert_eq!(v["verb"], "board");
    let data = &v["data"];
    assert!(data.get("lines").is_none(), "text rows stay out of JSON");
    let board = &data["board"];
    let titles: Vec<&str> = board["columns"]
        .as_array()
        .expect("columns")
        .iter()
        .map(|c| c["title"].as_str().expect("title"))
        .collect();
    assert_eq!(titles, ["triage", "todo", "in-progress", "blocked", "done"]);
    let lane = &board["expedite"];
    assert_eq!(lane["title"], "expedite");
    assert_eq!(lane["limit"], 1);
    let col = |k: &str| {
        board["columns"]
            .as_array()
            .expect("columns")
            .iter()
            .find(|c| c["kind"] == k)
            .expect("column")
            .clone()
    };
    assert_eq!(col("triage")["count"], 1);
    assert_eq!(col("todo")["count"], 1);
    let wip = col("in-progress");
    // The lease was never taken: the holder is stale, listed, not counted.
    assert_eq!(wip["count"], 0);
    assert_eq!(wip["limit"], 2);
    assert_eq!(wip["over"], false);
    let card = &wip["cards"][0];
    assert_eq!(card["title"], "abandoned");
    assert_eq!(card["stale"], true);
    for key in [
        "handle", "title", "points", "category", "class", "holder", "age", "age_secs", "stale",
        "due",
    ] {
        assert!(card.get(key).is_some(), "card key {key}");
    }
}

#[test]
fn text_mode_prints_ascii_rows_at_the_requested_width() {
    // frob:tests crates/frob/src/board_cmd.rs::BoardVerb
    let dir = repo();
    let out = frob(dir.path(), &["--text", "board", "--width", "96"]);
    assert_eq!(out.status.code(), Some(0));
    let text = String::from_utf8(out.stdout).expect("utf8");
    assert!(text.is_ascii());
    assert!(text.lines().all(|l| l.len() <= 96), "{text}");
    // frob:ticket 01M41B2P3B5KVG5FJ5B0X2ANR8
    assert!(!text.contains("board: ok"), "no envelope header: {text}");
    assert!(!text.contains("lines:"), "no envelope key: {text}");
    assert!(
        text.starts_with("expedite") || text.starts_with("triage"),
        "{text}"
    );
    assert!(
        text.lines().all(|l| !l.trim_start().starts_with("- ~")),
        "{text}"
    );
    for needle in [
        "triage 1",
        "todo 1",
        "in-progress 0/2",
        "blocked 0",
        "done 0",
        "STALE",
        "expedite 0/1",
    ] {
        assert!(text.contains(needle), "{needle} in\n{text}");
    }
}

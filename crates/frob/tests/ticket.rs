//! End-to-end tests of the `ticket` verbs and the ledger merge driver against temporary repositories.

use std::path::{Path, PathBuf};
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

/// A repository on `main` with an identity and `frob init` already run.
struct Repo {
    dir: tempfile::TempDir,
}

fn git(dir: &Path, args: &[&str]) -> String {
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
        "git {args:?} failed: {}{}",
        out.stdout,
        out.stderr
    );
    out.stdout.trim().to_owned()
}

fn frob_bin() -> PathBuf {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .get_program()
        .into()
}

impl Repo {
    fn new(branch_mode: bool) -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        git(dir.path(), &["init", "-q"]);
        git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
        git(dir.path(), &["config", "user.name", "Test User"]);
        git(dir.path(), &["config", "user.email", "test@example.com"]);
        // gob-git compares raw disk bytes with blobs, so CRLF conversion would look like local edits.
        git(dir.path(), &["config", "core.autocrlf", "false"]);
        let repo = Self { dir };
        assert_eq!(code(&repo.frob(&["init"])), 0);
        let driver = format!("{} merge-driver %O %A %B %P", frob_bin().display());
        git(
            repo.path(),
            &["config", "merge.frob-ledger.driver", &driver],
        );
        if branch_mode {
            let toml = repo.path().join("frob.toml");
            let text = std::fs::read_to_string(&toml).expect("frob.toml");
            std::fs::write(
                &toml,
                text.replace("ref_mode = \"trunk\"", "ref_mode = \"branch\""),
            )
            .expect("write");
        }
        git(repo.path(), &["add", "-A"]);
        git(repo.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn path(&self) -> &Path {
        self.dir.path()
    }

    fn frob(&self, args: &[&str]) -> Output {
        Command::cargo_bin("frob")
            .expect("frob binary")
            .current_dir(self.path())
            .env_remove("FROB_LOG")
            .arg("--json")
            .args(args)
            .output()
            .expect("run frob")
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

    fn id_of(&self, args: &[&str]) -> String {
        self.ok(args)["data"]["id"].as_str().expect("id").to_owned()
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

#[test]
fn new_update_close_makes_three_commits_and_frontmatter_equals_the_fold() {
    let repo = Repo::new(false);
    let id = repo.id_of(&["ticket", "new", "--title", "Lifecycle", "--type", "task"]);
    repo.ok(&[
        "ticket",
        "update",
        &id,
        "--priority",
        "high",
        "--points",
        "5",
    ]);
    let closed = repo.ok(&["ticket", "close", &id, "--outcome", "fixed"]);
    assert_eq!(closed["data"]["category"], "done");
    assert_eq!(closed["data"]["outcome"], "fixed");

    let ledger_repo = gob_git::Repo::discover(repo.path()).expect("discover");
    // base + new + update (two events, one commit) + close.
    let mut commits = Vec::new();
    let mut cur = ledger_repo.rev_parse("refs/heads/main").expect("tip");
    while let Ok(parent) = ledger_repo.rev_parse(&format!("{cur}^")) {
        let changed = ledger_repo
            .diff_names(&gob_git::TreeRef::Oid(parent), &gob_git::TreeRef::Oid(cur))
            .expect("diff");
        assert!(
            changed.iter().all(|c| c.path.starts_with("tickets/")),
            "{changed:?}"
        );
        commits.push(cur);
        cur = parent;
    }
    assert_eq!(commits.len(), 3, "new, update, close");

    let ledger = frob_ledger::Ledger::open(ledger_repo, frob_ledger::LedgerConfig::default());
    let tip = ledger
        .repo()
        .rev_parse("refs/heads/main")
        .expect("tip")
        .to_string();
    let tid: frob_ledger::TicketId = id.parse().expect("ulid");
    let events = ledger.read_events_at(&tip, tid).expect("events");
    assert_eq!(events.len(), 4, "create, priority, points, transition");
    let stored = ledger
        .read_ticket_at(&tip, tid)
        .expect("read")
        .expect("present");
    assert_eq!(
        frob_ledger::fold::fold(tid, &events).expect("fold").ticket,
        stored
    );

    let doctor = repo.ok(&["ticket", "doctor"]);
    assert_eq!(doctor["data"]["ok"], true);
}

#[test]
fn ambiguous_handle_exits_3_listing_both_candidates() {
    let repo = Repo::new(false);
    for title in ["first", "second"] {
        repo.ok(&["ticket", "new", "--title", title, "--alias", "T-0042"]);
    }
    let out = repo.frob(&["ticket", "show", "T-0042"]);
    assert_eq!(code(&out), 3);
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-TICKET-AMBIGUOUS");
    assert_eq!(v["error"]["retryable"], false);
    let msg = v["error"]["message"].as_str().expect("message");
    assert!(msg.contains("first") && msg.contains("second"), "{msg}");
    let missing = repo.frob(&["ticket", "show", "~NOSUCH"]);
    assert_eq!(code(&missing), 3);
    assert_eq!(json(&missing)["error"]["code"], "E-TICKET-NOT-FOUND");
}

#[test]
fn new_with_the_same_key_returns_already() {
    let repo = Repo::new(false);
    let args = [
        "ticket",
        "new",
        "--title",
        "Once",
        "--idempotency-key",
        "k-1",
    ];
    let first = repo.ok(&args);
    let second = repo.ok(&args);
    assert_eq!(first["already"], false);
    assert_eq!(second["already"], true);
    assert_eq!(first["data"]["id"], second["data"]["id"]);
    let list = repo.ok(&["ticket", "list"]);
    assert_eq!(list["data"]["count"], 1);
}

#[test]
fn links_blocked_doable_and_repeat_semantics() {
    let repo = Repo::new(false);
    let blocker = repo.id_of(&["ticket", "new", "--title", "blocker"]);
    let waiting = repo.id_of(&[
        "ticket",
        "new",
        "--title",
        "blocked",
        "--blocked-by",
        &blocker,
    ]);
    let doable = repo.ok(&["ticket", "doable"]);
    assert_eq!(doable["data"]["count"], 1);
    assert_eq!(doable["data"]["tickets"][0]["id"], blocker.as_str());
    let blocked_list = repo.ok(&["ticket", "list", "--blocked"]);
    assert_eq!(blocked_list["data"]["tickets"][0]["id"], waiting.as_str());

    let again = repo.ok(&["ticket", "link", &blocker, &waiting, "--kind", "blocks"]);
    assert_eq!(
        again["already"], true,
        "the inverse spelling is the same edge"
    );
    let cycle = repo.frob(&["ticket", "link", &blocker, &waiting, "--kind", "blocked-by"]);
    assert_eq!(code(&cycle), 3);
    assert_eq!(json(&cycle)["error"]["code"], "E-LINK-CYCLE");

    repo.ok(&["ticket", "close", &blocker, "--outcome", "done"]);
    let doable = repo.ok(&["ticket", "doable"]);
    assert_eq!(doable["data"]["tickets"][0]["id"], waiting.as_str());
    let repeat = repo.ok(&["ticket", "close", &blocker, "--outcome", "done"]);
    assert_eq!(repeat["already"], true);

    let missing_outcome = repo.frob(&["ticket", "close", &waiting]);
    assert_eq!(code(&missing_outcome), 3);
    assert_eq!(json(&missing_outcome)["error"]["code"], "E-CLOSE-OUTCOME");

    let dropped = repo.ok(&["ticket", "drop", &waiting, "--reason", "not needed"]);
    assert_eq!(dropped["data"]["outcome"], "wont-fix");
    let reopened = repo.ok(&["ticket", "reopen", &waiting, "--reason", "needed after all"]);
    assert_eq!(reopened["data"]["category"], "todo");

    let shown = repo.ok(&["ticket", "show", &waiting, "--events"]);
    let kinds: Vec<_> = shown["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .map(|e| e["kind"].as_str().expect("kind"))
        .collect();
    assert_eq!(kinds, ["create", "transition", "transition"]);
    let log = git(repo.path(), &["log", "--format=%s", "refs/heads/main"]);
    assert!(log.contains("tickets(drop): ~"), "{log}");
    assert!(log.contains("tickets(reopen): ~"), "{log}");
}

#[test]
fn update_set_comment_brief_and_parent() {
    let repo = Repo::new(false);
    let epic = repo.id_of(&["ticket", "new", "--title", "epic", "--type", "epic"]);
    let id = repo.id_of(&[
        "ticket",
        "new",
        "--title",
        "child",
        "--parent",
        &epic,
        "--acceptance",
        "it works",
        "--scope",
        "crates/x/**",
        "--body",
        "Details here.",
    ]);
    let upd = repo.ok(&[
        "ticket",
        "update",
        &id,
        "--set",
        "labels=a,b",
        "--set",
        "assignee=logan",
        "--add-label",
        "c",
    ]);
    assert_eq!(upd["already"], false);
    let noop = repo.ok(&["ticket", "update", &id, "--set", "assignee=logan"]);
    assert_eq!(noop["already"], true);
    let bad = repo.frob(&["ticket", "update", &id, "--set", "category=done"]);
    assert_eq!(code(&bad), 2);
    let bad_points = repo.frob(&["ticket", "update", &id, "--points", "4"]);
    assert_eq!(code(&bad_points), 2);
    repo.ok(&[
        "ticket",
        "comment",
        &id,
        "--body",
        "ship it",
        "--subtype",
        "decision",
    ]);

    let children = repo.ok(&["ticket", "list", "--parent", &epic]);
    assert_eq!(children["data"]["count"], 1);
    let by_label = repo.ok(&["ticket", "list", "--label", "c"]);
    assert_eq!(by_label["data"]["count"], 1);
    let brief = repo.ok(&["ticket", "brief", &id]);
    let md = brief["data"]["markdown"].as_str().expect("markdown");
    assert!(
        md.contains("Details here.") && md.contains("it works") && md.contains("crates/x/**"),
        "{md}"
    );

    let loop_ = repo.frob(&["ticket", "link", &epic, &id, "--kind", "parent"]);
    assert_eq!(code(&loop_), 3, "a parent cycle is refused");
    repo.ok(&["ticket", "unlink", &id, &epic, "--kind", "parent"]);
    let shown = repo.ok(&["ticket", "show", &id]);
    assert!(shown["data"]["ticket"]["front"]["parent"].is_null());
}

#[test]
fn merge_driver_unions_events_from_both_branches_and_refolds() {
    let repo = Repo::new(true);
    let id = repo.id_of(&["ticket", "new", "--title", "Shared"]);
    git(repo.path(), &["checkout", "-q", "-b", "side"]);
    repo.ok(&["ticket", "update", &id, "--priority", "high"]);
    repo.ok(&["ticket", "comment", &id, "--body", "from side"]);
    git(repo.path(), &["checkout", "-q", "main"]);
    repo.ok(&["ticket", "update", &id, "--add-label", "main-label"]);
    repo.ok(&["ticket", "comment", &id, "--body", "from main"]);

    git(repo.path(), &["merge", "--no-edit", "side"]);

    let dir = repo.path().join(format!("tickets/{id}/events"));
    let count = std::fs::read_dir(&dir).expect("events dir").count();
    assert_eq!(count, 5, "create + 2 on each branch survive the merge");
    let text = std::fs::read_to_string(repo.path().join(format!("tickets/{id}/ticket.md")))
        .expect("ticket.md");
    assert!(!text.contains("<<<<<<<"), "{text}");
    assert!(
        text.contains("priority = \"high\""),
        "side's change was folded: {text}"
    );
    assert!(
        text.contains("main-label"),
        "main's change was folded: {text}"
    );
    let doctor = repo.ok(&["ticket", "doctor"]);
    assert_eq!(doctor["data"]["ok"], true, "{doctor}");
    assert_eq!(doctor["data"]["events"], 5);
    let shown = repo.ok(&["ticket", "show", &id]);
    assert_eq!(shown["data"]["summary"]["priority"], "high");
}

#[test]
fn merge_driver_fails_with_exit_1_when_the_fold_fails() {
    let repo = Repo::new(false);
    // No event file on disk and none in any history: the fold has nothing to work with.
    let id = frob_ledger::TicketId::mint();
    let scratch = repo.path().join("ours.md");
    std::fs::write(&scratch, "x").expect("seed");
    let path = format!("tickets/{id}/ticket.md");
    let out = repo.frob(&["merge-driver", "base", "ours.md", "theirs", &path]);
    assert_eq!(code(&out), 1, "{}", String::from_utf8_lossy(&out.stdout));
}

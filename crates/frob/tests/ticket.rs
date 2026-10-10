//! End-to-end tests of the `ticket` verbs and the ledger merge driver against temporary repositories.

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

mod common;

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
        common::set_done_requires(repo.path(), &["no_open_children"]);
        // `frob init` writes the driver itself; the merge below runs exactly what a user gets.
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
        common::frob_command()
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
    let id = repo.id_of(&["ticket", "new", "--title", "Lifecycle", "--type", "chore"]);
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

    let ledger = frob_ledger::Ledger::open(
        ledger_repo,
        frob_ledger::LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
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
    let blocker = repo.id_of(&["ticket", "new", "--title", "blocker", "--type", "chore"]);
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
    let md = common::ticket_markdown(repo.path(), &id);
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

fn scope_of(repo: &Repo, id: &str) -> Value {
    repo.ok(&["ticket", "show", id])["data"]["fields"]["scope"].clone()
}

#[test]
fn empty_set_on_a_list_is_refused_and_clear_empties_it_with_an_event() {
    let repo = Repo::new(false);
    let id = repo.id_of(&["ticket", "new", "--title", "t", "--scope", "a/**"]);
    let bad = repo.frob(&["ticket", "update", &id, "--set", "scope="]);
    assert_eq!(code(&bad), 2, "{}", String::from_utf8_lossy(&bad.stdout));
    assert!(String::from_utf8_lossy(&bad.stdout).contains("--clear scope"));
    assert_eq!(scope_of(&repo, &id), serde_json::json!(["a/**"]));
    let cleared = repo.ok(&["ticket", "update", &id, "--clear", "scope"]);
    assert_eq!(cleared["already"], false);
    assert_eq!(scope_of(&repo, &id), serde_json::json!([]));
    let events = repo.ok(&["ticket", "show", &id, "--events"]);
    let fields: Vec<_> = events["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .filter(|e| e["body"]["field"] == "scope")
        .collect();
    assert_eq!(fields.len(), 1, "{events}");
    let again = repo.ok(&["ticket", "update", &id, "--clear", "scope"]);
    assert_eq!(again["already"], true);
    let not_list = repo.frob(&["ticket", "update", &id, "--clear", "title"]);
    assert_eq!(code(&not_list), 2);
}

#[test]
fn add_scope_and_remove_scope_round_trip_with_noop_semantics() {
    let repo = Repo::new(false);
    let id = repo.id_of(&["ticket", "new", "--title", "t", "--scope", "a/**"]);
    repo.ok(&["ticket", "update", &id, "--add-scope", "b/**"]);
    assert_eq!(scope_of(&repo, &id), serde_json::json!(["a/**", "b/**"]));
    let dup = repo.ok(&["ticket", "update", &id, "--add-scope", "b/**"]);
    assert_eq!(dup["already"], true);
    repo.ok(&["ticket", "update", &id, "--remove-scope", "a/**"]);
    assert_eq!(scope_of(&repo, &id), serde_json::json!(["b/**"]));
    let absent = repo.ok(&["ticket", "update", &id, "--remove-scope", "zzz"]);
    assert_eq!(absent["already"], true);
    repo.ok(&["ticket", "update", &id, "--remove-scope", "b/**"]);
    assert_eq!(scope_of(&repo, &id), serde_json::json!([]));
}

#[test]
fn show_json_has_every_schema_field() {
    let repo = Repo::new(false);
    let bare = repo.id_of(&["ticket", "new", "--title", "bare"]);
    let full = repo.id_of(&[
        "ticket",
        "new",
        "--title",
        "full",
        "--scope",
        "a/**",
        "--acceptance",
        "ok",
    ]);
    for id in [bare, full] {
        let shown = repo.ok(&["ticket", "show", &id]);
        let fields = shown["data"]["fields"].as_object().expect("fields");
        for desc in frob_ledger::schema::all_schemas() {
            for f in desc.fields {
                assert!(fields.contains_key(f.key), "missing `{}` in {shown}", f.key);
            }
        }
        assert!(fields["scope"].is_array());
    }
}

/// The criterion texts of ticket `id`, in order.
fn criteria(repo: &Repo, id: &str) -> Vec<String> {
    repo.ok(&["ticket", "show", id])["data"]["fields"]["acceptance"]
        .as_array()
        .expect("acceptance list")
        .iter()
        .map(|a| a["text"].as_str().expect("text").to_owned())
        .collect()
}

/// Record file evidence on ticket `id` for the 1-based criteria `accepts`; returns the event id.
fn offer(repo: &Repo, id: &str, name: &str, accepts: &[&str]) -> String {
    std::fs::write(repo.path().join(name), name).expect("write evidence file");
    let mut args = vec![
        "ticket",
        "evidence",
        "add",
        id,
        "--provider",
        "file",
        "--ref",
        name,
    ];
    for n in accepts {
        args.push("--accepts");
        args.push(n);
    }
    repo.ok(&args)["data"]["event"]
        .as_str()
        .expect("event")
        .to_owned()
}

fn three_criteria(repo: &Repo) -> String {
    repo.id_of(&[
        "ticket",
        "new",
        "--title",
        "t",
        "--acceptance",
        "one",
        "--acceptance",
        "two",
        "--acceptance",
        "three",
    ])
}

// frob:ticket 01M4055D28TPGSJW71D09P2DKX
#[test]
fn add_acceptance_keeps_commas_whole_and_is_idempotent() {
    let repo = Repo::new(false);
    let id = repo.id_of(&[
        "ticket",
        "new",
        "--title",
        "t",
        "--acceptance",
        "one",
        "--acceptance",
        "two",
    ]);
    let text = "Given a, b and c, when it runs, then d";
    let out = repo.ok(&["ticket", "update", &id, "--add-acceptance", text]);
    assert_eq!(out["already"], false);
    assert_eq!(out["data"]["lost_evidence"], serde_json::json!([]));
    assert_eq!(criteria(&repo, &id), ["one", "two", text]);
    let again = repo.ok(&["ticket", "update", &id, "--add-acceptance", text]);
    assert_eq!(again["already"], true);
    repo.ok(&[
        "ticket",
        "update",
        &id,
        "--add-acceptance",
        "x",
        "--add-acceptance",
        "y, z",
    ]);
    assert_eq!(criteria(&repo, &id).len(), 5);
    let events = repo.ok(&["ticket", "show", &id, "--events"]);
    let field: Vec<_> = events["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .filter(|e| e["body"]["field"] == "acceptance")
        .collect();
    assert_eq!(field.len(), 2, "one field event per update: {events}");
    assert_eq!(field[0]["body"]["old"], serde_json::json!(["one", "two"]));
    assert_eq!(field[0]["body"]["new"].as_array().expect("new").len(), 3);
    assert_eq!(repo.ok(&["ticket", "doctor"])["data"]["ok"], true);
}

// frob:ticket 01M4055D28TPGSJW71D09P2DKX
#[test]
fn removing_a_criterion_with_bound_evidence_reports_it_in_data_and_warning() {
    let repo = Repo::new(false);
    let id = three_criteria(&repo);
    let ev = offer(&repo, &id, "a.txt", &["1", "3"]);
    let out = repo.ok(&["ticket", "update", &id, "--remove-acceptance", "1"]);
    let lost = out["data"]["lost_evidence"].as_array().expect("lost");
    assert_eq!(lost.len(), 1, "{out}");
    assert_eq!(lost[0]["event"], ev);
    assert_eq!(lost[0]["lost"], serde_json::json!([1]));
    assert_eq!(lost[0]["kept"], serde_json::json!([2]));
    assert!(
        out["warnings"][0].as_str().expect("warning").contains(&ev),
        "{out}"
    );
    assert_eq!(criteria(&repo, &id), ["two", "three"]);
    let text = repo.frob(&["ticket", "update", &id, "--remove-acceptance", "9"]);
    assert_eq!(code(&text), 2, "{}", String::from_utf8_lossy(&text.stdout));
    assert_eq!(repo.ok(&["ticket", "doctor"])["data"]["ok"], true);
}

// frob:ticket 01M4055D28TPGSJW71D09P2DKX
#[test]
fn evidence_keeps_pointing_at_its_own_criterion_after_an_earlier_removal() {
    let repo = Repo::new(false);
    let id = three_criteria(&repo);
    let on_two = offer(&repo, &id, "a.txt", &["2"]);
    let on_three = offer(&repo, &id, "b.txt", &["3"]);
    // Removing "one" shifts the others up: the record for "two" now means 1, "three" means 2.
    repo.ok(&["ticket", "update", &id, "--remove-acceptance", "1"]);
    // Removing the current 1 ("two") must lose exactly the record offered for "two".
    let out = repo.ok(&["ticket", "update", &id, "--remove-acceptance", "1"]);
    let lost = out["data"]["lost_evidence"].as_array().expect("lost");
    assert_eq!(lost.len(), 1, "{out}");
    assert_eq!(lost[0]["event"], on_two);
    assert_eq!(lost[0]["lost"], serde_json::json!([1]));
    assert_ne!(lost[0]["event"], on_three);
    assert_eq!(criteria(&repo, &id), ["three"]);
    // Removing "three" now loses the other record, whose recorded index (3) is long out of range.
    let final_out = repo.ok(&["ticket", "update", &id, "--remove-acceptance", "1"]);
    assert_eq!(final_out["data"]["lost_evidence"][0]["event"], on_three);
}

// frob:ticket 01M4055D28TPGSJW71D09P2DKX
#[test]
fn clear_acceptance_empties_the_list_and_reports_all_bound_evidence() {
    let repo = Repo::new(false);
    let id = three_criteria(&repo);
    let ev = offer(&repo, &id, "a.txt", &["2"]);
    let out = repo.ok(&["ticket", "update", &id, "--clear-acceptance"]);
    assert_eq!(out["data"]["lost_evidence"][0]["event"], ev);
    assert_eq!(criteria(&repo, &id), Vec::<String>::new());
    let again = repo.ok(&["ticket", "update", &id, "--clear-acceptance"]);
    assert_eq!(again["already"], true);
    assert_eq!(again["data"]["lost_evidence"], serde_json::json!([]));
    assert_eq!(repo.ok(&["ticket", "doctor"])["data"]["ok"], true);
}

// frob:ticket 01M4055D28TPGSJW71D09P2DKX
#[test]
fn set_acceptance_is_refused_naming_the_dedicated_flags_and_schema_works() {
    let repo = Repo::new(false);
    let id = three_criteria(&repo);
    let bad = repo.frob(&["ticket", "update", &id, "--set", "acceptance=a,b"]);
    assert_eq!(code(&bad), 2, "{}", String::from_utf8_lossy(&bad.stdout));
    let body = String::from_utf8_lossy(&bad.stdout);
    for flag in [
        "--add-acceptance",
        "--remove-acceptance",
        "--clear-acceptance",
    ] {
        assert!(body.contains(flag), "{body}");
    }
    let clear = repo.frob(&["ticket", "update", &id, "--clear", "acceptance"]);
    assert_eq!(code(&clear), 2);
    assert!(String::from_utf8_lossy(&clear.stdout).contains("--clear-acceptance"));
    assert_eq!(criteria(&repo, &id).len(), 3);
    let schema = repo.ok(&["ticket", "update", "--schema"]);
    assert!(schema.to_string().contains("lost_evidence"), "{schema}");
}

// frob:ticket 01M4069VZVMHVZ15RSPZQRNCXY
#[test]
fn class_defaults_to_standard_and_new_and_update_set_it() {
    let repo = Repo::new(false);
    let plain = repo.id_of(&["ticket", "new", "--title", "plain"]);
    let shown = repo.ok(&["ticket", "show", &plain]);
    assert_eq!(shown["data"]["fields"]["class"], "standard");
    assert_eq!(shown["data"]["summary"]["class"], "standard");
    let hot = repo.id_of(&["ticket", "new", "--title", "hot", "--class", "expedite"]);
    let shown = repo.ok(&["ticket", "show", &hot]);
    assert_eq!(shown["data"]["fields"]["class"], "expedite");
    assert_eq!(shown["data"]["summary"]["class"], "expedite");
    let changed = repo.ok(&["ticket", "update", &plain, "--class", "fixed-date"]);
    assert_eq!(changed["data"]["class"], "fixed-date");
    repo.ok(&[
        "ticket",
        "update",
        &plain,
        "--set",
        "due=2026-12-01T00:00:00Z",
    ]);
    let listed = repo.ok(&["ticket", "list"]);
    let rows = listed["data"]["tickets"].as_array().expect("tickets");
    let row = rows
        .iter()
        .find(|r| r["id"] == plain.as_str())
        .expect("row");
    assert_eq!(row["class"], "fixed-date");
    assert_eq!(row["due"], "2026-12-01T00:00:00Z");
    let bad = repo.frob(&["ticket", "update", &plain, "--class", "urgent"]);
    assert_eq!(code(&bad), 2);
    // unsetting returns to the default
    repo.ok(&["ticket", "update", &plain, "--set", "class="]);
    let shown = repo.ok(&["ticket", "show", &plain]);
    assert_eq!(shown["data"]["fields"]["class"], "standard");
    assert_eq!(repo.ok(&["ticket", "doctor"])["data"]["ok"], true);
}

// frob:ticket 01M4069VZVMHVZ15RSPZQRNCXY
#[test]
fn doable_lists_expedite_first_then_fixed_date_by_due() {
    let repo = Repo::new(false);
    let std_one = repo.id_of(&["ticket", "new", "--title", "std"]);
    let late = repo.id_of(&["ticket", "new", "--title", "late", "--class", "fixed-date"]);
    let soon = repo.id_of(&["ticket", "new", "--title", "soon", "--class", "fixed-date"]);
    let hot = repo.id_of(&["ticket", "new", "--title", "hot", "--class", "expedite"]);
    repo.ok(&[
        "ticket",
        "update",
        &late,
        "--set",
        "due=2026-12-01T00:00:00Z",
    ]);
    repo.ok(&[
        "ticket",
        "update",
        &soon,
        "--set",
        "due=2026-11-01T00:00:00Z",
    ]);
    let doable = repo.ok(&["ticket", "doable"]);
    let rows = doable["data"]["tickets"].as_array().expect("tickets");
    let ids: Vec<&str> = rows.iter().map(|r| r["id"].as_str().expect("id")).collect();
    assert_eq!(
        ids,
        [hot.as_str(), soon.as_str(), late.as_str(), std_one.as_str()]
    );
}

/// The warnings of an envelope as one string.
fn warnings_of(v: &Value) -> String {
    v["warnings"].to_string()
}

// frob:ticket 01M1T07NWAFVRT2V4RAPVJ9SQM
#[test]
fn zero_match_scope_warns_on_new_and_update_but_new_scope_declares_it() {
    let repo = Repo::new(false);
    let made = repo.ok(&["ticket", "new", "--title", "t", "--scope", "frob.toml"]);
    assert!(
        !warnings_of(&made).contains("matches no tracked file"),
        "{made}"
    );
    let bad = repo.ok(&[
        "ticket",
        "new",
        "--title",
        "u",
        "--scope",
        "src/nothing_here.rs",
    ]);
    let w = warnings_of(&bad);
    assert!(
        w.contains("`src/nothing_here.rs` matches no tracked file"),
        "{w}"
    );
    let id = bad["data"]["id"].as_str().expect("id").to_owned();
    let upd = repo.ok(&["ticket", "update", &id, "--add-scope", "src/other.rs"]);
    assert!(
        warnings_of(&upd).contains("`src/other.rs` matches no tracked file"),
        "{upd}"
    );
    let declared = repo.ok(&["ticket", "update", &id, "--add-new-scope", "src/fresh.rs"]);
    assert!(!warnings_of(&declared).contains("fresh.rs"), "{declared}");
    let shown = repo.ok(&["ticket", "show", &id]);
    assert!(
        shown["data"]["fields"]["labels"]
            .to_string()
            .contains("creates:src/fresh.rs")
    );
    let new_decl = repo.ok(&[
        "ticket",
        "new",
        "--title",
        "v",
        "--new-scope",
        "crates/new/**",
    ]);
    assert!(
        !warnings_of(&new_decl).contains("matches no tracked file"),
        "{new_decl}"
    );
}

// frob:ticket 01M4GKAYSGHAE5QAXN1BJBTQN2
// frob:tests crates/frob/src/ticket/read.rs::List
#[test]
fn list_full_emits_every_ticket_with_its_events_and_aliases_in_one_call() {
    let repo = Repo::new(false);
    let a = repo.id_of(&["ticket", "new", "--title", "first"]);
    let b = repo.id_of(&["ticket", "new", "--title", "second"]);
    repo.ok(&["ticket", "comment", &a, "--body", "hello"]);
    let plain = repo.ok(&["ticket", "list"]);
    assert!(plain["data"]["tickets"][0].get("events").is_none());
    let full = repo.ok(&["ticket", "list", "--full"]);
    assert_eq!(full["data"]["count"], 2);
    let rows = full["data"]["tickets"].as_array().expect("tickets");
    for row in rows {
        assert!(row["aliases"].is_array(), "{row}");
        assert!(!row["events"].as_array().expect("events").is_empty());
    }
    let by_id = |id: &str| rows.iter().find(|r| r["id"] == id).expect("row");
    let kinds = |id: &str| -> Vec<String> {
        by_id(id)["events"]
            .as_array()
            .unwrap()
            .iter()
            .map(|e| e["kind"].as_str().unwrap().to_owned())
            .collect()
    };
    assert!(kinds(&a).contains(&"comment".to_owned()), "{:?}", kinds(&a));
    assert!(!kinds(&b).contains(&"comment".to_owned()));
}

//! The D104 read-verb trims: each folded verb keeps a hidden alias that prints one deprecation line on stderr (cli.md 4.0).
// frob:ticket 01M48Q281GRJ9TTAK2VA6JJ764

mod common;

use std::path::Path;
use std::process::Output;

use serde_json::Value;

/// A committed repository with `frob init` run and one todo ticket; returns (dir, ticket id).
fn fixture() -> (tempfile::TempDir, String) {
    let dir = common::git_repo();
    assert!(run(dir.path(), &["init"]).status.success());
    common::set_done_requires(dir.path(), &[]);
    for args in [&["add", "-A"][..], &["commit", "-q", "-m", "base"][..]] {
        let st = std::process::Command::new("git")
            .args(args)
            .current_dir(dir.path())
            .status()
            .expect("git");
        assert!(st.success(), "git {args:?}");
    }
    let out = run(
        dir.path(),
        &[
            "ticket", "new", "--title", "t", "--type", "chore", "--scope", "src/**",
        ],
    );
    let id = json(&out)["data"]["id"].as_str().expect("id").to_owned();
    (dir, id)
}

fn run(dir: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(dir)
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn stderr(out: &Output) -> String {
    String::from_utf8_lossy(&out.stderr).into_owned()
}

/// The note an alias must print, naming the old and the new spelling.
fn assert_note(out: &Output, old: &str, new: &str) {
    let err = stderr(out);
    assert_eq!(err.lines().count(), 1, "one deprecation line: {err}");
    assert!(
        err.contains(&format!("`{old}` is deprecated")) && err.contains(&format!("`frob {new}`")),
        "{err}"
    );
}

// frob:tests crates/frob/src/ticket/read.rs::Brief
#[test]
fn ticket_brief_alias_matches_show_format_md() {
    let (dir, id) = fixture();
    let old = run(dir.path(), &["ticket", "brief", &id]);
    assert!(old.status.success());
    assert_note(&old, "ticket brief", "ticket show --format md");
    let md = json(&old)["data"]["markdown"]
        .as_str()
        .expect("md")
        .to_owned();
    let new = common::ticket_markdown(dir.path(), &id);
    assert_eq!(
        new.trim_end(),
        md.trim_end(),
        "same markdown under both forms"
    );
    let shown = run(dir.path(), &["ticket", "show", &id]);
    assert!(stderr(&shown).is_empty(), "no note on the new form");
}

// frob:tests crates/frob/src/ticket/read.rs::List
#[test]
fn triage_list_alias_matches_list_category_triage() {
    let (dir, _) = fixture();
    let t = json(&run(
        dir.path(),
        &[
            "ticket",
            "new",
            "--title",
            "inbox",
            "--type",
            "task",
            "--category",
            "triage",
        ],
    ));
    assert!(t["ok"].as_bool().unwrap_or(false), "{t}");
    let old = run(dir.path(), &["ticket", "triage", "list"]);
    assert_note(&old, "ticket triage list", "ticket list --category triage");
    let new = run(dir.path(), &["ticket", "list", "--category", "triage"]);
    assert!(stderr(&new).is_empty());
    let ids = |o: &Output| -> Vec<String> {
        json(o)["data"]["tickets"]
            .as_array()
            .expect("tickets")
            .iter()
            .map(|t| t["id"].as_str().expect("id").to_owned())
            .collect()
    };
    assert_eq!(ids(&old), ids(&new));
    assert_eq!(ids(&new).len(), 1);
    let bad = run(dir.path(), &["ticket", "list", "--all"]);
    assert_eq!(bad.status.code(), Some(2), "--all needs --category triage");
}

// frob:tests crates/frob-lease/src/verbs.rs::LeaseList
#[test]
fn contention_alias_matches_lease_list_contention() {
    let (dir, _) = fixture();
    let old = run(dir.path(), &["ticket", "contention"]);
    assert_note(&old, "ticket contention", "lease list --contention");
    let new = run(dir.path(), &["lease", "list", "--contention"]);
    assert!(stderr(&new).is_empty());
    assert_eq!(json(&old)["data"]["files"], json(&new)["data"]["files"]);
    let plain = run(dir.path(), &["lease", "list"]);
    assert!(
        json(&plain)["data"].get("files").is_none(),
        "files only with the flag"
    );
}

// frob:tests crates/frob-worktree/src/verbs.rs::Work
#[test]
fn start_alias_matches_work_here() {
    let (dir, id) = fixture();
    let new = run(dir.path(), &["work", "--here", &id]);
    assert!(
        new.status.success(),
        "{}",
        String::from_utf8_lossy(&new.stdout)
    );
    assert!(stderr(&new).is_empty());
    let old = run(dir.path(), &["start", &id]);
    assert_note(&old, "start", "work --here");
    let (a, b) = (json(&new), json(&old));
    assert_eq!(b["already"], true, "same holder again");
    assert_eq!(a["data"]["path"], b["data"]["path"]);
    assert_eq!(a["data"]["lease"]["scope"], b["data"]["lease"]["scope"]);
}

#[test]
fn aliases_are_hidden_from_help() {
    let (dir, _) = fixture();
    let help = |args: &[&str]| {
        let out = common::frob_command()
            .current_dir(dir.path())
            .args(args)
            .arg("--help")
            .output()
            .expect("help");
        String::from_utf8_lossy(&out.stdout).into_owned()
    };
    let top = help(&[]);
    assert!(
        !top.lines().any(|l| l.trim_start().starts_with("start ")),
        "{top}"
    );
    assert!(top.contains("work"), "{top}");
    let ticket = help(&["ticket"]);
    assert!(
        !ticket.contains("brief") && !ticket.contains("contention"),
        "{ticket}"
    );
    let triage = help(&["ticket", "triage"]);
    assert!(
        !triage.lines().any(|l| l.trim_start().starts_with("list ")),
        "{triage}"
    );
}

// frob:ticket 01M49VYK2H6WXWYNRVX0WQ67AJ
#[test]
fn every_deprecated_alias_names_a_registered_verb() {
    let dangling: Vec<String> = gob_cli::dangling_deprecations()
        .iter()
        .map(|m| format!("`{}` -> `{}`", m.verb, m.deprecated.unwrap_or_default()))
        .collect();
    assert!(
        dangling.is_empty(),
        "deprecated aliases with no registered target: {dangling:?}"
    );
    let aliases = gob_cli::all_commands()
        .filter(|m| m.deprecated.is_some())
        .count();
    assert_eq!(
        aliases, 4,
        "the four D104 aliases are registered through the attribute"
    );
}

// frob:ticket 01M49VYK2H6WXWYNRVX0WQ67AJ
#[test]
fn format_md_on_a_verb_without_a_markdown_view_names_the_supporting_verbs() {
    let (dir, _id) = fixture();
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["--format", "md", "ticket", "list"])
        .output()
        .expect("run frob");
    assert_eq!(out.status.code(), Some(2));
    let text = format!("{}{}", String::from_utf8_lossy(&out.stdout), stderr(&out));
    assert!(
        text.contains("`ticket list` has no markdown view"),
        "{text}"
    );
    assert!(text.contains("ticket show"), "{text}");
}

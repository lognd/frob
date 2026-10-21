//! `--text` views of `ticket show/list/doable` and `cycle show/list`: human snapshots, not the envelope's key tree.
// frob:ticket 01M4CTTXC1E5MQEDFMY5JDQ45M

use std::path::Path;

use insta::assert_snapshot;
use serde_json::Value;

use crate::common;

/// Run `frob <args>` in `dir` and return stdout, asserting success.
fn run(dir: &Path, args: &[&str]) -> String {
    let out = common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob");
    assert_eq!(
        out.status.code(),
        Some(0),
        "{args:?}: {}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8(out.stdout).expect("utf8")
}

/// The ULID of the ticket `ticket new` created with `args`.
fn new_ticket(dir: &Path, args: &[&str]) -> String {
    let mut a = vec!["--json", "ticket", "new"];
    a.extend_from_slice(args);
    let v: Value = serde_json::from_str(&run(dir, &a)).expect("json");
    v["data"]["id"].as_str().expect("id").to_owned()
}

/// Replace the run-dependent tokens (handles, ULIDs, dates) with fixed-width placeholders so snapshots are stable.
fn normalize(text: &str) -> String {
    let b: Vec<char> = text.chars().collect();
    let crock = |c: char| c.is_ascii_uppercase() || c.is_ascii_digit();
    let mut out = String::new();
    let mut i = 0;
    while i < b.len() {
        let rest = &b[i..];
        let run_len = rest.iter().take_while(|c| crock(**c)).count();
        let word_start = i == 0 || !b[i - 1].is_ascii_alphanumeric();
        let is_date = rest.len() >= 10
            && rest[..10].iter().enumerate().all(|(k, c)| match k {
                4 | 7 => *c == '-',
                _ => c.is_ascii_digit(),
            });
        if b[i] == '~' && rest.len() > 7 && rest[1..8].iter().all(|c| crock(*c)) {
            out.push_str("~HANDLE0");
            i += 8;
        } else if word_start
            && run_len >= 26
            && !rest.get(26).is_some_and(char::is_ascii_alphanumeric)
        {
            out.push_str("ULID______________________");
            i += 26;
        } else if is_date {
            out.push_str("YYYY-MM-DD");
            i += 10;
        } else {
            out.push(b[i]);
            i += 1;
        }
    }
    out
}

/// A repo with `frob init` run, an epic, a story under it with acceptance, and a doable task.
fn fixture() -> tempfile::TempDir {
    let dir = common::git_repo();
    run(dir.path(), &["--json", "init"]);
    let epic = new_ticket(dir.path(), &["--title", "Ship the thing", "--type", "epic"]);
    let _ = new_ticket(
        dir.path(),
        &[
            "--title",
            "Write the renderer",
            "--parent",
            &epic,
            "--points",
            "3",
            "--priority",
            "high",
            "--label",
            "ux",
            "--scope",
            "crates/**",
            "--acceptance",
            "Output is a human view",
            "--body",
            "Render rows, not a key tree.",
        ],
    );
    dir
}

// frob:tests show_rows
#[test]
fn ticket_show_text_is_a_human_view() {
    let dir = fixture();
    let all = run(dir.path(), &["--json", "ticket", "list"]);
    let v: Value = serde_json::from_str(&all).expect("json");
    let handle = v["data"]["tickets"]
        .as_array()
        .expect("tickets")
        .iter()
        .find(|t| t["title"] == "Write the renderer")
        .expect("story")["handle"]
        .as_str()
        .expect("handle")
        .to_owned();
    let text = run(
        dir.path(),
        &["--text", "ticket", "show", &handle, "--events"],
    );
    assert!(!text.starts_with("ticket show: ok"), "{text}");
    assert_snapshot!("ticket_show_text", normalize(&text));
    let epic = run(dir.path(), &["--json", "ticket", "list", "--type", "epic"]);
    let v: Value = serde_json::from_str(&epic).expect("json");
    let eh = v["data"]["tickets"][0]["handle"]
        .as_str()
        .expect("h")
        .to_owned();
    let text = run(dir.path(), &["--text", "ticket", "show", &eh]);
    assert_snapshot!("ticket_show_text_epic", normalize(&text));
}

// frob:tests list_rows
#[test]
fn ticket_list_and_doable_text_are_tables() {
    let dir = fixture();
    let list = run(dir.path(), &["--text", "ticket", "list"]);
    assert_snapshot!("ticket_list_text", normalize(&list));
    let doable = run(dir.path(), &["--text", "ticket", "doable"]);
    assert_snapshot!("ticket_doable_text", normalize(&doable));
}

// frob:tests cycle_rows
// frob:tests cycle_list_rows
#[test]
fn cycle_show_and_list_text_are_human_views() {
    let dir = fixture();
    run(
        dir.path(),
        &[
            "--json",
            "cycle",
            "new",
            "--start",
            "2026-01-05",
            "--goal",
            "First cycle",
            "--capacity",
            "8",
        ],
    );
    let list = run(dir.path(), &["--text", "cycle", "list"]);
    assert_snapshot!("cycle_list_text", normalize(&list));
    let made = run(dir.path(), &["--json", "cycle", "list"]);
    let v: Value = serde_json::from_str(&made).expect("json");
    let handle = v["data"]["cycles"][0]["handle"]
        .as_str()
        .expect("handle")
        .to_owned();
    let show = run(dir.path(), &["--text", "cycle", "show", &handle]);
    assert_snapshot!("cycle_show_text", normalize(&show));
}

// frob:tests table
#[test]
fn text_views_are_not_the_generic_key_dump() {
    let dir = fixture();
    for args in [
        &["--text", "ticket", "list"][..],
        &["--text", "ticket", "doable"][..],
    ] {
        let text = run(dir.path(), args);
        assert!(!text.contains(": ok"), "generic dump leaked: {text}");
        assert!(text.contains("Write the renderer"), "{text}");
    }
}

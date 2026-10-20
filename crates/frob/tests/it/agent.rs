//! `frob agent sync|status|uninstall` through the CLI, against tmp homes (never the real `~/.claude`).
// frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ

use std::path::Path;
use std::process::Output;

use serde_json::Value;

use crate::common;

const MANIFEST: &str = r#"[agent]
items = [
    "hook:guard = hooks/guard.py",
    "support:lib = hooks/_lib.py",
    "agent:reviewer = agents/reviewer.md",
]
hooks = ["guard:PreToolUse:Bash"]
"#;

fn frob(cwd: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).expect("stdout is JSON")
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn git(cwd: &Path, args: &[&str]) {
    let s = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .status()
        .expect("git");
    assert!(s.success(), "git {args:?}");
}

/// A repo with the manifest and its sources, committed on `main`.
fn repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let r = dir.path();
    std::fs::create_dir_all(r.join("hooks")).unwrap();
    std::fs::create_dir_all(r.join("agents")).unwrap();
    std::fs::write(r.join("frob.toml"), MANIFEST).unwrap();
    std::fs::write(
        r.join("hooks/guard.py"),
        "#!/usr/bin/env python3\nprint(1)\n",
    )
    .unwrap();
    std::fs::write(r.join("hooks/_lib.py"), "X = 1\n").unwrap();
    std::fs::write(
        r.join("agents/reviewer.md"),
        "---\nname: reviewer\n---\nReview.\n",
    )
    .unwrap();
    git(r, &["add", "-A"]);
    git(r, &["commit", "-qm", "init"]);
    dir
}

fn sync(repo: &Path, home: &Path, extra: &[&str]) -> Output {
    let mut args = vec![
        "agent",
        "sync",
        "--agent",
        "claude",
        "--home",
        home.to_str().unwrap(),
    ];
    args.extend_from_slice(extra);
    frob(repo, &args)
}

fn settings(home: &Path) -> Value {
    serde_json::from_slice(&std::fs::read(home.join("settings.json")).unwrap()).unwrap()
}

// frob:tests crates/frob/src/agent_cmd.rs::AgentSync
#[test]
fn sync_into_empty_home_is_idempotent_and_byte_identical() {
    let repo = repo();
    let home = tempfile::tempdir().unwrap();
    let out = sync(repo.path(), home.path(), &[]);
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    let h = home.path();
    let guard = std::fs::read_to_string(h.join("hooks/guard.py")).unwrap();
    assert!(guard.starts_with("#!/usr/bin/env python3\n# frob-managed: do not edit"));
    assert!(
        std::fs::read_to_string(h.join("agents/reviewer.md"))
            .unwrap()
            .starts_with("---\nname: reviewer\n---\n<!-- frob-managed")
    );
    let cmd = settings(h)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        .as_str()
        .unwrap()
        .to_owned();
    assert!(cmd.starts_with("python3 ") && cmd.ends_with("# frob-owned:guard"));

    let snap = || {
        [
            "hooks/guard.py",
            "hooks/_lib.py",
            "agents/reviewer.md",
            "settings.json",
            ".frob-agent.json",
        ]
        .map(|f| std::fs::read(h.join(f)).unwrap())
    };
    let before = snap();
    let again = sync(repo.path(), home.path(), &[]);
    assert_eq!(code(&again), 0);
    assert_eq!(
        json(&again)["data"]["agents"][0]["written"],
        serde_json::json!([])
    );
    assert_eq!(before, snap(), "double sync is byte-identical");
}

// frob:tests crates/frob/src/agent_cmd.rs::AgentSync
// frob:tests crates/frob/src/agent_cmd.rs::AgentUninstall
#[test]
fn uninstall_keeps_user_hooks_settings_and_edited_files() {
    let repo = repo();
    let home = tempfile::tempdir().unwrap();
    let h = home.path();
    std::fs::write(
        h.join("settings.json"),
        r#"{"model": "x", "hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "mine.sh"}]}], "Stop": [{"hooks": [{"type": "command", "command": "bye"}]}]}}"#,
    )
    .unwrap();
    assert_eq!(code(&sync(repo.path(), h, &[])), 0);
    let s = settings(h);
    assert_eq!(
        s["hooks"]["PreToolUse"].as_array().unwrap().len(),
        2,
        "user group kept, frob group added"
    );
    assert!(
        h.join("settings.json.frob-bak").exists(),
        "backup before replacing"
    );

    std::fs::write(h.join("agents/reviewer.md"), "my own reviewer\n").unwrap();
    let un = frob(
        repo.path(),
        &[
            "agent",
            "uninstall",
            "--agent",
            "claude",
            "--home",
            h.to_str().unwrap(),
        ],
    );
    assert_eq!(code(&un), 0, "{}", String::from_utf8_lossy(&un.stdout));
    let s = settings(h);
    assert_eq!(s["model"], "x");
    assert_eq!(
        s["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
        "mine.sh"
    );
    assert_eq!(s["hooks"]["PreToolUse"].as_array().unwrap().len(), 1);
    assert_eq!(s["hooks"]["Stop"][0]["hooks"][0]["command"], "bye");
    assert!(!h.join("hooks/guard.py").exists());
    assert_eq!(
        std::fs::read_to_string(h.join("agents/reviewer.md")).unwrap(),
        "my own reviewer\n"
    );
}

// frob:tests crates/frob/src/agent_cmd.rs::AgentStatus
#[test]
fn status_exits_one_on_drift_and_zero_when_clean() {
    let repo = repo();
    let home = tempfile::tempdir().unwrap();
    let h = home.path();
    let st = |h: &Path| {
        frob(
            repo.path(),
            &[
                "agent",
                "status",
                "--agent",
                "claude",
                "--home",
                h.to_str().unwrap(),
            ],
        )
    };
    assert_eq!(code(&st(h)), 1, "an empty home has drifted");
    assert_eq!(code(&sync(repo.path(), h, &[])), 0);
    assert_eq!(code(&st(h)), 0);
    std::fs::write(h.join("hooks/_lib.py"), "tampered\n").unwrap();
    let out = st(h);
    assert_eq!(code(&out), 1);
    assert_eq!(
        json(&out)["data"]["agents"][0]["files"][1]["state"],
        "differs"
    );
}

// frob:tests crates/frob/src/agent_cmd.rs::AgentSync
#[test]
fn stale_worktree_source_is_refused_unless_allowed() {
    let repo = repo();
    let r = repo.path();
    git(r, &["checkout", "-qb", "feat"]);
    git(r, &["checkout", "-q", "main"]);
    std::fs::write(r.join("hooks/_lib.py"), "X = 2\n").unwrap();
    git(r, &["commit", "-qam", "newer"]);
    git(r, &["checkout", "-q", "feat"]);
    let home = tempfile::tempdir().unwrap();
    let out = sync(r, home.path(), &[]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert!(String::from_utf8_lossy(&out.stdout).contains("E-AGENT-STALE"));
    assert!(!home.path().join("hooks/_lib.py").exists());
    assert_eq!(code(&sync(r, home.path(), &["--allow-stale"])), 0);
}

// frob:tests crates/frob/src/agent_cmd.rs::AgentSync
#[test]
fn unknown_agent_is_a_usage_error() {
    let repo = repo();
    let r = repo.path();
    let bad = frob(r, &["agent", "status", "--agent", "nope"]);
    assert_ne!(code(&bad), 0);
}

//! Private-term redaction through the binary: refuse at write time, detect with `check`, repair with `doctor --fix`.
// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72

use std::path::Path;
use std::process::Output;

use serde_json::Value;

mod common;

const TERM: &str = "zorblax-7";
const LABEL: &str = "<private-host>";

struct Repo {
    dir: tempfile::TempDir,
    config: tempfile::TempDir,
}

fn git(dir: &Path, args: &[&str]) -> String {
    let out = std::process::Command::new("git")
        .args(args)
        .current_dir(dir)
        .output()
        .expect("git");
    String::from_utf8_lossy(&out.stdout).trim().to_owned()
}

impl Repo {
    fn new() -> Self {
        let repo = Self {
            dir: common::git_repo(),
            config: tempfile::tempdir().expect("config dir"),
        };
        assert_eq!(code(&repo.frob(&["init"])), 0);
        git(repo.path(), &["add", "-A"]);
        git(repo.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    fn path(&self) -> &Path {
        self.dir.path()
    }

    fn rule_file(&self) -> std::path::PathBuf {
        self.path().join(".git").join("frob").join("privacy.toml")
    }

    fn set_rule(&self) {
        let f = self.rule_file();
        std::fs::create_dir_all(f.parent().expect("parent")).expect("mkdir");
        std::fs::write(
            f,
            format!("[[rule]]\npattern = \"{TERM}\"\nreplace = \"{LABEL}\"\n"),
        )
        .expect("write rule");
    }

    fn frob(&self, args: &[&str]) -> Output {
        common::frob_command()
            .current_dir(self.path())
            .env_remove("FROB_LOG")
            .env("XDG_CONFIG_HOME", self.config.path())
            .env("HOME", self.config.path())
            .arg("--json")
            .args(args)
            .output()
            .expect("run frob")
    }

    fn json(&self, args: &[&str]) -> (i32, Value) {
        let out = self.frob(args);
        let v = serde_json::from_slice(&out.stdout).unwrap_or(Value::Null);
        (code(&out), v)
    }
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn everything(out: &Output) -> String {
    format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

fn head(repo: &Repo) -> String {
    git(repo.path(), &["rev-parse", "HEAD"])
}

/// `ticket new`, `update` and `comment` with a private term exit 2 naming the label, never the term, and write nothing.
// frob:tests crates/frob-ledger/src/ledger.rs::Ledger.refuse_private
#[test]
fn writes_with_a_private_term_exit_2_and_write_nothing() {
    let repo = Repo::new();
    let (_, v) = repo.json(&["ticket", "new", "--title", "Clean", "--acceptance", "ok"]);
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    repo.set_rule();
    let before = head(&repo);
    let tip_before = git(repo.path(), &["rev-list", "--all", "--count"]);
    let attempts: Vec<Vec<String>> = vec![
        vec!["ticket", "new", "--title", &format!("on {TERM}")],
        vec!["ticket", "update", &id, "--title", &format!("saw {TERM}")],
        vec!["ticket", "comment", &id, "--body", &format!("{TERM} again")],
    ]
    .into_iter()
    .map(|a| a.into_iter().map(str::to_owned).collect())
    .collect();
    for args in attempts {
        let refs: Vec<&str> = args.iter().map(String::as_str).collect();
        let out = repo.frob(&refs);
        let all = everything(&out);
        assert_eq!(code(&out), 2, "{refs:?}: {all}");
        assert!(all.contains(LABEL), "{all}");
        assert!(!all.contains(TERM), "term echoed: {all}");
    }
    assert_eq!(head(&repo), before);
    assert_eq!(
        git(repo.path(), &["rev-list", "--all", "--count"]),
        tip_before
    );
}

/// A fragment sentence with a private term is refused before any file is written.
// frob:tests crates/frob/src/ticket/fragment_cmd.rs::Fragment
#[test]
fn fragment_with_a_private_term_is_refused() {
    let repo = Repo::new();
    let (_, v) = repo.json(&["ticket", "new", "--title", "Clean", "--acceptance", "ok"]);
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    repo.set_rule();
    let out = repo.frob(&[
        "ticket",
        "fragment",
        &id,
        "--sentence",
        &format!("fixed {TERM}."),
    ]);
    assert_eq!(code(&out), 2, "{}", everything(&out));
    assert!(!everything(&out).contains(TERM));
    assert!(!repo.path().join("changelog.d").exists());
}

/// `check` flags a leaked term as a TICK005 error without echoing it, doctor --fix repairs it in one commit, and a second run changes nothing.
// frob:tests crates/frob/src/ticket/doctor_cmd.rs::scrub_ledger
// frob:tests crates/frob-check/src/product.rs::private_term_findings
#[test]
fn check_flags_and_doctor_fix_repairs() {
    let repo = Repo::new();
    let (_, v) = repo.json(&[
        "ticket",
        "new",
        "--title",
        "Leaky",
        "--acceptance",
        "ok",
        "--body",
        &format!("on {TERM}"),
    ]);
    let id = v["data"]["id"].as_str().expect("id").to_owned();
    git(repo.path(), &["add", "-A"]);

    let silent = repo.json(&["check", "--only", "TICK005"]);
    assert!(
        !silent.1.to_string().contains("TICK005"),
        "no local rules: {}",
        silent.1
    );

    repo.set_rule();
    let out = repo.frob(&["check", "--only", "TICK005"]);
    let all = everything(&out);
    assert_eq!(code(&out), 1, "{all}");
    assert!(all.contains("TICK005") && all.contains(LABEL), "{all}");
    assert!(!all.contains(TERM), "{all}");

    let base = head(&repo);
    let (c, fixed) = repo.json(&["ticket", "doctor", "--fix"]);
    assert_eq!(c, 0, "{fixed}");
    assert!(!fixed.to_string().contains(TERM));
    assert_eq!(fixed["data"]["scrubbed_tickets"][0], id.as_str());
    assert_ne!(head(&repo), base);
    assert_eq!(git(repo.path(), &["rev-parse", "HEAD~1"]), base);

    let again = repo.json(&["ticket", "doctor", "--fix"]);
    assert!(again.1["data"]["scrub_commit"].is_null(), "{}", again.1);
    let check = repo.frob(&["check", "--only", "TICK005"]);
    assert_eq!(code(&check), 0, "{}", everything(&check));
    let shown = repo.frob(&["ticket", "show", &id]);
    assert!(everything(&shown).contains(LABEL) && !everything(&shown).contains(TERM));
}

/// Nothing writes a rule or a term into the repository: no tracked privacy file, no rule in frob.toml, no term in any revision.
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.load_local
#[test]
fn the_repository_contains_neither_rule_nor_term() {
    let repo = Repo::new();
    repo.set_rule();
    let _ = repo.json(&["ticket", "new", "--title", "Clean", "--acceptance", "ok"]);
    let _ = repo.json(&["doctor"]);
    let _ = repo.json(&["init"]);
    let tracked = git(repo.path(), &["ls-files"]);
    assert!(
        !tracked.lines().any(|l| l.ends_with("privacy.toml")),
        "{tracked}"
    );
    let toml = std::fs::read_to_string(repo.path().join("frob.toml")).expect("frob.toml");
    assert!(!toml.contains("[[rule]]") && !toml.contains("privacy") && !toml.contains(TERM));
    let revs = git(repo.path(), &["rev-list", "--all"]);
    let revs: Vec<&str> = revs.lines().collect();
    let mut args = vec!["grep", "-l", "-e", TERM, "-e", LABEL];
    args.extend(revs.iter().copied());
    assert_eq!(git(repo.path(), &args), "", "a rule or term was committed");
}

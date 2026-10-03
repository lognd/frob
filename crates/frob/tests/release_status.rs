//! `release status` end to end: the readiness report is always exit 0.
// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
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
        repo.set_require_ci(false);
        git(repo.dir.path(), &["add", "-A"]);
        git(repo.dir.path(), &["commit", "-q", "-m", "base"]);
        repo
    }

    /// Rewrite `[release] require_ci` in frob.toml.
    fn set_require_ci(&self, value: bool) {
        let p = self.dir.path().join("frob.toml");
        let text = std::fs::read_to_string(&p).expect("frob.toml");
        let text = text
            .replace("require_ci = true", &format!("require_ci = {value}"))
            .replace("require_ci = false", &format!("require_ci = {value}"));
        std::fs::write(&p, text).expect("write frob.toml");
    }

    /// Run frob with `path` as the whole PATH (so a fake or absent `gh`).
    fn run_with_path(&self, path: &Path, args: &[&str]) -> Output {
        Command::cargo_bin("frob")
            .expect("frob binary")
            .current_dir(self.dir.path())
            .env_remove("FROB_LOG")
            .env("PATH", path)
            .args(args)
            .output()
            .expect("run frob")
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

    fn ticket(&self, ty: &str) -> String {
        self.titled(ty, "t")
    }

    fn titled(&self, ty: &str, title: &str) -> String {
        self.ok(&["ticket", "new", "--title", title, "--type", ty])["data"]["id"]
            .as_str()
            .expect("id")
            .to_owned()
    }
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn fragment(repo: &Repo, id: &str, kind: &str, body: &str) -> std::path::PathBuf {
    let dir = repo.dir.path().join("changelog.d");
    std::fs::create_dir_all(&dir).expect("mkdir");
    let p = dir.join(format!("{id}.{kind}.md"));
    std::fs::write(&p, body).expect("write fragment");
    p
}

fn report(v: &Value) -> &Value {
    &v["data"]["report"]
}

fn kinds(v: &Value) -> Vec<String> {
    report(v)["blockers"]
        .as_array()
        .expect("blockers")
        .iter()
        .map(|b| b["kind"].as_str().expect("kind").to_owned())
        .collect()
}

fn milestone(repo: &Repo, criteria: &[&str]) {
    let mut a = vec!["milestone", "new", "0.532.0", "--goal", "Ship PM"];
    for c in criteria {
        a.push("--criterion");
        a.push(c);
    }
    repo.ok(&a);
}

#[test]
fn an_unevidenced_criterion_is_listed_and_the_exit_is_zero() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    milestone(&repo, &["first", "second"]);
    std::fs::write(repo.dir.path().join("proof.txt"), "proof").expect("write");
    repo.ok(&[
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        "file",
        "--ref",
        "proof.txt",
        "--accepts",
        "1",
    ]);
    let out = repo.frob(&["release", "status"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["verb"], "release.status");
    let r = report(&v);
    assert_eq!(r["version"], "0.532.0");
    assert_eq!(r["ready"], false);
    assert_eq!(r["criteria"][0]["state"], "bound");
    assert_eq!(r["criteria"][0]["evidence"][0]["provider"], "file");
    assert_eq!(r["criteria"][1]["state"], "unbound");
    assert_eq!(kinds(&v), ["unbound-criterion"]);
    assert_eq!(r["verdict"], "NOT READY: 1 blocker");
    let unresolved = r["unresolved"].to_string();
    assert!(
        unresolved.contains("CI status on commit") && unresolved.contains("no `origin` remote"),
        "{unresolved}"
    );
    assert!(unresolved.contains("no history yet") && unresolved.contains("owner action"));
}

#[test]
fn everything_ready_prints_ready_and_the_changelog_preview() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    // frob:tests crates/frob-release/src/status.rs::assess
    let repo = Repo::new();
    milestone(&repo, &["only"]);
    std::fs::write(repo.dir.path().join("proof.txt"), "proof").expect("write");
    repo.ok(&[
        "milestone",
        "evidence",
        "add",
        "0.532.0",
        "--provider",
        "file",
        "--ref",
        "proof.txt",
        "--accepts",
        "1",
    ]);
    let t = repo.ticket("task");
    fragment(&repo, &t, "added", "frob: Added release status.\n");
    let v = repo.ok(&["release", "status", "0.532.0"]);
    let r = report(&v);
    assert_eq!(r["ready"], true);
    assert_eq!(r["verdict"], "READY");
    assert!(r["blockers"].as_array().expect("blockers").is_empty());
    assert_eq!(r["fragments"]["state"], "valid");
    assert!(
        r["changelog_preview"]
            .as_str()
            .expect("preview")
            .contains("Added release status.")
    );
    let out = repo.run(&["--text", "release", "status"]);
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.contains("0.532.0: READY"), "{text}");
}

#[test]
fn open_tickets_of_member_epics_are_listed_by_category_and_block() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    milestone(&repo, &[]);
    let epic = repo.titled("epic", "The epic");
    let child = repo.titled("task", "Child work");
    repo.ok(&[
        "ticket",
        "update",
        &child,
        "--set",
        &format!("parent={epic}"),
    ]);
    let done = repo.titled("task", "Finished work");
    repo.ok(&[
        "ticket",
        "update",
        &done,
        "--set",
        &format!("parent={epic}"),
    ]);
    repo.ok(&[
        "ticket",
        "close",
        &done,
        "--outcome",
        "done",
        "--no-evidence",
        "--reason",
        "test",
    ]);
    repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    let v = repo.ok(&["release", "status"]);
    let r = report(&v);
    let groups = &r["open_tickets"];
    let listed = groups.to_string();
    assert!(listed.contains("Child work"), "{listed}");
    assert!(!listed.contains("Finished work") && !listed.contains("The epic"));
    assert_eq!(kinds(&v), ["open-ticket"]);
}

#[test]
fn a_ticket_claiming_the_release_outside_its_epics_surfaces_pm034() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    // frob:tests crates/frob-pm/src/rules/membership.rs::claimants
    let repo = Repo::new();
    milestone(&repo, &[]);
    let epic = repo.titled("epic", "The epic");
    repo.ok(&["milestone", "add", &epic, "0.532.0"]);
    let stray = repo.titled("task", "Stray work");
    repo.ok(&["ticket", "update", &stray, "--add-label", "release:0.532.0"]);
    let v = repo.ok(&["release", "status"]);
    let r = report(&v);
    assert_eq!(r["pm034"].as_array().expect("pm034").len(), 1);
    assert!(r["pm034"][0].as_str().expect("msg").contains("Stray work"));
    let k = kinds(&v);
    assert!(
        k.contains(&"pm034".to_owned()) && k.contains(&"open-ticket".to_owned()),
        "{k:?}"
    );
}

#[test]
fn label_claims_are_listed_before_the_milestone_object_exists() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    let t = repo.titled("task", "Claimed work");
    repo.ok(&["ticket", "update", &t, "--add-label", "release:0.532.0"]);
    let out = repo.frob(&["release", "status", "0.532.0"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert!(
        report(&v)["open_tickets"]
            .to_string()
            .contains("Claimed work")
    );
    assert_eq!(kinds(&v)[0], "no-milestone");
}

#[test]
fn invalid_fragments_are_reported_without_failing_the_command() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    milestone(&repo, &[]);
    let dir = repo.dir.path().join("changelog.d");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(dir.join("oops.md"), "frob: x\n").expect("write");
    let out = repo.frob(&["release", "status"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    let r = report(&v);
    assert_eq!(r["fragments"]["state"], "invalid");
    assert!(
        r["fragments"]["errors"][0]
            .as_str()
            .expect("e")
            .contains("changelog.d/oops.md")
    );
    assert_eq!(kinds(&v), ["invalid-fragment"]);
    assert!(r["changelog_preview"].is_null());
}

#[test]
fn no_milestone_at_all_is_a_helpful_message_and_exit_zero() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    let out = repo.frob(&["release", "status"]);
    assert_eq!(code(&out), 0);
    let v = json(&out);
    assert_eq!(v["data"]["outcome"], "no-milestone");
    assert!(v["data"]["report"].is_null());
    assert!(
        v["data"]["message"]
            .as_str()
            .expect("message")
            .contains("frob milestone new")
    );
}

#[test]
fn the_default_version_is_the_lowest_open_milestone() {
    // frob:tests crates/frob/src/release_cmd.rs::ReleaseStatus.run
    let repo = Repo::new();
    repo.ok(&["milestone", "new", "0.10.0", "--goal", "later"]);
    repo.ok(&["milestone", "new", "0.9.0", "--goal", "sooner"]);
    let v = repo.ok(&["release", "status"]);
    assert_eq!(report(&v)["version"], "0.9.0");
}

/// A directory with a stub `gh`: prints `body` for check-runs and an empty status, or fails with `fail`.
fn fake_gh(body: &str, fail: Option<(i32, &str)>) -> tempfile::TempDir {
    use std::os::unix::fs::PermissionsExt;
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("runs.json"), body).expect("runs");
    let d = dir.path().display();
    let script = match fail {
        Some((code, err)) => format!("#!/bin/sh\necho '{err}' >&2\nexit {code}\n"),
        None => format!(
            "#!/bin/sh\ncase \"$*\" in\n*check-runs*) /bin/cat '{d}/runs.json';;\n*) echo '{{\"statuses\":[]}}';;\nesac\n"
        ),
    };
    let path = dir.path().join("gh");
    std::fs::write(&path, script).expect("script");
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    dir
}

/// A repo with a ready milestone and a GitHub origin, so only CI decides readiness.
fn ci_repo(require: bool) -> Repo {
    let repo = Repo::new();
    git(
        repo.dir.path(),
        &["remote", "add", "origin", "git@github.com:acme/widget.git"],
    );
    milestone(&repo, &[]);
    repo.set_require_ci(require);
    git(repo.dir.path(), &["add", "-A"]);
    git(
        repo.dir.path(),
        &["commit", "-q", "--allow-empty", "-m", "require_ci"],
    );
    repo
}

fn ci_status(repo: &Repo, gh: &Path) -> Value {
    let out = repo.run_with_path(gh, &["--json", "release", "status"]);
    assert_eq!(code(&out), 0, "status never fails");
    json(&out)
}

const RUNS_GREEN: &str = r#"{"check_runs":[{"name":"build","status":"completed","conclusion":"success","html_url":"https://x/1"},{"name":"docs","status":"completed","conclusion":"skipped","html_url":"https://x/2"}]}"#;
const RUNS_RED: &str = r#"{"check_runs":[{"name":"build","status":"completed","conclusion":"success","html_url":"https://x/1"},{"name":"lint","status":"completed","conclusion":"failure","html_url":"https://x/lint"}]}"#;
const RUNS_PENDING: &str = r#"{"check_runs":[{"name":"test","status":"in_progress","conclusion":null,"html_url":"https://x/3"}]}"#;

#[test]
fn green_ci_adds_nothing() {
    // frob:tests crates/frob/src/release_cmd.rs::ci_facts
    let repo = ci_repo(true);
    let gh = fake_gh(RUNS_GREEN, None);
    let v = ci_status(&repo, gh.path());
    let r = report(&v);
    assert_eq!(r["ci"]["state"], "green", "{}", r["ci"]);
    assert!(!r["unresolved"].to_string().contains("CI status"));
    assert_eq!(kinds(&v), Vec::<String>::new());
    assert_eq!(r["verdict"], "READY");
}

#[test]
fn red_ci_blocks_with_names_and_links_even_when_not_required() {
    // frob:tests crates/frob/src/release_cmd.rs::ci_facts
    let repo = ci_repo(false);
    let gh = fake_gh(RUNS_RED, None);
    let v = ci_status(&repo, gh.path());
    assert_eq!(kinds(&v), ["ci-red"]);
    let detail = report(&v)["blockers"][0]["detail"]
        .as_str()
        .expect("detail");
    assert!(detail.contains("lint (failure) https://x/lint"), "{detail}");
    assert_eq!(report(&v)["verdict"], "NOT READY: 1 blocker");
}

#[test]
fn pending_ci_blocks_as_still_running() {
    // frob:tests crates/frob/src/release_cmd.rs::ci_facts
    let repo = ci_repo(true);
    let gh = fake_gh(RUNS_PENDING, None);
    let v = ci_status(&repo, gh.path());
    assert_eq!(kinds(&v), ["ci-pending"]);
    assert!(
        report(&v)["blockers"][0]["detail"]
            .as_str()
            .expect("detail")
            .contains("CI still running")
    );
}

#[test]
fn unknown_ci_blocks_by_default_and_only_warns_with_require_ci_false() {
    // frob:tests crates/frob/src/release_cmd.rs::ci_facts
    let unauth = (
        4,
        "To get started with GitHub CLI, please run:  gh auth login",
    );
    let empty = tempfile::tempdir().expect("tempdir");
    for require in [true, false] {
        let repo = ci_repo(require);
        let cases = [
            (
                "no checks",
                fake_gh(r#"{"check_runs":[]}"#, None),
                "no checks",
            ),
            (
                "unauthenticated",
                fake_gh("", Some(unauth)),
                "not authenticated",
            ),
            (
                "gh missing",
                tempfile::tempdir().expect("tempdir"),
                "not installed",
            ),
        ];
        for (name, gh, needle) in cases {
            let v = ci_status(&repo, gh.path());
            let r = report(&v);
            let unresolved = r["unresolved"].to_string();
            assert!(unresolved.contains(needle), "{name}: {unresolved}");
            assert_eq!(r["ci"]["state"], "unknown", "{name}");
            assert_eq!(r["ci"]["required"], require, "{name}");
            if require {
                assert_eq!(kinds(&v), ["ci-unknown"], "{name}");
            } else {
                assert!(kinds(&v).is_empty() && r["ready"] == true, "{name}");
            }
        }
    }
    drop(empty);
}

#[test]
fn a_non_github_origin_is_unresolved_with_the_remedy() {
    // frob:tests crates/frob/src/release_cmd.rs::ci_facts
    let repo = ci_repo(true);
    git(
        repo.dir.path(),
        &[
            "remote",
            "set-url",
            "origin",
            "https://gitlab.com/acme/widget.git",
        ],
    );
    let gh = fake_gh(RUNS_GREEN, None);
    let v = ci_status(&repo, gh.path());
    assert_eq!(kinds(&v), ["ci-unknown"]);
    let unresolved = report(&v)["unresolved"].to_string();
    assert!(
        unresolved.contains("not a github.com remote"),
        "{unresolved}"
    );
    assert!(unresolved.contains("require_ci = false"), "{unresolved}");
}

#[test]
fn the_text_view_names_the_commit_inspected() {
    // frob:tests crates/frob/src/release_cmd.rs::ci_facts
    let repo = ci_repo(true);
    let gh = fake_gh(RUNS_RED, None);
    let out = repo.run_with_path(gh.path(), &["--text", "release", "status"]);
    assert_eq!(code(&out), 0);
    let text = String::from_utf8_lossy(&out.stdout);
    let tip = git_tip(repo.dir.path());
    assert!(text.contains(&format!("commit {}", &tip[..12])), "{text}");
    assert!(text.contains("CI: red"), "{text}");
}

fn git_tip(dir: &Path) -> String {
    let spec = Spec {
        program: Program::Git,
        args: vec!["rev-parse".to_owned(), "refs/heads/main".to_owned()],
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    out.stdout.trim().to_owned()
}

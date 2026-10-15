//! Markdown corpora run through the whole check: `GRL016` blocks are `.grl` files, `CI*` blocks are bound-linter output.
//!
//! The repository-rule corpora (`DRIFT*`, `EXC005`, `PERF001`, `PROC001`, `READ001`, `SCOPE001`,
//! `SIB001`, `TEST001`) build a small repository from the block. A line `=== path` starts a file
//! section (text up to the next `===` line); `=== git` commits the tree so far to `main`;
//! `=== ack <symref>...` records an ack; a later section for a path overwrites the file.

// frob:ticket 01M3ZX7H37B9GKN45MPD6ZNBTY
// frob:ticket 01M4YBK7YTVNC16GHFFK4JKY97

use std::path::Path;
use std::time::Duration;

use frob_check::{CheckOptions, run};
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_ledger::{Ledger, LedgerConfig};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_mdtest::Case;
use gob_rules::Finding;

/// Check the block as a repository holding only its file and return the findings.
fn grl_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join(&case.file_name);
    std::fs::create_dir_all(path.parent().expect("file has a parent")).expect("mkdir");
    std::fs::write(&path, &case.text).expect("write block");
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    tracing::debug!(file = %case.file_name, "GRL016 corpus block");
    run(dir.path(), &opts).expect("check runs").findings
}

/// Run the block as the output of a fake zizmor (or actionlint for `CI014`) and keep the rule's findings.
fn ci_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let write = |path: &str, text: &str| {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    };
    let workflow = format!("name: ci\n{}", "# padding line for offsets\n".repeat(30));
    write(".github/workflows/ci.yml", &workflow);
    write(".github/workflows/bad.yml", &workflow);
    write("fixture.json", &case.text);
    write("fake.sh", "cat fixture.json\n");
    let parser = if case.rule.as_str() == "CI014" {
        "actionlint-json"
    } else {
        "zizmor-json-v1"
    };
    write(
        "frob.toml",
        &format!(
            "[[check.tool]]\nname = \"fake\"\ncommand = \"sh\"\nargs = [\"fake.sh\"]\nparser = \"{parser}\"\nversion_args = [\"-c\", \"echo faketool 1.2.3\"]\n"
        ),
    );
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: false,
        only: vec!["TOOL".to_owned(), "CI".to_owned()],
        ..CheckOptions::default()
    };
    tracing::debug!(rule = %case.rule, "CI corpus block");
    run(root, &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

/// One step of a repository-rule block.
enum Step {
    /// Write `text` to `path`.
    File(String, String),
    /// Commit everything so far to `main`.
    Git,
    /// Ack the symrefs.
    Ack(Vec<String>),
}

/// Split a block into steps; text before the first `===` line is the block's own file.
fn steps(case: &Case) -> Vec<Step> {
    let mut out = Vec::new();
    let mut current: Option<(String, String)> = Some((case.file_name.clone(), String::new()));
    let flush = |cur: &mut Option<(String, String)>, out: &mut Vec<Step>| {
        if let Some((path, text)) = cur.take() {
            if !(text.is_empty() && path == case.file_name) {
                out.push(Step::File(path, text));
            }
        }
    };
    for line in case.text.split_inclusive('\n') {
        if let Some(head) = line.strip_prefix("=== ") {
            flush(&mut current, &mut out);
            let head = head.trim();
            if head == "git" {
                out.push(Step::Git);
            } else if let Some(rest) = head.strip_prefix("ack ") {
                out.push(Step::Ack(
                    rest.split_whitespace().map(str::to_owned).collect(),
                ));
            } else {
                current = Some((head.to_owned(), String::new()));
            }
        } else if let Some((_, text)) = current.as_mut() {
            text.push_str(line);
        }
    }
    flush(&mut current, &mut out);
    out
}

/// Run `git` in `dir`, failing the test when it does.
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
        "git {args:?}: {}{}",
        out.stdout,
        out.stderr
    );
}

/// Write one file under `root`, creating its directories.
fn write_file(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

/// Check options for a corpus run: no telemetry, no external tools.
fn quiet() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

/// Build the block's repository and check it; `PERF001` retries since a run can finish inside a zero budget.
fn repo_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    for step in steps(case) {
        match step {
            Step::File(path, text) => write_file(root, &path, &text),
            Step::Git => {
                git(root, &["init", "-q"]);
                git(root, &["symbolic-ref", "HEAD", "refs/heads/main"]);
                git(root, &["config", "user.name", "Test User"]);
                git(root, &["config", "user.email", "test@example.com"]);
                git(root, &["config", "core.autocrlf", "false"]);
                write_file(root, ".gitignore", ".frob/\n");
                git(root, &["add", "-A"]);
                git(root, &["commit", "-q", "-m", "corpus"]);
            }
            Step::Ack(targets) => {
                frob_ack::ack(
                    root,
                    &targets,
                    false,
                    Some("reviewed the contract in full"),
                    gob_time::Clock::now(&gob_time::SystemClock),
                )
                .expect("ack");
            }
        }
    }
    let attempts = if case.rule.as_str() == "PERF001" {
        5
    } else {
        1
    };
    let mut found = Vec::new();
    for _ in 0..attempts {
        let report = run(root, &quiet()).expect("check runs");
        found = report
            .findings
            .into_iter()
            .filter(|f| f.rule.as_str() == case.rule.as_str())
            .filter(|f| !format!("{f:?}").contains("opaque text file"))
            .collect();
        if !found.is_empty() {
            break;
        }
    }
    tracing::debug!(rule = %case.rule, findings = found.len(), "repository corpus block");
    found
}

/// `SIB001`: the block is the fake sibling's mode file in a repository configured for `grimble`.
fn sib_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    write_file(root, "grimble.toml", "");
    write_file(root, ".fake-sibling", &case.text);
    write_file(root, "a.txt", "aaa\n");
    let opts = CheckOptions {
        sibling_programs: vec![("grimble".to_owned(), gob_testsupport::fake_sibling())],
        ..quiet()
    };
    tracing::debug!(mode = %case.text.trim(), "SIB001 corpus block");
    run(root, &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "SIB001")
        .collect()
}

/// `SCOPE001`: a ticket scoped to `src/a/**` and the block written as a new file (default `src/b/lib.rs`).
fn scope_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let repo = Repo::init(root).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    let cfg = std::fs::read_to_string(repo.git_dir().join("config")).expect("config");
    std::fs::write(
        repo.git_dir().join("config"),
        format!("{cfg}[user]\n\tname = Test User\n\temail = test@example.com\n"),
    )
    .expect("identity");
    drop(repo);
    let repo = Repo::discover(root).expect("discover");
    repo.commit_paths(
        "refs/heads/main",
        &[(
            RelPath::new(".gitignore").expect("path"),
            Some(b".frob/\n".to_vec()),
        )],
        "root",
        &CommitOptions::default(),
    )
    .expect("root commit");
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut new = NewTicket::new("Scoped work", TicketType::Task);
    new.scope = vec!["src/a/**".to_owned()];
    let id = ledger.new_ticket(new).expect("ticket").ticket.front.id;
    write_file(root, &case.file_name, &case.text);
    tracing::debug!(file = %case.file_name, "SCOPE001 corpus block");
    let opts = CheckOptions {
        ticket: Some(id.to_string()),
        ..quiet()
    };
    run(root, &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == "SCOPE001")
        .collect()
}

/// Route a block to the runner for its rule family.
fn runner(case: &Case) -> Vec<Finding> {
    let rule = case.rule.as_str();
    if rule.starts_with("CI") {
        ci_runner(case)
    } else if rule.starts_with("GRL") {
        grl_runner(case)
    } else if rule == "SIB001" {
        sib_runner(case)
    } else if rule == "SCOPE001" {
        scope_runner(case)
    } else {
        repo_runner(case)
    }
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

//! Markdown corpora run through the whole check: `GRL016` blocks are `.grl` files, `CI*` blocks are bound-linter output.
//!
//! The repository-rule corpora (`DRIFT*`, `EXC005`, `PERF001`, `PROC001`, `READ001`, `SCOPE001`,
//! `SIB001`, `TEST001`) build a small repository from the block. A line `=== path` starts a file
//! section (text up to the next `===` line); `=== git` commits the tree so far to `main`;
//! `=== ack <symref>...` records an ack; `=== binary <path>` writes a non-UTF-8 file the graph cannot read; a later
//! section for a path overwrites the file.
//!
//! The ledger corpora (`TICK001`, `TICK003`, `TICK004`, `TICK005`, `TICK007`-`TICK009`) build a
//! repository holding one ticket and apply the block as the scenario (see `tick_dir_runner` and
//! `tick_branch_runner`); `TICK002` shares the scoped runner of `SCOPE001`; `TOOL001` and `TOOL002`
//! run a fake `[[check.tool]]` stage.

// frob:ticket 01M3ZX7H37B9GKN45MPD6ZNBTY
// frob:ticket 01M4YBK7YTVNC16GHFFK4JKY97
// frob:ticket 01M4YBK86ZC7V4VCBSMWTJ0SE3

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
    /// Write `path` with bytes that are not UTF-8, so the graph build cannot read it.
    Binary(String),
}

/// Split a block into steps; text before the first `===` line is the block's own file.
fn steps(case: &Case) -> Vec<Step> {
    let mut out = Vec::new();
    let mut current: Option<(String, String)> = Some((case.file_name.clone(), String::new()));
    let flush = |cur: &mut Option<(String, String)>, out: &mut Vec<Step>| {
        if let Some((path, text)) = cur.take()
            && !(text.is_empty() && path == case.file_name)
        {
            out.push(Step::File(path, text));
        }
    };
    for line in case.text.split_inclusive('\n') {
        if let Some(head) = line.strip_prefix("=== ") {
            flush(&mut current, &mut out);
            let head = head.trim();
            if head == "git" {
                out.push(Step::Git);
            } else if let Some(path) = head.strip_prefix("binary ") {
                out.push(Step::Binary(path.trim().to_owned()));
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
            Step::Binary(path) => {
                let full = root.join(&path);
                std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
                std::fs::write(full, [0xff_u8, 0xfe, b'\n']).expect("write binary");
            }
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

/// `SCOPE001`/`TICK002`: a ticket scoped to `src/a/**` and the block written as a new file (`{ticket}` expands to its id).
fn scope_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let repo = init_root_repo(root, &[(".gitignore", ".frob/\n")]);
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut new = NewTicket::new("Scoped work", TicketType::Task);
    new.scope = vec!["src/a/**".to_owned()];
    let id = ledger.new_ticket(new).expect("ticket").ticket.front.id;
    write_file(
        root,
        &case.file_name,
        &case.text.replace("{ticket}", &id.to_string()),
    );
    tracing::debug!(file = %case.file_name, rule = %case.rule, "scoped corpus block");
    let opts = CheckOptions {
        ticket: Some(id.to_string()),
        ..quiet()
    };
    run(root, &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

/// Initialise a repository at `root` on `main` with an identity and a root commit holding `files`.
fn init_root_repo(root: &Path, files: &[(&str, &str)]) -> Repo {
    let repo = Repo::init(root).expect("init");
    std::fs::write(repo.git_dir().join("HEAD"), "ref: refs/heads/main\n").expect("head");
    git(root, &["config", "user.name", "Test User"]);
    git(root, &["config", "user.email", "test@example.com"]);
    drop(repo);
    let repo = Repo::discover(root).expect("discover");
    let files: Vec<_> = files
        .iter()
        .map(|(p, t)| (*p, Some(t.as_bytes().to_vec())))
        .collect();
    commit_files(&repo, "refs/heads/main", &files, "root");
    repo
}

/// Commit `files` (`None` deletes) onto `reference` of `repo` with `message`.
fn commit_files(repo: &Repo, reference: &str, files: &[(&str, Option<Vec<u8>>)], message: &str) {
    let changes: Vec<_> = files
        .iter()
        .map(|(p, bytes)| (RelPath::new(*p).expect("path"), bytes.clone()))
        .collect();
    repo.commit_paths(reference, &changes, message, &CommitOptions::default())
        .expect("commit");
}

/// The findings of a full ledger check of `root` for the block's rule.
fn ledger_findings(root: &Path, case: &Case) -> Vec<Finding> {
    run(root, &quiet())
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

/// `TICK001`/`TICK003`/`TICK004`/`TICK005`: a trunk-mode ledger with one ticket.
///
/// `TICK001` and `TICK003` apply the block's `key = value` lines to the committed `ticket.md` (replacing the key's
/// line, else inserting it after the title); `TICK004` and `TICK005` take the block as the ticket body, and
/// `TICK005` then defines the private term `hush-term` in the local `frob/privacy.toml`.
fn tick_dir_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let repo = init_root_repo(root, &[(".gitignore", ".frob/\n")]);
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let mut new = NewTicket::new("Original", TicketType::Task);
    let by_body = matches!(case.rule.as_str(), "TICK004" | "TICK005");
    if by_body {
        new.body.clone_from(&case.text);
    }
    let id = ledger.new_ticket(new).expect("ticket").ticket.front.id;
    if case.rule.as_str() == "TICK005" {
        write_file(
            &root.join(".git"),
            "frob/privacy.toml",
            "[[rule]]\npattern = \"hush-term\"\nreplace = \"<hush>\"\n",
        );
    }
    if !by_body {
        let path = format!("tickets/{id}/ticket.md");
        let card = ledger
            .repo()
            .read_blob_at("refs/heads/main", &path)
            .expect("read card")
            .expect("card exists");
        let mut lines: Vec<String> = String::from_utf8(card)
            .expect("utf8")
            .lines()
            .map(str::to_owned)
            .collect();
        for edit in case.text.lines().filter(|l| l.contains(" = ")) {
            let key = edit.split(" = ").next().unwrap_or_default();
            let prefix = format!("{key} = ");
            if let Some(line) = lines.iter_mut().find(|l| l.starts_with(&prefix)) {
                edit.clone_into(line);
            } else if let Some(at) = lines.iter().position(|l| l.starts_with("title = ")) {
                lines.insert(at + 1, edit.to_owned());
            }
        }
        let text = format!("{}\n", lines.join("\n"));
        commit_files(
            ledger.repo(),
            "refs/heads/main",
            &[(&path, Some(text.into_bytes()))],
            "tickets(hand): edit card",
        );
    }
    tracing::debug!(rule = %case.rule, "ledger corpus block");
    ledger_findings(root, case)
}

/// `TICK007`-`TICK010`: an orphan-branch ledger with one task, then the block's first line as the scenario.
///
/// `none` leaves the ledger as written; `rename <path>` commits the task file under `<path>` without a trailer;
/// `edit <text>` commits a reindex-trailer commit that also appends `<text>` to the task; `stale-reindex` does the same with a trailer naming another frob version; `reindex` reparents the
/// task through the ledger and writes the genuine reindex commit.
fn tick_branch_runner(case: &Case) -> Vec<Finding> {
    const BRANCH: &str = "frob-tickets";
    const TASK: &str = "_unfiled/parser-rewrite.md";
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let repo = init_root_repo(
        root,
        &[
            (".gitignore", ".frob/\n"),
            ("frob.toml", "[tickets]\nref_mode = \"orphan\"\n"),
        ],
    );
    frob_ledger::branch::init_branch(&repo, BRANCH, 5).expect("branch init");
    let cfg = LedgerConfig {
        ref_name: BRANCH.to_owned(),
        ..LedgerConfig::default()
    };
    let ledger = Ledger::open(repo, cfg, std::sync::Arc::new(gob_time::SystemClock))
        .with_layout(frob_ledger::Layout::Branch);
    let task = ledger
        .new_ticket(NewTicket::new("Parser rewrite", TicketType::Task))
        .expect("task")
        .ticket
        .front
        .id;
    let tip = format!("refs/heads/{BRANCH}");
    let script = case.text.lines().next().unwrap_or("none").trim();
    let blob = || {
        ledger
            .repo()
            .read_blob_at(&tip, TASK)
            .expect("read task")
            .expect("task file")
    };
    if let Some(path) = script.strip_prefix("add ") {
        commit_files(
            ledger.repo(),
            &tip,
            &[(path, Some(b"name: x\n".to_vec()))],
            "tickets(hand): add file",
        );
    } else if script == "nudge" || script == "edited-nudge" {
        let spec = frob_ledger::nudge::NudgeSpec {
            ticket_branch: BRANCH.to_owned(),
            bot_ids: Vec::new(),
        };
        let mut bytes = frob_ledger::nudge::render(&spec)
            .expect("render")
            .into_bytes();
        if script == "edited-nudge" {
            bytes.extend_from_slice(b"# edited\n");
        }
        commit_files(
            ledger.repo(),
            &tip,
            &[(frob_ledger::nudge::NUDGE_PATH, Some(bytes))],
            "tickets(hand): nudge",
        );
    } else if let Some(to) = script.strip_prefix("rename ") {
        let bytes = blob();
        commit_files(
            ledger.repo(),
            &tip,
            &[(TASK, None), (to, Some(bytes))],
            "tickets(hand): rename",
        );
    } else if let Some(text) = script.strip_prefix("edit ") {
        let mut bytes = blob();
        bytes.extend_from_slice(format!("\n{text}\n").as_bytes());
        let msg = format!(
            "tickets(reindex): after X\n\nFrob-Reindex: {}\n",
            env!("CARGO_PKG_VERSION")
        );
        commit_files(ledger.repo(), &tip, &[(TASK, Some(bytes))], &msg);
    } else if script == "stale-reindex" {
        let mut bytes = blob();
        bytes.extend_from_slice(b"\nstale\n");
        let msg = "tickets(reindex): after X\n\nFrob-Reindex: 0.0.0\n";
        commit_files(ledger.repo(), &tip, &[(TASK, Some(bytes))], msg);
    } else if script == "bad-mirror" {
        write_file(
            root,
            "frob.toml",
            "[tickets]\nref_mode = \"orphan\"\n[mirror]\nbot_ids = \"not-a-list\"\n",
        );
    } else if script == "reindex" {
        let epic = ledger
            .new_ticket(NewTicket::new("Beta", TicketType::Epic))
            .expect("epic")
            .ticket
            .front
            .id;
        let patch = frob_ledger::ops::Patch {
            sets: vec![(
                "parent".to_owned(),
                Some(toml::Value::String(epic.to_string())),
            )],
            ..frob_ledger::ops::Patch::default()
        };
        ledger.update(task, &patch).expect("reparent");
        ledger.reindex_commit(None).expect("reindex");
    }
    tracing::debug!(rule = %case.rule, script, "ticket-branch corpus block");
    ledger_findings(root, case)
}

/// `TOOL001`/`TOOL002`: a fake tool stage; `TOOL001` runs the block as the stage's shell script, `TOOL002` prints it as zizmor JSON.
fn tool_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let workflow = format!("name: ci\n{}", "# padding line for offsets\n".repeat(30));
    write_file(root, ".github/workflows/ci.yml", &workflow);
    let (script, parser) = if case.rule.as_str() == "TOOL001" {
        // A first line `# parser: <name>` binds that output parser; otherwise the stage has none.
        let parser = case
            .text
            .lines()
            .next()
            .and_then(|l| l.strip_prefix("# parser: "))
            .map_or("none", str::trim);
        (case.text.clone(), parser)
    } else {
        write_file(root, "fixture.json", &case.text);
        ("cat fixture.json\n".to_owned(), "zizmor-json-v1")
    };
    write_file(root, "fake.sh", &script);
    write_file(
        root,
        "frob.toml",
        &format!(
            "[[check.tool]]\nname = \"fake\"\ncommand = \"sh\"\nargs = [\"fake.sh\"]\nparser = \"{parser}\"\nversion_args = [\"-c\", \"echo faketool 1.2.3\"]\n"
        ),
    );
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: false,
        only: vec!["TOOL".to_owned()],
        ..CheckOptions::default()
    };
    tracing::debug!(rule = %case.rule, "tool corpus block");
    run(root, &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

/// `REF001`/`TODO002`: a trunk-mode ledger with one open and one done ticket, or none for a `vacuous` block.
///
/// The block's `=== path` sections (or its own file) are written into the tree; `{{OPEN}}` and `{{DONE}}` expand to the
/// two ticket ids. A `vacuous` block gets an empty ledger, so the rule is applicable yet examines nothing.
fn ledger_ref_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let repo = init_root_repo(root, &[(".gitignore", ".frob/\n")]);
    let ledger = Ledger::open(
        repo,
        LedgerConfig::default(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let vacuous = case.text.contains("{{VACUOUS}}");
    let (mut open, mut done) = (String::new(), String::new());
    if !vacuous {
        let id = |title: &str| {
            ledger
                .new_ticket(NewTicket::new(title, TicketType::Task))
                .expect("ticket")
                .ticket
                .front
                .id
        };
        let open_id = id("Open work");
        let done_id = id("Finished work");
        ledger
            .drop_ticket(done_id, "not needed any more")
            .expect("drop ticket");
        open = open_id.to_string();
        done = done_id.to_string();
    }
    write_file(root, "frob.toml", "[tickets]\n");
    for step in steps(case) {
        if let Step::File(path, text) = step {
            let text = text
                .replace("{{VACUOUS}}", "")
                .replace("{{OPEN}}", &open)
                .replace("{{DONE}}", &done);
            write_file(root, &path, &text);
        }
    }
    tracing::debug!(rule = %case.rule, vacuous, "ledger-reference corpus block");
    ledger_findings(root, case)
}

/// Probe that answers every read with one canned reply (or the reason there was none).
struct CannedProbe(Result<frob_obligations::tick_protect::Reply, String>);

impl frob_obligations::tick_protect::ProtectionProbe for CannedProbe {
    fn get(&self, _path: &str) -> Result<frob_obligations::tick_protect::Reply, String> {
        self.0.clone()
    }
}

/// `TICK011`: the block is `<status> <body>` or `unreachable`, judged as the hosting API's protection reply.
fn tick_protect_runner(case: &Case) -> Vec<Finding> {
    let line = case.text.lines().next().unwrap_or_default().trim();
    let reply = match line.split_once(' ') {
        Some((status, body)) => Ok(frob_obligations::tick_protect::Reply {
            status: status.parse().expect("status code"),
            body: body.to_owned(),
        }),
        None => Err(format!("no reply: {line}")),
    };
    tracing::debug!(line, "TICK011 corpus block");
    let verdict =
        frob_obligations::tick_protect::check_branch(&CannedProbe(reply), "o", "r", "frob-tickets");
    frob_obligations::tick_protect::tick011(&verdict, "frob-tickets")
        .into_iter()
        .collect()
}

/// Route a block to the runner for its rule family.
fn runner(case: &Case) -> Vec<Finding> {
    let rule = case.rule.as_str();
    if rule.starts_with("CI") {
        ci_runner(case)
    } else if rule.starts_with("TOOL") {
        tool_runner(case)
    } else if matches!(rule, "TICK001" | "TICK003" | "TICK004" | "TICK005") {
        tick_dir_runner(case)
    } else if matches!(rule, "TICK007" | "TICK008" | "TICK009" | "TICK010") {
        tick_branch_runner(case)
    } else if rule == "TICK011" {
        tick_protect_runner(case)
    } else if rule.starts_with("GRL") {
        grl_runner(case)
    } else if matches!(rule, "REF001" | "TODO002") {
        ledger_ref_runner(case)
    } else if rule == "SIB001" {
        sib_runner(case)
    } else if matches!(rule, "SCOPE001" | "TICK002") {
        scope_runner(case)
    } else {
        repo_runner(case)
    }
}

/// The corpus drives fake tool stages through `sh`; without it the run is a named skip.
#[test]
fn mdtest_corpus() {
    if !gob_exec::require_sh("mdtest_corpus") {
        return;
    }
    let dir = gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR")).join("tests/mdtest");
    let report = gob_mdtest::run_dir(&dir, &gob_mdtest::Runner::new(runner));
    assert!(
        !report.files.is_empty(),
        "no markdown files under {}",
        gob_mdtest::shown(&dir)
    );
    assert!(
        report.passed(),
        "mdtest corpus failed:\n{}",
        report.render()
    );
}

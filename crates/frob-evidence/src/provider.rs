//! Evidence providers: `nextest`, `pytest`, `vitest`, `jest`, `dotnet`, `command` and `file`.
//!
//! Each provider turns one measurement into a [`Capture`] (or a hashed file),
//! and [`build_record`] turns that into an [`EvidenceRecord`]: the transcript is
//! redacted with `gob_log::redact`, hashed with blake3 and stored inline or in
//! the blob store. Processes only ever run through `gob-exec` with a bounded
//! timeout.

use gob_path::Shown;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use frob_ledger::model::Stamp;
use gob_exec::{Outcome, Program, Runner, Spec};

use crate::attestation::escape_non_ascii;
use crate::error::{EvidenceError, Result};
use crate::record::{EvidenceRecord, NonPassingCounts, Provider, Status, digest_hex};
use crate::scrub::PathScrub;
use crate::store::{BlobStore, Stored};
use crate::workspace::Workspace;

impl Capture {
    /// Opt in: count the named non-passing kinds (`skipped`, `xfailed`, `xpassed`) as executed tests so they can satisfy evidence.
    ///
    /// The counts in `non_passing` are kept, so the record still reports them as a distinct state.
    /// Unknown kind names are ignored with a warning.
    pub fn admit_non_passing(&mut self, kinds: &[String]) {
        for kind in kinds {
            let names = match kind.as_str() {
                "skipped" => &self.non_passing.skipped,
                "xfailed" => &self.non_passing.xfailed,
                "xpassed" => &self.non_passing.xpassed,
                other => {
                    tracing::warn!(
                        kind = other,
                        "unknown non-passing kind in [tests] non_passing_counts"
                    );
                    continue;
                }
            };
            for name in names {
                if !self.tests.contains(name) {
                    self.tests.push(name.clone());
                }
            }
            tracing::info!(
                kind = kind.as_str(),
                count = names.len(),
                "non-passing tests admitted as executed"
            );
        }
    }
}

/// What one measured process produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capture {
    /// The exit code when the process exited normally.
    pub exit_code: Option<i32>,
    /// True when the process exited 0 and no test failed.
    pub passed: bool,
    /// False when the process timed out or died on a signal (the run is unmeasured).
    pub measured: bool,
    /// Names of the tests that executed.
    pub tests: Vec<String>,
    /// Names of the tests that failed, timed out or crashed (a subset of `tests`).
    pub failed_tests: Vec<String>,
    /// Outcomes that executed without passing or failing (skip, xfail, xpass); never in `tests`.
    pub non_passing: NonPassing,
    /// The redacted transcript.
    pub transcript: String,
}

// frob:ticket 01M1T07NW78MGWRF7HZQMPSRAV
/// Test outcomes that are neither a pass nor a failure; counted apart, and never evidence that a test passed.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct NonPassing {
    /// Tests that were skipped (not executed).
    pub skipped: Vec<String>,
    /// Tests that failed as expected (`xfail`).
    pub xfailed: Vec<String>,
    /// Tests marked `xfail` that passed anyway (`XPASS`, non-strict).
    pub xpassed: Vec<String>,
}

impl NonPassing {
    /// The per-kind counts, as a record carries them.
    pub fn counts(&self) -> NonPassingCounts {
        NonPassingCounts {
            skipped: self.skipped.len() as u64,
            xfailed: self.xfailed.len() as u64,
            xpassed: self.xpassed.len() as u64,
        }
    }

    /// The total number of non-passing outcomes across the three kinds.
    pub fn count(&self) -> usize {
        self.skipped.len() + self.xfailed.len() + self.xpassed.len()
    }
}

// frob:ticket 01M40P6CWYKN4V9HEBRXR3342F
/// Split `input` into arguments by POSIX shell quoting rules, without running a shell.
///
/// Whitespace separates words; `'...'` is literal; inside `"..."` a backslash escapes only
/// `"`, `\`, `$`, backtick and newline; outside quotes a backslash escapes the next character
/// (backslash-newline vanishes); an empty quoted pair is an empty word. Nothing is expanded:
/// `$`, `|`, `;`, globs and `#` are ordinary characters, so the result goes to `gob-exec` as an argument vector.
///
/// # Errors
///
/// [`EvidenceError::BadReference`] for an unterminated quote or a trailing backslash.
pub fn split_args(input: &str) -> Result<Vec<String>> {
    #[derive(Clone, Copy, PartialEq)]
    enum Mode {
        Bare,
        Single,
        Double,
    }
    let bad = |what: &str| {
        tracing::warn!(input, what, "unparseable evidence reference");
        EvidenceError::BadReference(format!("{what} in `{input}`"))
    };
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut mode = Mode::Bare;
    let mut started = false;
    let mut chars = input.chars();
    while let Some(ch) = chars.next() {
        match (mode, ch) {
            (Mode::Single, '\'') | (Mode::Double, '"') => mode = Mode::Bare,
            (Mode::Double, '\\') => match chars.next() {
                Some('\n') => {}
                Some(c @ ('"' | '\\' | '$' | '`')) => cur.push(c),
                Some(c) => {
                    cur.push('\\');
                    cur.push(c);
                }
                None => return Err(bad("unterminated quote")),
            },
            (Mode::Single | Mode::Double, c) => cur.push(c),
            (Mode::Bare, '\'') => {
                mode = Mode::Single;
                started = true;
            }
            (Mode::Bare, '"') => {
                mode = Mode::Double;
                started = true;
            }
            (Mode::Bare, '\\') => match chars.next() {
                Some('\n') => {}
                Some(c) => {
                    cur.push(c);
                    started = true;
                }
                None => return Err(bad("trailing backslash")),
            },
            (Mode::Bare, c) if c.is_whitespace() => {
                if started {
                    out.push(std::mem::take(&mut cur));
                    started = false;
                }
            }
            (Mode::Bare, c) => {
                cur.push(c);
                started = true;
            }
        }
    }
    if mode != Mode::Bare {
        return Err(bad("unterminated quote"));
    }
    if started {
        out.push(cur);
    }
    Ok(out)
}

/// The tests a nextest or pytest run reported: every executed name and the failing subset.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Parsed {
    /// Names of the tests that executed, in first-seen order.
    pub tests: Vec<String>,
    /// Names of the tests that failed, timed out or crashed.
    pub failed: Vec<String>,
    /// Skip, xfail and xpass outcomes, kept out of `tests` so they never satisfy evidence.
    pub non_passing: NonPassing,
}

impl Parsed {
    /// Record `name` as executed, and as failed when `failed`; duplicates are ignored.
    fn note(&mut self, name: &str, failed: bool) {
        if !self.tests.iter().any(|n| n == name) {
            self.tests.push(name.to_owned());
        }
        if failed && !self.failed.iter().any(|n| n == name) {
            tracing::warn!(test = name, "test failed");
            self.failed.push(name.to_owned());
        }
    }
}

/// The tests in nextest's libtest-json lines (`ok` and `failed` events).
pub fn parse_libtest_json(stdout: &str) -> Parsed {
    let mut parsed = Parsed::default();
    for line in stdout.lines().map(str::trim).filter(|l| l.starts_with('{')) {
        let Ok(v) = serde_json::from_str::<serde_json::Value>(line) else {
            continue;
        };
        if v.get("type").and_then(|t| t.as_str()) != Some("test") {
            continue;
        }
        let event = v.get("event").and_then(|e| e.as_str()).unwrap_or_default();
        if !matches!(event, "ok" | "failed") {
            continue;
        }
        if let Some(name) = v.get("name").and_then(|n| n.as_str()) {
            // nextest names are `<binary id>$<test path>`; keep the test path.
            let name = name.rsplit_once('$').map_or(name, |(_, t)| t);
            parsed.note(name, event == "failed");
        }
    }
    parsed
}

/// The tests in nextest's human status lines (`PASS`, `FAIL`, `TIMEOUT`, `SIG...`).
///
/// Used when libtest-json is unavailable or printed no test events.
pub fn parse_human(transcript: &str) -> Parsed {
    let mut parsed = Parsed::default();
    for line in transcript.lines().map(str::trim) {
        let verdict = if line.starts_with("PASS ") {
            false
        } else if ["FAIL ", "TIMEOUT ", "SIG"]
            .iter()
            .any(|p| line.starts_with(p))
        {
            true
        } else {
            continue;
        };
        let Some((_, after)) = line.split_once(']') else {
            continue;
        };
        if let Some(name) = after.split_whitespace().last() {
            parsed.note(name, verdict);
        }
    }
    parsed
}

fn spec(program: Program, args: Vec<String>, cwd: &Path, timeout: Duration) -> Spec {
    Spec {
        program,
        args,
        cwd: Some(cwd.to_path_buf()),
        env: plain_env(),
        timeout,
        capture: true,
    }
}

/// Environment that makes a provider print plain text: no color, no progress bar, no Unicode.
///
/// cargo-nextest 0.9.146 has no Unicode option (its summary rule is always U+2500), so
/// `LC_ALL=C` only plains other tools and [`escape_non_ascii`] in [`build_record`] is what keeps nextest text ASCII.
/// `NEXTEST_SHOW_PROGRESS` is left unset because nextest warns when it meets `NEXTEST_HIDE_PROGRESS_BAR` too.
pub fn plain_env() -> Vec<(String, String)> {
    [
        ("NEXTEST_HIDE_PROGRESS_BAR", "1"),
        ("CARGO_TERM_COLOR", "never"),
        ("NO_COLOR", "1"),
        ("LC_ALL", "C"),
        ("DOTNET_CLI_TELEMETRY_OPTOUT", "1"),
        ("DOTNET_NOLOGO", "1"),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_owned(), v.to_owned()))
    .collect()
}

fn exit_of(status: Outcome) -> (Option<i32>, bool) {
    match status {
        Outcome::Exited(c) => (Some(c), true),
        Outcome::Signaled | Outcome::TimedOut => (None, false),
    }
}

// frob:ticket 01M40M7QE5VN76P1HTDY06BXB6
/// Run `cargo nextest run [--profile <profile>] <filter_args>` in `cwd` and capture the verdict and executed tests.
///
/// An empty `profile` means nextest's `default`. The profile is always passed as `--profile` and
/// exported as `NEXTEST_PROFILE`, so a `NEXTEST_PROFILE` inherited from an outer nextest run or
/// shell (which the target project may not define) never selects the profile.
///
/// First tries `--message-format libtest-json`; if nextest rejects it (older
/// versions) or prints no events, the human `PASS`/`FAIL` lines are parsed.
///
/// # Errors
///
/// [`EvidenceError::Exec`] when cargo cannot be started.
pub fn run_nextest(
    runner: &Runner,
    cwd: &Path,
    filter_args: &[String],
    profile: &str,
    timeout: Duration,
) -> Result<Capture> {
    run_nextest_with_env(runner, cwd, filter_args, profile, &[], timeout)
}

// frob:ticket 01M40M7QE5VN76P1HTDY06BXB6
/// [`run_nextest`] with extra child environment (applied before the profile pin; used to inject a hostile `NEXTEST_PROFILE` in tests).
///
/// # Errors
///
/// [`EvidenceError::Exec`] when cargo cannot be started.
pub fn run_nextest_with_env(
    runner: &Runner,
    cwd: &Path,
    filter_args: &[String],
    profile: &str,
    extra_env: &[(String, String)],
    timeout: Duration,
) -> Result<Capture> {
    let mut args = vec!["nextest".to_owned(), "run".to_owned()];
    let profile = if profile.is_empty() {
        "default"
    } else {
        profile
    };
    args.extend(["--profile".to_owned(), profile.to_owned()]);
    args.extend(filter_args.iter().cloned());
    let mut json_args = args.clone();
    json_args.extend(["--message-format".to_owned(), "libtest-json".to_owned()]);
    let mut json_spec = spec(Program::Cargo, json_args, cwd, timeout);
    json_spec.env.extend(extra_env.iter().cloned());
    json_spec
        .env
        .push(("NEXTEST_PROFILE".to_owned(), profile.to_owned()));
    json_spec.env.push((
        "NEXTEST_EXPERIMENTAL_LIBTEST_JSON".to_owned(),
        "1".to_owned(),
    ));
    let mut out = runner.run(&json_spec)?;
    let mut seen = parse_libtest_json(&out.stdout);
    let mut json = !seen.tests.is_empty();
    if !json
        && matches!(out.status, Outcome::Exited(c) if c != 0)
        && (out.stderr.contains("libtest-json") || out.stderr.contains("message-format"))
    {
        tracing::info!("nextest rejected libtest-json; retrying with the human reporter");
        let mut human = spec(Program::Cargo, args, cwd, timeout);
        human.env.extend(extra_env.iter().cloned());
        human
            .env
            .push(("NEXTEST_PROFILE".to_owned(), profile.to_owned()));
        out = runner.run(&human)?;
        json = false;
    }
    let mut transcript = out.stderr.clone();
    if !json {
        seen = parse_human(&out.stderr);
        if seen.tests.is_empty() {
            seen = parse_human(&out.stdout);
        }
        if !out.stdout.trim().is_empty() {
            transcript.push_str(&out.stdout);
        }
    }
    let (exit_code, measured) = exit_of(out.status);
    let passed = exit_code == Some(0) && seen.failed.is_empty();
    tracing::info!(
        ?exit_code,
        passed,
        tests = seen.tests.len(),
        failed = ?seen.failed,
        json,
        "nextest captured"
    );
    Ok(Capture {
        exit_code,
        passed,
        measured,
        tests: seen.tests,
        failed_tests: seen.failed,
        non_passing: NonPassing::default(),
        transcript,
    })
}

/// True when a nextest run executed no test because its filter matched none.
///
/// nextest exits 4 (or says "no tests to run") then; a build failure also runs no test but is a real failed measurement.
pub fn matched_no_tests(cap: &Capture) -> bool {
    cap.tests.is_empty() && (cap.exit_code == Some(4) || cap.transcript.contains("no tests to run"))
}

/// Decode the XML character and entity references in an attribute value.
fn xml_unescape(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    let mut rest = raw;
    while let Some(at) = rest.find('&') {
        out.push_str(&rest[..at]);
        rest = &rest[at..];
        let Some(end) = rest.find(';') else { break };
        let decoded = match &rest[1..end] {
            "lt" => Some('<'),
            "gt" => Some('>'),
            "amp" => Some('&'),
            "quot" => Some('"'),
            "apos" => Some('\''),
            num => num
                .strip_prefix('#')
                .and_then(|n| match n.strip_prefix(['x', 'X']) {
                    Some(hex) => u32::from_str_radix(hex, 16).ok(),
                    None => n.parse().ok(),
                })
                .and_then(char::from_u32),
        };
        if let Some(c) = decoded {
            out.push(c);
            rest = &rest[end + 1..];
        } else {
            out.push('&');
            rest = &rest[1..];
        }
    }
    out.push_str(rest);
    out
}

/// The value of attribute `key` in the start-tag text `tag`, decoded.
fn xml_attr(tag: &str, key: &str) -> Option<String> {
    let needle = format!(" {key}=\"");
    let from = tag.find(&needle)? + needle.len();
    let len = tag[from..].find('"')?;
    Some(xml_unescape(&tag[from..from + len]))
}

/// A junit `file` attribute as a portable repo-relative path (`/` separators on every host).
///
/// pytest writes the host's separators (`tests\\test_m.py` on Windows); the components are rebuilt
/// through [`gob_git::RelPath`]. A path it refuses (`..`, absolute) keeps its joined components.
// frob:ticket 01M44J072TEWFTCB1AFVTN9C8B
fn portable_file(file: &str) -> String {
    let joined = file
        .split(['/', '\\'])
        .filter(|c| !c.is_empty())
        .collect::<Vec<_>>()
        .join("/");
    match gob_git::RelPath::new(joined.clone()) {
        Ok(rel) => rel.to_string(),
        Err(e) => {
            tracing::debug!(file, error = %e, "junit file is not a repo-relative path; keeping it joined");
            joined
        }
    }
}

/// The pytest node id (`tests/test_m.py::TestC::test_m[1]`) of one junit `testcase` start tag.
///
/// Needs the xunit1 `file` attribute; `classname` minus the module's dotted path gives the
/// classes. Without `file` (collection errors) the classname and name are joined with `::`.
fn node_id(tag: &str, prefix: &str) -> String {
    let name = xml_attr(tag, "name").unwrap_or_default();
    let class = xml_attr(tag, "classname").unwrap_or_default();
    let Some(file) = xml_attr(tag, "file") else {
        return if class.is_empty() {
            name
        } else {
            format!("{class}::{name}")
        };
    };
    let file = portable_file(&file);
    let module = file.strip_suffix(".py").unwrap_or(&file).replace('/', ".");
    // frob:ticket 01M4CTTYH76JQASEJJQC02YD0F
    // A module that failed to collect is a testcase named by its dotted module path, not a test: its real node id is the file.
    if class.is_empty() && name == module {
        return if prefix.is_empty() {
            file
        } else {
            format!("{prefix}/{file}")
        };
    }
    let file = if prefix.is_empty() {
        file
    } else {
        format!("{prefix}/{file}")
    };
    let classes = class
        .strip_prefix(&module)
        .map_or("", |c| c.trim_start_matches('.'));
    let mut id = file;
    for c in classes.split('.').filter(|c| !c.is_empty()) {
        id.push_str("::");
        id.push_str(c);
    }
    id.push_str("::");
    id.push_str(&name);
    id
}

/// The tests in a pytest junit XML report (written with `-o junit_family=xunit1`).
///
/// Each `testcase` is named by its node id, relative to pytest's rootdir; one with a `failure` or
/// `error` child failed, one with a `skipped` child did not execute and is left out.
pub fn parse_junit(xml: &str) -> Parsed {
    parse_junit_under(xml, "")
}

// frob:ticket 01M4GKBEBGBTA03VFB90SDR858
/// [`parse_junit`] with every node id's file prefixed by `prefix`, the rootdir's path below the repository root.
pub fn parse_junit_under(xml: &str, prefix: &str) -> Parsed {
    let mut parsed = Parsed::default();
    let mut rest = xml;
    while let Some(at) = rest.find("<testcase") {
        rest = &rest[at + "<testcase".len()..];
        let Some(tag_end) = rest.find('>') else { break };
        let tag = &rest[..tag_end];
        let (body, next) = if tag.ends_with('/') {
            ("", &rest[tag_end + 1..])
        } else {
            let after = &rest[tag_end + 1..];
            let close = after.find("</testcase>").unwrap_or(after.len());
            (&after[..close], &after[close..])
        };
        rest = next;
        if body.contains("<skipped") {
            let id = node_id(tag, prefix);
            // pytest writes xfail as a skipped child typed `pytest.xfail`.
            if body.contains("pytest.xfail") {
                tracing::info!(test = %id, "xfail is not evidence: counted apart");
                parsed.non_passing.xfailed.push(id);
            } else {
                tracing::info!(test = %id, "skip is not evidence: counted apart");
                parsed.non_passing.skipped.push(id);
            }
            continue;
        }
        let failed = body.contains("<failure") || body.contains("<error");
        parsed.note(&node_id(tag, prefix), failed);
    }
    parsed
}

// frob:ticket 01M4GKBEBGBTA03VFB90SDR858
/// The pytest rootdir below `root` (repository-relative, `/`-separated), read from the `rootdir:` header of `transcript`.
///
/// Empty when pytest ran with `-q` (no header), when the rootdir is `root` itself or is outside it.
fn rootdir_prefix(transcript: &str, root: &Path) -> String {
    let Some(line) = transcript.lines().find_map(|l| l.strip_prefix("rootdir: ")) else {
        return String::new();
    };
    let dir = Path::new(line.split(", ").next().unwrap_or(line).trim());
    let canon = |p: &Path| gob_exec::canonical(p).unwrap_or_else(|_| p.to_path_buf());
    let rel = canon(dir)
        .strip_prefix(canon(root))
        .map(crate::pathtext::text)
        .unwrap_or_default();
    portable_file(&rel)
}

static JUNIT_SEQ: AtomicU64 = AtomicU64::new(0);

// frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
/// How pytest is started: the program, the arguments before pytest's own, and a label for `--dry-run`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PytestRunner {
    program: Program,
    prefix: Vec<String>,
    label: String,
}

impl PytestRunner {
    /// The command line as shown by `frob test --dry-run` (the interpreter relative to the repository when it lives there).
    pub fn label(&self) -> &str {
        &self.label
    }
}

// frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
/// Pick the pytest launcher for the work tree `root`.
///
/// `python` (`[tests] python`) wins: a bare name is found on `PATH`, a path is taken from `root` when relative.
/// Without it the project's own `.venv` interpreter in `root` runs `-m pytest`; with neither, `pytest` on `PATH`.
pub fn pytest_runner(root: &Path, python: &str) -> PytestRunner {
    let interpreter = |path: PathBuf| {
        let label = path.strip_prefix(root).map_or_else(
            |_| Shown::of(&path).to_string(),
            |r| Shown::of(r).to_string(),
        );
        PytestRunner {
            label: format!("{} -m pytest", label.replace('\\', "/")),
            program: Program::Hook { path },
            prefix: vec!["-m".to_owned(), "pytest".to_owned()],
        }
    };
    if !python.is_empty() {
        if python.contains(['/', '\\']) {
            return interpreter(root.join(python));
        }
        return PytestRunner {
            program: Program::Tool {
                name: python.to_owned(),
            },
            prefix: vec!["-m".to_owned(), "pytest".to_owned()],
            label: format!("{python} -m pytest"),
        };
    }
    for rel in [".venv/bin/python", ".venv/Scripts/python.exe"] {
        let path = root.join(rel);
        if path.is_file() {
            return interpreter(path);
        }
    }
    PytestRunner {
        program: Program::Tool {
            name: "pytest".to_owned(),
        },
        prefix: Vec::new(),
        label: "pytest".to_owned(),
    }
}

// frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
/// The files pytest's transcript names as failing to collect (`ERROR collecting <file>` headers and `ERROR <file> - ...` summary lines), in order and unique.
fn collection_error_files(transcript: &str) -> Vec<String> {
    let mut files: Vec<String> = Vec::new();
    for line in transcript.lines() {
        let line = line.trim().trim_matches('_').trim();
        let token = if let Some(rest) = line.strip_prefix("ERROR collecting ") {
            rest.split_whitespace().next()
        } else if let Some(rest) = line.strip_prefix("ERROR ") {
            rest.split_whitespace().next()
        } else {
            None
        };
        let Some(token) = token else { continue };
        let file = token.split("::").next().unwrap_or(token);
        if file.contains(".py") && !files.iter().any(|f| f == file) {
            files.push(file.to_owned());
        }
    }
    files
}

// frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
/// The refusal for a pytest run that exited `code` (2, 3 or 4) without running the tests, naming the files it failed to collect.
fn runner_error(code: i32, transcript: &str) -> EvidenceError {
    let files = collection_error_files(transcript);
    let detail = if files.is_empty() {
        transcript
            .lines()
            .rev()
            .find(|l| !l.trim().is_empty())
            .map_or_else(String::new, |l| format!("; last output: {}", l.trim()))
    } else {
        format!("; collection errors in {}", files.join(", "))
    };
    tracing::warn!(
        code,
        detail,
        "pytest could not run the tests; recording nothing"
    );
    EvidenceError::RunnerError {
        exit_code: code,
        files: detail,
    }
}

/// Run `pytest -o junit_family=xunit1 --junitxml=<tmp> <args>` in `cwd` and capture the verdict and executed tests.
///
/// `pytest` must be in `allowed` (`[evidence] allowed_tools`); `python` is `[tests] python` (see [`pytest_runner`]).
/// The junit file is read, then removed. The transcript is pytest's stdout then stderr, left to [`build_record`] to redact and escape.
///
/// # Errors
///
/// [`EvidenceError::ToolNotAllowed`] when `pytest` is not allowlisted, [`EvidenceError::Exec`] when it cannot start,
/// [`EvidenceError::RunnerError`] when pytest exits 2, 3 or 4 (it could not run the tests, so there is nothing to record).
pub fn run_pytest(
    runner: &Runner,
    allowed: &[String],
    cwd: &Path,
    python: &str,
    args: &[String],
    timeout: Duration,
) -> Result<Capture> {
    if !allowed.iter().any(|a| a == "pytest") {
        tracing::warn!("pytest evidence refused: tool not allowlisted");
        return Err(EvidenceError::ToolNotAllowed {
            tool: "pytest".to_owned(),
        });
    }
    let junit = std::env::temp_dir().join(format!(
        "frob-pytest-{}-{}.xml",
        std::process::id(),
        JUNIT_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    let launcher = pytest_runner(cwd, python);
    tracing::info!(runner = launcher.label(), "starting pytest");
    let mut full = launcher.prefix;
    full.extend([
        "-o".to_owned(),
        "junit_family=xunit1".to_owned(),
        "-rX".to_owned(),
        format!("--junitxml={}", Shown::with_home(&junit, None)),
    ]);
    full.extend(args.iter().cloned());
    let out = runner.run(&spec(launcher.program, full, cwd, timeout));
    let xml = std::fs::read_to_string(&junit).unwrap_or_default();
    if junit.exists()
        && let Err(e) = std::fs::remove_file(&junit)
    {
        tracing::warn!(path = %Shown::of(&junit), error = %e, "could not remove the junit file");
    }
    let out = out?;
    let prefix = rootdir_prefix(&out.stdout, cwd);
    let mut seen = parse_junit_under(&xml, &prefix);
    demote_xpass(&mut seen, &out.stdout, &prefix);
    let mut transcript = out.stdout;
    transcript.push_str(&out.stderr);
    let (exit_code, measured) = exit_of(out.status);
    if let Some(code @ 2..=4) = exit_code {
        return Err(runner_error(code, &transcript));
    }
    let passed = exit_code == Some(0) && seen.failed.is_empty();
    tracing::info!(
        ?exit_code,
        passed,
        tests = seen.tests.len(),
        failed = ?seen.failed,
        non_passing = seen.non_passing.count(),
        "pytest captured"
    );
    Ok(Capture {
        exit_code,
        passed,
        measured,
        tests: seen.tests,
        failed_tests: seen.failed,
        non_passing: seen.non_passing,
        transcript,
    })
}

// frob:ticket 01M1T07NW78MGWRF7HZQMPSRAV
/// Move every test pytest reported `XPASS` (the `-rX` summary) from `seen.tests` to `seen.non_passing.xpassed`.
///
/// junit writes a non-strict xpass as a plain passing testcase, so only the transcript tells it apart.
fn demote_xpass(seen: &mut Parsed, stdout: &str, prefix: &str) {
    for id in stdout.lines().filter_map(|l| l.strip_prefix("XPASS ")) {
        let id = id.split(" - ").next().unwrap_or(id).trim();
        let id = if prefix.is_empty() {
            id.to_owned()
        } else {
            format!("{prefix}/{id}")
        };
        if let Some(at) = seen.tests.iter().position(|t| *t == id) {
            seen.tests.remove(at);
            tracing::info!(test = %id, "xpass is not evidence: counted apart");
            seen.non_passing.xpassed.push(id);
        }
    }
}

/// True when a pytest run collected no test (pytest exits 5), which is no measurement rather than a failure.
pub fn pytest_matched_no_tests(cap: &Capture) -> bool {
    cap.tests.is_empty() && cap.exit_code == Some(5)
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// The program a JavaScript test runner needs on `PATH` before any runner starts.
pub const NODE_PROGRAM: &str = "node";

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// The portable repo-relative name of `file` from a runner report, made relative to `cwd` and prefixed with `member`.
fn js_rel_path(file: &str, cwd: &Path, member: &str) -> String {
    let rel = Path::new(file)
        .strip_prefix(cwd)
        .map_or_else(|_| file.to_owned(), crate::pathtext::text);
    let rel = portable_file(&rel);
    if member.is_empty() {
        rel
    } else {
        format!("{member}/{rel}")
    }
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// The tests in a vitest or jest JSON report (`testResults[].assertionResults[]`, the same shape for both runners).
///
/// A test is named `<file>::suite$<slug>::test$<slug>`: the file made relative to `cwd` and prefixed with
/// `member`, then the unit names the symbol graph gives that test (`gob_symbols::test_unit_name`), so evidence
/// names map back to test units. A repeated title in one suite chain gets `[dupN]` like the unit does; two
/// `describe` blocks of the same title are not told apart. `passed` and `failed` count as executed, `pending`,
/// `skipped`, `todo` and `disabled` do not (they are counted apart as skipped); a file that failed to load (no assertions, failed status) is
/// recorded as a failed test named by its path.
pub fn parse_js_json(json: &str, cwd: &Path, member: &str) -> Parsed {
    let mut parsed = Parsed::default();
    let Ok(doc) = serde_json::from_str::<serde_json::Value>(json) else {
        tracing::warn!("test runner JSON report is unreadable; no tests recorded");
        return parsed;
    };
    let files = doc["testResults"].as_array().map_or(&[][..], Vec::as_slice);
    for file in files {
        let rel = js_rel_path(file["name"].as_str().unwrap_or_default(), cwd, member);
        let cases = file["assertionResults"]
            .as_array()
            .map_or(&[][..], Vec::as_slice);
        if cases.is_empty() && file["status"].as_str() == Some("failed") {
            parsed.note(&rel, true);
            continue;
        }
        let mut seen: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        for case in cases {
            let status = case["status"].as_str().unwrap_or_default();
            let executed = matches!(status, "passed" | "failed");
            if !executed && !matches!(status, "pending" | "skipped" | "todo" | "disabled") {
                continue;
            }
            let mut id = rel.clone();
            for suite in case["ancestorTitles"].as_array().into_iter().flatten() {
                id.push_str("::");
                id.push_str(&gob_symbols::test_unit_name(
                    "suite",
                    suite.as_str().unwrap_or_default(),
                ));
            }
            id.push_str("::");
            id.push_str(&gob_symbols::test_unit_name(
                "case",
                case["title"].as_str().unwrap_or_default(),
            ));
            let count = seen.entry(id.clone()).or_default();
            *count += 1;
            if *count > 1 {
                let _ = write!(id, "[dup{count}]");
            }
            if executed {
                parsed.note(&id, status == "failed");
            } else {
                tracing::info!(test = %id, status, "skipped test is not evidence: counted apart");
                parsed.non_passing.skipped.push(id);
            }
        }
    }
    parsed
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// The runner binary `name`: `node_modules/.bin/<name>` in `cwd` or an ancestor up to `root`, else `name` on `PATH`.
fn find_js_runner(root: &Path, cwd: &Path, name: &str) -> Option<PathBuf> {
    for dir in cwd.ancestors() {
        let bin = dir.join("node_modules").join(".bin");
        let candidates = [bin.join(name), bin.join(format!("{name}.cmd"))];
        if let Some(hit) = candidates.into_iter().find(|c| c.is_file()) {
            return Some(hit);
        }
        if dir == root {
            break;
        }
    }
    which::which(name).ok()
}

// frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
/// The `PATH` value a JavaScript runner starts with: every `node_modules/.bin` from `cwd` up to `root` (nearest first), then `existing`.
///
/// Runners spawn sibling tools by bare name (vite, esbuild, tsc), which only resolve when the project's bin
/// directories lead `PATH`. Returns `None` when no such directory exists (nothing to add) or the value cannot be joined.
#[must_use]
pub fn js_bin_path(
    root: &Path,
    cwd: &Path,
    existing: Option<std::ffi::OsString>,
) -> Option<String> {
    let mut dirs: Vec<PathBuf> = Vec::new();
    for dir in cwd.ancestors() {
        let bin = dir.join("node_modules").join(".bin");
        if bin.is_dir() {
            dirs.push(bin);
        }
        if dir == root {
            break;
        }
    }
    if dirs.is_empty() {
        return None;
    }
    dirs.extend(std::env::split_paths(&existing.unwrap_or_default()));
    match std::env::join_paths(dirs) {
        Ok(joined) => gob_path::exact_text(&joined).map(str::to_owned),
        Err(e) => {
            tracing::warn!(error = %e, "node_modules bin directories not added to PATH: unjoinable entry");
            None
        }
    }
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// What one vitest or jest run needs.
#[derive(Debug, Clone, Copy)]
pub struct JsRun<'a> {
    /// [`Provider::Vitest`] or [`Provider::Jest`].
    pub provider: Provider,
    /// `[evidence] allowed_tools`; the runner must be listed.
    pub allowed: &'a [String],
    /// The program the runner needs on `PATH` ([`NODE_PROGRAM`]).
    pub node: &'a str,
    /// The work tree root.
    pub root: &'a Path,
    /// The workspace member directory relative to `root` (empty at the root); the runner runs there.
    pub member: &'a str,
    /// Runner arguments after the fixed ones (test files relative to the member); empty runs everything.
    pub args: &'a [String],
    /// Wall-clock limit for the runner process.
    pub timeout: Duration,
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// Run vitest or jest (`provider`) on `args` in `root/member` and capture the verdict and executed tests from its JSON report.
///
/// The runner must be in `allowed` (`[evidence] allowed_tools`). `node` names the program the runner needs
/// ([`NODE_PROGRAM`]); an absent `node` or an absent runner (neither in `node_modules/.bin` nor on `PATH`) is a
/// refusal, never a skip. An empty `args` runs every test of the member. Vitest runs as `vitest run`, jest with `--ci`.
///
/// # Errors
///
/// [`EvidenceError::ToolNotAllowed`] when the runner is not allowlisted, [`EvidenceError::RunnerMissing`] when
/// `node` or the runner is absent, [`EvidenceError::BadReference`] when `provider` is not vitest or jest,
/// [`EvidenceError::Exec`] when the runner cannot start.
pub fn run_js_tests(runner: &Runner, job: &JsRun<'_>) -> Result<Capture> {
    let JsRun {
        provider,
        allowed,
        node,
        root,
        member,
        args,
        timeout,
    } = *job;
    let tool = match provider {
        Provider::Vitest | Provider::Jest => provider.as_str(),
        other => {
            return Err(EvidenceError::BadReference(format!(
                "`{}` is not a JavaScript test runner",
                other.as_str()
            )));
        }
    };
    if !allowed.iter().any(|a| a == tool) {
        tracing::warn!(
            tool,
            "JavaScript test evidence refused: tool not allowlisted"
        );
        return Err(EvidenceError::ToolNotAllowed {
            tool: tool.to_owned(),
        });
    }
    let missing = |what: &str| {
        tracing::warn!(
            missing = what,
            runner = tool,
            "JavaScript test run refused: tool missing"
        );
        EvidenceError::RunnerMissing {
            missing: what.to_owned(),
            runner: tool.to_owned(),
        }
    };
    if which::which(node).is_err() {
        return Err(missing(node));
    }
    let cwd = root.join(member);
    let Some(path) = find_js_runner(root, &cwd, tool) else {
        return Err(missing(tool));
    };
    let report = std::env::temp_dir().join(format!(
        "frob-{tool}-{}-{}.json",
        std::process::id(),
        JUNIT_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    let mut full: Vec<String> = if provider == Provider::Vitest {
        vec![
            "run".to_owned(),
            "--reporter=default".to_owned(),
            "--reporter=json".to_owned(),
            format!("--outputFile.json={}", Shown::with_home(&report, None)),
        ]
    } else {
        vec![
            "--ci".to_owned(),
            "--json".to_owned(),
            format!("--outputFile={}", Shown::with_home(&report, None)),
        ]
    };
    full.extend(args.iter().cloned());
    let mut run_spec = spec(Program::Hook { path }, full, &cwd, timeout);
    if let Some(path_var) = js_bin_path(root, &cwd, std::env::var_os("PATH")) {
        tracing::debug!(tool, "node_modules bin directories put on PATH");
        run_spec.env.push(("PATH".to_owned(), path_var));
    }
    let out = runner.run(&run_spec);
    let json = std::fs::read_to_string(&report).unwrap_or_default();
    if report.exists()
        && let Err(e) = std::fs::remove_file(&report)
    {
        tracing::warn!(path = %Shown::of(&report), error = %e, "could not remove the JSON report");
    }
    let out = out?;
    let seen = parse_js_json(&json, &cwd, member);
    let mut transcript = out.stdout;
    transcript.push_str(&out.stderr);
    let (exit_code, measured) = exit_of(out.status);
    let passed = exit_code == Some(0) && seen.failed.is_empty();
    tracing::info!(tool, ?exit_code, passed, tests = seen.tests.len(), failed = ?seen.failed, "JavaScript tests captured");
    Ok(Capture {
        exit_code,
        passed,
        measured,
        tests: seen.tests,
        failed_tests: seen.failed,
        non_passing: NonPassing::default(),
        transcript,
    })
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// True when a vitest or jest run found no test (nothing executed and the runner said so), which is no measurement rather than a failure.
pub fn js_matched_no_tests(cap: &Capture) -> bool {
    cap.tests.is_empty()
        && cap.failed_tests.is_empty()
        && (cap.transcript.contains("No test files found")
            || cap.transcript.contains("No tests found"))
}

/// Run an allowlisted tool (`argv[0]` must be in `allowed`) and capture exit code and transcript.
///
/// # Errors
///
/// [`EvidenceError::BadReference`] for an empty command, [`EvidenceError::ToolNotAllowed`]
/// for a tool outside the allowlist, [`EvidenceError::Exec`] when it cannot start.
pub fn run_command(
    runner: &Runner,
    allowed: &[String],
    cwd: &Path,
    argv: &[String],
    timeout: Duration,
) -> Result<Capture> {
    let (tool, rest) = argv
        .split_first()
        .ok_or_else(|| EvidenceError::BadReference("empty command".to_owned()))?;
    let program = if allowed.iter().any(|a| a == tool) {
        match tool.as_str() {
            "cargo" => Program::Cargo,
            "git" => Program::Git,
            name => Program::Tool {
                name: name.to_owned(),
            },
        }
    } else if let Some(path) = builtin_tool(tool, &builtin_tools()) {
        tracing::debug!(tool, path = %Shown::of(&path), "command evidence: running frob tool allowed by default");
        Program::Hook { path }
    } else {
        tracing::warn!(tool, "command evidence refused: tool not allowlisted");
        return Err(EvidenceError::ToolNotAllowed { tool: tool.clone() });
    };
    let out = runner.run(&spec(program, rest.to_vec(), cwd, timeout))?;
    let (exit_code, measured) = exit_of(out.status);
    let mut transcript = out.stdout;
    transcript.push_str(&out.stderr);
    Ok(Capture {
        exit_code,
        passed: exit_code == Some(0),
        measured,
        tests: Vec::new(),
        failed_tests: Vec::new(),
        non_passing: NonPassing::default(),
        transcript,
    })
}

/// Canonical paths of the running executable and its `frob`/`grimble` siblings, allowed as command tools without listing.
pub fn builtin_tools() -> Vec<PathBuf> {
    let Ok(exe) = std::env::current_exe().and_then(|e| gob_exec::canonical(&e)) else {
        return Vec::new();
    };
    let mut out = vec![exe.clone()];
    if let Some(dir) = exe.parent() {
        for name in ["frob", "grimble"] {
            if let Ok(p) = gob_exec::canonical(&dir.join(name))
                && p.is_file()
                && !out.contains(&p)
            {
                out.push(p);
            }
        }
    }
    out
}

/// The canonical path `tool` names when it is one of `builtins` (a path, or a bare name found on `PATH`).
pub fn builtin_tool(tool: &str, builtins: &[PathBuf]) -> Option<PathBuf> {
    let found = if tool.contains(['/', '\\']) {
        PathBuf::from(tool)
    } else {
        which::which(tool).ok()?
    };
    let canon = gob_exec::canonical(&found).ok()?;
    builtins.contains(&canon).then_some(canon)
}

/// Turn a capture into a record: redact, scrub local paths, hash, store inline or by URI.
///
/// The digest is over the scrubbed, escaped text, exactly what is stored and written to the event.
///
/// # Errors
///
/// [`EvidenceError::Io`] when the blob store cannot be written.
pub fn build_record(
    store: &BlobStore,
    scrub: &PathScrub,
    provider: Provider,
    reference: &str,
    capture: &Capture,
    accepts: &[usize],
    at: Stamp,
) -> Result<EvidenceRecord> {
    // frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A
    let redacted = escape_non_ascii(&scrub.apply(&gob_log::redact(&capture.transcript)));
    let digest = digest_hex(redacted.as_bytes());
    let (uri, inline) = match store.put(&redacted)? {
        Stored::Inline(t) => (None, Some(t)),
        Stored::Uri(u) => (Some(u), None),
    };
    // frob:ticket 01M4NZCSJWT2XSEZQBVPNMA6HM
    // The full name list lives only in the artifact file; the event keeps the count and the list's digest.
    let (tests, test_count, tests_digest) = if capture.tests.is_empty() {
        (Vec::new(), None, None)
    } else {
        let joined = escape_non_ascii(&scrub.apply(&capture.tests.join("\n")));
        let count = capture.tests.len() as u64;
        match store.put_artifact(&joined)? {
            Some(_) => (Vec::new(), Some(count), Some(digest_hex(joined.as_bytes()))),
            None => (
                joined.lines().map(str::to_owned).collect(),
                Some(count),
                None,
            ),
        }
    };
    Ok(EvidenceRecord {
        provider,
        reference: scrub.apply(reference),
        digest,
        uri,
        status: if capture.measured {
            Status::Measured
        } else {
            Status::Unmeasured
        },
        captured_at: at.seconds(),
        accepts: accepts.to_vec(),
        passed: capture.measured.then_some(capture.passed),
        exit_code: capture.exit_code,
        tests,
        test_count,
        tests_digest,
        // frob:ticket 01M4K55NZMZWBGMZ6PP6V3WPZD
        failed_tests: capture
            .failed_tests
            .iter()
            .map(|t| scrub.apply(t))
            .collect(),
        non_passing: capture.non_passing.counts(),
        inline,
        size: redacted.len() as u64,
        attestation: None,
        head: None,
    })
}

// frob:ticket 01M4HW9GZT9T70NGGAHAH1CKJF
/// Refuse a `file` reference whose bytes are not exactly a regular file tracked at `HEAD`.
///
/// Gitignored, untracked, staged-but-uncommitted, modified, symlinked, absolute and
/// `..`-escaping paths all fail: the hash would name content that exists on no ref.
/// The comparison is on raw bytes, so a working tree that rewrites line endings on
/// checkout counts as modified.
///
/// # Errors
///
/// [`EvidenceError::FileNotCommitted`] with the reason; [`EvidenceError::Io`] when the file cannot be read.
pub fn require_committed(ws: &Workspace, path: &str) -> Result<()> {
    let refuse = |reason: &str| {
        tracing::warn!(path, reason, "file evidence refused");
        Err(EvidenceError::FileNotCommitted {
            path: path.to_owned(),
            reason: reason.to_owned(),
        })
    };
    let Ok(rel) = gob_path::RelPath::new(path.strip_prefix("./").unwrap_or(path)) else {
        return refuse("is not a path inside the repository");
    };
    let rel = rel.as_str();
    let full = ws.root.join(rel);
    let meta = std::fs::symlink_metadata(&full).map_err(|e| EvidenceError::io(&full, e))?;
    if meta.file_type().is_symlink() {
        return refuse("is a symlink, not a regular tracked file");
    }
    let disk = std::fs::read(&full).map_err(|e| EvidenceError::io(&full, e))?;
    let repo = ws.ledger.repo();
    if repo.rev_parse("HEAD").is_err() {
        return refuse("is not committed (the repository has no commit yet)");
    }
    match repo.read_blob_at("HEAD", rel)? {
        None => refuse("is not tracked at HEAD (it is untracked, gitignored or only staged)"),
        Some(committed) if committed != disk => {
            refuse("differs from its committed content (it is modified)")
        }
        Some(_) => {
            tracing::debug!(path, "file evidence matches HEAD");
            Ok(())
        }
    }
}

/// Hash the file at `path` (relative to `root`) as a `file` record.
///
/// # Errors
///
/// [`EvidenceError::Io`] when the file cannot be read.
pub fn hash_file(root: &Path, path: &str, accepts: &[usize], at: Stamp) -> Result<EvidenceRecord> {
    let full = root.join(path);
    let bytes = std::fs::read(&full).map_err(|e| EvidenceError::io(&full, e))?;
    tracing::info!(path, bytes = bytes.len(), "file evidence hashed");
    Ok(EvidenceRecord {
        provider: Provider::File,
        reference: path.to_owned(),
        digest: digest_hex(&bytes),
        uri: None,
        status: Status::Measured,
        captured_at: at.seconds(),
        accepts: accepts.to_vec(),
        passed: None,
        exit_code: None,
        tests: Vec::new(),
        test_count: None,
        tests_digest: None,
        failed_tests: Vec::new(),
        non_passing: NonPassingCounts::default(),
        inline: None,
        size: bytes.len() as u64,
        attestation: None,
        head: None,
    })
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The program a .NET test run needs on `PATH` (unless `[evidence.dotnet] path` names it).
pub const DOTNET_PROGRAM: &str = "dotnet";

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The file name `dotnet test` is told to write its TRX report to, inside the results directory.
const TRX_FILE: &str = "frob.trx";

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// What a TRX report said: the executed and failed test ids and a readable per-test summary.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Trx {
    /// Executed and failed test ids (`Namespace.Type.Method`).
    pub parsed: Parsed,
    /// One line per result (`Passed id [duration]`), with the error message and stdout under a non-passing one.
    pub summary: String,
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The text of the first `<tag>` element in `body`, decoded (CDATA kept verbatim), or `None` when absent.
fn xml_element_text(body: &str, tag: &str) -> Option<String> {
    let open = format!("<{tag}>");
    let from = body.find(&open)? + open.len();
    let len = body[from..].find(&format!("</{tag}>"))?;
    let raw = &body[from..from + len];
    let trimmed = raw.trim();
    Some(
        trimmed
            .strip_prefix("<![CDATA[")
            .and_then(|c| c.strip_suffix("]]>"))
            .map_or_else(|| xml_unescape(raw), str::to_owned),
    )
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// Map each `UnitTest` id of the TRX `TestDefinitions` to its `Namespace.Type.Method` name.
///
/// `MSTest` writes `className` assembly-qualified (`Ns.Type, Assembly, Version=...`); nested types use `+`.
fn trx_definitions(xml: &str) -> std::collections::HashMap<String, String> {
    let mut out = std::collections::HashMap::new();
    let mut rest = xml;
    while let Some(at) = rest.find("<UnitTest ") {
        rest = &rest[at + "<UnitTest ".len()..];
        let Some(tag_end) = rest.find('>') else { break };
        let tag = &rest[..tag_end];
        let close = rest.find("</UnitTest>").unwrap_or(rest.len());
        let body = &rest[tag_end..close];
        let Some(id) = xml_attr(&format!(" {tag}"), "id") else {
            continue;
        };
        let Some(method_at) = body.find("<TestMethod") else {
            continue;
        };
        let method_tag = &body[method_at
            ..body[method_at..]
                .find('>')
                .map_or(body.len(), |e| method_at + e)];
        let (Some(class), Some(name)) = (
            xml_attr(method_tag, "className"),
            xml_attr(method_tag, "name"),
        ) else {
            continue;
        };
        let class = class
            .split(',')
            .next()
            .unwrap_or_default()
            .trim()
            .replace('+', ".");
        let full = if name.starts_with(&format!("{class}.")) {
            name
        } else {
            format!("{class}.{name}")
        };
        out.insert(id, full);
    }
    out
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The tests in a TRX report (`dotnet test --logger trx`), named `Namespace.Type.Method`.
///
/// The name comes from the result's `UnitTest` definition (`TestMethod className` and `name`), so a
/// parameterized case folds into its method; a result without a definition keeps its `testName`.
/// `Passed` counts as executed, `Failed`, `Error`, `Timeout` and `Aborted` as executed and failed;
/// `NotExecuted`, `Inconclusive` and the rest did not run and are left out. A repeated name is one test,
/// failed if any case failed. The summary lists every result with its duration; a failure also shows its
/// error message and stdout, to be redacted and escaped with the rest of the transcript.
pub fn parse_trx(xml: &str) -> Trx {
    let defs = trx_definitions(xml);
    let mut trx = Trx::default();
    let mut rest = xml;
    while let Some(at) = rest.find("<UnitTestResult") {
        rest = &rest[at + "<UnitTestResult".len()..];
        let Some(tag_end) = rest.find('>') else { break };
        let tag = &rest[..tag_end];
        let (body, next) = if tag.ends_with('/') {
            ("", &rest[tag_end + 1..])
        } else {
            let after = &rest[tag_end + 1..];
            let close = after.find("</UnitTestResult>").unwrap_or(after.len());
            (&after[..close], &after[close..])
        };
        rest = next;
        let outcome = xml_attr(tag, "outcome").unwrap_or_default();
        let duration = xml_attr(tag, "duration").unwrap_or_default();
        let test_name = xml_attr(tag, "testName").unwrap_or_default();
        let id = xml_attr(tag, "testId")
            .and_then(|t| defs.get(&t).cloned())
            .unwrap_or_else(|| test_name.clone());
        let failed = matches!(outcome.as_str(), "Failed" | "Error" | "Timeout" | "Aborted");
        let _ = writeln!(trx.summary, "{outcome} {test_name} [{duration}]");
        if failed {
            for (label, tag) in [("message", "Message"), ("stdout", "StdOut")] {
                if let Some(text) = xml_element_text(body, tag).filter(|t| !t.trim().is_empty()) {
                    for line in text.trim().lines() {
                        let _ = writeln!(trx.summary, "    {label}: {line}");
                    }
                }
            }
        }
        if outcome == "Passed" || failed {
            trx.parsed.note(&id, failed);
        }
    }
    trx
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// Backslash-escape the characters a `VSTest` filter value treats as syntax (`\ ( ) & | = ! ~`).
fn vstest_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len());
    for c in value.chars() {
        if matches!(c, '\\' | '(' | ')' | '&' | '|' | '=' | '!' | '~') {
            out.push('\\');
        }
        out.push(c);
    }
    out
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The `VSTest` `--filter` expression that selects the C# tests `ids` (`Namespace.Type.Method`).
///
/// Each id matches exactly (`FullyQualifiedName=id`) or as the method of parameterized cases
/// (`FullyQualifiedName~id(`, whose display name carries the arguments); an id never matches a longer method name.
pub fn dotnet_filter(ids: &[String]) -> String {
    ids.iter()
        .map(|id| {
            let e = vstest_escape(id);
            format!("FullyQualifiedName={e}|FullyQualifiedName~{e}\\(")
        })
        .collect::<Vec<_>>()
        .join("|")
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// True when `arg` names a project or solution for `dotnet test` rather than a test id.
fn is_dotnet_project_arg(arg: &str) -> bool {
    [".csproj", ".fsproj", ".vbproj", ".sln", ".slnx", ".slnf"]
        .iter()
        .any(|ext| arg.ends_with(ext))
}

// frob:ticket 01M4DYPG8A4CEY04ARSW3H4AJR
/// The reference arguments of one `dotnet test` run, sorted by role.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct DotnetArgs {
    /// Allowed runner flags, in order, with their values (`--no-build`, `-c`, `Release`).
    pub flags: Vec<String>,
    /// Project and solution paths.
    pub projects: Vec<String>,
    /// Fully qualified test ids.
    pub ids: Vec<String>,
}

// frob:ticket 01M4DYPG8A4CEY04ARSW3H4AJR
/// Sort the reference arguments of a `dotnet test` run into allowed flags, projects and test ids.
///
/// Allowed flags are `--no-build`, `--no-restore`, and `-c`/`--configuration` followed by a build
/// configuration name (letters, digits, `_`, `-` and `.`, not starting with `-`). Any other argument starting
/// with `-` is refused so a reference cannot smuggle options.
///
/// # Errors
///
/// [`EvidenceError::BadReference`] for an unknown option or a configuration flag without a usable value.
pub fn split_dotnet_args(args: &[String]) -> Result<DotnetArgs> {
    let mut out = DotnetArgs::default();
    let mut it = args.iter();
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--no-build" | "--no-restore" => out.flags.push(arg.clone()),
            "-c" | "--configuration" => {
                let value = it.next().filter(|v| {
                    !v.is_empty()
                        && !v.starts_with('-')
                        && v.chars()
                            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-' | '.'))
                });
                let Some(value) = value else {
                    return Err(EvidenceError::BadReference(format!(
                        "`{arg}` needs a build configuration name such as `Release`"
                    )));
                };
                out.flags.push(arg.clone());
                out.flags.push(value.clone());
            }
            a if a.starts_with('-') => {
                return Err(EvidenceError::BadReference(format!(
                    "`{a}` is not an allowed option; allowed are --no-build, --no-restore and -c/--configuration <name>, then project paths and fully qualified test ids"
                )));
            }
            a if is_dotnet_project_arg(a) => out.projects.push(arg.clone()),
            _ => out.ids.push(arg.clone()),
        }
    }
    Ok(out)
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// What one `dotnet test` run needs.
#[derive(Debug, Clone, Copy)]
pub struct DotnetRun<'a> {
    /// `[evidence] allowed_tools`; `dotnet` must be listed.
    pub allowed: &'a [String],
    /// `[evidence.dotnet] path`: the executable to run; empty finds `dotnet` on `PATH`.
    pub path: &'a str,
    /// The directory `dotnet test` runs in.
    pub cwd: &'a Path,
    /// Project or solution paths (as in the reference) and fully qualified test ids; no ids runs every test.
    pub args: &'a [String],
    /// Wall-clock limit for the `dotnet` process.
    pub timeout: Duration,
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// Run `dotnet test` on the projects and test ids in `job.args` and capture the verdict and executed tests from its TRX.
///
/// Arguments ending in a project or solution extension (`.csproj`, `.sln`, ...) are passed as the thing to
/// test; every other argument is a test id and becomes part of a `--filter` ([`dotnet_filter`]). An argument
/// starting with `-` is refused unless it is an allowed flag ([`split_dotnet_args`]), so a reference cannot smuggle options. `dotnet` runs with a fresh
/// `--results-directory` whose TRX is parsed and removed; the transcript is `dotnet`'s stdout and stderr then
/// the per-test summary, left to [`build_record`] to redact and escape.
///
/// # Errors
///
/// [`EvidenceError::ToolNotAllowed`] when `dotnet` is not allowlisted, [`EvidenceError::RunnerMissing`] when
/// the executable is absent or `dotnet --version` does not exit 0 (no SDK), [`EvidenceError::BadReference`] for
/// an option-like argument, [`EvidenceError::Io`] when the results directory cannot be made,
/// [`EvidenceError::Exec`] when `dotnet` cannot start.
pub fn run_dotnet(runner: &Runner, job: &DotnetRun<'_>) -> Result<Capture> {
    let DotnetRun {
        allowed,
        path,
        cwd,
        args,
        timeout,
    } = *job;
    if !allowed.iter().any(|a| a == DOTNET_PROGRAM) {
        tracing::warn!("dotnet evidence refused: tool not allowlisted");
        return Err(EvidenceError::ToolNotAllowed {
            tool: DOTNET_PROGRAM.to_owned(),
        });
    }
    let split = split_dotnet_args(args).inspect_err(|e| {
        tracing::warn!(error = %e, "dotnet evidence refused: bad argument");
    })?;
    let missing = || {
        tracing::warn!("dotnet test run refused: dotnet SDK missing");
        EvidenceError::RunnerMissing {
            missing: DOTNET_PROGRAM.to_owned(),
            runner: DOTNET_PROGRAM.to_owned(),
        }
    };
    let program = if path.is_empty() {
        which::which(DOTNET_PROGRAM).map_err(|_| missing())?;
        Program::Tool {
            name: DOTNET_PROGRAM.to_owned(),
        }
    } else if Path::new(path).is_file() {
        Program::Hook {
            path: PathBuf::from(path),
        }
    } else {
        return Err(missing());
    };
    let probe = runner.run(&spec(
        program.clone(),
        vec!["--version".to_owned()],
        cwd,
        Duration::from_secs(60),
    ));
    if !probe.is_ok_and(|o| o.status == Outcome::Exited(0)) {
        return Err(missing());
    }
    let results = std::env::temp_dir().join(format!(
        "frob-dotnet-{}-{}",
        std::process::id(),
        JUNIT_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir_all(&results).map_err(|e| EvidenceError::io(&results, e))?;
    let DotnetArgs {
        flags,
        projects,
        ids,
    } = split;
    let mut full = vec!["test".to_owned()];
    full.extend(projects);
    full.extend(flags);
    full.extend([
        "--nologo".to_owned(),
        "--logger".to_owned(),
        format!("trx;LogFileName={TRX_FILE}"),
        "--results-directory".to_owned(),
        Shown::with_home(&results, None).to_string(),
    ]);
    if !ids.is_empty() {
        full.extend(["--filter".to_owned(), dotnet_filter(&ids)]);
    }
    let out = runner.run(&spec(program, full, cwd, timeout));
    let xml = std::fs::read_to_string(results.join(TRX_FILE)).unwrap_or_default();
    if let Err(e) = std::fs::remove_dir_all(&results) {
        tracing::warn!(path = %Shown::of(&results), error = %e, "could not remove the results directory");
    }
    let out = out?;
    let trx = parse_trx(&xml);
    let mut transcript = out.stdout;
    transcript.push_str(&out.stderr);
    if !trx.summary.is_empty() {
        transcript.push_str("\n-- trx results --\n");
        transcript.push_str(&trx.summary);
    }
    let (exit_code, measured) = exit_of(out.status);
    let passed = exit_code == Some(0) && trx.parsed.failed.is_empty();
    tracing::info!(?exit_code, passed, tests = trx.parsed.tests.len(), failed = ?trx.parsed.failed, "dotnet tests captured");
    Ok(Capture {
        exit_code,
        passed,
        measured,
        tests: trx.parsed.tests,
        failed_tests: trx.parsed.failed,
        non_passing: NonPassing::default(),
        transcript,
    })
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// True when a `dotnet test` run exited 0 yet executed no test (the filter matched nothing), which is no measurement.
pub fn dotnet_matched_no_tests(cap: &Capture) -> bool {
    cap.tests.is_empty() && cap.exit_code == Some(0)
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// The project-relative file that names the editor version a Unity project needs.
pub const UNITY_VERSION_FILE: &str = "ProjectSettings/ProjectVersion.txt";

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// The operating system family, which decides where Unity Hub installs editors.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnityHost {
    /// Windows: `C:/Program Files/Unity/Hub/Editor/<version>/Editor/Unity.exe`.
    Windows,
    /// macOS: `/Applications/Unity/Hub/Editor/<version>/Unity.app/Contents/MacOS/Unity`.
    MacOs,
    /// Linux and the rest: `~/Unity/Hub/Editor/<version>/Editor/Unity`.
    Linux,
}

impl UnityHost {
    /// The family this binary was built for.
    pub fn current() -> Self {
        if cfg!(windows) {
            Self::Windows
        } else if cfg!(target_os = "macos") {
            Self::MacOs
        } else {
            Self::Linux
        }
    }

    /// Unity Hub's default editor install directories (each holds one directory per version) for this family.
    ///
    /// `home` is the user's home directory, needed on Linux only.
    pub fn hub_roots(self, home: Option<&Path>) -> Vec<PathBuf> {
        match self {
            Self::Windows => vec![PathBuf::from("C:/Program Files/Unity/Hub/Editor")],
            Self::MacOs => vec![PathBuf::from("/Applications/Unity/Hub/Editor")],
            Self::Linux => home
                .map(|h| h.join("Unity/Hub/Editor"))
                .into_iter()
                .collect(),
        }
    }

    /// The editor executable inside one version directory of a Hub install root.
    pub fn editor_in(self, hub_root: &Path, version: &str) -> PathBuf {
        let dir = hub_root.join(version);
        match self {
            Self::Windows => dir.join("Editor/Unity.exe"),
            Self::MacOs => dir.join("Unity.app/Contents/MacOS/Unity"),
            Self::Linux => dir.join("Editor/Unity"),
        }
    }
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// The editor version `ProjectSettings/ProjectVersion.txt` requires (`m_EditorVersion: 6000.0.43f1`), or `None` when absent.
pub fn parse_unity_version(text: &str) -> Option<String> {
    text.lines().find_map(|line| {
        let v = line.trim().strip_prefix("m_EditorVersion:")?.trim();
        (!v.is_empty()).then(|| v.to_owned())
    })
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// Where to find the Unity editor for one project.
#[derive(Debug, Clone, Copy)]
pub struct UnityLookup<'a> {
    /// The Unity project directory (the one holding `ProjectSettings/`).
    pub project: &'a Path,
    /// `[evidence.unity] editor`: an explicit editor path (relative paths start at `base`); empty uses the Hub.
    pub configured: &'a str,
    /// The directory a relative `configured` path starts at (the repository root).
    pub base: &'a Path,
    /// The Hub editor install directories to search, in order ([`UnityHost::hub_roots`]).
    pub hub_roots: &'a [PathBuf],
    /// The OS family, which decides the editor's path under a Hub root.
    pub host: UnityHost,
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// The Unity editor a run will use.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnityEditor {
    /// The editor executable.
    pub path: PathBuf,
    /// The version the project requires, when its version file says (an explicit path is used whatever it says).
    pub version: Option<String>,
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// Find the Unity editor for `look.project`: `[evidence.unity] editor` when set, else the version in `ProjectVersion.txt` under the Hub roots.
///
/// An explicit editor is used whatever the version file says. Otherwise the editor must be the exact
/// version the project names; no other version is ever substituted, and nothing is guessed when the
/// version file is missing.
///
/// # Errors
///
/// [`EvidenceError::UnityEditor`] naming the required version and the `[evidence.unity] editor` key when the
/// configured path is not a file, the version file is missing or unreadable, or no Hub root holds that version.
pub fn find_unity_editor(look: &UnityLookup<'_>) -> Result<UnityEditor> {
    let version_file = look.project.join(UNITY_VERSION_FILE);
    let version = std::fs::read_to_string(&version_file)
        .ok()
        .and_then(|t| parse_unity_version(&t));
    if !look.configured.is_empty() {
        let path = look.base.join(look.configured);
        if path.is_file() {
            tracing::info!(editor = %Shown::of(&path), "unity editor taken from [evidence.unity] editor");
            return Ok(UnityEditor { path, version });
        }
        tracing::warn!(editor = %Shown::of(&path), "unity editor refused: configured path is not a file");
        return Err(EvidenceError::UnityEditor {
            problem: format!(
                "[evidence.unity] editor is `{}` but no file exists there",
                look.configured
            ),
        });
    }
    let Some(wanted) = version.clone() else {
        tracing::warn!(file = %Shown::of(&version_file), "unity editor refused: no editor version");
        return Err(EvidenceError::UnityEditor {
            problem: format!(
                "cannot tell which editor version the project needs ({UNITY_VERSION_FILE} is missing or has no m_EditorVersion) and [evidence.unity] editor is not set"
            ),
        });
    };
    let tried: Vec<PathBuf> = look
        .hub_roots
        .iter()
        .map(|root| look.host.editor_in(root, &wanted))
        .collect();
    if let Some(path) = tried.iter().find(|p| p.is_file()) {
        tracing::info!(editor = %Shown::of(path), version = %wanted, "unity editor found in the Hub");
        return Ok(UnityEditor {
            path: path.clone(),
            version,
        });
    }
    let searched = if tried.is_empty() {
        "no Unity Hub install location is known on this machine".to_owned()
    } else {
        format!(
            "looked for {}",
            tried
                .iter()
                .map(|p| format!("`{}`", Shown::of(p)))
                .collect::<Vec<_>>()
                .join(", ")
        )
    };
    tracing::warn!(version = %wanted, %searched, "unity editor refused: required version not installed");
    Err(EvidenceError::UnityEditor {
        problem: format!(
            "the project needs Unity editor {wanted} (from {UNITY_VERSION_FILE}) and it is not installed ({searched}); set [evidence.unity] editor to the executable to use another location"
        ),
    })
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// A refusal when the editor's output says it has no valid license, else `None`.
///
/// Unity prints `No valid Unity Editor license found` (and variants for an expired or unacquirable license)
/// to its log and exits without running anything; a run whose log says so measured nothing and must record
/// nothing. `version` is the required editor version for the message. The match is on those documented
/// phrases, case-insensitively, anywhere in `log`.
pub fn unity_license_refusal(version: Option<&str>, log: &str) -> Option<EvidenceError> {
    const PHRASES: [&str; 5] = [
        "no valid unity editor license",
        "no valid license",
        "failed to acquire license",
        "unable to acquire license",
        "license has expired",
    ];
    let hit = log.lines().find(|line| {
        let l = line.to_ascii_lowercase();
        PHRASES.iter().any(|p| l.contains(p))
    })?;
    tracing::warn!(line = hit.trim(), "unity editor reports no valid license");
    Some(EvidenceError::UnityLicense {
        version: version.unwrap_or("(version unknown)").to_owned(),
        detail: hit.trim().to_owned(),
    })
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// The file Unity holds open in `Temp/` while an editor has the project open.
pub const UNITY_LOCK_FILE: &str = "Temp/UnityLockfile";

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// Which Unity Test Framework platform a run uses.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnityMode {
    /// Tests run in the editor without entering play mode (the default).
    EditMode,
    /// Tests run in play mode.
    PlayMode,
}

impl UnityMode {
    /// The `-testPlatform` value and reference spelling.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EditMode => "EditMode",
            Self::PlayMode => "PlayMode",
        }
    }

    /// The mode spelled `text` (`EditMode` or `PlayMode`), `None` for anything else.
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "EditMode" => Some(Self::EditMode),
            "PlayMode" => Some(Self::PlayMode),
            _ => None,
        }
    }
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// Where one Unity run happens: which editor, in which project.
#[derive(Debug, Clone, Copy)]
pub struct UnityRun<'a> {
    /// `[evidence.unity] editor`; empty finds the Hub install of the project's version.
    pub editor: &'a str,
    /// The Unity project directory (the one holding `ProjectSettings/`).
    pub project: &'a Path,
    /// The repository root, where a relative `editor` path starts.
    pub base: &'a Path,
    /// The user's home directory, which locates the Hub on Linux.
    pub home: Option<&'a Path>,
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// What one batch-mode Unity test run needs.
#[derive(Debug, Clone, Copy)]
pub struct UnityTestRun<'a> {
    /// The editor and project.
    pub run: UnityRun<'a>,
    /// The test platform.
    pub mode: UnityMode,
    /// Assembly names (`-assemblyNames`, the `.asmdef` `name`); empty runs every assembly of the platform.
    pub assemblies: &'a [String],
    /// Fully qualified test ids (`-testFilter`); empty runs every test.
    pub ids: &'a [String],
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// The nearest ancestor directory of `asmdef` (repo-relative) under `root` that holds `ProjectSettings/`, else `root`.
pub fn unity_project_dir(root: &Path, asmdef: &str) -> PathBuf {
    let mut dir = Path::new(asmdef).parent();
    while let Some(rel) = dir {
        let candidate = root.join(rel);
        if candidate.join("ProjectSettings").is_dir() {
            return candidate;
        }
        dir = rel.parent();
    }
    root.to_path_buf()
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// The assembly name of a repo-relative `.asmdef` (its JSON `name`), the file stem when unreadable; a non-`.asmdef` id is its own name.
pub fn unity_assembly_name(root: &Path, id: &str) -> String {
    if !id.ends_with(".asmdef") {
        return id.strip_prefix("unity:").unwrap_or(id).to_owned();
    }
    let named = std::fs::read_to_string(root.join(id))
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .and_then(|v| v["name"].as_str().map(str::to_owned));
    named.unwrap_or_else(|| {
        tracing::warn!(id, "asmdef unreadable or unnamed; using its file stem");
        id.rsplit('/')
            .next()
            .and_then(|f| f.strip_suffix(".asmdef"))
            .unwrap_or(id)
            .to_owned()
    })
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// Refuse a run while another editor instance has the project open (a Unity project cannot be opened twice).
///
/// # Errors
///
/// [`EvidenceError::UnityProjectOpen`] when `Temp/UnityLockfile` exists under the project.
pub fn check_unity_unlocked(project: &Path) -> Result<()> {
    let lock = project.join(UNITY_LOCK_FILE);
    if lock.exists() {
        tracing::warn!(lock = %Shown::of(&lock), "unity project is open in another editor; refusing");
        return Err(EvidenceError::UnityProjectOpen {
            project: Shown::with_home(project, None).to_string(),
        });
    }
    Ok(())
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// The tests in an `NUnit` 3 result file (`<test-case>` elements), named `Namespace.Type.Method`.
///
/// The name is `classname` and `methodname` when present (nested `+` becomes `.`), else the `fullname` up to its
/// first `(`, so a parameterized case folds into its method. `Passed` is executed; `Failed` (any label)
/// is executed and failed; `Skipped`, `Inconclusive`, `Warning` and the rest did not pass or fail and are left out. A repeated
/// name is one test, failed if any case failed. The summary lists each result with its duration; a failure also
/// shows its message and output, to be redacted and escaped with the rest of the transcript.
pub fn parse_nunit(xml: &str) -> Trx {
    let mut trx = Trx::default();
    let mut rest = xml;
    while let Some(at) = rest.find("<test-case ") {
        rest = &rest[at + "<test-case".len()..];
        let Some(tag_end) = rest.find('>') else { break };
        let tag = &rest[..tag_end];
        let (body, next) = if tag.ends_with('/') {
            ("", &rest[tag_end + 1..])
        } else {
            let after = &rest[tag_end + 1..];
            let close = after.find("</test-case>").unwrap_or(after.len());
            (&after[..close], &after[close..])
        };
        rest = next;
        let outcome = xml_attr(tag, "result").unwrap_or_default();
        let duration = xml_attr(tag, "duration").unwrap_or_default();
        let full = xml_attr(tag, "fullname").unwrap_or_default();
        let id = match (xml_attr(tag, "classname"), xml_attr(tag, "methodname")) {
            (Some(class), Some(method)) => format!("{}.{method}", class.replace('+', ".")),
            _ => full.split('(').next().unwrap_or_default().replace('+', "."),
        };
        let failed = outcome == "Failed";
        let _ = writeln!(trx.summary, "{outcome} {full} [{duration}]");
        if failed {
            for (label, tag) in [("message", "message"), ("output", "output")] {
                if let Some(text) = xml_element_text(body, tag).filter(|t| !t.trim().is_empty()) {
                    for line in text.trim().lines() {
                        let _ = writeln!(trx.summary, "    {label}: {line}");
                    }
                }
            }
        }
        if outcome == "Passed" || failed {
            trx.parsed.note(&id, failed);
        }
    }
    trx
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// Run the Unity editor in batch mode over `job` and capture the verdict and executed tests from its `NUnit` result.
///
/// Refuses first when another editor has the project open ([`check_unity_unlocked`]) or no editor is found
/// ([`find_unity_editor`]), and after the run when the editor's log says it has no valid license
/// ([`unity_license_refusal`]). The editor runs `-batchmode -nographics -runTests -testPlatform <mode> -testResults <file>`
/// plus `-assemblyNames` and `-testFilter` (semicolon separated) when given. The XML is parsed with
/// [`parse_nunit`] and removed; the transcript is the editor's output then the per-test summary, left to
/// [`build_record`] to redact and escape. A run passes only when the editor exited 0 and no test failed.
///
/// # Errors
///
/// [`EvidenceError::UnityProjectOpen`], [`EvidenceError::UnityEditor`], [`EvidenceError::UnityLicense`], [`EvidenceError::BadReference`] for an
/// option-like assembly or id, [`EvidenceError::Io`] when the results directory cannot be made,
/// [`EvidenceError::Exec`] when the editor cannot start.
pub fn run_unity(runner: &Runner, job: &UnityTestRun<'_>, timeout: Duration) -> Result<Capture> {
    if let Some(bad) = job
        .assemblies
        .iter()
        .chain(job.ids)
        .find(|a| a.starts_with('-') || a.contains(';'))
    {
        tracing::warn!(arg = bad, "unity evidence refused: option-like argument");
        return Err(EvidenceError::BadReference(format!(
            "`{bad}` looks like an option or holds `;`; pass assembly names and fully qualified test ids only"
        )));
    }
    check_unity_unlocked(job.run.project)?;
    let hub_roots = UnityHost::current().hub_roots(job.run.home);
    let found = find_unity_editor(&UnityLookup {
        project: job.run.project,
        configured: job.run.editor,
        base: job.run.base,
        hub_roots: &hub_roots,
        host: UnityHost::current(),
    })?;
    let results = std::env::temp_dir().join(format!(
        "frob-unity-{}-{}",
        std::process::id(),
        JUNIT_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir_all(&results).map_err(|e| EvidenceError::io(&results, e))?;
    let file = results.join("frob-nunit.xml");
    let mut args: Vec<String> = [
        "-batchmode",
        "-nographics",
        "-runTests",
        "-testPlatform",
        job.mode.as_str(),
        "-testResults",
    ]
    .map(str::to_owned)
    .to_vec();
    args.push(Shown::with_home(&file, None).to_string());
    args.extend([
        "-logFile".to_owned(),
        "-".to_owned(),
        "-projectPath".to_owned(),
        Shown::with_home(job.run.project, None).to_string(),
    ]);
    if !job.assemblies.is_empty() {
        args.extend(["-assemblyNames".to_owned(), job.assemblies.join(";")]);
    }
    if !job.ids.is_empty() {
        args.extend(["-testFilter".to_owned(), job.ids.join(";")]);
    }
    tracing::info!(mode = job.mode.as_str(), assemblies = ?job.assemblies, ids = job.ids.len(), "running unity tests");
    let out = runner.run(&spec(
        Program::Hook { path: found.path },
        args,
        job.run.project,
        timeout,
    ));
    let xml = std::fs::read_to_string(&file).unwrap_or_default();
    if let Err(e) = std::fs::remove_dir_all(&results) {
        tracing::warn!(path = %Shown::of(&results), error = %e, "could not remove the results directory");
    }
    let out = out?;
    let mut transcript = out.stdout;
    transcript.push_str(&out.stderr);
    if let Some(refusal) = unity_license_refusal(found.version.as_deref(), &transcript) {
        return Err(refusal);
    }
    let nunit = parse_nunit(&xml);
    if !nunit.summary.is_empty() {
        transcript.push_str("\n-- nunit results --\n");
        transcript.push_str(&nunit.summary);
    }
    let (exit_code, measured) = exit_of(out.status);
    let passed = exit_code == Some(0) && nunit.parsed.failed.is_empty();
    tracing::info!(?exit_code, passed, tests = nunit.parsed.tests.len(), failed = ?nunit.parsed.failed, "unity tests captured");
    Ok(Capture {
        exit_code,
        passed,
        measured,
        tests: nunit.parsed.tests,
        failed_tests: nunit.parsed.failed,
        non_passing: NonPassing::default(),
        transcript,
    })
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// True when a Unity run exited 0 yet executed no test (the filter matched nothing), which is no measurement.
pub fn unity_matched_no_tests(cap: &Capture) -> bool {
    cap.tests.is_empty() && cap.exit_code == Some(0)
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// Run Unity tests for a reference `[EditMode|PlayMode] [<asmdef path>...] [<test id>...]`, refusing a run that executed no test.
///
/// The mode defaults to `EditMode`; each `.asmdef` path (repo-relative) selects its assembly and, for the first,
/// the Unity project it lives in (else the repository root); every other argument is a fully qualified test id.
fn capture_unity(ws: &Workspace, reference: &str) -> Result<Capture> {
    let mut args = split_args(reference)?;
    let mode = args
        .first()
        .and_then(|a| UnityMode::parse(a))
        .inspect(|_| {
            args.remove(0);
        })
        .unwrap_or(UnityMode::EditMode);
    let (asmdefs, ids): (Vec<String>, Vec<String>) =
        args.into_iter().partition(|a| a.ends_with(".asmdef"));
    let project = asmdefs
        .first()
        .map_or_else(|| ws.root.clone(), |a| unity_project_dir(&ws.root, a));
    let assemblies: Vec<String> = asmdefs
        .iter()
        .map(|a| unity_assembly_name(&ws.root, a))
        .collect();
    let home = std::env::var_os("HOME").map(PathBuf::from);
    let cap = run_unity(
        &ws.runner(),
        &UnityTestRun {
            run: UnityRun {
                editor: &ws.unity.editor,
                project: &project,
                base: &ws.root,
                home: home.as_deref(),
            },
            mode,
            assemblies: &assemblies,
            ids: &ids,
        },
        ws.timeout(),
    )?;
    refuse_empty(
        &cap,
        unity_matched_no_tests(&cap),
        "unity run executed no tests",
        reference,
    )?;
    Ok(cap)
}

/// Run the provider named by `provider` for `reference` and return its record.
///
/// `reference` is the nextest filter args, the pytest arguments, the command line or the file path.
///
/// # Errors
///
/// Whatever the provider returns: allowlist, spawn, I/O or store failures.
pub fn capture(
    ws: &Workspace,
    provider: Provider,
    reference: &str,
    accepts: &[usize],
) -> Result<EvidenceRecord> {
    let mut record = capture_unstamped(ws, provider, reference, accepts)?;
    // frob:ticket 01M5CW05SGKV3HDVCTTMAQT9TT
    record.head = crate::guard::head_of(ws.ledger.repo());
    Ok(record)
}

/// [`capture`] before the record is stamped with the measured commit.
fn capture_unstamped(
    ws: &Workspace,
    provider: Provider,
    reference: &str,
    accepts: &[usize],
) -> Result<EvidenceRecord> {
    tracing::info!(
        provider = provider.as_str(),
        reference,
        "capturing evidence"
    );
    let cap = match provider {
        Provider::File => {
            // frob:ticket 01M4HW9GZT9T70NGGAHAH1CKJF
            require_committed(ws, reference)?;
            return hash_file(&ws.root, reference, accepts, ws.ledger.clock().now());
        }
        Provider::Attestation => {
            return Err(EvidenceError::BadReference(
                "an attestation is made with --statement through attestation::attest, never captured from a reference".to_owned(),
            ));
        }
        Provider::Nextest => {
            let args = split_args(reference)?;
            let cap = run_nextest(
                &ws.runner(),
                &ws.root,
                &args,
                &ws.evidence.nextest_profile,
                ws.timeout(),
            )?;
            refuse_empty(
                &cap,
                matched_no_tests(&cap),
                "nextest filter matched no tests",
                reference,
            )?;
            cap
        }
        Provider::Pytest => {
            let args = split_args(reference)?;
            let mut cap = run_pytest(
                &ws.runner(),
                &ws.evidence.allowed_tools,
                &ws.root,
                &ws.tests.python,
                &args,
                ws.timeout(),
            )?;
            // frob:ticket 01M5B28YM1QJJ5PCZ7SJ5VX9W8
            cap.admit_non_passing(&ws.tests.non_passing_counts);
            refuse_empty(
                &cap,
                pytest_matched_no_tests(&cap),
                "pytest collected no tests",
                reference,
            )?;
            cap
        }
        // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
        Provider::Vitest | Provider::Jest => {
            let args = split_args(reference)?;
            let cap = run_js_tests(
                &ws.runner(),
                &JsRun {
                    provider,
                    allowed: &ws.evidence.allowed_tools,
                    node: NODE_PROGRAM,
                    root: &ws.root,
                    member: "",
                    args: &args,
                    timeout: ws.timeout(),
                },
            )?;
            refuse_empty(
                &cap,
                js_matched_no_tests(&cap),
                "JavaScript runner found no tests",
                reference,
            )?;
            cap
        }
        // frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
        Provider::Dotnet => capture_dotnet(ws, reference)?,
        // frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
        Provider::Unity => capture_unity(ws, reference)?,
        Provider::Command => return capture_command(ws, reference, accepts),
    };
    build_record(
        &ws.store,
        &ws.scrub(),
        provider,
        reference,
        &cap,
        accepts,
        ws.ledger.clock().now(),
    )
}

// frob:ticket 01M5B4R6YPM1D0A41AX7MRCHXP
/// Run an allowlisted command and record it, with the executed count its declared report field gives (if any).
fn capture_command(ws: &Workspace, reference: &str, accepts: &[usize]) -> Result<EvidenceRecord> {
    let argv = split_args(reference)?;
    let cap = run_command(
        &ws.runner(),
        &ws.evidence.allowed_tools,
        &ws.root,
        &argv,
        ws.timeout(),
    )?;
    let executed = command_executed(&ws.evidence.report_fields, &argv, &cap, reference)?;
    let mut record = build_record(
        &ws.store,
        &ws.scrub(),
        Provider::Command,
        reference,
        &cap,
        accepts,
        ws.ledger.clock().now(),
    )?;
    record.test_count = executed;
    Ok(record)
}

// frob:ticket 01M5B4R6YPM1D0A41AX7MRCHXP
/// The number at dotted `path` in the JSON a command printed: the whole stdout, else its last JSON line.
pub fn report_count(transcript: &str, path: &str) -> Option<u64> {
    let whole = serde_json::from_str::<serde_json::Value>(transcript.trim()).ok();
    let value = whole.or_else(|| {
        transcript
            .lines()
            .rev()
            .find_map(|l| serde_json::from_str::<serde_json::Value>(l.trim()).ok())
    })?;
    path.split('.')
        .try_fold(&value, |v, key| v.get(key))
        .and_then(serde_json::Value::as_u64)
}

// frob:ticket 01M5B4R6YPM1D0A41AX7MRCHXP
/// The executed-test count of a `command` run, from the tool's declared report field.
///
/// `Ok(None)` when the tool declares no field (UNMEASURED for granular evidence: the exit code alone is recorded).
/// A green run whose declared field is missing or zero is refused, since an exit code over zero executed tests is never evidence.
///
/// # Errors
///
/// [`EvidenceError::NotExecuted`] for a passing run that reported no executed test.
pub fn command_executed(
    fields: &std::collections::BTreeMap<String, String>,
    argv: &[String],
    cap: &Capture,
    reference: &str,
) -> Result<Option<u64>> {
    let Some(path) = argv.first().and_then(|t| fields.get(t)) else {
        tracing::debug!(
            reference,
            "command evidence: no report field; granular evidence unmeasured"
        );
        return Ok(None);
    };
    let count = report_count(&cap.transcript, path);
    if cap.passed && count.unwrap_or(0) == 0 {
        tracing::warn!(
            reference,
            path,
            ?count,
            "command exit 0 but report shows no executed test; refusing to record"
        );
        return Err(EvidenceError::NotExecuted {
            filter: reference.to_owned(),
            summary: format!(
                "report field `{path}` is {}",
                count.map_or_else(|| "absent".to_owned(), |c| c.to_string())
            ),
        });
    }
    Ok(count)
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// Run `dotnet test` for the project paths and test ids in `reference`, refusing a run that executed no test.
fn capture_dotnet(ws: &Workspace, reference: &str) -> Result<Capture> {
    let args = split_args(reference)?;
    let cap = run_dotnet(
        &ws.runner(),
        &DotnetRun {
            allowed: &ws.evidence.allowed_tools,
            path: &ws.dotnet.path,
            cwd: &ws.root,
            args: &args,
            timeout: ws.timeout(),
        },
    )?;
    refuse_empty(
        &cap,
        dotnet_matched_no_tests(&cap),
        "dotnet test ran no tests",
        reference,
    )?;
    Ok(cap)
}

/// The runner's own summary line: the last transcript line that mentions tests, else the last non-empty line.
pub fn summary_line(transcript: &str) -> String {
    let lines: Vec<&str> = transcript
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .collect();
    lines
        .iter()
        .rev()
        .find(|l| l.to_ascii_lowercase().contains("test"))
        .or(lines.last())
        .map_or_else(|| "no output".to_owned(), |l| (*l).to_owned())
}

// frob:ticket 01M3DG64CNAZ8K50HQ046VKHER
/// Refuse to record a run that executed no test: the filter matched none (`empty`), or it exited 0 with every test skipped.
///
/// A bound id needs at least one executed and passed test, so a green exit code over zero executed tests is never evidence.
fn refuse_empty(cap: &Capture, empty: bool, what: &str, reference: &str) -> Result<()> {
    if empty {
        tracing::warn!(filter = reference, "{what}; refusing to record");
        return Err(EvidenceError::NoTestsMatched {
            filter: reference.to_owned(),
        });
    }
    if cap.passed && cap.tests.is_empty() {
        let summary = summary_line(&cap.transcript);
        tracing::warn!(
            filter = reference,
            summary,
            "{what}: exit 0 but no test executed; refusing to record"
        );
        return Err(EvidenceError::NotExecuted {
            filter: reference.to_owned(),
            summary,
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M3DG64CNAZ8K50HQ046VKHER
    fn control_cap(tests: &[&str], transcript: &str) -> Capture {
        Capture {
            exit_code: Some(0),
            passed: true,
            measured: true,
            tests: tests.iter().map(|t| (*t).to_owned()).collect(),
            failed_tests: Vec::new(),
            non_passing: NonPassing::default(),
            transcript: transcript.to_owned(),
        }
    }

    // frob:ticket 01M5B4R6YPM1D0A41AX7MRCHXP
    #[test]
    fn a_command_with_a_report_field_must_have_executed_tests() {
        // frob:tests crates/frob-evidence/src/provider.rs::command_executed
        // frob:tests crates/frob-evidence/src/provider.rs::report_count
        let fields =
            std::collections::BTreeMap::from([("jest".to_owned(), "run.total".to_owned())]);
        let argv = vec!["jest".to_owned()];
        let green = control_cap(&[], r#"{"run":{"total":3}}"#);
        assert_eq!(
            command_executed(&fields, &argv, &green, "jest").expect("ok"),
            Some(3)
        );
        let zero = control_cap(
            &[],
            r#"noise
{"run":{"total":0}}"#,
        );
        assert!(matches!(
            command_executed(&fields, &argv, &zero, "jest"),
            Err(EvidenceError::NotExecuted { .. })
        ));
        let absent = control_cap(&[], "no json here");
        assert!(matches!(
            command_executed(&fields, &argv, &absent, "jest"),
            Err(EvidenceError::NotExecuted { .. })
        ));
    }

    // frob:ticket 01M5B4R6YPM1D0A41AX7MRCHXP
    #[test]
    fn a_command_without_a_report_field_is_unmeasured_for_granular_evidence() {
        // frob:tests crates/frob-evidence/src/provider.rs::command_executed
        let fields = std::collections::BTreeMap::new();
        let cap = control_cap(&[], "ok");
        assert_eq!(
            command_executed(&fields, &["git".to_owned()], &cap, "git status").expect("ok"),
            None
        );
    }

    // frob:ticket 01M3DG64CNAZ8K50HQ046VKHER
    #[test]
    fn a_matching_run_is_recorded() {
        // frob:tests crates/frob-evidence/src/provider.rs::refuse_empty
        let cap = control_cap(&["t::a"], "Tests 1 passed (1)");
        assert!(refuse_empty(&cap, false, "x", "-t a").is_ok());
    }

    // frob:ticket 01M3DG64CNAZ8K50HQ046VKHER
    #[test]
    fn a_skipped_only_green_run_is_not_executed() {
        // frob:tests crates/frob-evidence/src/provider.rs::refuse_empty
        let cap = control_cap(&[], "noise\n Tests  1 skipped (1)\n");
        let err = refuse_empty(&cap, false, "x", "-t a").unwrap_err();
        let EvidenceError::NotExecuted { summary, .. } = err else {
            panic!("expected NotExecuted");
        };
        assert_eq!(summary, "Tests  1 skipped (1)".trim());
    }

    // frob:ticket 01M3DG64CNAZ8K50HQ046VKHER
    #[test]
    fn a_filter_matching_nothing_is_refused() {
        // frob:tests crates/frob-evidence/src/provider.rs::refuse_empty
        let cap = control_cap(&[], "");
        assert!(matches!(
            refuse_empty(&cap, true, "x", "-t a"),
            Err(EvidenceError::NoTestsMatched { .. })
        ));
        assert!(matches!(
            refuse_empty(&cap, false, "x", "-t a"),
            Err(EvidenceError::NotExecuted { .. })
        ));
    }

    #[test]
    fn split_args_honours_quotes() {
        let got = split_args(r#"-p frob-ledger -E 'test(=a) | test(=b)' "x y""#).unwrap();
        assert_eq!(
            got,
            ["-p", "frob-ledger", "-E", "test(=a) | test(=b)", "x y"]
        );
        assert!(split_args("a 'b").is_err());
        assert!(split_args("   ").unwrap().is_empty());
        assert_eq!(split_args("a '' b").unwrap(), ["a", "", "b"]);
    }

    // frob:ticket 01M40P6CWYKN4V9HEBRXR3342F
    #[test]
    fn split_args_follows_posix_escapes_and_expands_nothing() {
        assert_eq!(split_args(r"a\ b c").unwrap(), ["a b", "c"]);
        assert_eq!(split_args(r#""a\"b" 'c\d'"#).unwrap(), ["a\"b", "c\\d"]);
        assert_eq!(split_args(r#""a\qb""#).unwrap(), ["a\\qb"]);
        assert_eq!(split_args(r#"x"y z"w"#).unwrap(), ["xy zw"]);
        assert_eq!(split_args("a\\\nb").unwrap(), ["ab"]);
        assert_eq!(
            split_args("$HOME | ; * #x").unwrap(),
            ["$HOME", "|", ";", "*", "#x"]
        );
        for bad in ["a 'b", "a \"b", "a\\", "\"a\\"] {
            let e = split_args(bad).unwrap_err().to_string();
            assert!(
                e.contains("unterminated quote") || e.contains("trailing backslash"),
                "{bad}: {e}"
            );
        }
    }

    #[test]
    fn zero_matched_tests_is_told_apart_from_a_failed_build() {
        let cap = |code, text: &str| Capture {
            exit_code: Some(code),
            passed: false,
            measured: true,
            tests: Vec::new(),
            failed_tests: Vec::new(),
            non_passing: NonPassing::default(),
            transcript: text.to_owned(),
        };
        assert!(matched_no_tests(&cap(4, "")));
        assert!(matched_no_tests(&cap(1, "error: no tests to run")));
        assert!(!matched_no_tests(&cap(
            101,
            "error[E0425]: cannot find value"
        )));
        let mut ran = cap(4, "");
        ran.tests.push("t".to_owned());
        assert!(!matched_no_tests(&ran));
    }

    #[test]
    fn libtest_json_events_become_names() {
        let out = concat!(
            "{\"type\":\"suite\",\"event\":\"started\",\"test_count\":2}\n",
            "{\"type\":\"test\",\"event\":\"started\",\"name\":\"c::bin/c$tests::a\"}\n",
            "{\"type\":\"test\",\"event\":\"ok\",\"name\":\"c::bin/c$tests::a\"}\n",
            "{\"type\":\"test\",\"event\":\"failed\",\"name\":\"c::bin/c$tests::b\"}\n",
            "not json\n",
        );
        let parsed = parse_libtest_json(out);
        assert_eq!(parsed.tests, ["tests::a", "tests::b"]);
        assert_eq!(parsed.failed, ["tests::b"]);
    }

    #[test]
    fn human_lines_become_names() {
        let out = "        PASS [   0.004s] frob-tests tests::one\n        FAIL [   0.004s] frob-tests tests::two\n     Summary [   0.01s] 2 tests run: 1 passed, 1 failed\n";
        let parsed = parse_human(out);
        assert_eq!(parsed.tests, ["tests::one", "tests::two"]);
        assert_eq!(parsed.failed, ["tests::two"]);
        let timeout =
            "     TIMEOUT [  60.0s] pkg tests::slow\n        FAIL [   0.1s] pkg tests::slow\n";
        assert_eq!(parse_human(timeout).failed, ["tests::slow"]);
        assert_eq!(parse_human("nothing here"), Parsed::default());
    }

    #[test]
    fn junit_cases_become_node_ids() {
        let xml = concat!(
            "<testsuites><testsuite>",
            "<testcase classname=\"tests.test_m\" name=\"test_a\" file=\"tests/test_m.py\" line=\"1\" time=\"0.0\" />",
            "<testcase classname=\"tests.test_m\" name=\"test_p[a&lt;b]\" file=\"tests/test_m.py\" />",
            "<testcase classname=\"tests.test_m\" name=\"test_f\" file=\"tests/test_m.py\"><failure message=\"x &lt;y&gt;\">E &lt;boom&gt;</failure></testcase>",
            "<testcase classname=\"tests.test_m\" name=\"test_s\" file=\"tests/test_m.py\"><skipped type=\"pytest.skip\" message=\"m\">t</skipped></testcase>",
            "<testcase classname=\"tests.test_m.TestC\" name=\"test_e\" file=\"tests/test_m.py\"><error message=\"e\">t</error></testcase>",
            "<testcase classname=\"\" name=\"tests.test_bad\"><error message=\"collect\">t</error></testcase>",
            "</testsuite></testsuites>",
        );
        let parsed = parse_junit(xml);
        assert_eq!(
            parsed.tests,
            [
                "tests/test_m.py::test_a",
                "tests/test_m.py::test_p[a<b]",
                "tests/test_m.py::test_f",
                "tests/test_m.py::TestC::test_e",
                "tests.test_bad"
            ]
        );
        assert_eq!(
            parsed.failed,
            [
                "tests/test_m.py::test_f",
                "tests/test_m.py::TestC::test_e",
                "tests.test_bad"
            ]
        );
        assert_eq!(parse_junit("not xml"), Parsed::default());
    }

    #[test]
    // frob:ticket 01M1T07NW78MGWRF7HZQMPSRAV
    fn skip_xfail_and_xpass_never_satisfy_evidence_and_are_counted_apart() {
        // frob:tests crates/frob-evidence/src/provider.rs::parse_junit
        let xml = concat!(
            "<testsuite>",
            "<testcase classname=\"t.m\" name=\"a\" file=\"t/m.py\" />",
            "<testcase classname=\"t.m\" name=\"s\" file=\"t/m.py\"><skipped type=\"pytest.skip\" message=\"m\">x</skipped></testcase>",
            "<testcase classname=\"t.m\" name=\"x\" file=\"t/m.py\"><skipped type=\"pytest.xfail\" message=\"m\">x</skipped></testcase>",
            "<testcase classname=\"t.m\" name=\"p\" file=\"t/m.py\" />",
            "</testsuite>",
        );
        let mut parsed = parse_junit(xml);
        assert_eq!(parsed.tests, ["t/m.py::a", "t/m.py::p"]);
        assert_eq!(parsed.non_passing.skipped, ["t/m.py::s"]);
        assert_eq!(parsed.non_passing.xfailed, ["t/m.py::x"]);
        demote_xpass(&mut parsed, "XPASS t/m.py::p - why\n", "");
        assert_eq!(parsed.tests, ["t/m.py::a"]);
        assert_eq!(parsed.non_passing.xpassed, ["t/m.py::p"]);
        assert_eq!(parsed.non_passing.count(), 3);
    }

    #[test]
    // frob:ticket 01M4CTTYH76JQASEJJQC02YD0F
    fn a_module_that_failed_to_collect_keeps_its_file_as_the_node_id() {
        // frob:tests crates/frob-evidence/src/provider.rs::parse_junit_under
        let xml = concat!(
            "<testsuite>",
            "<testcase classname=\"\" name=\"tests.test_mul\" file=\"tests/test_mul.py\"><error message=\"collection failure\">ModuleNotFoundError</error></testcase>",
            "<testcase classname=\"tests.test_ok\" name=\"test_a\" file=\"tests/test_ok.py\" />",
            "</testsuite>",
        );
        let parsed = parse_junit_under(xml, "py");
        assert_eq!(parsed.failed, ["py/tests/test_mul.py"]);
        assert_eq!(
            parsed.tests,
            ["py/tests/test_mul.py", "py/tests/test_ok.py::test_a"]
        );
        assert_eq!(parse_junit(xml).failed, ["tests/test_mul.py"]);
    }

    #[test]
    // frob:ticket 01M44J072TEWFTCB1AFVTN9C8B
    fn junit_windows_file_separators_give_portable_node_ids() {
        let xml = concat!(
            "<testsuite>",
            "<testcase classname=\"tests.test_probe.TestK\" name=\"test_bad\" file=\"tests\\test_probe.py\"><failure message=\"x\">t</failure></testcase>",
            "<testcase classname=\"tests.test_probe\" name=\"test_ok\" file=\"tests\\test_probe.py\" />",
            "</testsuite>",
        );
        let parsed = parse_junit(xml);
        assert_eq!(
            parsed.tests,
            [
                "tests/test_probe.py::TestK::test_bad",
                "tests/test_probe.py::test_ok"
            ]
        );
        assert_eq!(parsed.failed, ["tests/test_probe.py::TestK::test_bad"]);
    }

    #[test]
    // frob:ticket 01M4GKBEBGBTA03VFB90SDR858
    fn a_rootdir_below_the_repository_prefixes_the_node_ids() {
        let root = tempfile::tempdir().unwrap();
        let sub = root.path().join("py/sub");
        std::fs::create_dir_all(&sub).unwrap();
        let header = format!(
            "============ test session starts ============\nrootdir: {}, configfile: pytest.ini\n",
            Shown::of(&sub)
        );
        let prefix = rootdir_prefix(&header, root.path());
        assert_eq!(prefix, "py/sub");
        let xml = "<testcase classname=\"tests.test_m.TestC\" name=\"test_e\" file=\"tests/test_m.py\" />";
        assert_eq!(
            parse_junit_under(xml, &prefix).tests,
            ["py/sub/tests/test_m.py::TestC::test_e"]
        );
        assert_eq!(rootdir_prefix(&header, &sub), "", "rootdir is the root");
        assert_eq!(rootdir_prefix("no header\n", root.path()), "");
    }

    #[test]
    fn xml_entities_decode() {
        assert_eq!(
            xml_unescape("a&lt;b&amp;&#10;&#x41;&bogus;"),
            "a<b&\nA&bogus;"
        );
    }

    #[test]
    fn pytest_needs_its_allowlist_entry_and_no_collection_is_not_a_failure() {
        let runner = Runner::new(gob_exec::Limits { jobs: 1 });
        let err = run_pytest(
            &runner,
            &["cargo".to_owned()],
            Path::new("."),
            "",
            &[],
            Duration::from_secs(5),
        )
        .unwrap_err();
        assert!(matches!(err, EvidenceError::ToolNotAllowed { .. }), "{err}");
        let cap = |code| Capture {
            exit_code: Some(code),
            passed: false,
            measured: true,
            tests: Vec::new(),
            failed_tests: Vec::new(),
            non_passing: NonPassing::default(),
            transcript: String::new(),
        };
        assert!(pytest_matched_no_tests(&cap(5)));
        assert!(!pytest_matched_no_tests(&cap(1)));
    }
    // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
    #[test]
    fn a_js_report_names_tests_as_the_units_they_came_from() {
        // frob:tests crates/frob-evidence/src/provider.rs::parse_js_json
        let json = r#"{"testResults":[
          {"name":"/w/apps/a/src/x.test.ts","status":"failed","assertionResults":[
            {"ancestorTitles":["user api"],"title":"fetches","status":"passed"},
            {"ancestorTitles":["user api"],"title":"fetches","status":"failed"},
            {"ancestorTitles":[],"title":"is skipped","status":"skipped"},
            {"ancestorTitles":[],"title":"todo","status":"todo"}]},
          {"name":"/w/apps/a/src/broken.test.ts","status":"failed","assertionResults":[]}]}"#;
        let got = parse_js_json(json, Path::new("/w/apps/a"), "apps/a");
        assert_eq!(
            got.tests,
            [
                "apps/a/src/x.test.ts::suite$user_api::test$fetches",
                "apps/a/src/x.test.ts::suite$user_api::test$fetches[dup2]",
                "apps/a/src/broken.test.ts"
            ]
        );
        assert_eq!(
            got.failed,
            [
                "apps/a/src/x.test.ts::suite$user_api::test$fetches[dup2]",
                "apps/a/src/broken.test.ts"
            ]
        );
        assert!(
            parse_js_json("not json", Path::new("/w"), "")
                .tests
                .is_empty()
        );
        assert_eq!(
            got.non_passing.skipped,
            [
                "apps/a/src/x.test.ts::test$is_skipped",
                "apps/a/src/x.test.ts::test$todo"
            ]
        );
    }

    // frob:ticket 01M5B28YM1QJJ5PCZ7SJ5VX9W8
    #[test]
    fn non_passing_kinds_satisfy_evidence_only_when_opted_in() {
        // frob:tests crates/frob-evidence/src/provider.rs::Capture.admit_non_passing
        let mut cap = Capture {
            exit_code: Some(0),
            passed: true,
            measured: true,
            tests: vec!["a".to_owned()],
            failed_tests: Vec::new(),
            non_passing: NonPassing {
                skipped: vec!["s".to_owned()],
                xfailed: vec!["x".to_owned()],
                xpassed: vec!["p".to_owned()],
            },
            transcript: String::new(),
        };
        cap.admit_non_passing(&[]);
        assert_eq!(cap.tests, ["a"], "default admits nothing");
        cap.admit_non_passing(&["xfailed".to_owned(), "bogus".to_owned()]);
        assert_eq!(cap.tests, ["a", "x"]);
        assert_eq!(cap.non_passing.count(), 3, "counts are kept apart");
        let c = cap.non_passing.counts();
        assert_eq!((c.skipped, c.xfailed, c.xpassed), (1, 1, 1));
        assert!(!c.is_zero());
        assert!(crate::record::NonPassingCounts::default().is_zero());
    }

    // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
    #[test]
    fn js_runs_are_refused_with_a_named_reason_never_skipped() {
        // frob:tests crates/frob-evidence/src/provider.rs::run_js_tests
        let runner = Runner::new(gob_exec::Limits { jobs: 1 });
        let dir = tempfile::tempdir().unwrap();
        let allowed = ["vitest".to_owned()];
        let run = |provider, allowed: &[String], node: &str, root: &Path| {
            run_js_tests(
                &runner,
                &JsRun {
                    provider,
                    allowed,
                    node,
                    root,
                    member: "",
                    args: &[],
                    timeout: Duration::from_secs(5),
                },
            )
        };
        let err = run(Provider::Vitest, &[], NODE_PROGRAM, dir.path()).unwrap_err();
        assert!(matches!(err, EvidenceError::ToolNotAllowed { .. }), "{err}");
        let err = run(
            Provider::Vitest,
            &allowed,
            "frob-no-such-node-xyz",
            dir.path(),
        )
        .unwrap_err();
        assert!(
            matches!(&err, EvidenceError::RunnerMissing { missing, runner } if missing == "frob-no-such-node-xyz" && runner == "vitest"),
            "{err}"
        );
        assert!(
            err.to_string().contains("E-EVIDENCE-RUNNER-MISSING"),
            "{err}"
        );
        // The runner lookup finds a bin in an ancestor's node_modules and names a missing one as None.
        assert_eq!(
            find_js_runner(dir.path(), dir.path(), "frob-no-such-runner-xyz"),
            None
        );
        let bin = dir.path().join("node_modules/.bin");
        std::fs::create_dir_all(&bin).unwrap();
        std::fs::write(bin.join("vitest"), "").unwrap();
        let deep = dir.path().join("apps/a");
        assert_eq!(
            find_js_runner(dir.path(), &deep, "vitest"),
            Some(bin.join("vitest"))
        );
        let err = run(Provider::Command, &allowed, "sh", dir.path()).unwrap_err();
        assert!(matches!(err, EvidenceError::BadReference(_)), "{err}");
    }

    // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
    #[cfg(unix)]
    #[test]
    fn a_js_runner_in_the_members_node_modules_is_run_and_its_report_parsed() {
        // frob:tests crates/frob-evidence/src/provider.rs::run_js_tests
        use std::os::unix::fs::PermissionsExt;
        let dir = tempfile::tempdir().unwrap();
        let bin = dir.path().join("apps/a/node_modules/.bin");
        std::fs::create_dir_all(&bin).unwrap();
        let script = bin.join("jest");
        std::fs::write(
            &script,
            "#!/bin/sh\nfor a in \"$@\"; do case \"$a\" in --outputFile=*) out=\"${a#--outputFile=}\";; esac; done\nprintf '{\"testResults\":[{\"name\":\"x.test.ts\",\"status\":\"passed\",\"assertionResults\":[{\"ancestorTitles\":[],\"title\":\"adds\",\"status\":\"passed\"}]}]}' > \"$out\"\necho \"ran $*\"\n",
        )
        .unwrap();
        std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).unwrap();
        let runner = Runner::new(gob_exec::Limits { jobs: 1 });
        let allowed = ["jest".to_owned()];
        let cap = run_js_tests(
            &runner,
            &JsRun {
                provider: Provider::Jest,
                allowed: &allowed,
                node: "sh",
                root: dir.path(),
                member: "apps/a",
                args: &["x.test.ts".to_owned()],
                timeout: Duration::from_secs(30),
            },
        )
        .unwrap();
        assert!(cap.passed, "{cap:?}");
        assert_eq!(cap.tests, ["apps/a/x.test.ts::test$adds"]);
        assert!(cap.transcript.contains("--ci --json"), "{}", cap.transcript);
        assert!(cap.transcript.contains("x.test.ts"), "{}", cap.transcript);
        assert!(!js_matched_no_tests(&cap));
    }

    // frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
    #[test]
    fn pytest_runs_through_the_project_interpreter_when_there_is_one() {
        // frob:tests crates/frob-evidence/src/provider.rs::pytest_runner
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path();
        assert_eq!(pytest_runner(root, "").label(), "pytest");
        std::fs::create_dir_all(root.join(".venv/bin")).expect("venv");
        std::fs::write(root.join(".venv/bin/python"), "").expect("python");
        let venv = pytest_runner(root, "");
        assert_eq!(venv.label(), ".venv/bin/python -m pytest");
        assert_eq!(venv.prefix, ["-m", "pytest"]);
        assert!(matches!(venv.program, Program::Hook { .. }));
        let named = pytest_runner(root, "python3.12");
        assert_eq!(named.label(), "python3.12 -m pytest");
        assert!(matches!(named.program, Program::Tool { .. }));
        let pathed = pytest_runner(root, "tools/py");
        assert_eq!(pathed.label(), "tools/py -m pytest");
    }

    // frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
    #[test]
    fn collection_errors_are_named_by_file_path_never_module() {
        // frob:tests crates/frob-evidence/src/provider.rs::collection_error_files
        let out = "_____ ERROR collecting tests/test_m.py _____\nImportError\n=== short test summary info ===\nERROR tests/test_m.py - ImportError: no module\nERROR tests/sub/test_n.py::TestK - boom\n";
        assert_eq!(
            collection_error_files(out),
            ["tests/test_m.py", "tests/sub/test_n.py"]
        );
        assert!(collection_error_files("1 passed").is_empty());
    }
}

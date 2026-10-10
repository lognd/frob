//! Evidence providers: `nextest`, `pytest`, `vitest`, `jest`, `dotnet`, `command` and `file`.
//!
//! Each provider turns one measurement into a [`Capture`] (or a hashed file),
//! and [`build_record`] turns that into an [`EvidenceRecord`]: the transcript is
//! redacted with `gob_log::redact`, hashed with blake3 and stored inline or in
//! the blob store. Processes only ever run through `gob-exec` with a bounded
//! timeout.

use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use frob_ledger::model::Stamp;
use gob_exec::{Outcome, Program, Runner, Spec};

use crate::attestation::escape_non_ascii;
use crate::error::{EvidenceError, Result};
use crate::record::{EvidenceRecord, Provider, Status, digest_hex};
use crate::scrub::PathScrub;
use crate::store::{BlobStore, Stored};
use crate::workspace::Workspace;

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
    /// The redacted transcript.
    pub transcript: String,
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

// frob:ticket 01M4M0ABX9R9J96C1CF1PSGNZP
/// `"default"` when no profile is configured and the inherited `NEXTEST_PROFILE` names one that
/// the nextest config around `cwd` does not define (an outer `cargo nextest run --profile ci`
/// exports it to every test process, and a nested crate need not have that profile); else `None`.
fn inherited_profile_fallback(
    cwd: &Path,
    configured: &str,
    inherited: Option<&str>,
) -> Option<String> {
    if !configured.is_empty() {
        return None;
    }
    let inherited = inherited?.trim();
    if inherited.is_empty() || inherited == "default" || inherited.starts_with("default-") {
        return None;
    }
    let defined = cwd.ancestors().find_map(|dir| {
        let text = std::fs::read_to_string(dir.join(".config").join("nextest.toml")).ok()?;
        let doc: toml::Table = text.parse().ok()?;
        Some(
            doc.get("profile")
                .and_then(toml::Value::as_table)
                .is_some_and(|profiles| profiles.contains_key(inherited)),
        )
    });
    (!defined.unwrap_or(false)).then(|| "default".to_owned())
}

/// Run `cargo nextest run [--profile <profile>] <filter_args>` in `cwd` and capture the verdict and executed tests.
///
/// An empty `profile` passes no `--profile`.
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
    let mut args = vec!["nextest".to_owned(), "run".to_owned()];
    let inherited = inherited_profile_fallback(
        cwd,
        profile,
        std::env::var("NEXTEST_PROFILE").ok().as_deref(),
    );
    let profile = inherited.as_deref().unwrap_or(profile);
    if !profile.is_empty() {
        args.extend(["--profile".to_owned(), profile.to_owned()]);
    }
    args.extend(filter_args.iter().cloned());
    let mut json_args = args.clone();
    json_args.extend(["--message-format".to_owned(), "libtest-json".to_owned()]);
    let mut json_spec = spec(Program::Cargo, json_args, cwd, timeout);
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
        out = runner.run(&spec(Program::Cargo, args, cwd, timeout))?;
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
        .map(|r| r.to_string_lossy().into_owned())
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
        let label = path
            .strip_prefix(root)
            .map_or_else(|_| path.display().to_string(), |r| r.display().to_string());
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
        format!("--junitxml={}", junit.display()),
    ]);
    full.extend(args.iter().cloned());
    let out = runner.run(&spec(launcher.program, full, cwd, timeout));
    let xml = std::fs::read_to_string(&junit).unwrap_or_default();
    if junit.exists()
        && let Err(e) = std::fs::remove_file(&junit)
    {
        tracing::warn!(path = %junit.display(), error = %e, "could not remove the junit file");
    }
    let out = out?;
    let prefix = rootdir_prefix(&out.stdout, cwd);
    let seen = parse_junit_under(&xml, &prefix);
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
        "pytest captured"
    );
    Ok(Capture {
        exit_code,
        passed,
        measured,
        tests: seen.tests,
        failed_tests: seen.failed,
        transcript,
    })
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
        .map_or_else(|_| file.to_owned(), |r| r.to_string_lossy().into_owned());
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
/// `skipped`, `todo` and `disabled` do not; a file that failed to load (no assertions, failed status) is
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
            if !matches!(status, "passed" | "failed") {
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
            parsed.note(&id, status == "failed");
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
            format!("--outputFile.json={}", report.display()),
        ]
    } else {
        vec![
            "--ci".to_owned(),
            "--json".to_owned(),
            format!("--outputFile={}", report.display()),
        ]
    };
    full.extend(args.iter().cloned());
    let out = runner.run(&spec(Program::Hook { path }, full, &cwd, timeout));
    let json = std::fs::read_to_string(&report).unwrap_or_default();
    if report.exists()
        && let Err(e) = std::fs::remove_file(&report)
    {
        tracing::warn!(path = %report.display(), error = %e, "could not remove the JSON report");
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
        tracing::debug!(tool, path = %path.display(), "command evidence: running frob tool allowed by default");
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
        tests: capture.tests.clone(),
        failed_tests: capture.failed_tests.clone(),
        inline,
        size: redacted.len() as u64,
        attestation: None,
    })
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
        failed_tests: Vec::new(),
        inline: None,
        size: bytes.len() as u64,
        attestation: None,
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
/// starting with `-` is refused, so a reference cannot smuggle options. `dotnet` runs with a fresh
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
    if let Some(bad) = args.iter().find(|a| a.starts_with('-')) {
        tracing::warn!(arg = bad, "dotnet evidence refused: option-like argument");
        return Err(EvidenceError::BadReference(format!(
            "`{bad}` looks like an option; pass project paths and fully qualified test ids only"
        )));
    }
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
    let (projects, ids): (Vec<String>, Vec<String>) =
        args.iter().cloned().partition(|a| is_dotnet_project_arg(a));
    let mut full = vec!["test".to_owned()];
    full.extend(projects);
    full.extend([
        "--nologo".to_owned(),
        "--logger".to_owned(),
        format!("trx;LogFileName={TRX_FILE}"),
        "--results-directory".to_owned(),
        results.display().to_string(),
    ]);
    if !ids.is_empty() {
        full.extend(["--filter".to_owned(), dotnet_filter(&ids)]);
    }
    let out = runner.run(&spec(program, full, cwd, timeout));
    let xml = std::fs::read_to_string(results.join(TRX_FILE)).unwrap_or_default();
    if let Err(e) = std::fs::remove_dir_all(&results) {
        tracing::warn!(path = %results.display(), error = %e, "could not remove the results directory");
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
            tracing::info!(editor = %path.display(), "unity editor taken from [evidence.unity] editor");
            return Ok(UnityEditor { path, version });
        }
        tracing::warn!(editor = %path.display(), "unity editor refused: configured path is not a file");
        return Err(EvidenceError::UnityEditor {
            problem: format!(
                "[evidence.unity] editor is `{}` but no file exists there",
                look.configured
            ),
        });
    }
    let Some(wanted) = version.clone() else {
        tracing::warn!(file = %version_file.display(), "unity editor refused: no editor version");
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
        tracing::info!(editor = %path.display(), version = %wanted, "unity editor found in the Hub");
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
                .map(|p| format!("`{}`", p.display()))
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
    tracing::info!(
        provider = provider.as_str(),
        reference,
        "capturing evidence"
    );
    let cap = match provider {
        Provider::File => {
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
                matched_no_tests(&cap),
                "nextest filter matched no tests",
                reference,
            )?;
            cap
        }
        Provider::Pytest => {
            let args = split_args(reference)?;
            let cap = run_pytest(
                &ws.runner(),
                &ws.evidence.allowed_tools,
                &ws.root,
                &ws.tests.python,
                &args,
                ws.timeout(),
            )?;
            refuse_empty(
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
                js_matched_no_tests(&cap),
                "JavaScript runner found no tests",
                reference,
            )?;
            cap
        }
        // frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
        Provider::Dotnet => capture_dotnet(ws, reference)?,
        Provider::Command => {
            let argv = split_args(reference)?;
            run_command(
                &ws.runner(),
                &ws.evidence.allowed_tools,
                &ws.root,
                &argv,
                ws.timeout(),
            )?
        }
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
        dotnet_matched_no_tests(&cap),
        "dotnet test ran no tests",
        reference,
    )?;
    Ok(cap)
}

/// Refuse to record a run that matched no test (`empty`): there is nothing to measure.
fn refuse_empty(empty: bool, what: &str, reference: &str) -> Result<()> {
    if empty {
        tracing::warn!(filter = reference, "{what}; refusing to record");
        return Err(EvidenceError::NoTestsMatched {
            filter: reference.to_owned(),
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M4M0ABX9R9J96C1CF1PSGNZP
    #[test]
    fn an_inherited_profile_the_project_lacks_falls_back_to_default() {
        let dir = tempfile::tempdir().unwrap();
        let cfg = dir.path().join(".config");
        std::fs::create_dir_all(&cfg).unwrap();
        std::fs::write(cfg.join("nextest.toml"), "[profile.ci]\nretries = 0\n").unwrap();
        let fallback =
            |cwd: &Path, conf: &str, env: Option<&str>| inherited_profile_fallback(cwd, conf, env);
        assert_eq!(fallback(dir.path(), "", Some("ci")), None, "defined here");
        assert_eq!(
            fallback(dir.path(), "", Some("nope")).as_deref(),
            Some("default")
        );
        assert_eq!(fallback(dir.path(), "x", Some("nope")), None, "configured");
        assert_eq!(fallback(dir.path(), "", Some("default")), None);
        assert_eq!(fallback(dir.path(), "", None), None);
        let bare = tempfile::tempdir().unwrap();
        assert_eq!(
            fallback(bare.path(), "", Some("ci")).as_deref(),
            Some("default")
        );
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
            sub.display()
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

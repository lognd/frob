//! Evidence providers: `nextest`, `pytest`, `command` and `file`.
//!
//! Each provider turns one measurement into a [`Capture`] (or a hashed file),
//! and [`build_record`] turns that into an [`EvidenceRecord`]: the transcript is
//! redacted with `gob_log::redact`, hashed with blake3 and stored inline or in
//! the blob store. Processes only ever run through `gob-exec` with a bounded
//! timeout.

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
fn node_id(tag: &str) -> String {
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
/// Each `testcase` is named by its node id; one with a `failure` or `error` child failed, one
/// with a `skipped` child did not execute and is left out.
pub fn parse_junit(xml: &str) -> Parsed {
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
        parsed.note(&node_id(tag), failed);
    }
    parsed
}

static JUNIT_SEQ: AtomicU64 = AtomicU64::new(0);

/// Run `pytest -o junit_family=xunit1 --junitxml=<tmp> <args>` in `cwd` and capture the verdict and executed tests.
///
/// `pytest` must be in `allowed` (`[evidence] allowed_tools`); the junit file is read, then removed. The transcript is
/// pytest's stdout then stderr, left to [`build_record`] to redact and escape.
///
/// # Errors
///
/// [`EvidenceError::ToolNotAllowed`] when `pytest` is not allowlisted, [`EvidenceError::Exec`] when it cannot start.
pub fn run_pytest(
    runner: &Runner,
    allowed: &[String],
    cwd: &Path,
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
    let mut full = vec![
        "-o".to_owned(),
        "junit_family=xunit1".to_owned(),
        format!("--junitxml={}", junit.display()),
    ];
    full.extend(args.iter().cloned());
    let program = Program::Tool {
        name: "pytest".to_owned(),
    };
    let out = runner.run(&spec(program, full, cwd, timeout));
    let xml = std::fs::read_to_string(&junit).unwrap_or_default();
    if junit.exists()
        && let Err(e) = std::fs::remove_file(&junit)
    {
        tracing::warn!(path = %junit.display(), error = %e, "could not remove the junit file");
    }
    let out = out?;
    let seen = parse_junit(&xml);
    let mut transcript = out.stdout;
    transcript.push_str(&out.stderr);
    let (exit_code, measured) = exit_of(out.status);
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
        captured_at: Stamp::now(),
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
pub fn hash_file(root: &Path, path: &str, accepts: &[usize]) -> Result<EvidenceRecord> {
    let full = root.join(path);
    let bytes = std::fs::read(&full).map_err(|e| EvidenceError::io(&full, e))?;
    tracing::info!(path, bytes = bytes.len(), "file evidence hashed");
    Ok(EvidenceRecord {
        provider: Provider::File,
        reference: path.to_owned(),
        digest: digest_hex(&bytes),
        uri: None,
        status: Status::Measured,
        captured_at: Stamp::now(),
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
    match provider {
        Provider::File => hash_file(&ws.root, reference, accepts),
        Provider::Attestation => Err(EvidenceError::BadReference(
            "an attestation is made with --statement through attestation::attest, never captured from a reference".to_owned(),
        )),
        Provider::Nextest => {
            let args = split_args(reference)?;
            let cap = run_nextest(
                &ws.runner(),
                &ws.root,
                &args,
                &ws.evidence.nextest_profile,
                ws.timeout(),
            )?;
            if matched_no_tests(&cap) {
                tracing::warn!(
                    filter = reference,
                    "nextest filter matched no tests; refusing to record"
                );
                return Err(EvidenceError::NoTestsMatched {
                    filter: reference.to_owned(),
                });
            }
            build_record(&ws.store, &ws.scrub(), provider, reference, &cap, accepts)
        }
        Provider::Pytest => {
            let args = split_args(reference)?;
            let cap = run_pytest(
                &ws.runner(),
                &ws.evidence.allowed_tools,
                &ws.root,
                &args,
                ws.timeout(),
            )?;
            if pytest_matched_no_tests(&cap) {
                tracing::warn!(
                    filter = reference,
                    "pytest collected no tests; refusing to record"
                );
                return Err(EvidenceError::NoTestsMatched {
                    filter: reference.to_owned(),
                });
            }
            build_record(&ws.store, &ws.scrub(), provider, reference, &cap, accepts)
        }
        Provider::Command => {
            let argv = split_args(reference)?;
            let cap = run_command(
                &ws.runner(),
                &ws.evidence.allowed_tools,
                &ws.root,
                &argv,
                ws.timeout(),
            )?;
            build_record(&ws.store, &ws.scrub(), provider, reference, &cap, accepts)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
}

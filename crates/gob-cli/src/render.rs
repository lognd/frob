//! Rendering and the single place that writes to stdout and stderr.

use std::fmt::Write as _;
use std::io::Write as _;

use frob_present::{Capabilities, EnvSnapshot, Palette, Role, StreamFacts};
use gob_diagnostics::{
    ColorChoice, Envelope, EnvelopeError, ExitCode, FindingRecord, MemorySources, Report,
    TextOptions, TextOrigin, render_text,
};
use gob_rules::Registry;
use serde::Serialize;
use serde_json::Value;

use crate::command::Erased;
use crate::error::{CliError, FindingsFailure};

/// The finished result of one invocation, not yet written anywhere.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Execution {
    pub exit: i32,
    pub stdout: String,
    pub stderr: String,
    /// Set by `serve`: run the MCP loop in this directory instead of writing.
    pub serve_cwd: Option<std::path::PathBuf>,
}

impl Execution {
    /// Stdout only, exit 0.
    pub(crate) fn out(stdout: String) -> Self {
        Self {
            exit: ExitCode::Ok.code(),
            stdout,
            stderr: String::new(),
            serve_cwd: None,
        }
    }

    /// Hand control to the MCP loop rooted at `cwd`.
    pub(crate) fn serving(cwd: std::path::PathBuf) -> Self {
        Self {
            serve_cwd: Some(cwd),
            ..Self::out(String::new())
        }
    }
}

/// Which standard stream a styled rendering is destined for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Stream {
    Stdout,
    Stderr,
}

/// Colour for the gob-cli text views: paints only on a colour-capable terminal stream.
#[derive(Debug, Clone)]
struct Style {
    palette: Palette,
}

impl Style {
    /// No colour: every paint is the identity.
    fn plain() -> Self {
        Self {
            palette: Palette::plain(),
        }
    }

    /// Full colour, regardless of the environment (tests).
    #[cfg(test)]
    fn colored() -> Self {
        Self {
            palette: Palette::colored(),
        }
    }

    /// Decide from an environment and terminal facts whether `stream` gets colour (pure).
    fn detect(env: &EnvSnapshot, stdout_tty: bool, stderr_tty: bool, stream: Stream) -> Self {
        let caps = Capabilities::detect(
            env,
            StreamFacts {
                stdout_tty,
                stderr_tty,
                width: None,
            },
        );
        let color = match stream {
            Stream::Stdout => caps.stdout.color,
            Stream::Stderr => caps.stderr.color,
        };
        tracing::debug!(?stream, color, "gob-cli style detected");
        if color {
            Self {
                palette: Palette::colored(),
            }
        } else {
            Self::plain()
        }
    }

    /// Detect from the live process environment and terminals.
    fn for_stream(stream: Stream) -> Self {
        use std::io::IsTerminal as _;
        Self::detect(
            &EnvSnapshot::from_process(),
            std::io::stdout().is_terminal(),
            std::io::stderr().is_terminal(),
            stream,
        )
    }

    /// Wrap `text` in the style of `role` (plain text without colour).
    fn paint(&self, role: Role, text: &str) -> String {
        self.palette.paint(role, text)
    }
}

/// The envelope plus the verb name and `already` marker (cli.md section 2).
#[derive(Serialize)]
struct Wire<'a> {
    verb: Option<&'a str>,
    already: bool,
    #[serde(flatten)]
    envelope: Envelope<Value>,
}

fn to_json(wire: &Wire<'_>) -> String {
    let mut out = serde_json::to_string(wire).unwrap_or_else(|e| {
        unreachable!("string-keyed derived data serializes: {e}");
    });
    out.push('\n');
    out
}

/// Append `line` to `text` as its own final line, adding a newline first when `text` lacks one.
pub(crate) fn append_line(text: &mut String, line: &str) {
    if !text.is_empty() && !text.ends_with('\n') {
        text.push('\n');
    }
    text.push_str(line);
    text.push('\n');
}

/// Render a successful verb.
pub(crate) fn success(
    verb: &str,
    erased: Erased,
    json: bool,
    quiet: bool,
    color: ColorChoice,
) -> Execution {
    let registry = Registry::global();
    let sources = MemorySources::new();
    if json {
        let records = erased
            .findings
            .iter()
            .map(|f| FindingRecord::from_finding(f, &sources, registry))
            .collect();
        let mut envelope = Envelope::success(erased.data, records);
        envelope.warnings = erased.warnings;
        let wire = Wire {
            verb: Some(verb),
            already: erased.already,
            envelope,
        };
        return Execution::out(to_json(&wire));
    }
    if quiet {
        tracing::debug!(verb, "quiet: text output suppressed");
        return Execution::out(String::new());
    }
    let mut out = if let Some(rows) = &erased.rendered {
        tracing::debug!(verb, rows = rows.len(), "text view: pre-rendered rows, raw");
        rows.iter().fold(String::new(), |mut acc, row| {
            acc.push_str(row);
            acc.push('\n');
            acc
        })
    } else {
        let style = Style::for_stream(Stream::Stdout);
        let mut head = format!(
            "{verb}: {}{}\n",
            style.paint(Role::Ok, "ok"),
            if erased.already { " (already)" } else { "" }
        );
        value_lines_styled(&erased.data, 1, &mut head, &style);
        head
    };
    for w in &erased.warnings {
        let _ = writeln!(out, "warning: {w}");
    }
    if !erased.findings.is_empty() {
        out.push('\n');
        let report = Report {
            findings: &erased.findings,
            sources: &sources,
        };
        out.push_str(&render_text(
            &report,
            &TextOptions {
                color,
                snippets: false,
            },
        ));
    }
    Execution::out(out)
}

/// Render a failure: JSON envelope on stdout, plain text on stderr.
pub(crate) fn failure(verb: Option<&str>, err: &CliError, json: bool) -> Execution {
    let style = if json {
        Style::plain()
    } else {
        Style::for_stream(Stream::Stderr)
    };
    failure_styled(verb, err, json, &style)
}

/// [`failure`] with an explicit style, so the layout is testable without a terminal.
fn failure_styled(verb: Option<&str>, err: &CliError, json: bool, style: &Style) -> Execution {
    let exit = err.exit_code().code();
    if let (CliError::Gate { data, warnings, .. }, true) = (err, json) {
        let mut envelope = Envelope::success(data.clone(), Vec::new());
        envelope.warnings.clone_from(warnings);
        let wire = Wire {
            verb,
            already: false,
            envelope,
        };
        return Execution {
            exit,
            stdout: to_json(&wire),
            stderr: String::new(),
            serve_cwd: None,
        };
    }
    let body = envelope_error(err);
    if json {
        let mut envelope = Envelope::failure(body);
        if let CliError::Findings(f) = err {
            let FindingsFailure {
                data,
                findings,
                warnings,
                ..
            } = &**f;
            tracing::debug!(
                findings = findings.len(),
                "failure envelope carries findings"
            );
            envelope.data = Some(data.clone());
            envelope.findings.clone_from(findings);
            envelope.warnings.clone_from(warnings);
        }
        let wire = Wire {
            verb,
            already: false,
            envelope,
        };
        return Execution {
            exit,
            stdout: to_json(&wire),
            stderr: String::new(),
            serve_cwd: None,
        };
    }
    let mut text = format!(
        "{}: {}\n",
        style.paint(Role::Error, &format!("error[{}]", body.code)),
        body.message
    );
    if let CliError::Findings(f) = err {
        text.push_str(&f.detail);
        text.push('\n');
    }
    if let Some(remedy) = &body.remedy {
        let _ = writeln!(text, "  remedy: {remedy}");
    }
    if body.requires_human {
        text.push_str(
            "  requires_human: a person must do this; an agent must stop and tell the user\n",
        );
    }
    Execution {
        exit,
        stdout: String::new(),
        stderr: text,
        serve_cwd: None,
    }
}

/// The envelope error body for any [`CliError`].
pub(crate) fn envelope_error(err: &CliError) -> EnvelopeError {
    match err {
        CliError::Refusal(r) => EnvelopeError::from(r),
        CliError::Usage(m) => plain("E-USAGE", m.clone()),
        CliError::Negative(m) | CliError::Gate { message: m, .. } => plain("E-NEGATIVE", m.clone()),
        CliError::Findings(f) => plain("E-NEGATIVE", f.summary.clone()),
        CliError::Internal(e) => plain("E-INTERNAL", e.to_string()),
    }
}

fn plain(code: &str, message: String) -> EnvelopeError {
    EnvelopeError {
        code: code.to_owned(),
        message,
        // frob:ticket 01M4S1YMTPRCGNHN585C78QET8
        message_origin: TextOrigin::Host,
        remedy: None,
        command: None,
        retryable: false,
        requires_human: false,
    }
}

/// Indented `key: value` lines for a JSON value (the text view of `data`).
#[cfg(test)]
pub(crate) fn value_lines(value: &Value, depth: usize, out: &mut String) {
    value_lines_styled(value, depth, out, &Style::plain());
}

/// [`value_lines`] with keys dimmed and status words coloured by `style`.
fn value_lines_styled(value: &Value, depth: usize, out: &mut String, style: &Style) {
    let pad = "  ".repeat(depth);
    match value {
        Value::Object(map) => {
            for (k, v) in map {
                if is_scalar(v) {
                    let _ = writeln!(
                        out,
                        "{pad}{}: {}",
                        style.paint(Role::Dim, k),
                        status_scalar(v, style)
                    );
                } else {
                    let _ = writeln!(out, "{pad}{}:", style.paint(Role::Dim, k));
                    value_lines_styled(v, depth + 1, out, style);
                }
            }
        }
        Value::Array(items) => {
            for v in items {
                if is_scalar(v) {
                    let _ = writeln!(out, "{pad}- {}", status_scalar(v, style));
                } else {
                    let _ = writeln!(out, "{pad}-");
                    value_lines_styled(v, depth + 1, out, style);
                }
            }
        }
        other => {
            let _ = writeln!(out, "{pad}{}", status_scalar(other, style));
        }
    }
}

fn is_scalar(v: &Value) -> bool {
    !matches!(v, Value::Object(_) | Value::Array(_))
}

/// A scalar as text, coloured when it is a bare status word.
fn status_scalar(v: &Value, style: &Style) -> String {
    let text = scalar(v);
    let role = match text.as_str() {
        "ok" | "clean" | "passed" | "done" | "closed" | "landed" | "approved" => Some(Role::Ok),
        "error" | "failed" | "denied" | "blocked" | "refused" => Some(Role::Error),
        "warning" | "stale" | "skipped" | "snoozed" => Some(Role::Warn),
        _ => None,
    };
    role.map_or(text.clone(), |r| style.paint(r, &text))
}

fn scalar(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Null => "none".to_owned(),
        other => other.to_string(),
    }
}

/// The one function that writes to the process's stdout and stderr.
///
/// Broken pipes and other write failures are logged, never panics: the exit
/// code is the contract, not the bytes.
pub(crate) fn emit(exec: &Execution) {
    let mut stdout = std::io::stdout().lock();
    let mut stderr = std::io::stderr().lock();
    if let Err(e) = stdout
        .write_all(exec.stdout.as_bytes())
        .and_then(|()| stdout.flush())
    {
        tracing::warn!(error = %e, "writing stdout failed");
    }
    if let Err(e) = stderr
        .write_all(exec.stderr.as_bytes())
        .and_then(|()| stderr.flush())
    {
        tracing::warn!(error = %e, "writing stderr failed");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 13J001Y
    #[test]
    fn a_colour_terminal_styles_the_error_code_and_plain_is_byte_identical() {
        let err = CliError::Negative("nope".to_owned());
        let plain = failure_styled(Some("v"), &err, false, &Style::plain());
        assert_eq!(plain.stderr, "error[E-NEGATIVE]: nope\n");
        let colour = failure_styled(Some("v"), &err, false, &Style::colored());
        assert!(colour.stderr.contains("\x1b["), "{:?}", colour.stderr);
        assert!(colour.stderr.contains("error[E-NEGATIVE]"));
        assert_eq!(colour.exit, plain.exit);
        assert_eq!(colour.exit, 1);
    }

    // frob:ticket 13J001Y
    #[test]
    fn style_detection_honours_tty_no_color_and_dumb() {
        let env = |p: &[(&str, &str)]| EnvSnapshot::from_pairs(p.iter().copied());
        let on = |e: &EnvSnapshot, so, se, s| Style::detect(e, so, se, s).paint(Role::Ok, "x");
        let tty = env(&[("TERM", "xterm")]);
        assert!(on(&tty, false, true, Stream::Stderr).contains('\x1b'));
        assert!(!on(&tty, true, false, Stream::Stderr).contains('\x1b'));
        assert!(on(&tty, true, false, Stream::Stdout).contains('\x1b'));
        assert_eq!(on(&tty, false, false, Stream::Stdout), "x");
        let nc = env(&[("TERM", "xterm"), ("NO_COLOR", "1")]);
        assert_eq!(on(&nc, true, true, Stream::Stderr), "x");
        assert_eq!(
            on(&env(&[("TERM", "dumb")]), true, true, Stream::Stdout),
            "x"
        );
    }

    // frob:ticket 13J001Y
    #[test]
    fn value_lines_colours_keys_and_status_only_with_a_style() {
        let v = serde_json::json!({"state": "closed", "n": 1});
        let mut plain = String::new();
        value_lines(&v, 1, &mut plain);
        assert_eq!(plain, "  n: 1\n  state: closed\n");
        let mut col = String::new();
        value_lines_styled(&v, 1, &mut col, &Style::colored());
        assert!(col.contains('\x1b'));
        assert!(col.contains("closed"));
    }

    // frob:ticket 01M41B2P3B5KVG5FJ5B0X2ANR8
    #[test]
    fn rendered_rows_print_raw_in_text_and_stay_out_of_json() {
        let erased = || Erased {
            data: serde_json::json!({"k": 1}),
            findings: Vec::new(),
            warnings: Vec::new(),
            already: false,
            rendered: Some(vec!["a  b".to_owned(), "c".to_owned()]),
        };
        let text = success("v", erased(), false, false, ColorChoice::Never);
        assert_eq!(text.stdout, "a  b\nc\n");
        let json = success("v", erased(), true, false, ColorChoice::Never);
        let v: Value = serde_json::from_str(&json.stdout).unwrap();
        assert_eq!(v["data"], serde_json::json!({"k": 1}));
    }

    // frob:ticket 01M3ZX87VKDKC0N65NH77EBEJP
    #[test]
    fn append_line_ends_the_text_with_the_line() {
        let mut s = "a".to_owned();
        append_line(&mut s, "next: x");
        assert_eq!(s, "a\nnext: x\n");
        let mut e = String::new();
        append_line(&mut e, "next: y");
        assert_eq!(e, "next: y\n");
    }

    // frob:ticket 01M3Z713YNM5666B7YFEHPFVKD
    #[test]
    fn a_gate_failure_keeps_its_data_in_json_and_exits_one() {
        let err = CliError::Gate {
            message: "1 error".to_owned(),
            data: serde_json::json!({"answer": 42}),
            warnings: vec!["w".to_owned()],
        };
        let exec = failure(Some("check"), &err, true);
        assert_eq!(exec.exit, 1);
        let v: Value = serde_json::from_str(&exec.stdout).unwrap();
        assert_eq!(v["ok"], true);
        assert_eq!(v["data"]["answer"], 42);
        assert_eq!(v["warnings"][0], "w");
        let text = failure(Some("check"), &err, false);
        assert_eq!(text.exit, 1);
        assert!(text.stderr.contains("1 error"));
    }

    // frob:ticket 01M4FCZ19XSPWE1EDABY6GKQPS
    #[test]
    fn a_findings_failure_carries_structured_findings_in_json() {
        let sources = MemorySources::new();
        let finding = gob_rules::Finding::new(
            "TICK001".parse().unwrap(),
            gob_rules::Severity::Error,
            None,
            "bad",
            "a.rs",
        );
        let record = FindingRecord::from_finding(&finding, &sources, Registry::global());
        let err = CliError::Findings(Box::new(FindingsFailure {
            summary: "1 error(s)".to_owned(),
            detail: "TICK001 bad".to_owned(),
            data: serde_json::json!({"n": 1}),
            findings: vec![record],
            warnings: Vec::new(),
        }));
        let exec = failure(Some("check"), &err, true);
        assert_eq!(exec.exit, 1);
        let v: Value = serde_json::from_str(&exec.stdout).unwrap();
        assert_eq!(v["ok"], false);
        assert_eq!(v["findings"].as_array().unwrap().len(), 1);
        assert_eq!(v["findings"][0]["rule"], "TICK001");
        assert_eq!(v["error"]["message"], "1 error(s)");
        assert_eq!(v["data"]["n"], 1);
        let text = failure(Some("check"), &err, false);
        assert!(text.stderr.contains("TICK001 bad"));
    }
}

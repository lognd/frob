//! Rendering and the single place that writes to stdout and stderr.

use std::fmt::Write as _;
use std::io::Write as _;

use gob_diagnostics::{
    ColorChoice, Envelope, EnvelopeError, ExitCode, FindingRecord, MemorySources, Report,
    TextOptions, render_text,
};
use gob_rules::Registry;
use serde::Serialize;
use serde_json::Value;

use crate::command::Erased;
use crate::error::CliError;

/// The finished result of one invocation, not yet written anywhere.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Execution {
    pub exit: i32,
    pub stdout: String,
    pub stderr: String,
}

impl Execution {
    /// Stdout only, exit 0.
    pub(crate) fn out(stdout: String) -> Self {
        Self {
            exit: ExitCode::Ok.code(),
            stdout,
            stderr: String::new(),
        }
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
        let mut head = format!(
            "{verb}: ok{}\n",
            if erased.already { " (already)" } else { "" }
        );
        value_lines(&erased.data, 1, &mut head);
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
        };
    }
    let body = envelope_error(err);
    if json {
        let mut envelope = Envelope::failure(body);
        if let CliError::Findings {
            data,
            findings,
            warnings,
            ..
        } = err
        {
            tracing::debug!(findings = findings.len(), "failure envelope carries findings");
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
        };
    }
    let mut text = format!("error[{}]: {}\n", body.code, body.message);
    if let CliError::Findings { detail, .. } = err {
        text.push_str(detail);
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
    }
}

/// The envelope error body for any [`CliError`].
pub(crate) fn envelope_error(err: &CliError) -> EnvelopeError {
    match err {
        CliError::Refusal(r) => EnvelopeError::from(r),
        CliError::Usage(m) => plain("E-USAGE", m.clone()),
        CliError::Negative(m) | CliError::Gate { message: m, .. } => plain("E-NEGATIVE", m.clone()),
        CliError::Findings { summary, .. } => plain("E-NEGATIVE", summary.clone()),
        CliError::Internal(e) => plain("E-INTERNAL", e.to_string()),
    }
}

fn plain(code: &str, message: String) -> EnvelopeError {
    EnvelopeError {
        code: code.to_owned(),
        message,
        remedy: None,
        retryable: false,
        requires_human: false,
    }
}

/// Indented `key: value` lines for a JSON value (the text view of `data`).
pub(crate) fn value_lines(value: &Value, depth: usize, out: &mut String) {
    let pad = "  ".repeat(depth);
    match value {
        Value::Object(map) => {
            for (k, v) in map {
                if is_scalar(v) {
                    let _ = writeln!(out, "{pad}{k}: {}", scalar(v));
                } else {
                    let _ = writeln!(out, "{pad}{k}:");
                    value_lines(v, depth + 1, out);
                }
            }
        }
        Value::Array(items) => {
            for v in items {
                if is_scalar(v) {
                    let _ = writeln!(out, "{pad}- {}", scalar(v));
                } else {
                    let _ = writeln!(out, "{pad}-");
                    value_lines(v, depth + 1, out);
                }
            }
        }
        other => {
            let _ = writeln!(out, "{pad}{}", scalar(other));
        }
    }
}

fn is_scalar(v: &Value) -> bool {
    !matches!(v, Value::Object(_) | Value::Array(_))
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
        let err = CliError::Findings {
            summary: "1 error(s)".to_owned(),
            detail: "TICK001 bad".to_owned(),
            data: serde_json::json!({"n": 1}),
            findings: vec![record],
            warnings: Vec::new(),
        };
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

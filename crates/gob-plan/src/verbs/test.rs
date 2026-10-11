//! `rule test`: run every example of every rule in a file and say pass or fail per example.

use std::fmt::Write as _;

use super::{Diag, diagnostics, parse_clean};
use crate::examples::Mark;
use crate::examples::run_example;
use crate::grl::ast::ExpectKind;

/// The result of one example.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct ExampleLine {
    /// The rule id.
    pub rule: String,
    /// `fire`, `clean`, `unresolved`, `notapplicable` or `known-gap`.
    pub expect: String,
    /// The example's name, when it has one.
    pub name: Option<String>,
    /// `ok`, `fail` (GRL016) or `error` (the example could not run).
    pub status: String,
    /// What the run reported when it passed, or what went wrong.
    pub detail: String,
    /// The expected-versus-actual diff of a failure; empty otherwise.
    pub diff: String,
}

impl ExampleLine {
    /// The line the text view prints, such as `NOPE001  fire   ok (1 finding on line 1)`.
    pub fn text(&self) -> String {
        let mut s = format!(
            "{}  {:<6} {}",
            self.rule,
            self.expect,
            if self.status == "ok" {
                "ok".to_owned()
            } else {
                self.status.to_uppercase()
            }
        );
        if !self.detail.is_empty() {
            let _ = write!(s, " ({})", self.detail);
        }
        s
    }
}

/// The examples of one file.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct FileTest {
    /// The file path as given.
    pub path: String,
    /// Compile diagnostics; when any is an error no example ran.
    pub diagnostics: Vec<Diag>,
    /// One entry per example, in source order.
    pub examples: Vec<ExampleLine>,
}

impl FileTest {
    /// Whether every example passed and the file compiled.
    pub fn passed(&self) -> bool {
        !self.diagnostics.iter().any(|d| d.severity == "error")
            && self.examples.iter().all(|e| e.status == "ok")
    }
}

fn expect_word(kind: ExpectKind) -> &'static str {
    match kind {
        ExpectKind::Fire => "fire",
        ExpectKind::Clean => "clean",
        ExpectKind::Unresolved => "unresolved",
        ExpectKind::NotApplicable => "notapplicable",
        ExpectKind::KnownGap => "known-gap",
    }
}

fn summary(found: &[crate::examples::Actual], kind: ExpectKind) -> String {
    let wanted = |m: &Mark| match kind {
        ExpectKind::Unresolved => matches!(m, Mark::Unresolved),
        _ => matches!(m, Mark::Finding(_)),
    };
    let lines: Vec<String> = found
        .iter()
        .filter(|a| wanted(&a.mark))
        .map(|a| a.line.to_string())
        .collect();
    if lines.is_empty() {
        return String::new();
    }
    let noun = if matches!(kind, ExpectKind::Unresolved) {
        "unresolved"
    } else {
        "finding"
    };
    let plural = if matches!(kind, ExpectKind::Unresolved) || lines.len() == 1 {
        ""
    } else {
        "s"
    };
    let at = if lines.len() == 1 { "line" } else { "lines" };
    format!(
        "{} {noun}{plural} on {at} {}",
        lines.len(),
        lines.join(", ")
    )
}

/// Run the examples of one rule file. A file that does not compile runs nothing.
pub fn test_file(path: &str, source: &str) -> FileTest {
    let (diags, has_error) = diagnostics(path, source);
    let mut out = FileTest {
        path: path.to_owned(),
        diagnostics: diags,
        examples: Vec::new(),
    };
    if has_error {
        return out;
    }
    let Some(file) = parse_clean(path, source) else {
        return out;
    };
    for rule in &file.rules {
        for example in &rule.examples {
            let mut line = ExampleLine {
                rule: rule.id.text.clone(),
                expect: expect_word(example.expect.kind).to_owned(),
                name: example.name.as_ref().map(|n| n.value.clone()),
                status: "ok".to_owned(),
                detail: String::new(),
                diff: String::new(),
            };
            match run_example(rule, example) {
                Ok(r) if r.passed => line.detail = summary(&r.found, example.expect.kind),
                Ok(r) => {
                    "fail".clone_into(&mut line.status);
                    line.detail = r.message;
                    line.diff = r.diff;
                }
                Err(e) => {
                    "error".clone_into(&mut line.status);
                    line.detail = e.to_string();
                }
            }
            tracing::debug!(rule = %line.rule, status = %line.status, "ran example");
            out.examples.push(line);
        }
    }
    out
}

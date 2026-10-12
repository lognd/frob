//! `cargo --message-format=json` reader for rustc and clippy diagnostics.
//!
//! Pure: [`parse_cargo_json`] turns cargo's line-delimited stdout into
//! [`RawFinding`]s. The lint name (`unused_variables`, `clippy::too_many_arguments`)
//! becomes `tool_id`; the clippy group and the diagnostic level ride along in
//! [`RawMeta`] so `classify` can pick the frob id and severity.

use std::collections::BTreeSet;

use serde::Deserialize;

use crate::tool_parse::{ParseError, RawFinding, RawMeta, RawRange};

const FORMAT: &str = "cargo json diagnostics";

#[derive(Deserialize)]
struct Line {
    reason: String,
    message: Option<Diagnostic>,
}

#[derive(Deserialize)]
struct Diagnostic {
    message: String,
    code: Option<Code>,
    level: String,
    #[serde(default)]
    spans: Vec<Span>,
    #[serde(default)]
    children: Vec<Child>,
}

#[derive(Deserialize)]
struct Code {
    code: String,
}

#[derive(Deserialize)]
struct Span {
    file_name: String,
    byte_start: u32,
    byte_end: u32,
    #[serde(default)]
    is_primary: bool,
}

#[derive(Deserialize)]
struct Child {
    message: String,
}

/// `correctness` for a clippy lint that is deny-by-default.
///
/// The JSON never names the lint group, but every clippy correctness lint
/// carries the note "`#[deny(clippy::NAME)]` on by default" and no other
/// clippy group is deny-by-default.
fn clippy_group(code: &str, children: &[Child]) -> Option<String> {
    let marker = format!("#[deny({code})]");
    children
        .iter()
        .any(|c| c.message.contains(&marker))
        .then(|| "correctness".to_owned())
}

/// Parse cargo's stdout; non-diagnostic lines (artifacts, build scripts, summaries) are skipped.
///
/// # Errors
///
/// [`ParseError`] when a line is not JSON.
pub(crate) fn parse_cargo_json(stdout: &str) -> Result<Vec<RawFinding>, ParseError> {
    let mut out = Vec::new();
    // The same diagnostic repeats for each target (lib and lib test); one finding per site.
    let mut seen = BTreeSet::new();
    for text in stdout.lines().map(str::trim).filter(|l| !l.is_empty()) {
        let line: Line = serde_json::from_str(text).map_err(|source| ParseError::Json {
            format: FORMAT,
            source,
        })?;
        if line.reason != "compiler-message" {
            continue;
        }
        let Some(d) = line.message else { continue };
        if d.level != "warning" && d.level != "error" {
            continue;
        }
        let tool_id = match &d.code {
            Some(c) => c.code.clone(),
            // A summary ("aborting due to", "N warnings emitted") is not a finding;
            // any other code-less error is a build failure that must not read as a pass.
            None if d.level == "error" && !is_summary(&d.message) => "rustc".to_owned(),
            None => continue,
        };
        let span = d
            .spans
            .iter()
            .find(|s| s.is_primary)
            .or_else(|| d.spans.first());
        let (path, range) = span.map_or((String::new(), RawRange::None), |s| {
            (
                s.file_name.clone(),
                RawRange::Bytes {
                    start: s.byte_start,
                    end: s.byte_end,
                },
            )
        });
        if !seen.insert((
            tool_id.clone(),
            path.clone(),
            span.map(|s| (s.byte_start, s.byte_end)),
            d.message.clone(),
        )) {
            tracing::debug!(%tool_id, %path, "duplicate cargo diagnostic from another target; dropped");
            continue;
        }
        let group = clippy_group(&tool_id, &d.children);
        out.push(RawFinding {
            path,
            range,
            tool_id,
            message: d.message,
            suppressed: None,
            meta: RawMeta {
                group,
                level: Some(d.level),
            },
        });
    }
    tracing::debug!(count = out.len(), "cargo diagnostics parsed");
    Ok(out)
}

fn is_summary(message: &str) -> bool {
    message.starts_with("aborting due to")
        || message.starts_with("could not compile")
        || message.contains("warning emitted")
        || message.contains("warnings emitted")
}

#[cfg(test)]
mod tests {
    use super::*;

    const CLIPPY: &str = include_str!("../tests/fixtures/cargo-clippy.jsonl");

    // frob:tests crates/gob-check/src/cargo_json.rs::parse_cargo_json
    #[test]
    fn diagnostics_parse_with_byte_spans_groups_and_dedup() {
        let found = parse_cargo_json(CLIPPY).expect("parse");
        let got: Vec<_> = found
            .iter()
            .map(|f| {
                (
                    f.tool_id.as_str(),
                    f.meta.group.as_deref(),
                    f.meta.level.as_deref(),
                )
            })
            .collect();
        assert_eq!(
            got,
            [
                ("unused_variables", None, Some("warning")),
                ("clippy::too_many_arguments", None, Some("error")),
                (
                    "clippy::absurd_extreme_comparisons",
                    Some("correctness"),
                    Some("error")
                ),
                ("clippy::needless_return", None, Some("error")),
                ("rustc", None, Some("error")),
            ],
            "artifacts, notes and summaries are skipped and the repeated target is merged"
        );
        assert_eq!(found[0].path, "crates/a/src/lib.rs");
        assert_eq!(found[0].range, RawRange::Bytes { start: 41, end: 42 });
    }

    // frob:tests crates/gob-check/src/cargo_json.rs::parse_cargo_json
    #[test]
    fn a_line_that_is_not_json_is_an_error() {
        assert!(parse_cargo_json("{\"reason\":\"compiler-message\"}\nnope").is_err());
        assert!(parse_cargo_json("").expect("empty").is_empty());
    }
}

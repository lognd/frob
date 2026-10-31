//! The `crunk check` report renderers: Markdown, the v2 JSON report and the contrast table.
//!
//! All three read one run. The finding rows are the `FindingRecord`s of the sibling document, so
//! a report never disagrees with `--json`; counts come from [`gob_diagnostics::Summary`]. The
//! contrast table measures every declared role pair in every mode (WCAG 2.x ratio against the
//! role's floor), whether or not CONTRAST001 flagged it.

// frob:ticket 01M4MD9FEH1F337CTWPZ03B67Y

use std::fmt::Write as _;

use gob_diagnostics::Summary;
use serde_json::{Value, json};

use crate::CrunkRun;

/// The version of the machine report printed by `--report json`.
pub const REPORT_VERSION: u32 = 2;

/// The finding rows of a sibling `document`, empty when it has none.
fn rows(document: &Value) -> &[Value] {
    document["findings"].as_array().map_or(&[], Vec::as_slice)
}

/// The `{errors, unresolved, required}` counts of the run through [`Summary`].
fn counts(run: &CrunkRun) -> Value {
    let s = Summary::of(&run.report.findings, &[]);
    json!({"errors": s.errors, "unresolved": s.unresolved, "required": s.required})
}

/// The v2 JSON report: its own `version`, the counts and the finding rows of `document`.
pub fn report_v2(run: &CrunkRun, document: &Value) -> Value {
    tracing::debug!(findings = rows(document).len(), "report v2 built");
    json!({
        "version": REPORT_VERSION,
        "counts": counts(run),
        "findings": rows(document),
    })
}

/// The Markdown report: a heading, the counts, then one bullet per finding grouped by file.
pub fn markdown(run: &CrunkRun, document: &Value) -> String {
    let c = counts(run);
    let mut out = String::from("# crunk check report\n\n");
    let _ = writeln!(
        out,
        "{} error(s), {} unresolved ({} required).\n",
        c["errors"], c["unresolved"], c["required"]
    );
    let mut by_file = std::collections::BTreeMap::<String, Vec<&Value>>::new();
    for f in rows(document) {
        let file = f["file"].as_str().unwrap_or("(no file)").to_owned();
        by_file.entry(file).or_default().push(f);
    }
    if by_file.is_empty() {
        out.push_str("No findings.\n");
    }
    for (file, findings) in by_file {
        let _ = writeln!(out, "## `{file}`\n");
        for f in findings {
            let line = f["line"]
                .as_u64()
                .map_or(String::new(), |l| format!(":{l}"));
            let _ = writeln!(
                out,
                "- `{}` {}{} {}",
                f["rule"].as_str().unwrap_or("?"),
                f["severity"].as_str().unwrap_or("?"),
                line,
                f["message"].as_str().unwrap_or("").replace('\n', " "),
            );
        }
        out.push('\n');
    }
    tracing::debug!(len = out.len(), "report markdown built");
    out
}

/// Every declared role pair measured in every mode, or why the spec could not be read.
///
/// # Errors
///
/// The spec load error text when `crunk.toml` is not a valid design spec.
pub fn contrast(run: &CrunkRun) -> Result<Value, String> {
    let spec = crunk_spec::load_spec(&run.root).map_err(|e| e.to_string())?;
    let modes: Vec<Value> = crunk_rules::mode::modes(&spec)
        .iter()
        .map(|mode| {
            let roles: Vec<Value> = crunk_rules::contrast::measure_roles(&spec, mode)
                .iter()
                .map(|m| {
                    json!({
                        "role": m.role,
                        "foreground": m.foreground,
                        "background": m.background,
                        "ratio": (m.ratio * 100.0).round() / 100.0,
                        "floor": m.floor,
                        "fails": m.fails(),
                    })
                })
                .collect();
            json!({"mode": mode.name, "roles": roles})
        })
        .collect();
    tracing::debug!(modes = modes.len(), "contrast table built");
    Ok(json!({"model": "wcag", "modes": modes}))
}

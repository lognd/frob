//! Run the Rust crunk for a captured case and judge the result against the golden and the divergence list.

use std::collections::BTreeMap;
use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

use super::corpus::Case;
use super::divergences::{Divergence, Field};

/// The comparable part of one run's standard output.
#[derive(Debug, Clone, PartialEq)]
pub enum Body {
    /// Structured output (compared as data, so key order and whitespace do not matter).
    Json(Value),
    /// Human output (compared with trailing whitespace trimmed).
    Text(String),
}

impl Body {
    fn short(&self) -> String {
        let full = match self {
            Self::Json(v) => v.to_string(),
            Self::Text(t) => t.clone(),
        };
        let cut: String = full.chars().take(160).collect();
        format!("{cut:?}")
    }
}

/// An exit code and the projected stdout.
#[derive(Debug, Clone, PartialEq)]
pub struct Outcome {
    /// The process exit code.
    pub exit: i64,
    /// The projected standard output.
    pub body: Body,
}

/// The Python golden as an outcome: JSON when the capture parses as JSON, else text.
pub fn golden(case: &Case, work: &Path) -> Outcome {
    let text = case.stdout.replace("<WORK>", &quoted(work));
    let body = match body_of(&text) {
        Body::Json(mut v) => {
            // The Python `version` marker is replaced by the envelope's `schema_version`.
            if let Some(o) = v.as_object_mut() {
                o.remove("version");
            }
            Body::Json(if is_check(&case.argv) {
                check_view(&v, true)
            } else {
                v
            })
        }
        text @ Body::Text(_) => text,
    };
    Outcome {
        exit: case.exit,
        body,
    }
}

fn quoted(path: &Path) -> String {
    #[expect(
        clippy::disallowed_methods,
        reason = "the work dir is matched against raw subprocess output"
    )]
    path.to_string_lossy().into_owned()
}

/// JSON when `text` parses as JSON (so layout never matters), else text with trailing whitespace trimmed.
fn body_of(text: &str) -> Body {
    serde_json::from_str(text).map_or_else(|_| Body::Text(text.trim_end().to_owned()), Body::Json)
}

fn is_check(argv: &[String]) -> bool {
    argv.first().is_some_and(|a| a == "check")
}

/// Rules the Rust crunk added after the Python capture; absent from every golden by design.
// frob:ticket 01M5JHRGF0BKG6ZGNXBZR3F5DB
const RUST_ONLY_RULES: &[&str] = &[
    "EXPORT001",
    "EXPORT002",
    "TOKEN002",
    "TOKEN003",
    "TOKEN004",
    "TOKEN005",
    "TOKEN006",
    "TOKEN007",
    "TOKEN008",
    "TOKEN009",
    "CRAFT010",
];

/// The comparable core of a check report: sorted `rule severity path` triples of the findings.
///
/// `python` selects the Python shape (`violations[].path`) over the Rust one (`findings[].file`).
fn check_view(report: &Value, python: bool) -> Value {
    let (list, path) = if python {
        ("violations", "path")
    } else {
        ("findings", "file")
    };
    let mut rows: Vec<String> = report[list]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|f| !RUST_ONLY_RULES.contains(&f["rule"].as_str().unwrap_or_default()))
        .map(|f| {
            format!(
                "{} {} {}",
                f["rule"].as_str().unwrap_or_default(),
                f["severity"].as_str().unwrap_or_default(),
                f[path].as_str().unwrap_or_default()
            )
        })
        .collect();
    rows.sort();
    serde_json::json!({ "findings": rows })
}

/// The Rust argv for a Python argv: `tokens --format X` is `--target X` (`--format` is the global output format).
pub fn translate(argv: &[String]) -> Vec<String> {
    let tokens = argv.first().is_some_and(|a| a == "tokens");
    argv.iter()
        .map(|a| {
            if tokens && a == "--format" {
                "--target".to_owned()
            } else {
                a.clone()
            }
        })
        .collect()
}

/// Run the Rust crunk for `case` in `work`, projected to the shape of `want`.
pub fn observe(case: &Case, work: &Path, want: &Body) -> Outcome {
    let mut full = translate(&case.argv);
    if matches!(want, Body::Text(_)) {
        full.push("--text".to_owned());
    }
    let args: Vec<&str> = full.iter().map(String::as_str).collect();
    let (code, out, _err) = run_for_test(&crunk::cli(), &args, &work.join(&case.project));
    let out = out.replace(&quoted(work), "<WORK>");
    let body = match want {
        Body::Text(_) => Body::Text(out.trim_end().to_owned()),
        Body::Json(_) => {
            let env: Value = serde_json::from_str(&out).unwrap_or(Value::Null);
            let data = env["data"].clone();
            if is_check(&case.argv) {
                Body::Json(check_view(&data, false))
            } else if case.argv.first().is_some_and(|a| a == "tokens")
                && case.argv.iter().any(|a| a == "--check")
            {
                Body::Text(format!(
                    "tokens: {}",
                    data["status"].as_str().unwrap_or_default()
                ))
            } else if let Some(content) = data.get("content").and_then(Value::as_str) {
                // A previewed token target carries the raw file text.
                body_of(content)
            } else {
                Body::Json(data)
            }
        }
    };
    Outcome {
        exit: i64::from(code),
        body,
    }
}

fn differences(want: &Outcome, got: &Outcome) -> BTreeMap<&'static str, String> {
    let mut d = BTreeMap::new();
    if want.exit != got.exit {
        d.insert("exit", format!("python {} rust {}", want.exit, got.exit));
    }
    if want.body != got.body {
        d.insert(
            "stdout",
            format!("python {} rust {}", want.body.short(), got.body.short()),
        );
    }
    d
}

const fn name(f: Field) -> &'static str {
    match f {
        Field::Exit => "exit",
        Field::Stdout => "stdout",
    }
}

/// Judge one case: failures for an unlisted difference or a listed one that no longer differs.
pub fn judge(
    case: &Case,
    want: &Outcome,
    got: &Outcome,
    listed: Option<&Divergence>,
) -> Vec<String> {
    let diff = differences(want, got);
    let mut failures = Vec::new();
    let allowed: Vec<&str> = listed
        .map(|d| d.fields.iter().map(|f| name(*f)).collect())
        .unwrap_or_default();
    for (field, what) in &diff {
        if !allowed.contains(field) {
            failures.push(format!("{}: unlisted {field} difference: {what}", case.id));
        }
    }
    if let Some(d) = listed {
        for field in &allowed {
            if !diff.contains_key(field) {
                failures.push(format!(
                    "{}: divergence `{}` lists {field} but {} no longer differs",
                    case.id, d.id, case.id
                ));
            }
        }
    }
    failures
}

//! `cargo dev bench-ic`: compare gungraun (Valgrind) instruction counts of a base and a head run.
//!
//! A benchmark run under gungraun with `--save-summary=json` leaves one `summary.json` per
//! benchmark. [`collect`] reads every such file under a directory into a name-to-instructions map;
//! [`compare`] lines a base map up against a head map; [`render`] turns the deltas into the
//! Markdown a pull-request comment carries (build-test-ci.md section 6).

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use serde_json::Value;

// frob:ticket 01M47QVC49RXV29NCG3N9G1JSM

/// Default regression threshold in percent: a head run this much above the base is flagged.
pub const DEFAULT_THRESHOLD_PCT: f64 = 2.0;

/// Marker on the first line of the comment so a re-run edits it instead of adding another.
pub const COMMENT_MARKER: &str = "<!-- frob-bench-ic -->";

/// Why a summary could not be read.
#[derive(Debug, thiserror::Error)]
pub enum BenchIcError {
    /// A directory or file could not be read.
    #[error("read {path}: {source}")]
    Io {
        /// The path involved.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// A summary file is not valid JSON.
    #[error("parse {path}: {source}")]
    Json {
        /// The summary file.
        path: PathBuf,
        /// Underlying error.
        source: serde_json::Error,
    },
}

/// Instruction counts keyed by benchmark name.
pub type Counts = BTreeMap<String, u64>;

/// How one benchmark moved between base and head.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Change {
    /// Present in both; `pct` is the signed percentage change of the head over the base.
    Moved {
        /// Base instruction count.
        base: u64,
        /// Head instruction count.
        head: u64,
        /// Signed change in percent (0 when the base is 0 and the head is 0).
        pct: f64,
    },
    /// Only the head has it.
    New {
        /// Head instruction count.
        head: u64,
    },
    /// Only the base has it.
    Removed {
        /// Base instruction count.
        base: u64,
    },
}

/// One benchmark and how it moved.
#[derive(Debug, Clone, PartialEq)]
pub struct Delta {
    /// Benchmark name (module path, plus `::id` when it has one).
    pub name: String,
    /// The movement.
    pub change: Change,
}

impl Delta {
    /// Whether this benchmark got more than `threshold_pct` percent slower.
    #[must_use]
    pub fn regressed(&self, threshold_pct: f64) -> bool {
        matches!(self.change, Change::Moved { pct, .. } if pct > threshold_pct)
    }
}

/// The instruction total of a metric value: a bare number, or an object wrapping one.
fn metric_value(v: &Value) -> Option<u64> {
    match v {
        Value::Number(n) => n.as_u64(),
        Value::Object(o) => o.values().find_map(metric_value),
        _ => None,
    }
}

/// Name and total `Ir` of the Callgrind profile in one gungraun `summary.json` text, if it has one.
///
/// # Errors
/// [`serde_json::Error`] when `text` is not JSON.
pub fn parse_summary(text: &str) -> Result<Option<(String, u64)>, serde_json::Error> {
    let v: Value = serde_json::from_str(text)?;
    let Some(module) = v.get("module_path").and_then(Value::as_str) else {
        return Ok(None);
    };
    let name = match v.get("id").and_then(Value::as_str) {
        Some(id) => format!("{module}::{id}"),
        None => module.to_owned(),
    };
    let ir = v
        .get("profiles")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter(|p| p.get("tool").and_then(Value::as_str) == Some("Callgrind"))
        .find_map(|p| {
            let ir = p.pointer("/data/total/metrics/Ir/values/new")?;
            metric_value(ir)
        });
    Ok(ir.map(|ir| (name, ir)))
}

/// Read every `summary.json` under `dir` (recursively) into one count per benchmark.
///
/// # Errors
/// [`BenchIcError`] when a directory or summary cannot be read or parsed.
pub fn collect(dir: &Path) -> Result<Counts, BenchIcError> {
    let mut counts = Counts::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        let io = |source| BenchIcError::Io {
            path: d.clone(),
            source,
        };
        for entry in std::fs::read_dir(&d).map_err(io)? {
            let path = entry.map_err(io)?.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.file_name().is_some_and(|n| n == "summary.json") {
                let text = std::fs::read_to_string(&path).map_err(|source| BenchIcError::Io {
                    path: path.clone(),
                    source,
                })?;
                let parsed = parse_summary(&text).map_err(|source| BenchIcError::Json {
                    path: path.clone(),
                    source,
                })?;
                if let Some((name, ir)) = parsed {
                    tracing::debug!(%name, ir, "read benchmark summary");
                    counts.insert(name, ir);
                }
            }
        }
    }
    tracing::info!(count = counts.len(), "collected benchmark summaries");
    Ok(counts)
}

#[expect(clippy::cast_precision_loss, reason = "a percentage for display")]
fn percent(base: u64, head: u64) -> f64 {
    if base == 0 {
        0.0
    } else {
        (head as f64 - base as f64) / base as f64 * 100.0
    }
}

/// Line the base counts up against the head counts, sorted by benchmark name.
#[must_use]
pub fn compare(base: &Counts, head: &Counts) -> Vec<Delta> {
    let names: std::collections::BTreeSet<&String> = base.keys().chain(head.keys()).collect();
    names
        .into_iter()
        .map(|name| {
            let change = match (base.get(name), head.get(name)) {
                (Some(&b), Some(&h)) => Change::Moved {
                    base: b,
                    head: h,
                    pct: percent(b, h),
                },
                (None, Some(&head)) => Change::New { head },
                (Some(&base), None) => Change::Removed { base },
                (None, None) => unreachable!("name came from one of the maps"),
            };
            Delta {
                name: name.clone(),
                change,
            }
        })
        .collect()
}

/// The pull-request comment: a marker line, then one table row per benchmark.
#[must_use]
pub fn render(deltas: &[Delta], threshold_pct: f64) -> String {
    let mut out = format!("{COMMENT_MARKER}\n### Instruction counts (head vs base)\n\n");
    if deltas.is_empty() {
        out.push_str("No benchmarks produced a summary.\n");
        return out;
    }
    out.push_str("| benchmark | base | head | change |\n|---|---:|---:|---:|\n");
    for d in deltas {
        let row = match d.change {
            Change::Moved { base, head, pct } => {
                let flag = if d.regressed(threshold_pct) {
                    " (regression)"
                } else {
                    ""
                };
                format!("| `{}` | {base} | {head} | {pct:+.2}%{flag} |", d.name)
            }
            Change::New { head } => format!("| `{}` | - | {head} | new |", d.name),
            Change::Removed { base } => format!("| `{}` | {base} | - | removed |", d.name),
        };
        let _ = writeln!(out, "{row}");
    }
    let n = deltas.iter().filter(|d| d.regressed(threshold_pct)).count();
    let _ = write!(
        out,
        "\n{n} of {} benchmarks above the {threshold_pct}% threshold.\n",
        deltas.len()
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn summary(module: &str, id: Option<&str>, ir: u64) -> String {
        serde_json::json!({
            "module_path": module,
            "id": id,
            "profiles": [
                {"tool": "Dhat", "data": {"total": {"metrics": {"Ir": {"values": {"new": 1}}}}}},
                {"tool": "Callgrind",
                 "data": {"total": {"metrics": {"Ir": {"values": {"new": ir}}}}}}
            ]
        })
        .to_string()
    }

    // frob:tests crates/gob-dev/src/bench_ic.rs::parse_summary
    #[test]
    fn parse_reads_callgrind_ir_and_id() {
        let got = parse_summary(&summary("ic::g::f", Some("small"), 42)).unwrap();
        assert_eq!(got, Some(("ic::g::f::small".to_owned(), 42)));
        let got = parse_summary(&summary("ic::g::f", None, 7)).unwrap();
        assert_eq!(got, Some(("ic::g::f".to_owned(), 7)));
    }

    // frob:tests crates/gob-dev/src/bench_ic.rs::parse_summary
    #[test]
    fn parse_skips_summaries_without_callgrind() {
        assert_eq!(
            parse_summary(r#"{"module_path":"a","profiles":[]}"#).unwrap(),
            None
        );
        assert!(parse_summary("not json").is_err());
    }

    // frob:tests crates/gob-dev/src/bench_ic.rs::collect
    #[test]
    fn collect_walks_nested_summaries() {
        let d = tempfile::tempdir().unwrap();
        let nested = d.path().join("a").join("b");
        std::fs::create_dir_all(&nested).unwrap();
        std::fs::write(nested.join("summary.json"), summary("m::x", None, 5)).unwrap();
        std::fs::write(d.path().join("other.json"), "ignored").unwrap();
        let counts = collect(d.path()).unwrap();
        assert_eq!(counts.get("m::x"), Some(&5));
        assert!(collect(&d.path().join("missing")).is_err());
    }

    fn counts(pairs: &[(&str, u64)]) -> Counts {
        pairs.iter().map(|&(k, v)| (k.to_owned(), v)).collect()
    }

    // frob:tests crates/gob-dev/src/bench_ic.rs::compare
    #[test]
    fn compare_classifies_each_benchmark() {
        let d = compare(
            &counts(&[("a", 100), ("b", 100), ("gone", 3)]),
            &counts(&[("a", 110), ("b", 90), ("fresh", 9)]),
        );
        let by = |n: &str| d.iter().find(|x| x.name == n).unwrap();
        assert!(matches!(by("a").change, Change::Moved { pct, .. } if (pct - 10.0).abs() < 1e-9));
        assert!(by("a").regressed(2.0));
        assert!(!by("b").regressed(2.0));
        assert_eq!(by("fresh").change, Change::New { head: 9 });
        assert_eq!(by("gone").change, Change::Removed { base: 3 });
    }

    // frob:tests crates/gob-dev/src/bench_ic.rs::render
    #[test]
    fn render_lists_per_benchmark_deltas() {
        let d = compare(&counts(&[("a", 100)]), &counts(&[("a", 110), ("n", 1)]));
        let md = render(&d, DEFAULT_THRESHOLD_PCT);
        assert!(md.starts_with(COMMENT_MARKER));
        assert!(md.contains("| `a` | 100 | 110 | +10.00% (regression) |"));
        assert!(md.contains("| `n` | - | 1 | new |"));
        assert!(md.contains("1 of 2 benchmarks above the 2% threshold."));
        assert!(render(&[], 2.0).contains("No benchmarks"));
    }

    // frob:tests crates/gob-dev/src/bench_ic.rs::harness_is_recorded_and_wired
    #[test]
    fn harness_is_recorded_and_wired() {
        let doc = include_str!("../../../docs/design/build-test-ci.md");
        assert!(doc.contains("gungraun 0.20"));
        let wf = include_str!("../../../.github/workflows/bench-pr.yml");
        assert!(wf.contains("--save-summary=json") && wf.contains("bench-ic"));
        let bench = include_str!("../../gob-plan/benches/ic_plan.rs");
        assert!(bench.contains("use gungraun::"));
    }
}

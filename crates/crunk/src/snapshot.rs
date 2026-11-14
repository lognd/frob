//! `snapshot [--update]`: compare solved layouts with the committed baselines.
//!
//! Baselines live at `design/baselines/<screen>/<state>/<platform>.layout.json` (`--baselines`
//! moves them). Without `--update` a missing baseline fails and names its path, and a baseline
//! that differs fails with a node-level diff (node id, field, old and new value, numeric delta).
//! With `--update` only baselines whose bytes change are rewritten, so a clean tree stays clean.
//! Solving is shared with `render`, so the order of results never depends on `--jobs`.

// frob:ticket 01M5XCWYMSEMEQPNZ7EFHHY9Z7

use std::collections::{BTreeMap, BTreeSet};

use crunk_layout::output::{LayoutSolve, SolvedNode};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::{Map, Value};

use crate::render::{self, SelectArgs};

/// Default baseline directory, relative to the project root.
const DEFAULT_BASELINES: &str = "design/baselines";
/// The pseudo node id carrying viewport and focus-order differences.
const DOCUMENT: &str = "(document)";

/// Compare solved layouts with the committed baselines, or rewrite them with `--update`.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "snapshot",
    product = "crunk",
    idempotent = false,
    exits(ok, negative, refused, usage, internal)
)]
pub struct Snapshot {
    update: bool,
    baselines: String,
    select: SelectArgs,
}

/// `snapshot` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct SnapshotArgs {
    #[arg(
        long,
        help = "Write baselines (only those that changed) instead of comparing"
    )]
    update: bool,
    #[arg(
        long,
        value_name = "DIR",
        default_value = DEFAULT_BASELINES,
        help = "Baseline directory, relative to the project root"
    )]
    baselines: String,
    #[command(flatten)]
    select: SelectArgs,
}

/// How one field of a node differs between baseline and current.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct FieldDelta {
    /// The field name (`x`, `width`, `parent`, ...).
    pub field: String,
    /// Baseline value, absent when the field is new.
    pub from: Option<Value>,
    /// Current value, absent when the field is gone.
    pub to: Option<Value>,
    /// `to - from` for numeric fields.
    pub delta: Option<f64>,
}

/// How a node differs: added, removed or changed fields.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct NodeDelta {
    /// The node's scene id, or `(document)` for viewport and focus order.
    pub id: String,
    /// `added`, `removed` or `changed`.
    pub change: String,
    /// The differing fields (empty for added and removed nodes).
    pub fields: Vec<FieldDelta>,
}

/// The outcome for one cell.
#[derive(Debug, Clone, PartialEq, Serialize, JsonSchema)]
pub struct SnapshotCell {
    /// Screen id.
    pub screen: String,
    /// State id.
    pub state: String,
    /// Platform id.
    pub platform: String,
    /// The baseline file, relative to the project root.
    pub path: String,
    /// `match`, `missing`, `changed`, `written` (new baseline) or `updated` (rewritten).
    pub status: String,
    /// Node-level differences, for `changed` and `updated`.
    pub diff: Vec<NodeDelta>,
}

/// Output of `snapshot`.
#[derive(Debug, Clone, Default, PartialEq, Serialize, JsonSchema)]
pub struct SnapshotData {
    /// Every cell, in cell order.
    pub cells: Vec<SnapshotCell>,
}

fn field_names(a: &Map<String, Value>, b: &Map<String, Value>) -> Vec<String> {
    let mut names: Vec<String> = a.keys().chain(b.keys()).cloned().collect();
    names.sort();
    names.dedup();
    names
}

fn deltas(a: &Map<String, Value>, b: &Map<String, Value>) -> Vec<FieldDelta> {
    field_names(a, b)
        .into_iter()
        .filter(|k| a.get(k) != b.get(k))
        .map(|field| {
            let (from, to) = (a.get(&field).cloned(), b.get(&field).cloned());
            let delta = match (&from, &to) {
                (Some(Value::Number(x)), Some(Value::Number(y))) => {
                    x.as_f64().zip(y.as_f64()).map(|(x, y)| y - x)
                }
                _ => None,
            };
            FieldDelta {
                field,
                from,
                to,
                delta,
            }
        })
        .collect()
}

fn object(v: Value) -> Map<String, Value> {
    match v {
        Value::Object(m) => m,
        _ => Map::new(),
    }
}

/// The node-level differences between a baseline and a current solve, in baseline node order
/// with added nodes last; empty when the two are identical.
pub fn diff_layouts(base: &LayoutSolve, now: &LayoutSolve) -> Vec<NodeDelta> {
    let mut out = Vec::new();
    let top = |s: &LayoutSolve| {
        object(serde_json::json!({
            "viewport_width": s.viewport_width,
            "viewport_height": s.viewport_height,
            "focus_order": s.focus_order,
        }))
    };
    let fields = deltas(&top(base), &top(now));
    if !fields.is_empty() {
        out.push(NodeDelta {
            id: DOCUMENT.to_owned(),
            change: "changed".to_owned(),
            fields,
        });
    }
    let old: BTreeSet<&str> = base.nodes.iter().map(|n| n.id.as_str()).collect();
    let by_id: BTreeMap<&str, &SolvedNode> = now.nodes.iter().map(|n| (n.id.as_str(), n)).collect();
    for n in &base.nodes {
        match by_id.get(n.id.as_str()) {
            None => out.push(NodeDelta {
                id: n.id.clone(),
                change: "removed".to_owned(),
                fields: Vec::new(),
            }),
            Some(m) => {
                let fields = deltas(
                    &object(serde_json::to_value(n).unwrap_or_default()),
                    &object(serde_json::to_value(m).unwrap_or_default()),
                );
                if !fields.is_empty() {
                    out.push(NodeDelta {
                        id: n.id.clone(),
                        change: "changed".to_owned(),
                        fields,
                    });
                }
            }
        }
    }
    for n in &now.nodes {
        if !old.contains(n.id.as_str()) {
            out.push(NodeDelta {
                id: n.id.clone(),
                change: "added".to_owned(),
                fields: Vec::new(),
            });
        }
    }
    out
}

/// Render an optional JSON value, `-` when absent.
fn show(v: Option<&Value>) -> String {
    v.map_or_else(|| "-".to_owned(), Value::to_string)
}

/// Text lines for a node delta: `~ id field from -> to (+delta)`.
fn delta_lines(d: &NodeDelta) -> Vec<String> {
    match d.change.as_str() {
        "added" => vec![format!("    + {}", d.id)],
        "removed" => vec![format!("    - {}", d.id)],
        _ => d
            .fields
            .iter()
            .map(|f| {
                let by = f.delta.map_or_else(String::new, |x| format!(" ({x:+})"));
                format!(
                    "    ~ {} {} {} -> {}{by}",
                    d.id,
                    f.field,
                    show(f.from.as_ref()),
                    show(f.to.as_ref())
                )
            })
            .collect(),
    }
}

impl Command for Snapshot {
    type Data = SnapshotData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<SnapshotArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<SnapshotArgs>(m)?;
        Ok(Self {
            update: a.update,
            baselines: a.baselines,
            select: a.select,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<SnapshotData> {
        let plan = render::plan(ctx, &self.select)?;
        let results = render::solve_all(&plan);
        let mut data = SnapshotData::default();
        let mut text = plan.skipped.clone();
        let mut failures = Vec::new();
        let mut bad = 0usize;
        for (item, result) in plan.items.iter().zip(results) {
            let label = format!("{}/{} on {}", item.screen, item.state, item.platform);
            let rel = render::cell_file(&self.baselines, item);
            let path = plan.root.join(&rel);
            let mut cell = SnapshotCell {
                screen: item.screen.clone(),
                state: item.state.clone(),
                platform: item.platform.clone(),
                path: render::posix(&rel),
                status: "match".to_owned(),
                diff: Vec::new(),
            };
            let solved = match result {
                Ok(s) => s,
                Err(e) => {
                    tracing::info!(cell = %label, error = %e, "snapshot: cell failed");
                    failures.push(format!("{label}: {e}"));
                    continue;
                }
            };
            let current = std::fs::read_to_string(&path).ok();
            match current {
                None => {
                    cell.status = if self.update { "written" } else { "missing" }.into();
                }
                Some(old) if old == solved.json => {}
                Some(old) => {
                    cell.diff = serde_json::from_str::<LayoutSolve>(&old)
                        .ok()
                        .and_then(|b| {
                            let n: LayoutSolve = serde_json::from_str(&solved.json).ok()?;
                            Some(diff_layouts(&b, &n))
                        })
                        .unwrap_or_default();
                    cell.status = if self.update { "updated" } else { "changed" }.into();
                }
            }
            if self.update && matches!(cell.status.as_str(), "written" | "updated") {
                if let Err(e) = render::write_file(&path, &solved.json) {
                    failures.push(format!("{label}: {e}"));
                    continue;
                }
                tracing::info!(cell = %label, status = %cell.status, "snapshot: baseline written");
            }
            match cell.status.as_str() {
                "missing" => {
                    bad += 1;
                    failures.push(format!("{label}: baseline missing: {}", cell.path));
                }
                "changed" => {
                    bad += 1;
                    failures.push(format!("{label}: layout differs from {}", cell.path));
                }
                _ => {}
            }
            text.push(format!("{label}: {} {}", cell.status, cell.path));
            text.extend(cell.diff.iter().flat_map(delta_lines));
            data.cells.push(cell);
        }
        tracing::info!(
            cells = data.cells.len(),
            bad,
            update = self.update,
            "snapshot done"
        );
        if failures.is_empty() {
            return Ok(Payload::new(data).with_rendered(text));
        }
        let value = serde_json::to_value(&data).map_err(CliError::internal)?;
        let mut warnings = text;
        warnings.extend(failures.iter().cloned());
        Err(CliError::Gate {
            message: format!("snapshot: {}", failures.join("; ")),
            data: value,
            warnings,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn solve(width: f32) -> LayoutSolve {
        LayoutSolve {
            version: 1,
            viewport_width: width,
            viewport_height: 600.0,
            nodes: Vec::new(),
            focus_order: Vec::new(),
        }
    }

    // frob:tests crates/crunk/src/snapshot.rs::diff_layouts
    #[test]
    fn identical_solves_have_no_diff_and_viewport_change_is_reported() {
        assert!(diff_layouts(&solve(800.0), &solve(800.0)).is_empty());
        let d = diff_layouts(&solve(800.0), &solve(900.0));
        assert_eq!(d.len(), 1);
        assert_eq!(d[0].id, DOCUMENT);
    }
}

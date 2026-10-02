//! `[[check.tool]]` stages: external commands run after the built-in rules.
//!
//! A stage with a `parser` also turns the tool's JSON output into findings
//! with real spans and CI ids; a stage whose tool version is outside its
//! configured range yields one non-required Unresolved finding instead.

use std::collections::HashMap;
use std::path::Path;
use std::time::{Duration, Instant};

use gob_exec::{ExecError, Limits, Outcome, Output, Program, Runner, Spec};
use gob_rules::{Finding, RequiredReason, Rule, RuleId, Severity};
use gob_text::{FileInterner, LineCol, LineIndex, Span, TextRange, TextSize};

use crate::config::{ToolParser, ToolStage};
use crate::report::Timing;
use crate::rules::Tool001;
use crate::tool_parse::{
    RawFinding, RawRange, VersionVerdict, check_version, classify, default_version_args,
    find_version, parse,
};

/// Trailing characters of a tool's output quoted in the finding.
const TAIL: usize = 400;

fn tail(text: &str) -> String {
    let t = text.trim();
    let skip = t.chars().count().saturating_sub(TAIL);
    t.chars().skip(skip).collect()
}

/// What running one stage produced.
enum StageResult {
    /// The binary was not found.
    Missing(String),
    /// The stage failed for another reason.
    Problem(String),
    /// The tool's version is outside the configured range.
    Lag(String),
    /// The stage ran; these findings are its parsed output (empty without a parser).
    Done(Vec<Finding>),
}

fn spec(root: &Path, stage: &ToolStage, args: Vec<String>) -> Spec {
    Spec {
        program: Program::Tool {
            name: stage.command.clone(),
        },
        args,
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(stage.timeout_secs),
        capture: true,
    }
}

/// Repo-relative, forward-slash form of a path a tool printed.
fn normalize(root: &Path, printed: &str) -> String {
    let unified = printed.replace('\\', "/");
    let root_text = root.to_string_lossy().replace('\\', "/");
    let rel = unified
        .strip_prefix(root_text.trim_end_matches('/'))
        .map_or(unified.as_str(), |r| r.trim_start_matches('/'));
    rel.trim_start_matches("./").to_owned()
}

/// Per-stage cache of line indexes, so a file is read once.
#[derive(Default)]
struct Indexes(HashMap<String, Option<(String, LineIndex)>>);

impl Indexes {
    fn line_range(
        &mut self,
        root: &Path,
        path: &str,
        line: u32,
        col: u32,
        end: u32,
    ) -> Option<TextRange> {
        let slot = self.0.entry(path.to_owned()).or_insert_with(|| {
            let text = std::fs::read_to_string(root.join(path)).ok()?;
            let index = LineIndex::new(&text).ok()?;
            Some((text, index))
        });
        let (_, index) = slot.as_ref()?;
        let start = index.offset(LineCol { line, col })?;
        let stop = index
            .offset(LineCol { line, col: end })
            .filter(|s| *s >= start)
            .unwrap_or(start);
        Some(TextRange::new(start, stop))
    }
}

/// The span of `raw` in the repository, or `None` when the tool gave no usable location.
fn locate(
    root: &Path,
    files: &mut FileInterner,
    indexes: &mut Indexes,
    path: &str,
    raw: &RawRange,
) -> Option<Span> {
    if path.is_empty() {
        return None;
    }
    let range = match *raw {
        RawRange::None => return None,
        RawRange::Bytes { start, end } => {
            TextRange::new(TextSize::new(start), TextSize::new(end.max(start)))
        }
        RawRange::LineCol { line, col, end_col } => {
            indexes.line_range(root, path, line, col, end_col)?
        }
    };
    Some(Span::new(files.intern(path), range))
}

/// Turn the parsed findings of `stage` into frob findings (dropped ones omitted).
fn to_findings(
    root: &Path,
    stage: &ToolStage,
    raws: &[RawFinding],
    files: &mut FileInterner,
) -> Vec<Finding> {
    let mut indexes = Indexes::default();
    let mut out = Vec::new();
    for raw in raws {
        let Some((rule, severity)) = classify(stage, raw) else {
            continue;
        };
        let path = normalize(root, &raw.path);
        let span = locate(root, files, &mut indexes, &path, &raw.range);
        let message = format!("{}/{}: {}", stage.name, raw.tool_id, raw.message);
        tracing::debug!(stage = %stage.name, tool_id = %raw.tool_id, rule = %rule, path = %path, located = span.is_some(), "tool finding");
        out.push(Finding::new(rule, severity, span, message, &path));
    }
    out
}

/// The tool's version text, or `Err` only when its binary is missing.
fn tool_version(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
) -> Result<Option<String>, ExecError> {
    let Some(args) = stage
        .version_args
        .clone()
        .or_else(|| default_version_args(stage.parser))
    else {
        return Ok(None);
    };
    match runner.run(&spec(root, stage, args)) {
        Ok(o) => Ok(find_version(&format!("{}\n{}", o.stdout, o.stderr))),
        Err(err @ ExecError::NotFound { .. }) => Err(err),
        Err(err) => {
            tracing::warn!(stage = %stage.name, %err, "could not read the tool version");
            Ok(None)
        }
    }
}

/// Describe a run that did not finish normally; `None` for a normal exit.
fn abnormal(o: &Output, stage: &ToolStage) -> Option<String> {
    match o.status {
        Outcome::Exited(0) => None,
        Outcome::Exited(code) => Some(format!(
            "exited {code}: {}",
            tail(&format!("{}\n{}", o.stdout, o.stderr))
        )),
        Outcome::Signaled => Some("was terminated by a signal".to_owned()),
        Outcome::TimedOut => Some(format!("timed out after {}s", stage.timeout_secs)),
    }
}

fn execute(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
    files: &mut FileInterner,
) -> StageResult {
    if stage.parser != ToolParser::None {
        match tool_version(runner, root, stage) {
            Err(err) => return StageResult::Missing(format!("could not run: {err}")),
            Ok(version) => {
                tracing::info!(stage = %stage.name, version = version.as_deref().unwrap_or("unknown"), "tool version");
                if let VersionVerdict::Lag(why) = check_version(stage, version.as_deref()) {
                    return StageResult::Lag(why);
                }
            }
        }
    }
    let output = match runner.run(&spec(root, stage, stage.args.clone())) {
        Ok(o) => o,
        Err(err @ ExecError::NotFound { .. }) => {
            return StageResult::Missing(format!("could not run: {err}"));
        }
        Err(err) => return StageResult::Problem(format!("could not run: {err}")),
    };
    if stage.parser == ToolParser::None {
        return abnormal(&output, stage)
            .map_or(StageResult::Done(Vec::new()), StageResult::Problem);
    }
    // A parsed stage exits nonzero when it has findings; only unparseable output is a failure.
    if matches!(output.status, Outcome::Signaled | Outcome::TimedOut) {
        return StageResult::Problem(abnormal(&output, stage).unwrap_or_default());
    }
    match parse(stage.parser, &output.stdout) {
        Ok(raws) => {
            tracing::info!(stage = %stage.name, findings = raws.len(), "tool output parsed");
            StageResult::Done(to_findings(root, stage, &raws, files))
        }
        Err(err) => StageResult::Problem(format!(
            "{err}; {}",
            abnormal(&output, stage).unwrap_or_else(|| "exited 0".to_owned())
        )),
    }
}

/// Run `stages` in order; each is timed outside the budget.
///
/// Findings of parsed stages carry spans interned into `files`; failures and
/// version lag yield at most one `TOOL001` per stage.
pub(crate) fn run_tools(
    root: &Path,
    stages: &[ToolStage],
    timing: &mut Timing,
    files: &mut FileInterner,
) -> Vec<Finding> {
    if stages.is_empty() {
        return Vec::new();
    }
    let id: RuleId = Tool001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let runner =
        Runner::new(Limits::default()).allow_tools(stages.iter().map(|s| s.command.clone()));
    let mut out = Vec::new();
    for stage in stages {
        let started = Instant::now();
        let result = execute(&runner, root, stage, files);
        timing.push(format!("tool:{}", stage.name), started.elapsed(), false);
        let unresolved = |message: String| {
            Finding::new(id.clone(), Severity::Unresolved, None, message, &stage.name)
        };
        match result {
            StageResult::Done(found) => {
                tracing::info!(stage = %stage.name, findings = found.len(), "tool stage passed");
                out.extend(found);
            }
            StageResult::Lag(why) => {
                tracing::warn!(stage = %stage.name, %why, "tool schema lag; output discarded");
                out.push(unresolved(format!(
                    "tool stage `{}` ({}) {why} (schema lag)",
                    stage.name, stage.command
                )));
            }
            StageResult::Missing(p) if stage.optional => {
                tracing::warn!(stage = %stage.name, problem = %p, "optional tool binary missing");
                out.push(unresolved(format!(
                    "tool stage `{}` ({}) {p} (optional)",
                    stage.name, stage.command
                )));
            }
            StageResult::Missing(p) if stage.fail_on_nonzero => {
                tracing::warn!(stage = %stage.name, problem = %p, "tool binary missing");
                let message = format!("tool stage `{}` ({}) {p}", stage.name, stage.command);
                out.push(
                    unresolved(message).with_required(RequiredReason::SiblingMissing {
                        product: stage.command.clone(),
                    }),
                );
            }
            StageResult::Problem(p) if stage.fail_on_nonzero => {
                tracing::warn!(stage = %stage.name, problem = %p, "tool stage failed");
                out.push(Finding::new(
                    id.clone(),
                    Severity::Error,
                    None,
                    format!("tool stage `{}` ({}) {p}", stage.name, stage.command),
                    &stage.name,
                ));
            }
            StageResult::Missing(p) | StageResult::Problem(p) => {
                tracing::info!(stage = %stage.name, problem = %p, "tool stage failed (not gating)");
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-check/src/tools.rs::normalize
    #[test]
    fn printed_paths_become_repo_relative() {
        let root = Path::new("/r/repo");
        assert_eq!(normalize(root, "./.github/a.yml"), ".github/a.yml");
        assert_eq!(normalize(root, "/r/repo/.github/a.yml"), ".github/a.yml");
        assert_eq!(normalize(root, ".github\\a.yml"), ".github/a.yml");
    }
}

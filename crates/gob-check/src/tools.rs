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

/// Escape `text` for one line of a finding: control characters become visible escapes.
fn escape(text: &str) -> String {
    text.chars()
        .flat_map(|c| {
            if c.is_control() {
                c.escape_default().collect::<Vec<_>>()
            } else {
                vec![c]
            }
        })
        .collect()
}

/// The escaped, capped tail of a stream, or `(empty)`.
fn excerpt(text: &str) -> String {
    let t = tail(text);
    if t.is_empty() {
        "(empty)".to_owned()
    } else {
        escape(&t)
    }
}

/// The command line of a stage invocation, for a finding.
fn command_line(stage: &ToolStage, args: &[String]) -> String {
    escape(
        &std::iter::once(stage.command.as_str())
            .chain(args.iter().map(String::as_str))
            .collect::<Vec<_>>()
            .join(" "),
    )
}

/// The status of a finished run, for a finding.
fn status_text(o: &Output) -> String {
    match o.status {
        Outcome::Exited(code) => format!("exit {code}"),
        Outcome::Signaled => "terminated by a signal".to_owned(),
        Outcome::TimedOut => "timed out".to_owned(),
    }
}

/// The message of a `tool-failed` finding: stage, command, status and stderr excerpt.
fn failure(stage: &ToolStage, args: &[String], what: &str, status: &str, stderr: &str) -> String {
    format!(
        "tool stage `{}` {what}: command `{}`; status: {status}; stderr: {}",
        stage.name,
        command_line(stage, args),
        excerpt(stderr)
    )
}

/// What running one stage produced.
enum StageResult {
    /// The binary was not found.
    Missing(String),
    /// The tool did not produce evidence (unresolvable, abnormal exit, unreadable output); carries the full message.
    Failed(String),
    /// The stage failed for another reason.
    Problem(String),
    /// The tool's version is outside the configured range.
    Lag(String),
    /// The stage ran; these are the tool's parsed findings, not yet located (empty without a parser).
    Done(Vec<RawFinding>),
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

/// The tool's version text, or `Err` with the stage result when the probe fails.
fn tool_version(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
) -> Result<Option<String>, StageResult> {
    let Some(args) = stage
        .version_args
        .clone()
        .or_else(|| default_version_args(stage.parser))
    else {
        return Ok(None);
    };
    match runner.run(&spec(root, stage, args.clone())) {
        Ok(o) if o.status == Outcome::Exited(0) => {
            Ok(find_version(&format!("{}\n{}", o.stdout, o.stderr)))
        }
        Ok(o) => Err(StageResult::Failed(failure(
            stage,
            &args,
            "version probe failed",
            &status_text(&o),
            &o.stderr,
        ))),
        Err(err @ ExecError::NotFound { .. }) => {
            Err(StageResult::Missing(format!("could not run: {err}")))
        }
        Err(err) => Err(StageResult::Failed(failure(
            stage,
            &args,
            &format!("version probe could not run ({err})"),
            "not run",
            "",
        ))),
    }
}

/// Exit codes a parsed tool uses to report findings rather than failure.
fn normal_exits(parser: ToolParser) -> &'static [i32] {
    match parser {
        ToolParser::None => &[0],
        ToolParser::ZizmorJsonV1 => &[0, 10, 11, 12, 13, 14],
        ToolParser::ActionlintJson => &[0, 1],
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

fn execute(runner: &Runner, root: &Path, stage: &ToolStage) -> StageResult {
    let parsed = stage.parser != ToolParser::None;
    if parsed {
        match tool_version(runner, root, stage) {
            Err(result) => return result,
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
        Err(err) if parsed => {
            return StageResult::Failed(failure(
                stage,
                &stage.args,
                &format!("could not run ({err})"),
                "not run",
                "",
            ));
        }
        Err(err) => return StageResult::Problem(format!("could not run: {err}")),
    };
    if !parsed {
        return abnormal(&output, stage)
            .map_or(StageResult::Done(Vec::new()), StageResult::Problem);
    }
    // A parsed stage exits nonzero when it has findings; only an undeclared status or unreadable output is a failure.
    let declared =
        matches!(output.status, Outcome::Exited(c) if normal_exits(stage.parser).contains(&c));
    if !declared {
        return StageResult::Failed(failure(
            stage,
            &stage.args,
            "exited abnormally",
            &status_text(&output),
            &output.stderr,
        ));
    }
    if output.status != Outcome::Exited(0) && output.stdout.trim().is_empty() {
        return StageResult::Failed(failure(
            stage,
            &stage.args,
            "printed no output despite a findings exit",
            &status_text(&output),
            &output.stderr,
        ));
    }
    match parse(stage.parser, &output.stdout) {
        Ok(raws) => {
            tracing::info!(stage = %stage.name, findings = raws.len(), "tool output parsed");
            StageResult::Done(raws)
        }
        Err(err) => StageResult::Failed(failure(
            stage,
            &stage.args,
            &format!("printed output its parser cannot read ({err})"),
            &status_text(&output),
            &output.stderr,
        )),
    }
}

/// True when `stage` declares inputs and none of the scoped `files` matches one of them.
///
/// A stage without inputs, or an input glob that does not parse, never counts as untouched:
/// the stage runs (frob:ticket 01M4GRW6NH23YPTSAQERDRSZC5).
fn untouched(stage: &ToolStage, files: &std::collections::BTreeSet<String>) -> bool {
    if stage.inputs.is_empty() {
        return false;
    }
    let mut builder = globset::GlobSetBuilder::new();
    for glob in &stage.inputs {
        match globset::Glob::new(glob) {
            Ok(g) => {
                builder.add(g);
            }
            Err(e) => {
                tracing::warn!(stage = %stage.name, %glob, error = %e, "bad tool input glob; the stage runs");
                return false;
            }
        }
    }
    match builder.build() {
        Ok(set) => !files.iter().any(|f| set.is_match(f)),
        Err(e) => {
            tracing::warn!(stage = %stage.name, error = %e, "tool inputs not compiled; the stage runs");
            false
        }
    }
}

/// The stages a run executes: all of them unscoped, else those whose declared inputs the scope touches.
pub(crate) fn applicable_stages(
    stages: &[ToolStage],
    scope_files: Option<&std::collections::BTreeSet<String>>,
) -> Vec<ToolStage> {
    stages
        .iter()
        .filter(|stage| {
            let skip = scope_files.is_some_and(|files| untouched(stage, files));
            if skip {
                tracing::info!(stage = %stage.name, "tool stage skipped: the scope touches none of its inputs");
            }
            !skip
        })
        .cloned()
        .collect()
}

/// One stage's outcome and wall time, as a worker thread produced it.
type Finished = (usize, StageResult, Duration);

/// Tool stages running on background threads; [`ToolRun::finish`] joins them and builds the findings.
///
/// Stages that share a cargo target directory lock (every `cargo` command) run one after the
/// other on one thread, in configured order; every other stage gets a thread of its own, so
/// the run takes as long as its slowest group, not the sum of its stages
/// (frob:ticket 01M4D6NEQYAZEFFX3P0S2EJV2N).
pub(crate) struct ToolRun {
    root: std::path::PathBuf,
    stages: Vec<ToolStage>,
    workers: Vec<std::thread::JoinHandle<Vec<Finished>>>,
}

/// The lock group of a stage: stages with an equal key run serially.
fn group_key(stage: &ToolStage, index: usize) -> String {
    if stage.command == "cargo" {
        "cargo".to_owned()
    } else {
        format!("stage-{index}")
    }
}

/// Start `stages` on background threads and return at once; `None` when there are no stages.
pub(crate) fn start_tools(root: &Path, stages: &[ToolStage]) -> Option<ToolRun> {
    if stages.is_empty() {
        return None;
    }
    let runner = std::sync::Arc::new(
        Runner::new(Limits::default()).allow_tools(stages.iter().map(|s| s.command.clone())),
    );
    let mut groups: Vec<(String, Vec<usize>)> = Vec::new();
    for (i, stage) in stages.iter().enumerate() {
        let key = group_key(stage, i);
        match groups.iter_mut().find(|(k, _)| *k == key) {
            Some((_, members)) => members.push(i),
            None => groups.push((key, vec![i])),
        }
    }
    tracing::info!(
        stages = stages.len(),
        groups = groups.len(),
        "tool stages started"
    );
    let workers = groups
        .into_iter()
        .map(|(key, members)| {
            let runner = std::sync::Arc::clone(&runner);
            let root = root.to_path_buf();
            let work: Vec<(usize, ToolStage)> = members
                .into_iter()
                .map(|i| (i, stages[i].clone()))
                .collect();
            std::thread::spawn(move || {
                tracing::debug!(group = %key, "tool group running");
                work.into_iter()
                    .map(|(i, stage)| {
                        let started = Instant::now();
                        let result = execute(&runner, &root, &stage);
                        (i, result, started.elapsed())
                    })
                    .collect()
            })
        })
        .collect();
    Some(ToolRun {
        root: root.to_path_buf(),
        stages: stages.to_vec(),
        workers,
    })
}

impl ToolRun {
    /// Wait for every stage and return its findings in configured stage order.
    ///
    /// Each stage is timed outside the budget with its own duration, so the per-stage
    /// timing still adds up to more than the wall time when stages overlapped.
    /// Findings of parsed stages carry spans interned into `files`; failures and version lag
    /// yield at most one `TOOL001` per stage.
    pub(crate) fn finish(self, timing: &mut Timing, files: &mut FileInterner) -> Vec<Finding> {
        let mut done: Vec<Finished> = Vec::with_capacity(self.stages.len());
        for worker in self.workers {
            match worker.join() {
                Ok(mut part) => done.append(&mut part),
                Err(panic) => std::panic::resume_unwind(panic),
            }
        }
        done.sort_by_key(|(i, _, _)| *i);
        let id: RuleId = Tool001
            .meta()
            .rule_id()
            .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
        let mut out = Vec::new();
        for (index, result, took) in done {
            let stage = &self.stages[index];
            timing.push(format!("tool:{}", stage.name), took, false);
            out.extend(stage_findings(&self.root, &id, stage, result, files));
        }
        out
    }
}

/// The findings one finished stage contributes.
fn stage_findings(
    root: &Path,
    id: &RuleId,
    stage: &ToolStage,
    result: StageResult,
    files: &mut FileInterner,
) -> Vec<Finding> {
    let mut out = Vec::new();
    {
        let unresolved = |message: String| {
            Finding::new(id.clone(), Severity::Unresolved, None, message, &stage.name)
        };
        match result {
            StageResult::Done(raws) => {
                let found = to_findings(root, stage, &raws, files);
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
            StageResult::Failed(message) => {
                tracing::warn!(stage = %stage.name, %message, "tool stage failed to produce evidence");
                out.push(
                    unresolved(message).with_required(RequiredReason::ToolFailed {
                        stage: stage.name.clone(),
                    }),
                );
            }
            StageResult::Missing(p) => {
                tracing::warn!(stage = %stage.name, problem = %p, "tool binary missing");
                let message = failure(stage, &stage.args, &p, "not run", "");
                out.push(
                    unresolved(message).with_required(RequiredReason::ToolFailed {
                        stage: stage.name.clone(),
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
            StageResult::Problem(p) => {
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

    fn sh_stage(name: &str, parser: ToolParser, script: &str, probe: &str) -> ToolStage {
        ToolStage {
            name: name.to_owned(),
            command: "sh".to_owned(),
            args: vec!["-c".to_owned(), script.to_owned()],
            timeout_secs: 30,
            fail_on_nonzero: true,
            parser,
            labels: Vec::new(),
            id_map: std::collections::BTreeMap::new(),
            min_version: Some("1.7.0".to_owned()),
            max_version: Some("1.7.99".to_owned()),
            version_args: Some(vec!["-c".to_owned(), probe.to_owned()]),
            optional: false,
            inputs: Vec::new(),
        }
    }

    fn run_one(stage: &ToolStage) -> Vec<Finding> {
        let mut timing = Timing::default();
        let mut files = FileInterner::default();
        start_tools(Path::new("."), std::slice::from_ref(stage))
            .expect("one stage")
            .finish(&mut timing, &mut files)
    }

    // frob:ticket 01M4D6NEQYAZEFFX3P0S2EJV2N
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn independent_stages_overlap_and_keep_their_order_and_timing() {
        let slow = |name: &str| sh_stage(name, ToolParser::None, "sleep 1", "true");
        let stages = [slow("a"), slow("b"), slow("c")];
        let mut timing = Timing::default();
        let mut files = FileInterner::default();
        let started = Instant::now();
        let found = start_tools(Path::new("."), &stages)
            .expect("stages")
            .finish(&mut timing, &mut files);
        let wall = started.elapsed();
        assert!(found.is_empty(), "{found:?}");
        let names: Vec<_> = timing.stages.iter().map(|t| t.name.as_str()).collect();
        assert_eq!(names, ["tool:a", "tool:b", "tool:c"]);
        assert!(timing.tools_ms() >= 3000, "each stage reports its own time");
        assert!(wall < Duration::from_millis(2500), "ran serially: {wall:?}");
    }

    // frob:ticket 01M4GRW6NH23YPTSAQERDRSZC5
    // frob:tests crates/gob-check/src/tools.rs::applicable_stages
    #[test]
    fn a_stage_is_skipped_only_when_it_declares_inputs_the_scope_misses() {
        let mut stage = sh_stage("gen", ToolParser::None, "true", "true");
        let scope: std::collections::BTreeSet<String> =
            ["docs/a.md".to_owned()].into_iter().collect();
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&scope)).len(),
            1
        );
        stage.inputs = vec!["crates/**/*.rs".to_owned()];
        assert!(applicable_stages(std::slice::from_ref(&stage), Some(&scope)).is_empty());
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), None).len(),
            1
        );
        let hit: std::collections::BTreeSet<String> =
            ["crates/x/src/lib.rs".to_owned()].into_iter().collect();
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&hit)).len(),
            1
        );
        stage.inputs = vec!["[".to_owned()];
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&scope)).len(),
            1
        );
    }

    // frob:ticket 01M4D6NEQYAZEFFX3P0S2EJV2N
    // frob:tests crates/gob-check/src/tools.rs::group_key
    #[test]
    fn cargo_stages_share_one_group_and_others_get_their_own() {
        let mut cargo = sh_stage("c", ToolParser::None, "true", "true");
        cargo.command = "cargo".to_owned();
        let other = sh_stage("o", ToolParser::None, "true", "true");
        assert_eq!(group_key(&cargo, 0), group_key(&cargo, 5));
        assert_ne!(group_key(&other, 1), group_key(&other, 2));
        assert_ne!(group_key(&cargo, 0), group_key(&other, 0));
    }

    fn assert_tool_failed(found: &[Finding], needles: &[&str]) {
        assert_eq!(found.len(), 1, "{found:?}");
        let f = &found[0];
        assert_eq!(f.severity, Severity::Unresolved);
        assert_eq!(
            f.required,
            Some(RequiredReason::ToolFailed {
                stage: "lint".to_owned()
            })
        );
        for needle in needles {
            assert!(f.message.contains(needle), "{needle} not in {}", f.message);
        }
    }

    const VERSION_OK: &str = "echo actionlint 1.7.12";

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_missing_binary_is_a_required_tool_failed() {
        let mut stage = sh_stage("lint", ToolParser::ActionlintJson, "true", VERSION_OK);
        stage.command = "frob-no-such-binary".to_owned();
        assert_tool_failed(
            &run_one(&stage),
            &["`lint`", "frob-no-such-binary", "not found"],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn an_unresolvable_pin_fails_the_version_probe_loudly() {
        let stage = sh_stage(
            "lint",
            ToolParser::ActionlintJson,
            "echo '[]'",
            "echo 'No solution found: actionlint-py==1.7.12' >&2; exit 2",
        );
        assert_tool_failed(
            &run_one(&stage),
            &[
                "version probe failed",
                "exit 2",
                "No solution found: actionlint-py==1.7.12",
            ],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn an_undeclared_exit_with_empty_output_names_status_and_stderr() {
        let stage = sh_stage(
            "lint",
            ToolParser::ActionlintJson,
            "echo boom >&2; exit 2",
            VERSION_OK,
        );
        assert_tool_failed(
            &run_one(&stage),
            &[
                "exited abnormally",
                "exit 2",
                "stderr: boom",
                "command `sh -c",
            ],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_findings_exit_with_no_output_is_a_failure() {
        let stage = sh_stage("lint", ToolParser::ActionlintJson, "exit 1", VERSION_OK);
        assert_tool_failed(
            &run_one(&stage),
            &["printed no output", "exit 1", "stderr: (empty)"],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn unparseable_output_is_a_failure() {
        let stage = sh_stage(
            "lint",
            ToolParser::ActionlintJson,
            "echo 'not json'",
            VERSION_OK,
        );
        assert_tool_failed(&run_one(&stage), &["parser cannot read", "exit 0"]);
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_clean_run_yields_no_finding() {
        for script in ["echo null", "echo '[]'", "echo '[]'; exit 1"] {
            let stage = sh_stage("lint", ToolParser::ActionlintJson, script, VERSION_OK);
            assert!(run_one(&stage).is_empty(), "{script}");
        }
    }

    // frob:tests crates/gob-check/src/tools.rs::excerpt
    #[test]
    fn stderr_is_escaped_and_capped() {
        let stage = sh_stage(
            "lint",
            ToolParser::ActionlintJson,
            "printf '\\033[31mred\\n' >&2; head -c 5000 /dev/zero | tr '\\0' x >&2; exit 2",
            VERSION_OK,
        );
        let found = run_one(&stage);
        let msg = &found[0].message;
        assert!(!msg.contains('\u{1b}') && !msg.contains('\n'), "{msg:?}");
        assert!(msg.len() < 900, "capped: {}", msg.len());
        let esc = escape("\u{1b}[31mx\n");
        assert_eq!(esc, "\\u{1b}[31mx\\n");
    }
}

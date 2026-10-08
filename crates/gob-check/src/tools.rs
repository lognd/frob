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

/// A frob finding produced from a tool result, with the tool's own id kept beside the mapped rule id.
#[derive(Debug, Clone)]
pub(crate) struct ToolFinding {
    /// The finding as the pipeline treats it.
    pub finding: Finding,
    /// The tool's own id (`source_rule`); `None` for a `TOOL001` about the stage itself.
    pub source_rule: Option<String>,
}

/// A result the tool itself suppressed (`# noqa`, `eslint-disable`, `#pragma warning disable`): input of EXC017.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ToolSuppression {
    /// Stage that ran the tool.
    pub stage: String,
    /// The tool's own id.
    pub source_rule: String,
    /// The frob rule the id maps to (`TOOL002` when unmapped).
    pub rule: RuleId,
    /// Repo-relative path the suppression applies to.
    pub path: String,
    /// SARIF suppression kind (`inSource` or `external`).
    pub kind: String,
    /// The author's justification, possibly empty.
    pub justification: String,
}

/// Everything the tool stages produced.
#[derive(Debug, Default)]
pub(crate) struct ToolRun {
    /// Findings (and stage failures) in stage order.
    pub findings: Vec<ToolFinding>,
    /// Natively suppressed results, which are not findings.
    pub suppressed: Vec<ToolSuppression>,
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
    /// The stage ran; these are its parsed output (empty without a parser).
    Done(ToolRun),
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
    /// The range from `start` to `end` (line, character column; end exclusive), or `None` when the file is unreadable.
    fn char_range(
        &mut self,
        root: &Path,
        path: &str,
        start: (u32, u32),
        end: (u32, u32),
    ) -> Option<TextRange> {
        let slot = self.slot(root, path);
        let (text, index) = slot?;
        let from = char_offset(text, index, start.0, start.1)?;
        let to = char_offset(text, index, end.0, end.1)
            .filter(|t| *t >= from)
            .unwrap_or(from);
        Some(TextRange::new(from, to))
    }

    fn slot(&mut self, root: &Path, path: &str) -> Option<&(String, LineIndex)> {
        self.0
            .entry(path.to_owned())
            .or_insert_with(|| {
                let text = std::fs::read_to_string(root.join(path)).ok()?;
                let index = LineIndex::new(&text).ok()?;
                Some((text, index))
            })
            .as_ref()
    }

    fn line_range(
        &mut self,
        root: &Path,
        path: &str,
        line: u32,
        col: u32,
        end: u32,
    ) -> Option<TextRange> {
        let slot = self.slot(root, path);
        let (_, index) = slot?;
        let start = index.offset(LineCol { line, col })?;
        let stop = index
            .offset(LineCol { line, col: end })
            .filter(|s| *s >= start)
            .unwrap_or(start);
        Some(TextRange::new(start, stop))
    }
}

/// The byte offset of 1-based character column `col` on `line`, clamped to the line's end.
fn char_offset(text: &str, index: &LineIndex, line: u32, col: u32) -> Option<TextSize> {
    let start = index.offset(LineCol { line, col: 1 })?;
    let rest = &text[start.to_usize()..];
    let line_text = rest.split('\n').next().unwrap_or_default();
    let skip = usize::try_from(col.saturating_sub(1)).unwrap_or(usize::MAX);
    let bytes = line_text
        .char_indices()
        .nth(skip)
        .map_or(line_text.len(), |(i, _)| i);
    Some(TextSize::new(u32::try_from(start.to_usize() + bytes).ok()?))
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
        RawRange::CharRange {
            line,
            col,
            end_line,
            end_col,
        } => indexes.char_range(root, path, (line, col), (end_line, end_col))?,
    };
    Some(Span::new(files.intern(path), range))
}

/// Turn the parsed findings of `stage` into frob findings (dropped ones omitted; suppressed ones set aside).
fn to_findings(
    root: &Path,
    stage: &ToolStage,
    raws: &[RawFinding],
    files: &mut FileInterner,
) -> ToolRun {
    let mut indexes = Indexes::default();
    let mut run = ToolRun::default();
    for raw in raws {
        let Some((rule, severity)) = classify(stage, raw) else {
            continue;
        };
        let path = normalize(root, &raw.path);
        if let Some(s) = &raw.suppressed {
            tracing::debug!(stage = %stage.name, tool_id = %raw.tool_id, rule = %rule, path = %path, kind = %s.kind, "tool result suppressed natively");
            run.suppressed.push(ToolSuppression {
                stage: stage.name.clone(),
                source_rule: raw.tool_id.clone(),
                rule,
                path,
                kind: s.kind.clone(),
                justification: s.justification.clone(),
            });
            continue;
        }
        let span = locate(root, files, &mut indexes, &path, &raw.range);
        let message = format!("{}/{}: {}", stage.name, raw.tool_id, raw.message);
        tracing::debug!(stage = %stage.name, tool_id = %raw.tool_id, rule = %rule, path = %path, located = span.is_some(), "tool finding");
        run.findings.push(ToolFinding {
            finding: Finding::new(rule, severity, span, message, &path),
            source_rule: Some(raw.tool_id.clone()),
        });
    }
    run
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
        ToolParser::ActionlintJson | ToolParser::Sarif => &[0, 1],
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
            .map_or(StageResult::Done(ToolRun::default()), StageResult::Problem);
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
            StageResult::Done(to_findings(root, stage, &raws, files))
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

/// Add a finding about the stage itself (no tool id) to `run`.
fn push_own(run: &mut ToolRun, finding: Finding) {
    run.findings.push(ToolFinding {
        finding,
        source_rule: None,
    });
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
) -> ToolRun {
    if stages.is_empty() {
        return ToolRun::default();
    }
    let id: RuleId = Tool001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let runner =
        Runner::new(Limits::default()).allow_tools(stages.iter().map(|s| s.command.clone()));
    let mut out = ToolRun::default();
    for stage in stages {
        let started = Instant::now();
        let result = execute(&runner, root, stage, files);
        timing.push(format!("tool:{}", stage.name), started.elapsed(), false);
        let unresolved = |message: String| {
            Finding::new(id.clone(), Severity::Unresolved, None, message, &stage.name)
        };
        match result {
            StageResult::Done(found) => {
                tracing::info!(stage = %stage.name, findings = found.findings.len(), suppressed = found.suppressed.len(), "tool stage passed");
                out.findings.extend(found.findings);
                out.suppressed.extend(found.suppressed);
            }
            StageResult::Lag(why) => {
                tracing::warn!(stage = %stage.name, %why, "tool schema lag; output discarded");
                push_own(
                    &mut out,
                    unresolved(format!(
                        "tool stage `{}` ({}) {why} (schema lag)",
                        stage.name, stage.command
                    )),
                );
            }
            StageResult::Missing(p) if stage.optional => {
                tracing::warn!(stage = %stage.name, problem = %p, "optional tool binary missing");
                push_own(
                    &mut out,
                    unresolved(format!(
                        "tool stage `{}` ({}) {p} (optional)",
                        stage.name, stage.command
                    )),
                );
            }
            StageResult::Failed(message) => {
                tracing::warn!(stage = %stage.name, %message, "tool stage failed to produce evidence");
                push_own(
                    &mut out,
                    unresolved(message).with_required(RequiredReason::ToolFailed {
                        stage: stage.name.clone(),
                    }),
                );
            }
            StageResult::Missing(p) => {
                tracing::warn!(stage = %stage.name, problem = %p, "tool binary missing");
                let message = failure(stage, &stage.args, &p, "not run", "");
                push_own(
                    &mut out,
                    unresolved(message).with_required(RequiredReason::ToolFailed {
                        stage: stage.name.clone(),
                    }),
                );
            }
            StageResult::Problem(p) if stage.fail_on_nonzero => {
                tracing::warn!(stage = %stage.name, problem = %p, "tool stage failed");
                push_own(
                    &mut out,
                    Finding::new(
                        id.clone(),
                        Severity::Error,
                        None,
                        format!("tool stage `{}` ({}) {p}", stage.name, stage.command),
                        &stage.name,
                    ),
                );
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
        }
    }

    fn run_one(stage: &ToolStage) -> Vec<Finding> {
        run_full(stage, Path::new("."))
            .findings
            .into_iter()
            .map(|t| t.finding)
            .collect()
    }

    fn run_full(stage: &ToolStage, root: &Path) -> ToolRun {
        let mut timing = Timing::default();
        let mut files = FileInterner::default();
        run_tools(root, std::slice::from_ref(stage), &mut timing, &mut files)
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

    // frob:tests crates/gob-check/src/tools.rs::run_tools
    #[test]
    fn a_missing_binary_is_a_required_tool_failed() {
        let mut stage = sh_stage("lint", ToolParser::ActionlintJson, "true", VERSION_OK);
        stage.command = "frob-no-such-binary".to_owned();
        assert_tool_failed(
            &run_one(&stage),
            &["`lint`", "frob-no-such-binary", "not found"],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::run_tools
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

    // frob:tests crates/gob-check/src/tools.rs::run_tools
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

    // frob:tests crates/gob-check/src/tools.rs::run_tools
    #[test]
    fn a_findings_exit_with_no_output_is_a_failure() {
        let stage = sh_stage("lint", ToolParser::ActionlintJson, "exit 1", VERSION_OK);
        assert_tool_failed(
            &run_one(&stage),
            &["printed no output", "exit 1", "stderr: (empty)"],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::run_tools
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

    // frob:tests crates/gob-check/src/tools.rs::run_tools
    #[test]
    fn a_clean_run_yields_no_finding() {
        for script in ["echo null", "echo '[]'", "echo '[]'; exit 1"] {
            let stage = sh_stage("lint", ToolParser::ActionlintJson, script, VERSION_OK);
            assert!(run_one(&stage).is_empty(), "{script}");
        }
    }

    const ESLINT_SARIF: &str = include_str!("../tests/fixtures/sarif-eslint-9.39.5.json");

    fn sarif_stage(script: &str) -> ToolStage {
        let mut stage = sh_stage("lint", ToolParser::Sarif, script, VERSION_OK);
        stage.min_version = None;
        stage.max_version = None;
        stage.version_args = None;
        stage
            .id_map
            .insert("eqeqeq".to_owned(), "NEAT002".to_owned());
        stage
    }

    // frob:tests crates/gob-check/src/tools.rs::run_tools
    #[test]
    fn sarif_results_map_keep_source_rule_and_set_suppressed_aside() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(
            dir.path().join("a.js"),
            "debugger;\nvar s = '\u{e9}\u{e9}'; if (s == 1) {}\n",
        )
        .expect("write");
        let log =
            ESLINT_SARIF.replace("/work/repo/a.js", &format!("{}/a.js", dir.path().display()));
        std::fs::write(dir.path().join("out.sarif"), log).expect("write");
        let run = run_full(&sarif_stage("cat out.sarif; exit 1"), dir.path());
        let got: Vec<_> = run
            .findings
            .iter()
            .map(|t| {
                (
                    t.finding.rule.to_string(),
                    t.source_rule.clone().unwrap_or_default(),
                )
            })
            .collect();
        assert_eq!(
            got,
            [
                ("TOOL002".to_owned(), "no-debugger".to_owned()),
                ("NEAT002".to_owned(), "eqeqeq".to_owned()),
            ],
            "unknown id falls back to TOOL002; the mapped one keeps its tool id"
        );
        assert!(run.findings[1].finding.message.starts_with("lint/eqeqeq: "));
        assert!(run.findings.iter().all(|t| t.finding.span.is_some()));
        assert_eq!(run.suppressed.len(), 1);
        let s = &run.suppressed[0];
        assert_eq!(
            (s.source_rule.as_str(), s.kind.as_str()),
            ("eqeqeq", "inSource")
        );
        assert_eq!(s.rule.as_str(), "NEAT002");
        assert_eq!(s.path, "a.js");
    }

    // frob:tests crates/gob-check/src/tools.rs::char_offset
    #[test]
    fn character_columns_become_byte_offsets() {
        let text = "ab\n\u{e9}\u{e9}x\n";
        let index = LineIndex::new(text).expect("index");
        assert_eq!(char_offset(text, &index, 2, 3), Some(TextSize::new(3 + 4)));
        assert_eq!(
            char_offset(text, &index, 2, 99),
            Some(TextSize::new(3 + 5)),
            "clamped to the line end"
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::run_tools
    #[test]
    fn unreadable_sarif_is_a_required_tool_failed() {
        for script in ["echo 'not sarif'", "echo '{}'", "exit 2", "exit 1"] {
            let found = run_one(&sarif_stage(script));
            assert_tool_failed(&found, &["`lint`"]);
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

//! `[[check.tool]]` stages: external commands run after the built-in rules.
//!
//! A stage with a `parser` also turns the tool's JSON output into findings
//! with real spans and CI ids; a stage whose tool version is outside its
//! configured range yields one non-required Unresolved finding instead.

use std::collections::HashMap;
use std::path::Path;
use std::time::{Duration, Instant};

use gob_exec::{
    ExecError, Limits, Outcome, Output, ProcessPack, Program, Runner, Spec, resolve_pack,
};
use gob_rules::{Finding, RequiredReason, Rule, RuleId, Severity};
use gob_text::{FileInterner, LineCol, LineIndex, Span, TextRange, TextSize};

use crate::config::{FILE_TOKEN, ToolParser, ToolStage};
use crate::packages::Affected;
use crate::prereq::Prereqs;
use crate::report::Timing;
use crate::rules::Tool001;
use crate::tool_parse::{
    RawFinding, RawRange, VersionVerdict, check_version, classify, default_version_args,
    find_version, parse,
};
use crate::version_bump::Gate;

/// A store of finished tool-stage results keyed by the hash of everything the stage reads.
///
/// Payloads are opaque to the store. A failed `store` only costs a later re-run, so it reports nothing.
pub trait ToolMemo: std::fmt::Debug + Send + Sync {
    /// The payload recorded under `key`, if any.
    fn load(&self, key: &str) -> Option<String>;
    /// Record `payload` under `key`.
    fn store(&self, key: &str, payload: &str);
}

/// Decides whether a resolved tool program may run (security.md section 2.4, I11).
///
/// The implementor owns the trust store or base-ref lock lookup; this crate only asks.
pub trait ToolTrust: std::fmt::Debug + Send + Sync {
    /// True when the binary at `pack.path` with `pack.digest` is trusted for this repository.
    fn is_trusted(&self, pack: &ProcessPack) -> bool;
    /// The command a user runs to trust `pack`, named in the remedy of an untrusted stage.
    fn trust_command(&self, pack: &ProcessPack) -> String;
}

/// Bumped when the key recipe or the payload shape changes, so old records never match.
const MEMO_VERSION: &str = "tool-memo-v1";

/// Feed one tagged, length-prefixed field to `h` so adjacent values cannot run together.
fn field(h: &mut blake3::Hasher, tag: &str, value: &[u8]) {
    h.update(tag.as_bytes());
    h.update(&(value.len() as u64).to_le_bytes());
    h.update(value);
}

/// Files that are implicit inputs of every stage: its configuration (frob:ticket 01M4HKDJDC1ZMQRHY83TFM9EYJ).
const IMPLICIT_INPUTS: &[&str] = &["frob.toml"];

/// The memo key of `stage`: its command line and version window plus the content of every file its `inputs` match.
///
/// `None` when the stage declares no inputs (what it reads is unknown) or a glob does not parse.
/// No process is spawned: the key is a pure function of the stage and the file digests.
fn memo_key(stage: &ToolStage, files: &[gob_walk::FileEntry]) -> Option<String> {
    if stage.inputs.is_empty() {
        return None;
    }
    let mut builder = globset::GlobSetBuilder::new();
    for glob in &stage.inputs {
        builder.add(globset::Glob::new(glob).ok()?);
    }
    let set = builder.build().ok()?;
    let mut h = blake3::Hasher::new();
    field(&mut h, "v", MEMO_VERSION.as_bytes());
    field(&mut h, "command", stage.command.as_bytes());
    field(&mut h, "parser", format!("{:?}", stage.parser).as_bytes());
    for a in &stage.args {
        field(&mut h, "arg", a.as_bytes());
    }
    for a in stage.version_args.iter().flatten() {
        field(&mut h, "varg", a.as_bytes());
    }
    field(
        &mut h,
        "min",
        stage.min_version.as_deref().unwrap_or("").as_bytes(),
    );
    field(
        &mut h,
        "max",
        stage.max_version.as_deref().unwrap_or("").as_bytes(),
    );
    for f in files
        .iter()
        .filter(|f| set.is_match(&f.path) || IMPLICIT_INPUTS.contains(&f.path.as_str()))
    {
        field(&mut h, "file", f.path.as_bytes());
        field(&mut h, "digest", f.digest.as_bytes());
    }
    Some(h.finalize().to_hex().to_string())
}

/// Trailing characters of a tool's output quoted in the finding.
const TAIL: usize = 400;

fn tail(text: &str) -> String {
    let t = text.trim();
    let skip = t.chars().count().saturating_sub(TAIL);
    t.chars().skip(skip).collect()
}

/// Escape `text` for one line of a finding: control characters become visible escapes.
pub(crate) fn escape(text: &str) -> String {
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

// frob:ticket 01M4GKCBT6MW3BHED91718ANQ7
/// True when a stderr line looks like the tool reporting a failure rather than progress.
fn error_looking(line: &str) -> bool {
    let l = line.to_ascii_lowercase();
    ["error", "fatal", "panic", "failed", "cannot", "no such"]
        .iter()
        .any(|k| l.contains(k))
}

// frob:ticket 01M4GKCBT6MW3BHED91718ANQ7
/// The escaped, capped excerpt of a stream, or `(empty)`.
///
/// Output that fits the cap is quoted whole. Longer output shows the last two
/// error-looking lines and the last two lines, so leading INFO noise is dropped.
pub(crate) fn excerpt(text: &str) -> String {
    let t = text.trim();
    if t.is_empty() {
        return "(empty)".to_owned();
    }
    if t.chars().count() <= TAIL {
        return escape(t);
    }
    let lines: Vec<&str> = t.lines().map(str::trim).filter(|l| !l.is_empty()).collect();
    let mut keep: Vec<usize> = lines
        .iter()
        .enumerate()
        .filter(|(_, l)| error_looking(l))
        .map(|(i, _)| i)
        .rev()
        .take(2)
        .collect();
    keep.extend(lines.len().saturating_sub(2)..lines.len());
    keep.sort_unstable();
    keep.dedup();
    let picked: Vec<String> = keep
        .iter()
        .map(|&i| {
            let l = lines[i];
            if l.chars().count() > 90 {
                format!("{}...", l.chars().take(90).collect::<String>())
            } else {
                l.to_owned()
            }
        })
        .collect();
    escape(&tail(&picked.join(" | ")))
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
pub(crate) fn status_text(o: &Output) -> String {
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
pub(crate) struct ToolOutput {
    /// Findings (and stage failures) in stage order.
    pub findings: Vec<ToolFinding>,
    /// Natively suppressed results, which are not findings.
    pub suppressed: Vec<ToolSuppression>,
}

/// What running one stage produced.
enum StageResult {
    /// The binary was not found.
    Missing(String),
    /// The program is not trusted (or resolves inside the work tree); the stage did not run.
    Untrusted(String),
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

/// Run `stage` with `args`: through the verified `pack` when there is one, else by name.
pub(crate) fn launch(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
    pack: Option<&ProcessPack>,
    args: Vec<String>,
) -> Result<Output, ExecError> {
    match pack {
        Some(pack) => runner.run_pack(
            pack,
            args,
            Some(root.to_path_buf()),
            Duration::from_secs(stage.timeout_secs),
        ),
        None => runner.run(&spec(root, stage, args)),
    }
}

/// Resolve and vet the stage's program under `trust`; `Err` is the stage result that replaces the run.
///
/// Refuses a program inside the work tree, and an unknown digest is Unresolved untrusted with the
/// trust command. `None` trust is the unenforced legacy path (a caller that has no trust source).
fn vet(
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
) -> Result<Option<ProcessPack>, StageResult> {
    let search = std::env::var_os("PATH").unwrap_or_default();
    vet_on(root, stage, trust, &search)
}

/// [`vet`] against an explicit `PATH` list.
fn vet_on(
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
    search: &std::ffi::OsStr,
) -> Result<Option<ProcessPack>, StageResult> {
    let Some(trust) = trust else {
        return Ok(None);
    };
    match resolve_pack(&stage.command, root, search) {
        Ok(pack) if trust.is_trusted(&pack) => {
            tracing::debug!(stage = %stage.name, path = %pack.path.display(), "tool program trusted");
            Ok(Some(pack))
        }
        Ok(pack) => {
            tracing::warn!(stage = %stage.name, path = %pack.path.display(), digest = %pack.digest, "tool program untrusted; not run");
            Err(StageResult::Untrusted(format!(
                "tool stage `{}` ({}) is untrusted: {} {} was not run; run `{}` to trust it",
                stage.name,
                stage.command,
                pack.path.display(),
                pack.digest,
                trust.trust_command(&pack)
            )))
        }
        Err(err @ ExecError::NotFound { .. }) => {
            Err(StageResult::Missing(format!("could not run: {err}")))
        }
        Err(err) => {
            tracing::warn!(stage = %stage.name, %err, "tool program refused");
            Err(StageResult::Untrusted(format!(
                "tool stage `{}` ({}) was refused and not run: {err}",
                stage.name, stage.command
            )))
        }
    }
}

/// Repo-relative, forward-slash form of a path a tool printed.
fn normalize(root: &Path, printed: &str) -> String {
    let unified = printed.replace('\\', "/");
    let root_text = gob_path::forward_slashes(root);
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

    #[allow(
        clippy::disallowed_methods,
        reason = "external tool locations name on-disk files the tool read, which may lie outside the walk"
    )]
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
) -> ToolOutput {
    let mut indexes = Indexes::default();
    let mut run = ToolOutput::default();
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
    pack: Option<&ProcessPack>,
) -> Result<Option<String>, StageResult> {
    let Some(args) = stage
        .version_args
        .clone()
        .or_else(|| default_version_args(stage.parser))
    else {
        return Ok(None);
    };
    match launch(runner, root, stage, pack, args.clone()) {
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
        // frob:ticket 01M4D90ZDHTSR1JX06Z17FNR3C
        // ruff exits 1 when it reports violations and 2 on abnormal termination.
        ToolParser::ActionlintJson
        | ToolParser::Sarif
        | ToolParser::RuffJson
        | ToolParser::TyGitlab
        | ToolParser::PyrightJson
        | ToolParser::EslintJson
        | ToolParser::FormatterList
        | ToolParser::SemverChecksText
        | ToolParser::GriffeText
        | ToolParser::ApiExtractorText
        | ToolParser::RoslynSarif => &[0, 1],
        // frob:ticket 01M4CXSY224VNMR2R5Q69D9E89
        // tsc exits 1 on diagnostics with emit skipped and 2 on diagnostics with emit generated.
        ToolParser::TscText => &[0, 1, 2],
        // Lints under `-D warnings` and compile errors both exit 101; the diagnostics decide.
        ToolParser::CargoJson => &[0, 101],
        // frob:ticket 01M4D95VS2KPK91REEZ8KA74BB
        // frob:ticket 01M4D92HMPWHFY5WGGY3KGFTNE
        // typos exits 2 when it reports typos.
        ToolParser::StylelintJson | ToolParser::TyposJson => &[0, 2],
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

/// Exit statuses of `stage` that are not a tool error: its definition's classes, else the parser's.
fn stage_normal_exits(stage: &ToolStage) -> Vec<i32> {
    stage
        .def
        .as_deref()
        .and_then(crate::tool_def::lookup)
        .map(crate::tool_def::ToolDef::normal_exits)
        .filter(|e| !e.is_empty())
        .unwrap_or_else(|| normal_exits(stage.parser).to_vec())
}

/// `stage` with the definition's argv variant for the probed `version`, when its `def` has one that matches.
///
/// Only a stage still on the definition's default argv is swapped; an explicit `args` always wins.
fn with_variant(stage: &ToolStage, version: Option<&str>) -> ToolStage {
    let Some(def) = stage.def.as_deref().and_then(crate::tool_def::lookup) else {
        return stage.clone();
    };
    let mut out = stage.clone();
    if stage.args == def.default_args() {
        out.args = def.args_for(version);
    }
    out
}

// frob:ticket 01M4D94J5J2TZEXTB8GH36992B
// frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
/// The text a parser reads: formatters, cargo-semver-checks, griffe and api-extractor report on stderr too.
fn report_text(stage: &ToolStage, output: &gob_exec::Output) -> String {
    let both = matches!(
        stage.parser,
        ToolParser::FormatterList
            | ToolParser::SemverChecksText
            | ToolParser::GriffeText
            | ToolParser::ApiExtractorText
    );
    if both {
        format!("{}\n{}", output.stdout, output.stderr)
    } else {
        output.stdout.clone()
    }
}

/// The `uv sync` line a uv-run `stage` needs before it can run in `root`, when the checkout has no `.venv`.
///
/// `None` unless the stage runs `uv run` against a project (a `pyproject.toml` in `root`, no
/// `--no-project`/`--isolated`/`--script`), the checkout has no virtual environment yet, and the
/// environment location is not redirected by `UV_PROJECT_ENVIRONMENT`. It is `uv sync --frozen`
/// when a lockfile exists so the sync never rewrites it, else `uv sync`.
// frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
#[must_use]
pub(crate) fn uv_sync_line(root: &Path, stage: &ToolStage) -> Option<String> {
    if stage.command != "uv" || std::env::var_os("UV_PROJECT_ENVIRONMENT").is_some() {
        return None;
    }
    let mut words = stage.args.iter().filter(|a| !a.starts_with('-'));
    if words.next().map(String::as_str) != Some("run") {
        return None;
    }
    let opts_out = ["--no-project", "--isolated", "--script"];
    if stage.args.iter().any(|a| opts_out.contains(&a.as_str())) {
        return None;
    }
    if !root.join("pyproject.toml").is_file() || root.join(".venv").join("pyvenv.cfg").is_file() {
        return None;
    }
    Some(if root.join("uv.lock").is_file() {
        "uv sync --frozen".to_owned()
    } else {
        "uv sync".to_owned()
    })
}

/// Run the prerequisites `stage` needs, syncing a missing uv environment first; `Err` is the Unresolved message.
// frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
fn ensure_prereqs(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
    prereqs: &Prereqs,
) -> Result<(), String> {
    let Some(line) = uv_sync_line(root, stage) else {
        return prereqs.ensure(runner, root, stage, trust);
    };
    tracing::info!(stage = %stage.name, line, "uv environment missing; syncing first");
    let mut with_sync = stage.clone();
    with_sync.requires.insert(0, line);
    prereqs.ensure(runner, root, &with_sync, trust)
}

fn execute(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
    prereqs: &Prereqs,
) -> StageResult {
    let pack = match vet(root, stage, trust) {
        Ok(pack) => pack,
        Err(result) => return result,
    };
    // frob:ticket 01M4GKDSGA7ZSF99T7M5S319B4
    // frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
    // Build output the stage reads is produced first; a failed prerequisite is Unresolved, never a verdict.
    // A uv-run stage in a checkout without `.venv` syncs the environment as its first prerequisite.
    if let Err(message) = ensure_prereqs(runner, root, stage, trust, prereqs) {
        return StageResult::Failed(message);
    }
    let pack = pack.as_ref();
    let parsed = stage.parser != ToolParser::None;
    let variant_stage;
    let mut stage = stage;
    if parsed {
        match tool_version(runner, root, stage, pack) {
            Err(result) => return result,
            Ok(version) => {
                tracing::info!(stage = %stage.name, version = version.as_deref().unwrap_or("unknown"), "tool version");
                if let VersionVerdict::Lag(why) = check_version(stage, version.as_deref()) {
                    return StageResult::Lag(why);
                }
                variant_stage = with_variant(stage, version.as_deref());
                stage = &variant_stage;
            }
        }
    }
    let output = match launch(runner, root, stage, pack, stage.args.clone()) {
        Ok(o) => o,
        Err(err @ ExecError::NotFound { .. }) => {
            return StageResult::Missing(format!("could not run: {err}"));
        }
        // Any other run error (spawn or write I/O such as ENOSPC) means the gate never ran:
        // it is required evidence missing, never a pass (frob:ticket 01M4M27E8E0DK7XAQ2D7T0Q8TR).
        Err(err) => {
            tracing::error!(stage = %stage.name, %err, "tool stage could not run");
            return StageResult::Failed(failure(
                stage,
                &stage.args,
                &format!("could not run ({err})"),
                "not run",
                "",
            ));
        }
    };
    if !parsed {
        return abnormal(&output, stage)
            .map_or(StageResult::Done(Vec::new()), StageResult::Problem);
    }
    // A parsed stage exits nonzero when it has findings; only an undeclared status or unreadable output is a failure.
    let declared =
        matches!(output.status, Outcome::Exited(c) if stage_normal_exits(stage).contains(&c));
    if !declared {
        return StageResult::Failed(failure(
            stage,
            &stage.args,
            "exited abnormally",
            &status_text(&output),
            &output.stderr,
        ));
    }
    let text = report_text(stage, &output);
    if output.status != Outcome::Exited(0) && text.trim().is_empty() {
        return StageResult::Failed(failure(
            stage,
            &stage.args,
            "printed no output despite a findings exit",
            &status_text(&output),
            &output.stderr,
        ));
    }
    match parse(stage.parser, &text) {
        Ok(raws) => {
            tracing::info!(stage = %stage.name, findings = raws.len(), "tool output parsed");
            // frob:ticket 01M5HYTAQEYA72YHZWGHPACR52
            // griffe cannot see the package version, so a version bump that permits breakage is applied here.
            if stage.parser == ToolParser::GriffeText && !raws.is_empty() {
                return match crate::version_bump::gate_for(root, &stage.args) {
                    Gate::Allowed => StageResult::Done(Vec::new()),
                    Gate::Violation => StageResult::Done(raws),
                    Gate::Unresolved(why) => StageResult::Failed(failure(
                        stage,
                        &stage.args,
                        &format!("reported breaking changes but {why}"),
                        &status_text(&output),
                        &output.stderr,
                    )),
                };
            }
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

/// [`vet`] with the refusal reduced to its message, for callers that only need the reason.
pub(crate) fn vet_message(
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
) -> Result<Option<ProcessPack>, String> {
    vet(root, stage, trust).map_err(|result| match result {
        StageResult::Missing(m)
        | StageResult::Untrusted(m)
        | StageResult::Failed(m)
        | StageResult::Problem(m)
        | StageResult::Lag(m) => m,
        StageResult::Done(_) => String::new(),
    })
}

// frob:ticket 01M4D94J5J2TZEXTB8GH36992B
/// Run `stage`'s fix command `args` under the same trust gate as its check; `Err` is the reason it did not complete.
pub(crate) fn run_fix(
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
    args: &[String],
) -> Result<(), String> {
    let pack = vet_message(root, stage, trust)?;
    let runner = Runner::new(Limits::default()).allow_tools([stage.command.clone()]);
    match launch(&runner, root, stage, pack.as_ref(), args.to_vec()) {
        Ok(o) if o.status == Outcome::Exited(0) => {
            tracing::info!(stage = %stage.name, "fix command finished");
            Ok(())
        }
        Ok(o) => Err(failure(
            stage,
            args,
            "fix command failed",
            &status_text(&o),
            &o.stderr,
        )),
        Err(err) => Err(failure(
            stage,
            args,
            &format!("fix command could not run ({err})"),
            "not run",
            "",
        )),
    }
}

/// Add a finding about the stage itself (no tool id) to `run`.
fn push_own(run: &mut ToolOutput, finding: Finding) {
    run.findings.push(ToolFinding {
        finding,
        source_rule: None,
    });
}

/// True when `stage` declares inputs and none of the scoped `files` matches one of them.
///
/// A stage without inputs, or an input glob that does not parse, never counts as untouched:
/// the stage runs (frob:ticket 01M4GRW6NH23YPTSAQERDRSZC5).
fn untouched(stage: &ToolStage, files: &std::collections::BTreeSet<String>) -> bool {
    if stage.inputs.is_empty() || files.iter().any(|f| IMPLICIT_INPUTS.contains(&f.as_str())) {
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

/// The argument token a stage uses to ask for the affected cargo packages.
const PACKAGES_TOKEN: &str = "{packages}";

/// `stage` with its `{packages}` token expanded for `affected`, or `None` when no package is affected.
///
/// Unscoped runs and [`Affected::Everything`] expand to the stage's `unscoped_packages`; a named set
/// becomes one `-p <name>` pair per package. A stage without the token is returned unchanged.
fn expand_packages(stage: &ToolStage, affected: Option<&Affected>) -> Option<ToolStage> {
    if !stage.args.iter().any(|a| a == PACKAGES_TOKEN) {
        return Some(stage.clone());
    }
    let replacement: Vec<String> = match affected {
        Some(Affected::Packages(names)) if names.is_empty() => return None,
        Some(Affected::Packages(names)) => names
            .iter()
            .flat_map(|n| ["-p".to_owned(), n.clone()])
            .collect(),
        Some(Affected::Everything) | None => stage.unscoped_packages.clone(),
    };
    let mut out = stage.clone();
    out.args = stage
        .args
        .iter()
        .flat_map(|a| {
            if a == PACKAGES_TOKEN {
                replacement.clone()
            } else {
                vec![a.clone()]
            }
        })
        .collect();
    Some(out)
}

/// `stage` with each `{file}` token replaced by `./<path>`, or the refusal when `path` is not tracked.
///
/// The `./` prefix keeps a file named `-rf` from being read as an option (security.md section 2.4).
///
/// # Errors
///
/// A message naming the stage and the path when `path` is outside `tracked`.
// frob:ticket 01M3ZX7VJE22Y68R184Y9WQC2N
#[allow(
    dead_code,
    reason = "no stage runs per file yet; the typed expander lands first"
)]
pub(crate) fn expand_file(
    stage: &ToolStage,
    path: &str,
    tracked: &std::collections::BTreeSet<String>,
) -> Result<ToolStage, String> {
    if !stage.args.iter().any(|a| a == FILE_TOKEN) {
        return Ok(stage.clone());
    }
    if !tracked.contains(path) {
        tracing::warn!(stage = %stage.name, path, "tool stage refused: path not tracked");
        return Err(format!(
            "tool stage `{}` refused: `{path}` is not a tracked path",
            stage.name
        ));
    }
    let mut out = stage.clone();
    out.args = stage
        .args
        .iter()
        .map(|a| {
            if a == FILE_TOKEN {
                format!("./{path}")
            } else {
                a.clone()
            }
        })
        .collect();
    Ok(out)
}

/// The stages a run executes: all of them unscoped, else those whose declared inputs the scope touches, with `{packages}` expanded.
pub(crate) fn applicable_stages(
    stages: &[ToolStage],
    scope_files: Option<&std::collections::BTreeSet<String>>,
    affected: Option<&Affected>,
) -> Vec<ToolStage> {
    stages
        .iter()
        .filter_map(|stage| {
            if scope_files.is_some_and(|files| untouched(stage, files)) {
                tracing::info!(stage = %stage.name, "tool stage skipped: the scope touches none of its inputs");
                return None;
            }
            let expanded = expand_packages(stage, affected);
            if expanded.is_none() {
                tracing::info!(stage = %stage.name, "tool stage skipped: no cargo package is affected");
            }
            expanded
        })
        .collect()
}

/// One stage's outcome and wall time, as a worker thread produced it.
type Finished = (usize, StageResult, Duration, bool);

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
    // `env VAR=x cargo ...` wraps cargo to set an env var and shares cargo's build lock
    // (frob:ticket 01M4DYPEJYZSKH9VDD1AJKH9PM).
    let wraps_cargo = stage.command == "env" && stage.args.iter().any(|a| a == "cargo");
    if stage.command == "cargo" || wraps_cargo {
        "cargo".to_owned()
    } else {
        format!("stage-{index}")
    }
}

/// Start `stages` on background threads and return at once; `None` when there are no stages.
pub(crate) fn start_tools(
    root: &Path,
    stages: &[ToolStage],
    memo: Option<&std::sync::Arc<dyn ToolMemo>>,
    trust: Option<&std::sync::Arc<dyn ToolTrust>>,
    setup: &[String],
) -> Option<ToolRun> {
    if stages.is_empty() {
        return None;
    }
    // One walk hashes the inputs for every stage; it is skipped when nothing can be memoized.
    let digests = memo
        .filter(|_| stages.iter().any(|s| !s.inputs.is_empty()))
        .and_then(|_| {
            let config = gob_walk::WalkConfig {
                size_cap: u64::MAX,
                ..gob_walk::WalkConfig::default()
            };
            match gob_walk::walk(root, &config) {
                Ok(w) => Some(w.files),
                Err(e) => {
                    tracing::warn!(error = %e, "tool memo disabled: the input walk failed");
                    None
                }
            }
        });
    let prereqs = std::sync::Arc::new(Prereqs::new(setup));
    let runner = std::sync::Arc::new(
        Runner::new(Limits::default()).allow_tools(
            stages
                .iter()
                .map(|s| s.command.clone())
                .chain(prereqs.programs(stages)),
        ),
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
            let prereqs = std::sync::Arc::clone(&prereqs);
            let root = root.to_path_buf();
            let work: Vec<(usize, ToolStage, Option<String>)> = members
                .into_iter()
                .map(|i| {
                    let key = digests.as_deref().and_then(|f| memo_key(&stages[i], f));
                    (i, stages[i].clone(), key)
                })
                .collect();
            let memo = memo.cloned();
            let trust = trust.cloned();
            std::thread::spawn(move || {
                tracing::debug!(group = %key, "tool group running");
                work.into_iter()
                    .map(|(i, stage, key)| {
                        let started = Instant::now();
                        let hit = memo
                            .as_ref()
                            .zip(key.as_deref())
                            .and_then(|(m, k)| m.load(k))
                            .and_then(|p| serde_json::from_str::<Vec<RawFinding>>(&p).ok());
                        if let Some(raws) = hit {
                            tracing::info!(stage = %stage.name, "tool stage reused a recorded pass");
                            return (i, StageResult::Done(raws), started.elapsed(), true);
                        }
                        let result = execute(&runner, &root, &stage, trust.as_deref(), &prereqs);
                        // Only a stage that ran to a verdict is recorded; failures are never reused.
                        if let (StageResult::Done(raws), Some(m), Some(k)) =
                            (&result, memo.as_ref(), key.as_deref())
                            && let Ok(payload) = serde_json::to_string(raws)
                        {
                            m.store(k, &payload);
                        }
                        (i, result, started.elapsed(), false)
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
    pub(crate) fn finish(self, timing: &mut Timing, files: &mut FileInterner) -> ToolOutput {
        let mut done: Vec<Finished> = Vec::with_capacity(self.stages.len());
        for worker in self.workers {
            match worker.join() {
                Ok(mut part) => done.append(&mut part),
                Err(panic) => std::panic::resume_unwind(panic),
            }
        }
        done.sort_by_key(|(i, _, _, _)| *i);
        let id: RuleId = Tool001
            .meta()
            .rule_id()
            .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
        let mut out = ToolOutput::default();
        for (index, result, took, cached) in done {
            let stage = &self.stages[index];
            let suffix = if cached { " (cached)" } else { "" };
            timing.push(format!("tool:{}{suffix}", stage.name), took, false);
            let part = stage_findings(&self.root, &id, stage, result, files);
            out.findings.extend(part.findings);
            out.suppressed.extend(part.suppressed);
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
) -> ToolOutput {
    let mut out = ToolOutput::default();
    {
        let unresolved = |message: String| {
            Finding::new(id.clone(), Severity::Unresolved, None, message, &stage.name)
        };
        match result {
            StageResult::Done(raws) => {
                let found = to_findings(root, stage, &raws, files);
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
            StageResult::Untrusted(message) => {
                tracing::warn!(stage = %stage.name, %message, "tool stage untrusted; not run");
                push_own(
                    &mut out,
                    unresolved(message).with_required(RequiredReason::ToolFailed {
                        stage: stage.name.clone(),
                    }),
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

#[allow(
    clippy::disallowed_methods,
    reason = "tests read the log a fake tool wrote to a temp dir"
)]
#[cfg(test)]
mod tests {

    /// Trusts exactly the digests it was given.
    #[cfg(unix)]
    #[derive(Debug)]
    struct Digests(Vec<String>);

    #[cfg(unix)]
    impl ToolTrust for Digests {
        fn is_trusted(&self, pack: &ProcessPack) -> bool {
            self.0.contains(&pack.digest)
        }
        fn trust_command(&self, pack: &ProcessPack) -> String {
            format!("frob trust --tool {}", pack.name)
        }
    }

    #[cfg(unix)]
    fn script(dir: &Path, name: &str, body: &str) {
        use std::os::unix::fs::PermissionsExt;
        std::fs::create_dir_all(dir).expect("mkdir");
        let p = dir.join(name);
        std::fs::write(&p, body).expect("write");
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    }

    #[cfg(unix)]
    fn named_stage(command: &str) -> ToolStage {
        let mut stage = sh_stage("t", ToolParser::None, "true", "true");
        stage.command = command.to_owned();
        stage.args = Vec::new();
        stage
    }

    // frob:tests crates/gob-check/src/tools.rs::vet_on
    #[cfg(unix)]
    #[test]
    fn a_program_resolving_inside_the_work_tree_is_refused() {
        let root = tempfile::tempdir().expect("root");
        script(&root.path().join("bin"), "tool", "#!/bin/sh\n");
        let stage = named_stage("tool");
        let trust = Digests(Vec::new());
        let search = root.path().join("bin");
        let Err(StageResult::Untrusted(msg)) =
            vet_on(root.path(), &stage, Some(&trust), search.as_os_str())
        else {
            panic!("expected a refusal");
        };
        assert!(msg.contains("inside the work tree"), "{msg}");
    }

    // frob:tests crates/gob-check/src/tools.rs::vet_on
    // frob:tests crates/gob-check/src/tools.rs::stage_findings
    #[cfg(unix)]
    #[test]
    fn an_untrusted_stage_is_unresolved_with_the_trust_command_and_a_changed_digest_drops_trust() {
        let root = tempfile::tempdir().expect("root");
        let out = tempfile::tempdir().expect("out");
        script(out.path(), "tool", "#!/bin/sh\n");
        let stage = named_stage("tool");
        let untrusted = Digests(Vec::new());
        let Err(result) = vet_on(
            root.path(),
            &stage,
            Some(&untrusted),
            out.path().as_os_str(),
        ) else {
            panic!("untrusted must not run");
        };
        let id: RuleId = Tool001.meta().rule_id().expect("id");
        let mut files = FileInterner::default();
        let found = stage_findings(root.path(), &id, &stage, result, &mut files);
        let f = &found.findings[0].finding;
        assert_eq!(f.severity, Severity::Unresolved);
        assert!(f.message.contains("untrusted"), "{}", f.message);
        assert!(
            f.message.contains("frob trust --tool tool"),
            "{}",
            f.message
        );

        // Trust the current digest, then change the binary: trust is gone.
        let pack = resolve_pack("tool", root.path(), out.path().as_os_str()).expect("pack");
        let trusted = Digests(vec![pack.digest.clone()]);
        assert!(matches!(
            vet_on(root.path(), &stage, Some(&trusted), out.path().as_os_str()),
            Ok(Some(_))
        ));
        script(out.path(), "tool", "#!/bin/sh\necho swapped\n");
        assert!(matches!(
            vet_on(root.path(), &stage, Some(&trusted), out.path().as_os_str()),
            Err(StageResult::Untrusted(_))
        ));
    }
    use super::*;

    // frob:tests crates/gob-check/src/tools.rs::normalize
    // frob:ticket 01M3ZX7VJE22Y68R184Y9WQC2N
    #[test]
    fn a_file_placeholder_renders_tracked_paths_and_refuses_others() {
        if !gob_exec::require_sh("a_file_placeholder_renders_tracked_paths_and_refuses_others") {
            return;
        }
        let mut stage = sh_stage("t", ToolParser::None, "", "");
        stage.args = vec!["--".to_owned(), FILE_TOKEN.to_owned()];
        let tracked: std::collections::BTreeSet<String> = ["a.rs".to_owned()].into();
        let ok = expand_file(&stage, "a.rs", &tracked).expect("tracked");
        assert_eq!(ok.args, ["--", "./a.rs"]);
        let err = expand_file(&stage, "../etc/passwd", &tracked).expect_err("outside");
        assert!(
            err.contains("`t`") && err.contains("not a tracked path"),
            "{err}"
        );
    }

    // frob:ticket 01M3ZX7VJE22Y68R184Y9WQC2N
    #[test]
    fn shell_strings_and_missing_templates_are_cfg_errors_naming_the_stage() {
        let dir = tempfile::tempdir().expect("tmp");
        let load = |toml: &str| {
            std::fs::write(dir.path().join("frob.toml"), toml).expect("write");
            crate::config::CheckTable::load(dir.path(), "frob")
        };
        for toml in [
            "[[check.tool]]\nname = \"s1\"\ncommand = \"cargo fmt && ls\"\nargs = []\n",
            "[[check.tool]]\nname = \"s1\"\ncommand = \"cargo\"\n",
        ] {
            let e = load(toml).expect_err("refused").to_string();
            assert!(e.contains("stage `s1`"), "{e}");
        }
        assert!(load("[[check.tool]]\nname = \"ok\"\ncommand = \"cargo\"\nargs = []\n").is_ok());
    }

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
            def: None,
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
            tier: crate::ToolTier::Ticket,
            unscoped_packages: vec!["--workspace".to_owned()],
            requires: Vec::new(),
        }
    }

    fn run_one(stage: &ToolStage) -> Vec<Finding> {
        run_full(stage, Path::new("."))
            .findings
            .into_iter()
            .map(|t| t.finding)
            .collect()
    }

    fn run_full(stage: &ToolStage, root: &Path) -> ToolOutput {
        let mut timing = Timing::default();
        let mut files = FileInterner::default();
        start_tools(root, std::slice::from_ref(stage), None, None, &[])
            .expect("one stage")
            .finish(&mut timing, &mut files)
    }

    // frob:ticket 01M4D6NEQYAZEFFX3P0S2EJV2N
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn independent_stages_overlap_and_keep_their_order_and_timing() {
        if !gob_exec::require_sh("independent_stages_overlap_and_keep_their_order_and_timing") {
            return;
        }
        let slow = |name: &str| sh_stage(name, ToolParser::None, "sleep 1", "true");
        let stages = [slow("a"), slow("b"), slow("c")];
        let mut timing = Timing::default();
        let mut files = FileInterner::default();
        let started = Instant::now();
        let found = start_tools(Path::new("."), &stages, None, None, &[])
            .expect("stages")
            .finish(&mut timing, &mut files);
        let wall = started.elapsed();
        assert!(found.findings.is_empty(), "{found:?}");
        let names: Vec<_> = timing.stages.iter().map(|t| t.name.as_str()).collect();
        assert_eq!(names, ["tool:a", "tool:b", "tool:c"]);
        assert!(timing.tools_ms() >= 3000, "each stage reports its own time");
        assert!(wall < Duration::from_millis(2500), "ran serially: {wall:?}");
    }

    // frob:ticket 01M4GRW6NH23YPTSAQERDRSZC5
    // frob:tests crates/gob-check/src/tools.rs::applicable_stages
    #[test]
    fn a_stage_is_skipped_only_when_it_declares_inputs_the_scope_misses() {
        if !gob_exec::require_sh("a_stage_is_skipped_only_when_it_declares_inputs_the_scope_misses")
        {
            return;
        }
        let mut stage = sh_stage("gen", ToolParser::None, "true", "true");
        let scope: std::collections::BTreeSet<String> =
            ["docs/a.md".to_owned()].into_iter().collect();
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&scope), None).len(),
            1
        );
        stage.inputs = vec!["crates/**/*.rs".to_owned()];
        assert!(applicable_stages(std::slice::from_ref(&stage), Some(&scope), None).is_empty());
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), None, None).len(),
            1
        );
        let hit: std::collections::BTreeSet<String> =
            ["crates/x/src/lib.rs".to_owned()].into_iter().collect();
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&hit), None).len(),
            1
        );
        stage.inputs = vec!["[".to_owned()];
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&scope), None).len(),
            1
        );
    }

    // frob:ticket 01M4HKDJDC1ZMQRHY83TFM9EYJ
    // frob:tests crates/gob-check/src/tools.rs::untouched
    #[test]
    fn frob_toml_is_an_implicit_input_of_every_stage() {
        if !gob_exec::require_sh("frob_toml_is_an_implicit_input_of_every_stage") {
            return;
        }
        let mut stage = sh_stage("gen", ToolParser::None, "true", "true");
        stage.inputs = vec!["crates/**/*.rs".to_owned()];
        let scope: std::collections::BTreeSet<String> =
            ["frob.toml".to_owned()].into_iter().collect();
        assert_eq!(
            applicable_stages(std::slice::from_ref(&stage), Some(&scope), None).len(),
            1
        );
    }

    // frob:ticket 01M4HADVZ8JGBB406JJAJGEC9Q
    // frob:tests crates/gob-check/src/tools.rs::expand_packages
    #[test]
    fn the_packages_token_expands_to_the_affected_set_or_the_unscoped_default() {
        if !gob_exec::require_sh(
            "the_packages_token_expands_to_the_affected_set_or_the_unscoped_default",
        ) {
            return;
        }
        let mut stage = sh_stage("clippy", ToolParser::None, "true", "true");
        stage.args = vec![
            "clippy".to_owned(),
            PACKAGES_TOKEN.to_owned(),
            "--all-targets".to_owned(),
        ];
        let set = Affected::Packages(vec!["a".to_owned(), "b".to_owned()]);
        let scoped = expand_packages(&stage, Some(&set)).expect("runs");
        assert_eq!(
            scoped.args,
            ["clippy", "-p", "a", "-p", "b", "--all-targets"]
        );
        let all = expand_packages(&stage, Some(&Affected::Everything)).expect("runs");
        assert_eq!(all.args, ["clippy", "--workspace", "--all-targets"]);
        assert_eq!(expand_packages(&stage, None).expect("runs").args, all.args);
        assert!(expand_packages(&stage, Some(&Affected::Packages(Vec::new()))).is_none());
        let plain = sh_stage("gen", ToolParser::None, "true", "true");
        assert_eq!(expand_packages(&plain, Some(&set)), Some(plain.clone()));
    }

    // frob:ticket 01M4D6NEQYAZEFFX3P0S2EJV2N
    // frob:tests crates/gob-check/src/tools.rs::group_key
    #[test]
    fn cargo_stages_share_one_group_and_others_get_their_own() {
        if !gob_exec::require_sh("cargo_stages_share_one_group_and_others_get_their_own") {
            return;
        }
        let mut cargo = sh_stage("c", ToolParser::None, "true", "true");
        cargo.command = "cargo".to_owned();
        let other = sh_stage("o", ToolParser::None, "true", "true");
        assert_eq!(group_key(&cargo, 0), group_key(&cargo, 5));
        let mut wrapped = cargo.clone();
        wrapped.command = "env".to_owned();
        wrapped.args = vec!["RUSTDOCFLAGS=-D warnings".to_owned(), "cargo".to_owned()];
        assert_eq!(group_key(&wrapped, 3), group_key(&cargo, 0));
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

    // frob:ticket 01M4M27E8E0DK7XAQ2D7T0Q8TR
    // frob:tests crates/gob-check/src/tools.rs::execute
    #[test]
    fn a_spawn_io_failure_is_a_required_tool_failed_even_when_not_gating() {
        if !gob_exec::require_sh(
            "a_spawn_io_failure_is_a_required_tool_failed_even_when_not_gating",
        ) {
            return;
        }
        {
            let mut stage = sh_stage("lint", ToolParser::None, "true", VERSION_OK);
            stage.fail_on_nonzero = false;
            let runner = Runner::new(Limits::default()).allow_tools(["sh".to_owned()]);
            // A working directory that does not exist makes the OS refuse the spawn.
            let result = execute(
                &runner,
                Path::new("/frob-no-such-dir/x"),
                &stage,
                None,
                &Prereqs::new(&[]),
            );
            let mut files = FileInterner::default();
            let id: RuleId = Tool001.meta().rule_id().expect("id");
            let found = stage_findings(Path::new("."), &id, &stage, result, &mut files);
            assert_tool_failed(
                &found
                    .findings
                    .iter()
                    .map(|t| t.finding.clone())
                    .collect::<Vec<_>>(),
                &["could not run", "failed to spawn"],
            );
        }
    }

    // frob:ticket 01M4D94J5J2TZEXTB8GH36992B
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn formatter_check_output_yields_one_fmt001_per_file() {
        if !gob_exec::require_sh("formatter_check_output_yields_one_fmt001_per_file") {
            return;
        }
        let script = "echo 'Diff in src/lib.rs:3:'; echo 'Diff in src/lib.rs:9:'; \
            echo 'Would reformat: app/main.py'; echo 'Would reformat: app/main.py'; \
            echo '[warn] web/index.ts' >&2; echo '[warn] Code style issues found in the above file.' >&2; \
            echo 'Game/Player.cs(4,1): error WHITESPACE: Fix whitespace formatting.'; exit 1";
        let stage = sh_stage("fmt", ToolParser::FormatterList, script, VERSION_OK);
        let found = run_one(&stage);
        assert!(
            found.iter().all(|f| f.rule.as_str() == "FMT001"),
            "{found:?}"
        );
        assert_eq!(found.len(), 4, "{found:?}");
    }

    /// Script printing a cargo-semver-checks report for one removed function; `$1` is the change kind.
    const SEMVER_REPORT: &str = "echo '     Checking foo v1.2.0 -> v1.2.1 (CHANGE)' >&2; \
        echo '--- failure function_missing: pub fn removed or renamed ---' >&2; \
        echo 'Failed in:' >&2; \
        echo '  function foo::bar, previously in file src/lib.rs:12' >&2; exit 1";

    // frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn removed_public_function_without_a_version_bump_is_a_version001_error() {
        if !gob_exec::require_sh("removed_public_function_without_a_version_bump") {
            return;
        }
        let script = SEMVER_REPORT.replace("CHANGE", "no change");
        let stage = sh_stage("semver", ToolParser::SemverChecksText, &script, VERSION_OK);
        let found = run_one(&stage);
        assert_eq!(found.len(), 1, "{found:?}");
        assert_eq!(found[0].rule.as_str(), "VERSION001");
        assert_eq!(found[0].severity, Severity::Error);
        assert!(found[0].message.contains("foo::bar"), "{found:?}");
    }

    // frob:ticket 01M4D94PD6M68GJ6MEDBVDP7MK
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_major_version_bump_yields_no_version001_finding() {
        if !gob_exec::require_sh("a_major_version_bump_yields_no_version001_finding") {
            return;
        }
        let script = SEMVER_REPORT.replace("v1.2.1 (CHANGE)", "v2.0.0 (breaking change)");
        let stage = sh_stage("semver", ToolParser::SemverChecksText, &script, VERSION_OK);
        assert!(run_one(&stage).is_empty());
    }

    // frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn api_extractor_report_drift_is_a_version001_error() {
        if !gob_exec::require_sh("api_extractor_report_drift_is_a_version001_error") {
            return;
        }
        let script = "echo 'Error: You have changed the public API signature for this project. Please copy the file \"temp/foo.api.md\" to \"etc/foo.api.md\", or perform a local build.'; exit 1";
        let stage = sh_stage("api", ToolParser::ApiExtractorText, script, VERSION_OK);
        let found = run_one(&stage);
        assert_eq!(found.len(), 1, "{found:?}");
        assert_eq!(found[0].rule.as_str(), "VERSION001");
        assert_eq!(found[0].severity, Severity::Error);
    }

    // frob:ticket 01M5HYTAKXCZB6B2MAEM8X2G5Y
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_missing_api_extractor_is_unresolved() {
        if !gob_exec::require_sh("a_missing_api_extractor_is_unresolved") {
            return;
        }
        let mut stage = sh_stage("lint", ToolParser::ApiExtractorText, "true", VERSION_OK);
        stage.command = "frob-no-such-api-extractor".to_owned();
        assert_tool_failed(
            &run_one(&stage),
            &["`lint`", "frob-no-such-api-extractor", "not found"],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_missing_binary_is_a_required_tool_failed() {
        if !gob_exec::require_sh("a_missing_binary_is_a_required_tool_failed") {
            return;
        }
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
        if !gob_exec::require_sh("an_unresolvable_pin_fails_the_version_probe_loudly") {
            return;
        }
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
        if !gob_exec::require_sh("an_undeclared_exit_with_empty_output_names_status_and_stderr") {
            return;
        }
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
        if !gob_exec::require_sh("a_findings_exit_with_no_output_is_a_failure") {
            return;
        }
        let stage = sh_stage("lint", ToolParser::ActionlintJson, "exit 1", VERSION_OK);
        assert_tool_failed(
            &run_one(&stage),
            &["printed no output", "exit 1", "stderr: (empty)"],
        );
    }

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn unparseable_output_is_a_failure() {
        if !gob_exec::require_sh("unparseable_output_is_a_failure") {
            return;
        }
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
        if !gob_exec::require_sh("a_clean_run_yields_no_finding") {
            return;
        }
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

    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn sarif_results_map_keep_source_rule_and_set_suppressed_aside() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(
            dir.path().join("a.js"),
            "debugger;\nvar s = '\u{e9}\u{e9}'; if (s == 1) {}\n",
        )
        .expect("write");
        let log = ESLINT_SARIF.replace(
            "/work/repo/a.js",
            &gob_path::forward_slashes(&dir.path().join("a.js")),
        );
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

    // frob:tests crates/gob-check/src/tools.rs::start_tools
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
        if !gob_exec::require_sh("stderr_is_escaped_and_capped") {
            return;
        }
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

    // frob:ticket 01M4GKCBT6MW3BHED91718ANQ7
    #[test]
    fn the_excerpt_shows_error_lines_and_the_tail_not_leading_info_noise() {
        let mut lines: Vec<String> = (0..40)
            .map(|i| format!("INFO starting step {i} of the long running tool"))
            .collect();
        lines.push("error: could not parse config.yml line 7".to_owned());
        lines.extend((0..10).map(|i| format!("INFO cleanup {i}")));
        lines.push("tool exited with status 3".to_owned());
        let text = lines.join("\n");
        let out = excerpt(&text);
        assert!(!out.contains("starting step 0"), "{out}");
        assert!(
            out.contains("error: could not parse config.yml line 7"),
            "{out}"
        );
        assert!(out.contains("tool exited with status 3"), "{out}");
        assert!(out.contains("INFO cleanup 9"), "{out}");
        assert!(out.chars().count() <= TAIL + 8, "capped: {}", out.len());
    }

    // frob:ticket 01M4GKCBT6MW3BHED91718ANQ7
    #[test]
    fn a_failing_tool_with_info_noise_quotes_its_error_line_in_tool001() {
        if !gob_exec::require_sh("a_failing_tool_with_info_noise_quotes_its_error_line_in_tool001")
        {
            return;
        }
        let stage = sh_stage(
            "lint",
            ToolParser::ActionlintJson,
            "for i in $(seq 1 60); do echo \"INFO warming up $i\" >&2; done; echo 'error: bad workflow file' >&2; echo 'INFO done' >&2; exit 2",
            VERSION_OK,
        );
        let found = run_one(&stage);
        let msg = &found[0].message;
        assert!(msg.contains("error: bad workflow file"), "{msg}");
        assert!(msg.contains("INFO done"), "{msg}");
        assert!(!msg.contains("warming up 1 "), "{msg}");
    }

    #[derive(Debug, Default)]
    struct MapMemo(std::sync::Mutex<HashMap<String, String>>);

    impl ToolMemo for MapMemo {
        fn load(&self, key: &str) -> Option<String> {
            self.0.lock().expect("lock").get(key).cloned()
        }
        fn store(&self, key: &str, payload: &str) {
            self.0
                .lock()
                .expect("lock")
                .insert(key.to_owned(), payload.to_owned());
        }
    }

    // frob:ticket 01M4MH624WYQHRVHT9B3K1MDJD
    // frob:tests crates/gob-check/src/tools.rs::start_tools
    #[test]
    fn a_recorded_pass_is_reused_until_one_input_changes() {
        if !gob_exec::require_sh("a_recorded_pass_is_reused_until_one_input_changes") {
            return;
        }
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join("a.txt"), "one").expect("write");
        let mut stage = sh_stage("m", ToolParser::None, "echo x >> spawns.log", "true");
        stage.inputs = vec!["*.txt".to_owned()];
        let memo: std::sync::Arc<dyn ToolMemo> = std::sync::Arc::new(MapMemo::default());
        let run = || {
            let mut timing = Timing::default();
            let mut files = FileInterner::default();
            start_tools(
                dir.path(),
                std::slice::from_ref(&stage),
                Some(&memo),
                None,
                &[],
            )
            .expect("stage")
            .finish(&mut timing, &mut files);
            timing.stages[0].name.clone()
        };
        let spawns = || {
            std::fs::read_to_string(dir.path().join("spawns.log"))
                .unwrap_or_default()
                .lines()
                .count()
        };
        assert_eq!(run(), "tool:m");
        assert_eq!(spawns(), 1);
        assert_eq!(run(), "tool:m (cached)", "same inputs hit");
        assert_eq!(spawns(), 1, "a hit spawns nothing");
        std::fs::write(dir.path().join("a.txt"), "two").expect("write");
        assert_eq!(run(), "tool:m", "a changed input misses");
        assert_eq!(spawns(), 2);
    }

    // frob:tests crates/gob-check/src/config.rs::ToolStage.resolved
    #[test]
    fn a_def_stage_runs_from_data_for_zizmor_and_ruff() {
        let t: crate::config::CheckTable = toml::from_str(
            "[[tool]]\nname = \"zizmor\"\ndef = \"zizmor\"\n[[tool]]\nname = \"ruff\"\ndef = \"ruff\"\nid_map = { F401 = \"DEAD001\" }\n",
        )
        .unwrap_or_else(|e| panic!("{e}"));
        let [z, r] = &t.tool[..] else {
            panic!("two stages")
        };
        z.validate().unwrap();
        let (z, r) = (z.resolved(), r.resolved());
        assert_eq!(z.command, "uvx");
        assert_eq!(z.parser, ToolParser::ZizmorJsonV1);
        assert_eq!(z.args[0], "zizmor@1.30.1");
        assert_eq!(z.min_version.as_deref(), Some("1.30.0"));
        assert!(z.inputs.contains(&".github/workflows/**".to_owned()));
        assert_eq!(stage_normal_exits(&z), [0, 10, 11, 12, 13, 14]);
        assert_eq!(r.parser, ToolParser::RuffJson);
        assert!(r.inputs.contains(&"ruff.toml".to_owned()));
        assert_eq!(r.id_map["F401"], "DEAD001");
        assert_eq!(with_variant(&r, Some("0.14.1")).args, r.args);
    }

    // frob:tests crates/gob-check/src/config.rs::ToolStage.validate
    #[test]
    fn an_unknown_def_is_a_cfg_error() {
        let t: crate::config::CheckTable =
            toml::from_str("[[tool]]\nname = \"x\"\ndef = \"nope\"\n").unwrap();
        assert!(t.tool[0].validate().is_err());
    }

    fn uv_run(args: &[&str]) -> ToolStage {
        let mut stage = named_uv();
        stage.args = args.iter().map(|a| (*a).to_owned()).collect();
        stage
    }

    fn named_uv() -> ToolStage {
        let mut stage = sh_stage("py", ToolParser::None, "true", "true");
        stage.command = "uv".to_owned();
        stage
    }

    // frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
    // frob:tests crates/gob-check/src/tools.rs::uv_sync_line
    #[test]
    fn a_uv_run_stage_without_a_venv_syncs_first_and_otherwise_does_not() {
        if std::env::var_os("UV_PROJECT_ENVIRONMENT").is_some() {
            return;
        }
        let root = tempfile::tempdir().expect("root");
        let stage = uv_run(&["run", "--no-sync", "pytest"]);
        // No pyproject: nothing to sync.
        assert_eq!(uv_sync_line(root.path(), &stage), None);
        std::fs::write(root.path().join("pyproject.toml"), "[project]\n").expect("write");
        assert_eq!(
            uv_sync_line(root.path(), &stage).as_deref(),
            Some("uv sync")
        );
        // A lockfile makes the sync frozen so it never rewrites the lock.
        std::fs::write(root.path().join("uv.lock"), "").expect("write");
        assert_eq!(
            uv_sync_line(root.path(), &stage).as_deref(),
            Some("uv sync --frozen")
        );
        // Flags before the subcommand still find `run`; project-less runs and other programs never sync.
        let flagged = uv_run(&["--quiet", "run", "pytest"]);
        assert!(uv_sync_line(root.path(), &flagged).is_some());
        for args in [
            &["run", "--no-project", "x"][..],
            &["run", "--isolated", "x"],
            &["pip", "list"],
        ] {
            assert_eq!(uv_sync_line(root.path(), &uv_run(args)), None, "{args:?}");
        }
        let mut other = uv_run(&["run", "pytest"]);
        other.command = "poetry".to_owned();
        assert_eq!(uv_sync_line(root.path(), &other), None);
        // An existing environment is left alone.
        let venv = root.path().join(".venv");
        std::fs::create_dir_all(&venv).expect("mkdir");
        std::fs::write(venv.join("pyvenv.cfg"), "home = x\n").expect("write");
        assert_eq!(uv_sync_line(root.path(), &stage), None);
    }

    // frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
    // frob:tests crates/gob-check/src/tools.rs::execute
    #[test]
    fn a_failed_environment_sync_is_unresolved_never_a_red_verdict() {
        let on_path = std::env::var_os("PATH")
            .is_some_and(|p| std::env::split_paths(&p).any(|d| d.join("uv").is_file()));
        if !on_path || std::env::var_os("UV_PROJECT_ENVIRONMENT").is_some() {
            return;
        }
        let root = tempfile::tempdir().expect("root");
        // A malformed project makes `uv sync` fail deterministically, offline or not.
        std::fs::write(root.path().join("pyproject.toml"), "[project\n").expect("write");
        let mut stage = uv_run(&["run", "--no-sync", "pytest"]);
        stage.name = "py".to_owned();
        let found = run_full(&stage, root.path()).findings;
        assert_eq!(found.len(), 1, "{found:?}");
        let finding = &found[0].finding;
        assert_eq!(finding.severity, Severity::Unresolved, "{finding:?}");
        assert!(finding.message.contains("uv sync"), "{}", finding.message);
        assert!(
            finding.message.contains("then re-run"),
            "{}",
            finding.message
        );
    }
}

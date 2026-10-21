//! `cargo dev ecosystem`: the finding diff of a base and a head binary over a pinned corpus.
//!
//! `ecosystem.toml` pins real repositories by commit ([`Corpus`]). The runner ([`run`]) checks each
//! project with the base and the head build of frob, grimble and crunk and classifies every run
//! ([`classify`]): findings, a structured error, or a crash. This module holds the pure part: how
//! two runs of one tool compare ([`diff_runs`]) and the markdown a pull-request comment carries
//! ([`render`]). Design: `docs/design/build-test-ci.md` section 6 ("Ecosystem check").
//!
//! Comparison rules, chosen so a diff is never noise and never silently empty:
//! - A finding is identified by `(rule, file, message)`, not by line: code that merely shifts is
//!   not a change. Identical findings are counted as a multiset, and every ordering is sorted, so
//!   the output does not depend on the order a binary emits findings in.
//! - A finding whose severity differs between the sides is `changed`; one that kept its rule and
//!   message but moved to another file is also `changed` (a rename), not an add plus a remove.
//! - An empty base that ran fine makes every head finding `added`. A base that crashed or errored
//!   makes no diff at all (nothing was learned), and is reported as such.
//! - A head that crashed or errored where the base did not is the loudest line of the report.
// frob:ticket 01M47QV23EAN5DE6DDV9HS3VP7

pub mod run;

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Component, MAIN_SEPARATOR, Path, PathBuf};

use gob_exec::Outcome;
use serde::Deserialize;
use serde_json::Value;

/// Marker on the first line of the comment so a re-run edits it instead of adding another.
pub const COMMENT_MARKER: &str = "<!-- frob-ecosystem -->";

/// The severity string frob and grimble give a finding they could not decide.
pub const UNRESOLVED: &str = "unresolved";

/// Rule rows shown per project and tool before the rest are summarised.
const MAX_RULE_ROWS: usize = 25;

/// Example findings listed per rule and direction.
const MAX_EXAMPLES: usize = 3;

/// GitHub rejects comments over 65536 characters; stay clear of it.
const MAX_COMMENT_CHARS: usize = 60_000;

/// Why a corpus could not be loaded or a run could not start.
#[derive(Debug, thiserror::Error)]
pub enum EcosystemError {
    /// `ecosystem.toml` could not be read.
    #[error("read {path}: {source}")]
    Io {
        /// The file or directory involved.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// `ecosystem.toml` is not valid TOML of the expected shape.
    #[error("parse corpus: {0}")]
    Parse(String),
    /// The corpus parses but an entry is unusable.
    #[error("invalid corpus: {0}")]
    Invalid(String),
    /// A process could not be run.
    #[error("{0}")]
    Spawn(String),
    /// A project checkout failed.
    #[error("checkout of {project}: {detail}")]
    Checkout {
        /// Project name.
        project: String,
        /// What git said.
        detail: String,
    },
}

/// Language family a corpus project stands for.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Language {
    /// Rust.
    Rust,
    /// Python.
    Python,
    /// TypeScript and React.
    Typescript,
    /// C# and Unity.
    Csharp,
}

/// One of the three products the corpus is checked with.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Tool {
    /// `frob check`.
    Frob,
    /// `grimble check`.
    Grimble,
    /// `crunk check`.
    Crunk,
}

impl Tool {
    /// Every tool, in report order.
    pub const ALL: [Self; 3] = [Self::Frob, Self::Grimble, Self::Crunk];

    /// The binary and subcommand name, which are the same word.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Frob => "frob",
            Self::Grimble => "grimble",
            Self::Crunk => "crunk",
        }
    }
}

/// One pinned repository.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Project {
    /// Short unique name; also the checkout directory name.
    pub name: String,
    /// Language family, for the report and the corpus-coverage test.
    pub language: Language,
    /// Clone URL (or a local path).
    pub repo: String,
    /// Full 40-hex commit id.
    pub sha: String,
    /// Tools to run; all three when absent.
    #[serde(default)]
    pub tools: Option<Vec<Tool>>,
}

impl Project {
    /// The tools this project is checked with.
    #[must_use]
    pub fn tools(&self) -> Vec<Tool> {
        self.tools.clone().unwrap_or_else(|| Tool::ALL.to_vec())
    }
}

/// The parsed `ecosystem.toml`.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Corpus {
    /// The pinned projects, in file order.
    #[serde(rename = "project")]
    pub projects: Vec<Project>,
}

impl Corpus {
    /// Parse and validate corpus text: unique safe names, full-length hex shas, a repo for each.
    ///
    /// # Errors
    /// [`EcosystemError::Parse`] for malformed TOML, [`EcosystemError::Invalid`] for a bad entry
    /// or an empty corpus.
    pub fn parse(text: &str) -> Result<Self, EcosystemError> {
        let corpus: Self =
            toml::from_str(text).map_err(|e| EcosystemError::Parse(e.to_string()))?;
        if corpus.projects.is_empty() {
            return Err(EcosystemError::Invalid("no [[project]] entries".to_owned()));
        }
        let mut seen = std::collections::BTreeSet::new();
        for p in &corpus.projects {
            let safe_name = !p.name.is_empty()
                && p.name
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_');
            if !safe_name {
                return Err(EcosystemError::Invalid(format!(
                    "project name `{}` must be non-empty ASCII letters, digits, `-` or `_`",
                    p.name
                )));
            }
            if !seen.insert(p.name.as_str()) {
                return Err(EcosystemError::Invalid(format!(
                    "duplicate project `{}`",
                    p.name
                )));
            }
            if p.sha.len() != 40 || !p.sha.chars().all(|c| c.is_ascii_hexdigit()) {
                return Err(EcosystemError::Invalid(format!(
                    "project `{}`: sha must be a full 40-character hex commit id",
                    p.name
                )));
            }
            if p.repo.trim().is_empty() {
                return Err(EcosystemError::Invalid(format!(
                    "project `{}`: empty repo",
                    p.name
                )));
            }
            if p.tools.as_ref().is_some_and(Vec::is_empty) {
                return Err(EcosystemError::Invalid(format!(
                    "project `{}`: `tools` is empty (omit it to run all three)",
                    p.name
                )));
            }
        }
        tracing::debug!(projects = corpus.projects.len(), "corpus parsed");
        Ok(corpus)
    }

    /// Read and [`parse`](Self::parse) the corpus file at `path`.
    ///
    /// # Errors
    /// [`EcosystemError`] when the file cannot be read or is invalid.
    pub fn load(path: &Path) -> Result<Self, EcosystemError> {
        let text = std::fs::read_to_string(path).map_err(|source| EcosystemError::Io {
            path: path.to_path_buf(),
            source,
        })?;
        Self::parse(&text)
    }
}

/// One finding as the diff sees it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// Rule id.
    pub rule: String,
    /// Severity word (`error`, `warn`, `advisory`, `unresolved`).
    pub severity: String,
    /// Project-relative path, normalised by [`normalize_path`].
    pub file: String,
    /// 1-based line, 0 when the finding carried none.
    pub line: u64,
    /// The message.
    pub message: String,
}

/// How a run of one tool ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RunStatus {
    /// The tool produced an envelope without an error.
    Ok,
    /// The tool answered with a structured error (for example `E-NO-CONFIG`).
    Error {
        /// Error code.
        code: String,
        /// Error message, first line only.
        message: String,
    },
    /// The tool died, timed out, could not start, or printed no envelope.
    Crash {
        /// What was observed.
        detail: String,
    },
}

impl RunStatus {
    /// Whether the run produced findings that can be compared.
    #[must_use]
    pub fn is_ok(&self) -> bool {
        matches!(self, Self::Ok)
    }

    /// One-line description of a failed run (empty for [`RunStatus::Ok`]).
    #[must_use]
    pub fn describe(&self) -> String {
        match self {
            Self::Ok => String::new(),
            Self::Error { code, message } => format!("error {code}: {message}"),
            Self::Crash { detail } => format!("crash: {detail}"),
        }
    }
}

/// One tool's run on one project by one binary.
#[derive(Debug, Clone, PartialEq)]
pub struct ToolRun {
    /// How it ended.
    pub status: RunStatus,
    /// Findings (empty unless `status` is [`RunStatus::Ok`]).
    pub findings: Vec<Finding>,
    /// Wall-clock milliseconds.
    pub wall_ms: f64,
}

impl ToolRun {
    /// A run that could not even be observed (for example a binary that is missing).
    #[must_use]
    pub fn crashed(detail: impl Into<String>) -> Self {
        Self {
            status: RunStatus::Crash {
                detail: detail.into(),
            },
            findings: Vec::new(),
            wall_ms: 0.0,
        }
    }
}

/// Normalise a finding path to components joined by the host separator, without `.`, root or
/// drive parts, so the same file compares equal however a tool spelled it.
#[must_use]
pub fn normalize_path(raw: &str) -> String {
    let mut out = String::new();
    for c in Path::new(raw).components() {
        let part = match c {
            Component::CurDir | Component::RootDir | Component::Prefix(_) => continue,
            Component::ParentDir => "..".to_owned(),
            Component::Normal(s) => {
                gob_path::Shown::with_home(std::path::Path::new(&s), None).to_string()
            }
        };
        if !out.is_empty() {
            out.push(MAIN_SEPARATOR);
        }
        out.push_str(&part);
    }
    out
}

/// The envelope object in `stdout`: the whole text when it is JSON, else the last JSON line (a
/// tool may log a warning line before the envelope).
fn envelope(stdout: &str) -> Option<Value> {
    if let Ok(v @ Value::Object(_)) = serde_json::from_str::<Value>(stdout) {
        return Some(v);
    }
    stdout
        .lines()
        .rev()
        .filter(|l| l.trim_start().starts_with('{'))
        .find_map(|l| match serde_json::from_str::<Value>(l) {
            Ok(v @ Value::Object(_)) if v.get("verb").is_some() => Some(v),
            _ => None,
        })
}

/// The last `max` characters of `text`, trimmed, for a crash detail.
fn tail(text: &str, max: usize) -> String {
    let t = text.trim();
    let skip = t.chars().count().saturating_sub(max);
    t.chars().skip(skip).collect()
}

/// Turn one finished process into a [`ToolRun`].
///
/// A nonzero exit is not a crash by itself (`check` exits 1 on findings); a crash is a signal, a
/// timeout, or an exit with no envelope on stdout (a panic exits 101 and prints none).
#[must_use]
pub fn classify(outcome: Outcome, stdout: &str, stderr: &str, wall_ms: f64) -> ToolRun {
    let crash = |detail: String| ToolRun {
        status: RunStatus::Crash { detail },
        findings: Vec::new(),
        wall_ms,
    };
    let code = match outcome {
        Outcome::TimedOut => return crash("timed out".to_owned()),
        Outcome::Signaled => return crash(format!("killed by a signal: {}", tail(stderr, 200))),
        Outcome::Exited(c) => c,
    };
    let Some(env) = envelope(stdout) else {
        return crash(format!(
            "exit {code} with no JSON envelope: {}",
            tail(stderr, 200)
        ));
    };
    if let Some(err) = env.get("error").filter(|e| !e.is_null()) {
        let text = |k: &str| {
            err.get(k)
                .and_then(Value::as_str)
                .unwrap_or_default()
                .lines()
                .next()
                .unwrap_or_default()
                .to_owned()
        };
        return ToolRun {
            status: RunStatus::Error {
                code: text("code"),
                message: text("message"),
            },
            findings: Vec::new(),
            wall_ms,
        };
    }
    let findings = env
        .get("findings")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .map(|f| {
            let s = |k: &str| f.get(k).and_then(Value::as_str).unwrap_or_default();
            Finding {
                rule: s("rule").to_owned(),
                severity: s("severity").to_owned(),
                file: normalize_path(s("file")),
                line: f.get("line").and_then(Value::as_u64).unwrap_or(0),
                message: s("message").to_owned(),
            }
        })
        .collect();
    ToolRun {
        status: RunStatus::Ok,
        findings,
        wall_ms,
    }
}

/// Added, removed and changed findings of one rule, and its Unresolved movement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuleDelta {
    /// Rule id.
    pub rule: String,
    /// Findings only the head has.
    pub added: usize,
    /// Findings only the base has.
    pub removed: usize,
    /// Findings on both sides that differ in severity or file.
    pub changed: usize,
    /// Head minus base count of `unresolved` findings of this rule.
    pub unresolved: i64,
    /// A few added findings as `file:line message`.
    pub added_examples: Vec<String>,
    /// A few removed findings as `file:line message`.
    pub removed_examples: Vec<String>,
}

impl RuleDelta {
    fn new(rule: &str) -> Self {
        Self {
            rule: rule.to_owned(),
            added: 0,
            removed: 0,
            changed: 0,
            unresolved: 0,
            added_examples: Vec::new(),
            removed_examples: Vec::new(),
        }
    }

    fn is_zero(&self) -> bool {
        self.added == 0 && self.removed == 0 && self.changed == 0 && self.unresolved == 0
    }
}

fn example(f: &Finding) -> String {
    format!("{}:{} {}", f.file, f.line, f.message)
}

type Pool<'a> = BTreeMap<(&'a str, &'a str, &'a str), Vec<&'a Finding>>;

fn pool(findings: &[Finding]) -> Pool<'_> {
    let mut p = Pool::new();
    for f in findings {
        p.entry((f.rule.as_str(), f.file.as_str(), f.message.as_str()))
            .or_default()
            .push(f);
    }
    for v in p.values_mut() {
        v.sort_by(|a, b| a.severity.cmp(&b.severity).then(a.line.cmp(&b.line)));
    }
    p
}

/// Count of `unresolved` findings per rule.
fn unresolved_counts(fs: &[Finding]) -> BTreeMap<&str, i64> {
    let mut m = BTreeMap::new();
    for f in fs.iter().filter(|f| f.severity == UNRESOLVED) {
        *m.entry(f.rule.as_str()).or_default() += 1;
    }
    m
}

/// Compare two successful finding lists into per-rule deltas, sorted by rule, zero rows dropped.
///
/// Findings are matched by `(rule, file, message)` with multiplicity; equal severities pair off
/// first, then leftover severities pair as `changed`, then a leftover removed and added finding of
/// the same rule and message in different files pair as `changed` (a rename).
#[must_use]
pub fn diff_findings(base: &[Finding], head: &[Finding]) -> Vec<RuleDelta> {
    let (bp, hp) = (pool(base), pool(head));
    let mut deltas: BTreeMap<String, RuleDelta> = BTreeMap::new();

    // Leftovers keyed by (rule, message) for the rename pass.
    let mut gone: BTreeMap<(&str, &str), Vec<&Finding>> = BTreeMap::new();
    let mut fresh: BTreeMap<(&str, &str), Vec<&Finding>> = BTreeMap::new();
    let keys: std::collections::BTreeSet<_> = bp.keys().chain(hp.keys()).copied().collect();
    for key in keys {
        let mut b: Vec<&Finding> = bp.get(&key).cloned().unwrap_or_default();
        let mut h: Vec<&Finding> = hp.get(&key).cloned().unwrap_or_default();
        // Pair equal severities (both lists are sorted by severity).
        let mut i = 0;
        while i < b.len() {
            if let Some(j) = h.iter().position(|x| x.severity == b[i].severity) {
                b.remove(i);
                h.remove(j);
            } else {
                i += 1;
            }
        }
        // Pair what is left as a severity change.
        let both = b.len().min(h.len());
        if both > 0 {
            deltas
                .entry(key.0.to_owned())
                .or_insert_with(|| RuleDelta::new(key.0))
                .changed += both;
            b.drain(..both);
            h.drain(..both);
        }
        gone.entry((key.0, key.2)).or_default().extend(b);
        fresh.entry((key.0, key.2)).or_default().extend(h);
    }
    let pair_keys: Vec<(&str, &str)> = gone.keys().chain(fresh.keys()).copied().collect();
    let mut done = std::collections::BTreeSet::new();
    for key in pair_keys {
        if !done.insert(key) {
            continue;
        }
        let mut r = gone.remove(&key).unwrap_or_default();
        let mut a = fresh.remove(&key).unwrap_or_default();
        let moved = r.len().min(a.len());
        let d = deltas
            .entry(key.0.to_owned())
            .or_insert_with(|| RuleDelta::new(key.0));
        d.changed += moved;
        r.drain(..moved);
        a.drain(..moved);
        d.removed += r.len();
        d.added += a.len();
        d.removed_examples
            .extend(r.iter().take(MAX_EXAMPLES).map(|f| example(f)));
        d.added_examples
            .extend(a.iter().take(MAX_EXAMPLES).map(|f| example(f)));
    }

    let (bu, hu) = (unresolved_counts(base), unresolved_counts(head));
    for rule in bu.keys().chain(hu.keys()) {
        let moved = hu.get(rule).copied().unwrap_or(0) - bu.get(rule).copied().unwrap_or(0);
        deltas
            .entry((*rule).to_owned())
            .or_insert_with(|| RuleDelta::new(rule))
            .unresolved = moved;
    }
    let mut out: Vec<RuleDelta> = deltas.into_values().filter(|d| !d.is_zero()).collect();
    for d in &mut out {
        d.added_examples.truncate(MAX_EXAMPLES);
        d.removed_examples.truncate(MAX_EXAMPLES);
    }
    out
}

/// How the two runs of one tool on one project compare.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    /// Both succeeded; the per-rule deltas (empty when nothing moved).
    Compared {
        /// Rules whose findings moved.
        deltas: Vec<RuleDelta>,
        /// Findings on the head side, for context.
        head_total: usize,
    },
    /// The base succeeded and the head errored or crashed: a regression.
    HeadFailed {
        /// What the head did.
        head: RunStatus,
    },
    /// The base failed and the head succeeded: nothing to diff against.
    BaseFailed {
        /// What the base did.
        base: RunStatus,
        /// Findings the head produced.
        head_total: usize,
    },
    /// Both returned the same structured error, so the tool does not apply here.
    NotApplicable {
        /// The shared error.
        status: RunStatus,
    },
    /// Both failed, differently.
    BothFailed {
        /// What the base did.
        base: RunStatus,
        /// What the head did.
        head: RunStatus,
    },
}

/// One tool's comparison and timing on one project.
#[derive(Debug, Clone, PartialEq)]
pub struct ToolReport {
    /// The tool.
    pub tool: Tool,
    /// The comparison.
    pub verdict: Verdict,
    /// Base wall-clock milliseconds.
    pub base_ms: f64,
    /// Head wall-clock milliseconds.
    pub head_ms: f64,
}

impl ToolReport {
    /// Whether the head crashed (as opposed to returning a structured error).
    #[must_use]
    pub fn head_crashed(&self) -> bool {
        match &self.verdict {
            Verdict::HeadFailed { head } | Verdict::BothFailed { head, .. } => {
                matches!(head, RunStatus::Crash { .. })
            }
            _ => false,
        }
    }
}

/// Compare the base and head runs of `tool`.
#[must_use]
pub fn compare(tool: Tool, base: &ToolRun, head: &ToolRun) -> ToolReport {
    let verdict = match (&base.status, &head.status) {
        (RunStatus::Ok, RunStatus::Ok) => Verdict::Compared {
            deltas: diff_findings(&base.findings, &head.findings),
            head_total: head.findings.len(),
        },
        (RunStatus::Ok, h) => Verdict::HeadFailed { head: h.clone() },
        (b, RunStatus::Ok) => Verdict::BaseFailed {
            base: b.clone(),
            head_total: head.findings.len(),
        },
        (b @ RunStatus::Error { code: bc, .. }, RunStatus::Error { code: hc, .. }) if bc == hc => {
            Verdict::NotApplicable { status: b.clone() }
        }
        (b, h) => Verdict::BothFailed {
            base: b.clone(),
            head: h.clone(),
        },
    };
    tracing::debug!(tool = tool.name(), ?verdict, "compared");
    ToolReport {
        tool,
        verdict,
        base_ms: base.wall_ms,
        head_ms: head.wall_ms,
    }
}

/// One corpus project in the report.
#[derive(Debug, Clone, PartialEq)]
pub struct ProjectReport {
    /// Project name.
    pub name: String,
    /// Language family.
    pub language: Language,
    /// Pinned commit.
    pub sha: String,
    /// Why the project could not be checked out, when it could not.
    pub setup_error: Option<String>,
    /// Per-tool comparisons.
    pub tools: Vec<ToolReport>,
}

/// The whole report.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Report {
    /// One entry per project.
    pub projects: Vec<ProjectReport>,
}

impl Report {
    /// `project/tool` of every head crash.
    #[must_use]
    pub fn head_crashes(&self) -> Vec<String> {
        self.projects
            .iter()
            .flat_map(|p| {
                p.tools
                    .iter()
                    .filter(|t| t.head_crashed())
                    .map(move |t| format!("{}/{}", p.name, t.tool.name()))
            })
            .collect()
    }
}

fn change_pct(base: f64, head: f64) -> String {
    if base <= 0.0 {
        return "n/a".to_owned();
    }
    format!("{:+.0}%", (head - base) / base * 100.0)
}

fn timing(t: &ToolReport) -> String {
    format!(
        "{:.0} ms -> {:.0} ms ({})",
        t.base_ms,
        t.head_ms,
        change_pct(t.base_ms, t.head_ms)
    )
}

fn language_word(l: Language) -> &'static str {
    match l {
        Language::Rust => "rust",
        Language::Python => "python",
        Language::Typescript => "typescript",
        Language::Csharp => "csharp",
    }
}

/// Escape text for a markdown table cell.
fn cell(text: &str) -> String {
    text.replace('|', "\\|").replace('\n', " ")
}

fn render_tool(out: &mut String, t: &ToolReport) {
    let name = t.tool.name();
    match &t.verdict {
        Verdict::Compared { deltas, head_total } if deltas.is_empty() => {
            let _ = writeln!(
                out,
                "- `{name}`: no finding changes ({head_total} findings); {}",
                timing(t)
            );
        }
        Verdict::Compared { deltas, head_total } => {
            let _ = writeln!(
                out,
                "- `{name}`: {} rules moved ({head_total} findings on head); {}\n",
                deltas.len(),
                timing(t)
            );
            let _ = writeln!(
                out,
                "  | rule | added | removed | changed | unresolved delta |\n  |---|---:|---:|---:|---:|"
            );
            for d in deltas.iter().take(MAX_RULE_ROWS) {
                let _ = writeln!(
                    out,
                    "  | {} | {} | {} | {} | {:+} |",
                    cell(&d.rule),
                    d.added,
                    d.removed,
                    d.changed,
                    d.unresolved
                );
            }
            if deltas.len() > MAX_RULE_ROWS {
                let _ = writeln!(
                    out,
                    "  | ... and {} more rules | | | | |",
                    deltas.len() - MAX_RULE_ROWS
                );
            }
            for d in deltas.iter().take(MAX_RULE_ROWS) {
                for e in &d.added_examples {
                    let _ = writeln!(out, "  - `{}` added: {}", d.rule, cell(e));
                }
                for e in &d.removed_examples {
                    let _ = writeln!(out, "  - `{}` removed: {}", d.rule, cell(e));
                }
            }
        }
        Verdict::HeadFailed { head } => {
            let _ = writeln!(
                out,
                "- `{name}`: **HEAD FAILED** where base succeeded: {}; {}",
                head.describe(),
                timing(t)
            );
        }
        Verdict::BaseFailed { base, head_total } => {
            let _ = writeln!(
                out,
                "- `{name}`: base failed ({}), nothing to diff; head produced {head_total} findings",
                base.describe()
            );
        }
        Verdict::NotApplicable { status } => {
            let _ = writeln!(out, "- `{name}`: not applicable ({})", status.describe());
        }
        Verdict::BothFailed { base, head } => {
            let _ = writeln!(
                out,
                "- `{name}`: both failed; base {}; head {}",
                base.describe(),
                head.describe()
            );
        }
    }
}

/// Render the report as the markdown body of the PR comment, capped under GitHub's limit.
#[must_use]
pub fn render(report: &Report) -> String {
    let mut out = String::new();
    let _ = writeln!(out, "{COMMENT_MARKER}\n## Ecosystem check\n");
    let _ = writeln!(
        out,
        "Finding diff of the base and head builds over {} pinned projects. Informational; this job never fails the run.\n",
        report.projects.len()
    );
    let crashes = report.head_crashes();
    if crashes.is_empty() {
        let _ = writeln!(out, "No head crashes.\n");
    } else {
        let _ = writeln!(out, "**Head crashes ({}):**\n", crashes.len());
        for c in &crashes {
            let _ = writeln!(out, "- `{c}`");
        }
        out.push('\n');
    }
    for p in &report.projects {
        let _ = writeln!(
            out,
            "### {} ({}, `{}`)\n",
            p.name,
            language_word(p.language),
            p.sha.get(..12).unwrap_or(&p.sha)
        );
        if let Some(e) = &p.setup_error {
            let _ = writeln!(out, "- not checked: {}\n", cell(e));
            continue;
        }
        for t in &p.tools {
            render_tool(&mut out, t);
        }
        out.push('\n');
    }
    if out.len() > MAX_COMMENT_CHARS {
        let mut cut = MAX_COMMENT_CHARS;
        while !out.is_char_boundary(cut) {
            cut -= 1;
        }
        out.truncate(cut);
        out.push_str("\n\n... report truncated (comment size limit); see the job summary.\n");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn f(rule: &str, sev: &str, file: &str, line: u64, msg: &str) -> Finding {
        Finding {
            rule: rule.into(),
            severity: sev.into(),
            file: file.into(),
            line,
            message: msg.into(),
        }
    }

    fn ok(findings: Vec<Finding>, ms: f64) -> ToolRun {
        ToolRun {
            status: RunStatus::Ok,
            findings,
            wall_ms: ms,
        }
    }

    const REAL: &str = include_str!("../../../ecosystem.toml");
    const WORKFLOW: &str = include_str!("../../../.github/workflows/ecosystem-pr.yml");

    // frob:tests crates/gob-dev/src/ecosystem.rs::parse
    #[test]
    fn corpus_pins_at_least_five_projects_across_languages() {
        let c = Corpus::parse(REAL).unwrap();
        assert!(c.projects.len() >= 5);
        for l in [
            Language::Rust,
            Language::Python,
            Language::Typescript,
            Language::Csharp,
        ] {
            assert!(c.projects.iter().any(|p| p.language == l), "{l:?}");
        }
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::parse
    #[test]
    fn corpus_rejects_bad_entries() {
        let sha = "a".repeat(40);
        let one = |extra: &str| {
            format!(
                "[[project]]\nname = \"x\"\nlanguage = \"rust\"\nrepo = \"r\"\nsha = \"{sha}\"\n{extra}"
            )
        };
        assert!(Corpus::parse(&one("")).is_ok());
        assert!(Corpus::parse(&format!("{}{}", one(""), one(""))).is_err());
        assert!(Corpus::parse(&one("").replace(&sha, "abc")).is_err());
        assert!(Corpus::parse(&one("tools = []")).is_err());
        assert!(Corpus::parse(&one("bogus = 1")).is_err());
        assert!(Corpus::parse("").is_err());
        assert!(Corpus::parse(&one("").replace("name = \"x\"", "name = \"../x\"")).is_err());
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::normalize_path
    #[test]
    fn paths_normalise() {
        assert_eq!(normalize_path("./a/b"), normalize_path("a/b"));
        assert_eq!(normalize_path(""), "");
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::diff_findings
    #[test]
    fn line_shifts_are_not_changes_and_order_is_irrelevant() {
        let base = vec![
            f("R1", "error", "a.rs", 3, "m"),
            f("R1", "error", "a.rs", 9, "m"),
        ];
        let mut head = vec![
            f("R1", "error", "a.rs", 30, "m"),
            f("R1", "error", "a.rs", 90, "m"),
        ];
        assert!(diff_findings(&base, &head).is_empty());
        head.reverse();
        assert!(diff_findings(&base, &head).is_empty());
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::diff_findings
    #[test]
    fn added_removed_changed_and_unresolved_are_counted_per_rule() {
        let base = vec![
            f("R1", "error", "a.rs", 1, "gone"),
            f("R2", "warn", "b.rs", 1, "sev"),
            f("R3", "error", "old.rs", 1, "moved"),
        ];
        let head = vec![
            f("R1", "error", "a.rs", 1, "new"),
            f("R2", "unresolved", "b.rs", 1, "sev"),
            f("R3", "error", "new.rs", 1, "moved"),
        ];
        let d = diff_findings(&base, &head);
        let by = |r: &str| d.iter().find(|x| x.rule == r).unwrap().clone();
        let r1 = by("R1");
        assert_eq!((r1.added, r1.removed, r1.changed), (1, 1, 0));
        let r2 = by("R2");
        assert_eq!(
            (r2.added, r2.removed, r2.changed, r2.unresolved),
            (0, 0, 1, 1)
        );
        let r3 = by("R3");
        assert_eq!((r3.added, r3.removed, r3.changed), (0, 0, 1));
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::compare
    #[test]
    fn empty_base_makes_every_head_finding_added() {
        let r = compare(
            Tool::Frob,
            &ok(vec![], 1.0),
            &ok(vec![f("R", "error", "a", 1, "m")], 1.0),
        );
        match r.verdict {
            Verdict::Compared { deltas, .. } => assert_eq!(deltas[0].added, 1),
            v => panic!("{v:?}"),
        }
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::compare
    #[test]
    fn failed_base_is_not_a_diff_and_same_error_collapses() {
        let err = |c: &str| ToolRun {
            status: RunStatus::Error {
                code: c.into(),
                message: "m".into(),
            },
            findings: vec![],
            wall_ms: 0.0,
        };
        let head = ok(vec![f("R", "error", "a", 1, "m")], 1.0);
        assert!(matches!(
            compare(Tool::Frob, &err("E-X"), &head).verdict,
            Verdict::BaseFailed { head_total: 1, .. }
        ));
        assert!(matches!(
            compare(Tool::Crunk, &err("E-NO-CONFIG"), &err("E-NO-CONFIG")).verdict,
            Verdict::NotApplicable { .. }
        ));
        assert!(matches!(
            compare(Tool::Crunk, &err("E-A"), &err("E-B")).verdict,
            Verdict::BothFailed { .. }
        ));
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::classify
    #[test]
    fn classify_separates_findings_errors_and_crashes() {
        let env = r#"{"verb":"check","ok":false,"findings":[{"rule":"R1","severity":"error","file":"./a.rs","line":4,"message":"m"}],"error":null}"#;
        let r = classify(Outcome::Exited(1), env, "", 5.0);
        assert!(r.status.is_ok());
        assert_eq!(r.findings[0].file, normalize_path("a.rs"));
        let logged = format!("{{\"level\":\"WARN\"}}\n{env}\n");
        assert!(
            classify(Outcome::Exited(0), &logged, "", 1.0)
                .status
                .is_ok()
        );
        let e = r#"{"verb":"check","findings":[],"error":{"code":"E-NO-CONFIG","message":"no\nconfig"}}"#;
        assert!(matches!(
            classify(Outcome::Exited(3), e, "", 1.0).status,
            RunStatus::Error { ref code, .. } if code == "E-NO-CONFIG"
        ));
        for o in [Outcome::Exited(101), Outcome::Signaled, Outcome::TimedOut] {
            assert!(matches!(
                classify(o, "", "panicked", 1.0).status,
                RunStatus::Crash { .. }
            ));
        }
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::render
    #[test]
    fn render_lists_per_rule_deltas_and_timing() {
        let base = ok(vec![f("R1", "warn", "a.rs", 1, "x")], 100.0);
        let head = ok(vec![f("R2", "unresolved", "b.rs", 2, "y")], 150.0);
        let report = Report {
            projects: vec![ProjectReport {
                name: "demo".into(),
                language: Language::Rust,
                sha: "a".repeat(40),
                setup_error: None,
                tools: vec![compare(Tool::Frob, &base, &head)],
            }],
        };
        let md = render(&report);
        assert!(md.starts_with(COMMENT_MARKER));
        assert!(md.contains("| R1 | 0 | 1 | 0 | +0 |"), "{md}");
        assert!(md.contains("| R2 | 1 | 0 | 0 | +1 |"), "{md}");
        assert!(md.contains("100 ms -> 150 ms (+50%)"), "{md}");
        assert!(md.contains("No head crashes"));
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::render
    #[test]
    fn render_reports_a_head_crash_loudly() {
        let base = ok(vec![], 1.0);
        let head = ToolRun::crashed("exit 101 with no JSON envelope: boom");
        let report = Report {
            projects: vec![ProjectReport {
                name: "demo".into(),
                language: Language::Python,
                sha: "b".repeat(40),
                setup_error: None,
                tools: vec![compare(Tool::Grimble, &base, &head)],
            }],
        };
        assert_eq!(report.head_crashes(), vec!["demo/grimble".to_owned()]);
        let md = render(&report);
        assert!(md.contains("**Head crashes (1):**"), "{md}");
        assert!(md.contains("HEAD FAILED"), "{md}");
        assert!(md.contains("boom"), "{md}");
    }

    // frob:tests crates/gob-dev/src/ecosystem.rs::render
    #[test]
    fn render_stays_under_the_comment_limit() {
        let many: Vec<Finding> = (0..5000)
            .map(|i| f(&format!("R{i}"), "error", "a", 1, "m"))
            .collect();
        let projects = (0..120)
            .map(|i| ProjectReport {
                name: format!("p{i}"),
                language: Language::Rust,
                sha: "c".repeat(40),
                setup_error: None,
                tools: vec![compare(
                    Tool::Frob,
                    &ok(vec![], 1.0),
                    &ok(many.clone(), 1.0),
                )],
            })
            .collect();
        let md = render(&Report { projects });
        assert!(md.len() < 65_536);
        assert!(md.contains("truncated"));
    }

    #[test]
    fn workflow_is_non_blocking_and_comments() {
        assert!(WORKFLOW.contains("continue-on-error: true"));
        assert!(WORKFLOW.contains("pull-requests: write"));
        assert!(WORKFLOW.contains("pull_request:"));
        assert!(WORKFLOW.contains("ecosystem"));
        assert!(!WORKFLOW.contains("--edit-last"));
    }
}

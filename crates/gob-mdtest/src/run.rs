//! Running parsed blocks and rendering reports.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_diagnostics::{ColorChoice, MemorySources, Report as DiagReport, TextOptions, render_text};
use gob_rules::{Finding, RuleId, RuleReport, Severity};
use gob_text::{LineIndex, SourceText};
use walkdir::WalkDir;

use crate::parse::{Block, Expect, Marker, parse_suite};

/// What the caller's closure receives for each block.
#[derive(Debug, Clone)]
pub struct Case {
    /// Block language tag.
    pub language: String,
    /// Virtual file name of the block.
    pub file_name: String,
    /// Block text; finding offsets are relative to it.
    pub text: String,
    /// Rule under test.
    pub rule: RuleId,
    /// Inline TOML config, if any.
    pub config: Option<String>,
}

/// Which positive control is absent.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Missing {
    /// No `expect=fire` block.
    Fire,
    /// No `expect=clean` block.
    Clean,
}

/// A rule lacking a firing or clean control in a file.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("MissingControl: rule {rule} has no expect={missing_name} block", missing_name = match .missing { Missing::Fire => "fire", Missing::Clean => "clean" })]
pub struct MissingControl {
    /// The rule without the control.
    pub rule: RuleId,
    /// Which control is missing.
    pub missing: Missing,
}

/// Result of one block.
#[derive(Debug, Clone)]
pub struct CaseReport {
    /// Heading path, ordinal and fence line.
    pub name: String,
    /// `Err` holds the rendered expected-vs-actual diff.
    pub outcome: Result<(), String>,
}

/// Result of one markdown file.
#[derive(Debug, Clone)]
pub struct FileReport {
    /// Path of the markdown file.
    pub path: PathBuf,
    /// Parse failure, if the suite could not be read.
    pub parse_error: Option<String>,
    /// Per-block results.
    pub cases: Vec<CaseReport>,
    /// Positive-control violations.
    pub missing: Vec<MissingControl>,
}

impl FileReport {
    /// True when every case passed and no control is missing.
    pub fn passed(&self) -> bool {
        self.parse_error.is_none()
            && self.missing.is_empty()
            && self.cases.iter().all(|c| c.outcome.is_ok())
    }

    /// Render the failures of this file (empty string when it passed).
    pub fn render_failures(&self) -> String {
        let mut s = String::new();
        if let Some(e) = &self.parse_error {
            let _ = writeln!(s, "  parse error: {e}");
        }
        for c in &self.cases {
            if let Err(d) = &c.outcome {
                let _ = writeln!(s, "  FAIL {}\n{d}", c.name);
            }
        }
        for m in &self.missing {
            let _ = writeln!(s, "  {m}");
        }
        s
    }
}

/// Results of a directory run.
#[derive(Debug, Clone, Default)]
pub struct Report {
    /// One entry per markdown file, sorted by path.
    pub files: Vec<FileReport>,
}

impl Report {
    /// True when every file passed.
    pub fn passed(&self) -> bool {
        self.files.iter().all(FileReport::passed)
    }

    /// One line per file (`ok`/`FAIL`) followed by failure details.
    pub fn render(&self) -> String {
        let mut s = String::new();
        for f in &self.files {
            let tag = if f.passed() { "ok  " } else { "FAIL" };
            let _ = writeln!(s, "{tag} {} ({} cases)", f.path.display(), f.cases.len());
            s.push_str(&f.render_failures());
        }
        s
    }
}

/// What a runner closure may return for one case: bare findings or a full [`RuleReport`].
pub trait CaseOutput {
    /// The findings the case's expectations are checked against.
    fn into_findings(self) -> Vec<Finding>;
}

impl CaseOutput for Vec<Finding> {
    fn into_findings(self) -> Vec<Finding> {
        self
    }
}

impl CaseOutput for RuleReport {
    fn into_findings(self) -> Vec<Finding> {
        tracing::debug!(
            rule = %self.rule,
            total = self.subjects_total,
            examined = self.subjects_examined,
            not_applicable = ?self.not_applicable,
            "mdtest case returned a rule report"
        );
        self.findings
    }
}

/// Wraps the caller's closure that turns a [`Case`] into findings or a [`RuleReport`].
#[derive(Debug, Clone)]
pub struct Runner<F>(F);

impl<R: CaseOutput, F: Fn(&Case) -> R> Runner<F> {
    /// Wrap `f`, which evaluates one case.
    pub fn new(f: F) -> Self {
        Self(f)
    }
}

/// One `(line, rule, severity)` triple used for exact comparison.
type Key = (u32, RuleId, Severity);

/// Convert findings to block-relative line keys (line 0 when spanless).
fn actual_keys(text: &str, findings: &[Finding]) -> Vec<Key> {
    let idx = LineIndex::new(text).ok();
    let mut keys: Vec<Key> = findings
        .iter()
        .map(|f| {
            let line = f
                .span
                .and_then(|s| idx.as_ref()?.line_col(s.range.start()))
                .map_or(0, |lc| lc.line);
            (line, f.rule.clone(), f.severity)
        })
        .collect();
    keys.sort();
    keys
}

/// Render an expected-vs-actual table, one row per differing entry.
fn diff(expected: &[Key], actual: &[Key]) -> String {
    let mut rows: BTreeMap<u32, (Vec<String>, Vec<String>)> = BTreeMap::new();
    let show = |k: &Key| format!("{:?} {}", k.2, k.1);
    for k in expected {
        rows.entry(k.0).or_default().0.push(show(k));
    }
    for k in actual {
        rows.entry(k.0).or_default().1.push(show(k));
    }
    let mut s = String::from("    line | expected | actual\n");
    for (line, (e, a)) in rows {
        let (e, a) = (e.join(", "), a.join(", "));
        let mark = if e == a { " " } else { "!" };
        let dash = |x: String| if x.is_empty() { "-".to_owned() } else { x };
        let _ = writeln!(s, "  {mark} {line:>4} | {} | {}", dash(e), dash(a));
    }
    s
}

/// Check one block's findings against its expectations.
fn check(block: &Block, findings: &[Finding]) -> Result<(), String> {
    let mine: Vec<Finding> = findings
        .iter()
        .filter(|f| f.rule == block.rule || block.markers.iter().any(|m| m.rule == f.rule))
        .cloned()
        .collect();
    let actual = actual_keys(&block.text, &mine);
    match (block.expect, block.markers.is_empty()) {
        (Expect::Clean, _) if actual.is_empty() => Ok(()),
        (Expect::Fire, true) if !actual.is_empty() => Ok(()),
        (Expect::Fire, false) => {
            let mut expected: Vec<Key> = block
                .markers
                .iter()
                .map(
                    |Marker {
                         line,
                         rule,
                         severity,
                     }| (*line, rule.clone(), *severity),
                )
                .collect();
            expected.sort();
            if expected == actual {
                Ok(())
            } else {
                Err(diff(&expected, &actual))
            }
        }
        (Expect::Fire, true) => Err(format!(
            "    expected at least one {} finding, got none\n",
            block.rule
        )),
        (Expect::Clean, _) => Err(format!(
            "    expected no {} findings\n{}",
            block.rule,
            diff(&[], &actual)
        )),
    }
}

/// Positive-control audit over the blocks of one file.
fn controls(blocks: &[Block]) -> Vec<MissingControl> {
    let mut seen: BTreeMap<&RuleId, (bool, bool)> = BTreeMap::new();
    for b in blocks {
        let e = seen.entry(&b.rule).or_default();
        match b.expect {
            Expect::Fire => e.0 = true,
            Expect::Clean => e.1 = true,
        }
    }
    let mut out = Vec::new();
    for (rule, (fire, clean)) in seen {
        if !fire {
            out.push(MissingControl {
                rule: rule.clone(),
                missing: Missing::Fire,
            });
        }
        if !clean {
            out.push(MissingControl {
                rule: rule.clone(),
                missing: Missing::Clean,
            });
        }
    }
    out
}

/// Render `findings` of `block` with the full text renderer (source excerpt, labels, help).
fn render_diagnostics(block: &Block, findings: &[Finding]) -> String {
    let mut sources = MemorySources::new();
    for f in findings {
        let Some(span) = f.span else { continue };
        match SourceText::new(block.text.as_str()) {
            Ok(text) => sources.insert(span.file, block.file_name.as_str(), text),
            Err(e) => tracing::warn!(case = %block.name, error = %e, "block too large to render"),
        }
    }
    render_text(
        &DiagReport {
            findings,
            sources: &sources,
        },
        &TextOptions {
            color: ColorChoice::Never,
            snippets: true,
        },
    )
}

/// Snapshot name for `block` of the suite at `path`: `<stem>__<heading path and ordinal>`.
///
/// The fence line is dropped so moving a block does not orphan its snapshot.
fn snapshot_name(path: &Path, block: &Block) -> String {
    let stem = path
        .file_stem()
        .map_or_else(String::new, |s| s.to_string_lossy().into_owned());
    let base = block
        .name
        .rsplit_once(" (line ")
        .map_or(block.name.as_str(), |(b, _)| b);
    let raw = format!("{stem}__{base}");
    let mut out = String::new();
    for c in raw.chars() {
        if c.is_ascii_alphanumeric() || c == '-' {
            out.push(c.to_ascii_lowercase());
        } else if !out.ends_with('_') {
            out.push('_');
        }
    }
    out.trim_end_matches('_').to_owned()
}

/// Assert the rendered diagnostics of `block` against its insta snapshot beside the corpus.
///
/// Snapshots live in `snapshots/` next to the markdown file; `INSTA_UPDATE=always`
/// writes or refreshes them, and a mismatch fails with insta's diff on stderr.
fn check_snapshot(path: &Path, block: &Block, findings: &[Finding]) -> Result<(), String> {
    let rendered = render_diagnostics(block, findings);
    let name = snapshot_name(path, block);
    let dir = path.parent().unwrap_or(Path::new(".")).join("snapshots");
    let mut settings = insta::Settings::clone_current();
    settings.set_snapshot_path(dir);
    settings.set_prepend_module_to_snapshot(false);
    settings.set_omit_expression(true);
    let attempt = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        settings.bind(|| insta::assert_snapshot!(name.as_str(), rendered));
    }));
    attempt.map_err(|_| {
        format!(
            "    snapshot `{name}` does not match the rendered diagnostics (insta diff above)\n"
        )
    })
}

/// Run every block of one markdown file through `runner`.
pub fn run_file<R: CaseOutput, F: Fn(&Case) -> R>(path: &Path, runner: &Runner<F>) -> FileReport {
    let mut report = FileReport {
        path: path.to_path_buf(),
        parse_error: None,
        cases: Vec::new(),
        missing: Vec::new(),
    };
    let md = match std::fs::read_to_string(path) {
        Ok(m) => m,
        Err(e) => {
            report.parse_error = Some(format!("cannot read: {e}"));
            return report;
        }
    };
    let blocks = match parse_suite(&md) {
        Ok(b) => b,
        Err(e) => {
            report.parse_error = Some(e.to_string());
            return report;
        }
    };
    for b in &blocks {
        let case = Case {
            language: b.language.clone(),
            file_name: b.file_name.clone(),
            text: b.text.clone(),
            rule: b.rule.clone(),
            config: b.config.clone(),
        };
        let findings = (runner.0)(&case).into_findings();
        let mut outcome = check(b, &findings);
        if outcome.is_ok() && b.snapshot {
            outcome = check_snapshot(path, b, &findings);
        }
        tracing::debug!(case = %b.name, ok = outcome.is_ok(), "mdtest case");
        report.cases.push(CaseReport {
            name: b.name.clone(),
            outcome,
        });
    }
    report.missing = controls(&blocks);
    report
}

/// Run every `**/*.md` under `dir` (sorted) through `runner`.
pub fn run_dir<R: CaseOutput, F: Fn(&Case) -> R>(dir: &Path, runner: &Runner<F>) -> Report {
    let mut paths: Vec<PathBuf> = WalkDir::new(dir)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|e| e.file_type().is_file() && e.path().extension().is_some_and(|x| x == "md"))
        .map(walkdir::DirEntry::into_path)
        .collect();
    paths.sort();
    Report {
        files: paths.iter().map(|p| run_file(p, runner)).collect(),
    }
}

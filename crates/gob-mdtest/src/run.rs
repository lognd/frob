//! Running parsed blocks and rendering reports.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_diagnostics::{ColorChoice, MemorySources, Report as DiagReport, TextOptions, render_text};
use gob_rules::{Finding, RuleId, RuleReport, Severity};
use gob_text::{LineIndex, SourceText};
use walkdir::WalkDir;

use crate::contain::{Panicked, contained};
use crate::parse::{Block, Expect, Marker, Subjects, parse_document};

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
    /// Extra rules the case selects (`rules=`); findings of these must be marked.
    pub rules: Vec<RuleId>,
    /// Effective TOML config (inherited section config merged with inline `config=`), if any.
    pub config: Option<String>,
    /// Every file of the case: index 0 is the case block itself, then its `file=` blocks in
    /// document order. A finding belongs to `files[i]` when its span's `FileId::index()` is `i`;
    /// a spanless finding or an out-of-range index belongs to file 0.
    pub files: Vec<CaseFile>,
}

// frob:ticket 01M48PC09SX0KFAM4B3V88AAXW
impl Case {
    /// Re-point every finding's span at the position of its file in [`Case::files`].
    ///
    /// `path_of` names the file a runner-side `FileId` refers to; a path that matches no
    /// `files[i].file_name` is left to the harness, which attributes it to file 0.
    pub fn attribute<'a>(
        &self,
        findings: &mut [Finding],
        path_of: impl Fn(gob_text::FileId) -> Option<&'a str>,
    ) {
        let mut ids = gob_text::FileInterner::new();
        for f in &self.files {
            ids.intern(&f.file_name);
        }
        for f in findings {
            if let Some(span) = f.span.as_mut()
                && let Some(p) = path_of(span.file)
            {
                span.file = ids.intern(p);
            }
        }
    }
}

/// One file of a multi-file [`Case`].
#[derive(Debug, Clone)]
pub struct CaseFile {
    /// Fence language of the file.
    pub language: String,
    /// Virtual file name.
    pub file_name: String,
    /// File text; finding offsets are relative to it.
    pub text: String,
    /// `fidelity=` of the file, if given.
    pub fidelity: Option<String>,
    /// `parse=` of the file, if given.
    pub parse: Option<String>,
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
    /// One line per inline snapshot edit written to the markdown (update mode only).
    pub updated: Vec<String>,
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
            let _ = writeln!(
                s,
                "{tag} {} ({} cases)",
                gob_path::Shown::with_home(&f.path, None),
                f.cases.len()
            );
            s.push_str(&f.render_failures());
        }
        s
    }
}

/// Everything one case run produced: findings plus the rule's subject accounting.
#[derive(Debug, Clone, Default)]
pub struct CaseResult {
    /// The findings the case's expectations are checked against.
    pub findings: Vec<Finding>,
    /// `(total, examined)` subjects, when the runner reports them; `None` for bare findings.
    pub subjects: Option<(usize, usize)>,
    /// Why the rule cannot apply to this artifact, when it reported `NotApplicable`.
    pub not_applicable: Option<String>,
}

/// What a runner closure may return for one case: bare findings or a full [`RuleReport`].
pub trait CaseOutput {
    /// The findings and subject accounting the case's expectations are checked against.
    fn into_result(self) -> CaseResult;
}

impl CaseOutput for Vec<Finding> {
    fn into_result(self) -> CaseResult {
        CaseResult {
            findings: self,
            ..CaseResult::default()
        }
    }
}

impl CaseOutput for RuleReport {
    fn into_result(self) -> CaseResult {
        tracing::debug!(
            rule = %self.rule,
            total = self.subjects_total,
            examined = self.subjects_examined,
            not_applicable = ?self.not_applicable,
            "mdtest case returned a rule report"
        );
        CaseResult {
            findings: self.findings,
            subjects: Some((self.subjects_total, self.subjects_examined)),
            not_applicable: self.not_applicable,
        }
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

    /// Evaluate one case with any panic contained (see [`crate::contain`]).
    pub(crate) fn evaluate(&self, case: &Case) -> Result<CaseResult, Panicked> {
        contained(|| (self.0)(case).into_result())
    }
}

/// What one finding looks like in block-relative terms (line 0 when spanless).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct Actual {
    /// Position in the case's files the finding belongs to.
    file: usize,
    /// 1-based line within that file.
    line: u32,
    /// Rule of the finding.
    rule: RuleId,
    /// Severity of the finding.
    severity: Severity,
    /// 1-based byte column (0 when spanless).
    col: u32,
    /// Finding message.
    message: String,
    /// Unresolved reason code, if any.
    reason: Option<String>,
    /// True when the finding is a required Unresolved.
    required: bool,
}

impl Actual {
    /// Short form `Severity RULE`, with `[reason]` for an Unresolved.
    fn short(&self) -> String {
        match (&self.reason, self.severity) {
            (Some(r), Severity::Unresolved) => format!("Unresolved[{r}] {}", self.rule),
            _ => format!("{:?} {}", self.severity, self.rule),
        }
    }

    /// Outcome class of the finding: `unresolved` for an Unresolved, else `fire`.
    fn class(&self) -> &'static str {
        match self.severity {
            Severity::Unresolved => "unresolved",
            Severity::Error => "fire",
        }
    }

    /// Short form plus column, message and required flag.
    fn detail(&self) -> String {
        let req = if self.required { " required" } else { "" };
        format!(
            "{}{req} [col {}] \"{}\"",
            self.short(),
            self.col,
            self.message
        )
    }

    /// True when this finding satisfies every constraint the marker states.
    fn satisfies(&self, m: &Marker) -> bool {
        self.file == m.file
            && self.line == m.line
            && self.rule == m.rule
            && self.severity == m.severity
            && m.col.is_none_or(|c| c == self.col)
            && m.message.as_ref().is_none_or(|t| self.message.contains(t))
            && m.reason
                .as_ref()
                .is_none_or(|r| self.reason.as_ref() == Some(r))
            && (!m.required || self.required)
    }
}

/// Convert findings to file-relative, sorted [`Actual`]s.
fn actuals(block: &Block, findings: &[Finding]) -> Vec<Actual> {
    let texts: Vec<&str> = std::iter::once(block.text.as_str())
        .chain(block.files.iter().map(|f| f.text.as_str()))
        .collect();
    let idx: Vec<Option<LineIndex>> = texts.iter().map(|t| LineIndex::new(t).ok()).collect();
    let mut out: Vec<Actual> = findings
        .iter()
        .map(|f| {
            let file = f
                .span
                .map(|s| s.file.index() as usize)
                .filter(|i| *i < texts.len())
                .unwrap_or(0);
            let lc = f
                .span
                .and_then(|s| idx[file].as_ref()?.line_col(s.range.start()));
            Actual {
                file,
                line: lc.map_or(0, |lc| lc.line),
                rule: f.rule.clone(),
                severity: f.severity,
                col: lc.map_or(0, |lc| lc.col),
                message: f.message.clone(),
                reason: f.reason.as_ref().map(|r| r.code().to_owned()),
                required: f.required.is_some(),
            }
        })
        .collect();
    out.sort();
    out
}

/// Describe a marker as the `Severity RULE [col N] "msg"` it asserts.
fn show_marker(m: &Marker) -> String {
    let mut s = match (&m.reason, m.severity) {
        (Some(r), Severity::Unresolved) => format!("Unresolved[{r}] {}", m.rule),
        _ => format!("{:?} {}", m.severity, m.rule),
    };
    if m.required {
        s.push_str(" required");
    }
    if let Some(c) = m.col {
        let _ = write!(s, " [col {c}]");
    }
    if let Some(t) = &m.message {
        let _ = write!(s, " \"{t}\"");
    }
    s
}

/// Pair each marker with a distinct satisfying finding; return unmatched markers and findings.
fn match_markers<'a>(
    markers: &'a [Marker],
    actual: &'a [Actual],
) -> (Vec<&'a Marker>, Vec<&'a Actual>, Vec<&'a Actual>) {
    let mut used = vec![false; actual.len()];
    let mut missing = Vec::new();
    for m in markers {
        match (0..actual.len()).find(|&i| !used[i] && actual[i].satisfies(m)) {
            Some(i) => used[i] = true,
            None => missing.push(m),
        }
    }
    let (hit, extra): (Vec<_>, Vec<_>) = actual.iter().zip(&used).partition(|(_, u)| **u);
    (
        missing,
        hit.into_iter().map(|(a, _)| a).collect(),
        extra.into_iter().map(|(a, _)| a).collect(),
    )
}

/// Render an expected-vs-actual table, one row per line; `!` marks unmatched entries.
fn diff(missing: &[&Marker], matched: &[&Actual], extra: &[&Actual]) -> String {
    let mut rows: BTreeMap<u32, (Vec<String>, Vec<String>, bool)> = BTreeMap::new();
    for a in matched {
        let r = rows.entry(a.line).or_default();
        r.0.push(a.short());
        r.1.push(a.short());
    }
    for m in missing {
        let r = rows.entry(m.line).or_default();
        r.0.push(show_marker(m));
        r.2 = true;
    }
    for a in extra {
        let r = rows.entry(a.line).or_default();
        r.1.push(a.detail());
        r.2 = true;
    }
    let mut s = String::from("    line | expected | actual\n");
    for (line, (e, a, bad)) in rows {
        let (e, a) = (e.join(", "), a.join(", "));
        let mark = if bad { "!" } else { " " };
        let dash = |x: String| if x.is_empty() { "-".to_owned() } else { x };
        let _ = writeln!(s, "  {mark} {line:>4} | {} | {}", dash(e), dash(a));
    }
    s
}

/// Fail unless the reported subject count satisfies the block's `subjects` constraint.
///
/// A clean block defaults to at least one subject; a runner that reports no accounting
/// is only held to an explicit constraint.
fn check_subjects(block: &Block, res: &CaseResult) -> Result<(), String> {
    let want = block
        .subjects
        .or((block.expect == Expect::Clean).then_some(Subjects::AtLeast(1)));
    match (want, res.subjects) {
        (Some(w), Some((total, examined))) if !w.admits(examined) => Err(format!(
            "    expected {w}, the rule examined {examined} of {total} subjects\n"
        )),
        (Some(w), None) if block.subjects.is_some() => Err(format!(
            "    expected {w}, but the runner reports no subject accounting\n"
        )),
        _ => Ok(()),
    }
}

/// Findings of a block without markers that neither the header assertion nor the rule under test covers.
///
/// A finding of another rule is always a stray. For the block rule under `expect=fire`, the header
/// matches Error findings; an optional (non-required) Unresolved finding is a stray. `unresolved`
/// blocks accept Unresolved; other classes are checked separately.
fn strays<'a>(block: &Block, actual: &'a [Actual]) -> Vec<&'a Actual> {
    actual
        .iter()
        .filter(|a| {
            if a.rule != block.rule {
                return true;
            }
            block.expect == Expect::Fire && a.severity == Severity::Unresolved && !a.required
        })
        .collect()
}

/// Report unexpected findings with their class, severity and reason.
fn unexpected_report(strays: &[&Actual]) -> String {
    let mut s = String::from("    unexpected findings no marker or header assertion matches\n");
    for a in strays {
        let _ = writeln!(
            s,
            "      class={} severity={:?} reason={} rule={} line={} [col {}] \"{}\"",
            a.class(),
            a.severity,
            a.reason.as_deref().unwrap_or("-"),
            a.rule,
            a.line,
            a.col,
            a.message
        );
    }
    s
}

/// Strict mode: in a marker-free block every selected finding must be covered by the header.
fn check_strict(block: &Block, actual: &[Actual]) -> Result<(), String> {
    if !block.markers.is_empty() {
        return Ok(());
    }
    let strays = strays(block, actual);
    if strays.is_empty() {
        Ok(())
    } else {
        Err(unexpected_report(&strays))
    }
}

/// Match the block's markers against `actual` as a multiset.
fn check_markers(block: &Block, actual: &[Actual]) -> Result<(), String> {
    let (missing, matched, extra) = match_markers(&block.markers, actual);
    if missing.is_empty() && extra.is_empty() {
        Ok(())
    } else {
        Err(diff(&missing, &matched, &extra))
    }
}

/// Check one block's result against its expected outcome class.
fn check(block: &Block, res: &CaseResult) -> Result<(), String> {
    // Only selected rules are judged: the block rule, `rules=` and marker rules. A runner that
    // evaluates more than that has its other findings ignored; selected ones are strict.
    let mine: Vec<Finding> = res
        .findings
        .iter()
        .filter(|f| {
            f.rule == block.rule
                || block.rules.contains(&f.rule)
                || block.markers.iter().any(|m| m.rule == f.rule)
        })
        .cloned()
        .collect();
    let actual = actuals(block, &mine);
    let unexpected = || diff(&[], &[], &actual.iter().collect::<Vec<_>>());
    if let (Some(why), false) = (&res.not_applicable, block.expect == Expect::NotApplicable) {
        return Err(format!(
            "    expected {}, but {} reported NotApplicable: {why}\n",
            block.expect, block.rule
        ));
    }
    match block.expect {
        Expect::Fire if !block.markers.is_empty() => check_markers(block, &actual)?,
        Expect::Fire => {
            // A required Unresolved fails the gate, so it fires; an optional one is no verdict.
            if !actual
                .iter()
                .any(|a| a.severity != Severity::Unresolved || a.required)
            {
                return Err(format!(
                    "    expected at least one {} finding that is not Unresolved, got {}\n{}",
                    block.rule,
                    actual.len(),
                    unexpected()
                ));
            }
        }
        Expect::Clean => {
            if !actual.is_empty() {
                return Err(format!(
                    "    expected no {} findings\n{}",
                    block.rule,
                    unexpected()
                ));
            }
        }
        Expect::Unresolved => {
            if let Some(a) = actual.iter().find(|a| a.severity != Severity::Unresolved) {
                return Err(format!(
                    "    expected only Unresolved findings, got {}\n{}",
                    a.short(),
                    unexpected()
                ));
            }
            let unresolved: Vec<&Actual> = actual
                .iter()
                .filter(|a| a.severity == Severity::Unresolved)
                .collect();
            if unresolved.is_empty() {
                return Err(format!(
                    "    expected an Unresolved {} finding, got none\n",
                    block.rule
                ));
            }
            if let Some(r) = &block.reason
                && !unresolved.iter().any(|a| a.reason.as_ref() == Some(r))
            {
                let got: Vec<String> = unresolved.iter().map(|a| a.short()).collect();
                return Err(format!(
                    "    expected Unresolved reason `{r}`, got {}\n",
                    got.join(", ")
                ));
            }
            if !block.markers.is_empty() {
                check_markers(block, &actual)?;
            }
        }
        Expect::NotApplicable => {
            let Some(why) = &res.not_applicable else {
                return Err(format!(
                    "    expected {} to report NotApplicable, it applied\n",
                    block.rule
                ));
            };
            if !actual.is_empty() {
                return Err(format!(
                    "    NotApplicable must carry no findings\n{}",
                    unexpected()
                ));
            }
            if let Some(r) = &block.reason
                && !why.contains(r.as_str())
            {
                return Err(format!(
                    "    expected NotApplicable reason `{r}`, got `{why}`\n"
                ));
            }
        }
    }
    check_strict(block, &actual)?;
    check_subjects(block, res)
}

/// Positive-control audit over the blocks of one file.
fn controls(blocks: &[Block]) -> Vec<MissingControl> {
    let mut seen: BTreeMap<&RuleId, (bool, bool)> = BTreeMap::new();
    for b in blocks {
        let e = seen.entry(&b.rule).or_default();
        match b.expect {
            Expect::Fire => e.0 = true,
            Expect::Clean => e.1 = true,
            Expect::Unresolved | Expect::NotApplicable => {}
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
    let stem = path.file_stem().map_or_else(String::new, |s| {
        gob_path::Shown::with_home(Path::new(s), None).to_string()
    });
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

/// Environment variable that switches inline snapshots to update mode when it is `1`.
pub const UPDATE_ENV: &str = "FROB_MDTEST_UPDATE";

/// Whether inline `snapshot` fences are checked or rewritten in the markdown.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum SnapshotMode {
    /// A missing, stale or orphan snapshot fails the case (the default).
    #[default]
    Check,
    /// Insert, rewrite or remove snapshot fences in the markdown; never changes a case header.
    Update,
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
impl SnapshotMode {
    /// Read [`UPDATE_ENV`]: `1` selects [`SnapshotMode::Update`]; unset, empty or `0` selects check.
    pub fn from_env() -> Self {
        Self::from_value(std::env::var(UPDATE_ENV).ok().as_deref())
    }

    /// Map an [`UPDATE_ENV`] value (`None` when unset) to a mode.
    pub fn from_value(value: Option<&str>) -> Self {
        match value.map(str::trim) {
            Some("1") => Self::Update,
            _ => Self::Check,
        }
    }
}

/// One edit to the markdown lines: replace `start..end` (0-based, end exclusive) with `with`.
#[derive(Debug, Clone)]
struct Edit {
    start: usize,
    end: usize,
    with: Vec<String>,
    what: String,
}

/// Fence lines recording `rendered` as a `snapshot` block (the fence outgrows any backtick run inside).
fn snapshot_lines(rendered: &str) -> Vec<String> {
    let longest = rendered
        .lines()
        .map(|l| {
            let mut run = 0usize;
            l.chars()
                .map(|c| {
                    run = if c == '`' { run + 1 } else { 0 };
                    run
                })
                .max()
                .unwrap_or(0)
        })
        .max()
        .unwrap_or(0);
    let fence = "`".repeat(longest.saturating_add(1).max(3));
    let mut out = vec![format!("{fence}snapshot")];
    out.extend(rendered.trim_end().lines().map(str::to_owned));
    out.push(fence);
    out
}

/// The edit that removes the fence spanning 1-based lines `open..=close` and the blank line before it.
fn removal(lines: &[String], open: usize, close: usize, what: String) -> Edit {
    let mut start = open - 1;
    if start > 0 && lines.get(start - 1).is_some_and(|l| l.trim().is_empty()) {
        start -= 1;
    }
    Edit {
        start,
        end: close,
        with: Vec::new(),
        what,
    }
}

/// Judge `rendered` against the case's inline snapshot: `Ok(None)` matches, `Ok(Some(edit))` is
/// what update mode would write, and `Err` is the failure text of check mode.
fn inline_verdict(
    b: &Block,
    rendered: &str,
    lines: &[String],
) -> Result<Option<Edit>, (String, Edit)> {
    let hint = format!("rerun with {UPDATE_ENV}=1 to write it");
    let actual = rendered.trim_end();
    match &b.inline {
        Some(f) if f.body.trim_end() == actual => Ok(None),
        Some(f) => {
            let edit = if actual.is_empty() {
                removal(
                    lines,
                    f.open_line,
                    f.close_line,
                    format!("removed stale snapshot at line {}", f.open_line),
                )
            } else {
                Edit {
                    start: f.open_line - 1,
                    end: f.close_line,
                    with: snapshot_lines(rendered),
                    what: format!("rewrote snapshot at line {}", f.open_line),
                }
            };
            Err((
                format!(
                    "    stale inline snapshot (line {}): it differs from the rendered diagnostics; {hint}\n    --- recorded\n{}\n    --- rendered\n{}\n",
                    f.open_line,
                    indent(f.body.trim_end()),
                    indent(actual)
                ),
                edit,
            ))
        }
        None if actual.is_empty() || !b.inline_required => Ok(None),
        None => Err((
            format!(
                "    missing inline snapshot: `inline-snapshots` is on and the case renders diagnostics but has no `snapshot` fence after it (line {}); {hint}\n    --- rendered\n{}\n",
                b.fence_line,
                indent(actual)
            ),
            Edit {
                start: b.end_line,
                end: b.end_line,
                with: std::iter::once(String::new())
                    .chain(snapshot_lines(rendered))
                    .collect(),
                what: format!("inserted snapshot after line {}", b.end_line),
            },
        )),
    }
}

/// Indent every line of `text` by eight spaces for failure output.
fn indent(text: &str) -> String {
    text.lines()
        .map(|l| format!("        {l}"))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Apply `edits` to the markdown `lines` bottom-to-top and join them back.
fn apply_edits(lines: &mut Vec<String>, mut edits: Vec<Edit>) -> String {
    edits.sort_by_key(|e| std::cmp::Reverse((e.start, e.end)));
    for e in edits {
        let end = e.end.min(lines.len());
        lines.splice(e.start.min(end)..end, e.with);
    }
    lines.join("\n")
}

/// Run one block through `runner` with panics contained, and judge it against its expectations.
///
/// The second value is the rendered diagnostics when the case passed and an inline snapshot applies.
fn run_case<R: CaseOutput, F: Fn(&Case) -> R>(
    path: &Path,
    b: &Block,
    case: &Case,
    runner: &Runner<F>,
) -> (Result<(), String>, Option<String>) {
    let ran = runner.evaluate(case);
    match (ran, &b.expect_panic) {
        (Ok(result), None) => {
            let outcome = check(b, &result);
            if outcome.is_ok() {
                let wants = b.inline.is_some() || b.inline_required;
                // No findings means nothing to record: the renderer's summary line is not a snapshot.
                let rendered = wants.then(|| {
                    if result.findings.is_empty() {
                        String::new()
                    } else {
                        render_diagnostics(b, &result.findings)
                    }
                });
                let snap = if b.snapshot {
                    check_snapshot(path, b, &result.findings)
                } else {
                    outcome
                };
                (snap, rendered)
            } else {
                (outcome, None)
            }
        }
        (Ok(result), Some(sub)) => {
            let mut msg = format!(
                "    expected the runner to panic{}, but it returned (line {})\n",
                quoted_substring(sub),
                b.fence_line
            );
            if let Err(other) = check(b, &result) {
                msg.push_str("    it also failed its expectations:\n");
                msg.push_str(&other);
            }
            (Err(msg), None)
        }
        (Err(p), None) => (
            Err(format!(
                "    the runner panicked at markdown line {}: {}{}\n",
                b.fence_line,
                p.message,
                at(&p)
            )),
            None,
        ),
        (Err(p), Some(sub)) if p.message.contains(sub.as_str()) => {
            tracing::debug!(case = %b.name, "expected panic observed");
            (Ok(()), None)
        }
        (Err(p), Some(sub)) => (
            Err(format!(
                "    expected a panic{}, but the runner panicked at markdown line {} with: {}{}\n",
                quoted_substring(sub),
                b.fence_line,
                p.message,
                at(&p)
            )),
            None,
        ),
    }
}

/// Text for the "containing" clause of a message, or nothing for the empty any-panic substring.
fn quoted_substring(sub: &str) -> String {
    if sub.is_empty() {
        String::new()
    } else {
        format!(" containing `{sub}`")
    }
}

/// ` (at file:line)` for a panic whose location is known.
fn at(p: &Panicked) -> String {
    p.location
        .as_ref()
        .map_or_else(String::new, |l| format!(" (at {l})"))
}

/// Run every block of one markdown file through `runner`, in the mode [`SnapshotMode::from_env`] gives.
pub fn run_file<R: CaseOutput, F: Fn(&Case) -> R>(path: &Path, runner: &Runner<F>) -> FileReport {
    run_file_with(path, runner, SnapshotMode::from_env())
}

/// The runner input for block `b`: the case block first, then its `file=` blocks.
fn case_of(b: &Block) -> Case {
    Case {
        language: b.language.clone(),
        file_name: b.file_name.clone(),
        text: b.text.clone(),
        rule: b.rule.clone(),
        rules: b.rules.clone(),
        config: b.config.clone(),
        files: std::iter::once(CaseFile {
            language: b.language.clone(),
            file_name: b.file_name.clone(),
            text: b.text.clone(),
            fidelity: b.fidelity.clone(),
            parse: b.parse.clone(),
        })
        .chain(b.files.iter().map(|f| CaseFile {
            language: f.language.clone(),
            file_name: f.file_name.clone(),
            text: f.text.clone(),
            fidelity: f.fidelity.clone(),
            parse: f.parse.clone(),
        }))
        .collect(),
    }
}

// frob:ticket 01M48PC0TZ7MHW4KA89V6ZFY72
/// Run every block of one markdown file, checking or updating its inline `snapshot` fences per `mode`.
pub fn run_file_with<R: CaseOutput, F: Fn(&Case) -> R>(
    path: &Path,
    runner: &Runner<F>,
    mode: SnapshotMode,
) -> FileReport {
    let mut report = FileReport {
        path: path.to_path_buf(),
        parse_error: None,
        cases: Vec::new(),
        missing: Vec::new(),
        updated: Vec::new(),
    };
    let md = match std::fs::read_to_string(path) {
        Ok(m) => m,
        Err(e) => {
            report.parse_error = Some(format!("cannot read: {e}"));
            return report;
        }
    };
    let parsed = match parse_document(&md) {
        Ok(p) => p,
        Err(e) => {
            report.parse_error = Some(e.to_string());
            return report;
        }
    };
    let lines: Vec<String> = md.split('\n').map(str::to_owned).collect();
    let mut edits: Vec<Edit> = Vec::new();
    for b in &parsed.blocks {
        let case = case_of(b);
        let (mut outcome, rendered) = run_case(path, b, &case, runner);
        if let (Ok(()), Some(rendered)) = (&outcome, &rendered) {
            match (inline_verdict(b, rendered, &lines), mode) {
                (Ok(_), _) => {}
                (Err((_, edit)), SnapshotMode::Update) => {
                    tracing::info!(case = %b.name, edit = %edit.what, "inline snapshot update");
                    edits.push(edit);
                }
                (Err((msg, _)), SnapshotMode::Check) => outcome = Err(msg),
            }
        } else if outcome.is_err()
            && mode == SnapshotMode::Update
            && (b.inline.is_some() || b.inline_required)
        {
            tracing::warn!(case = %b.name, "inline snapshot not updated: the case fails first");
            if let Err(m) = &mut outcome {
                m.push_str(
                    "    inline snapshot not updated: the case fails its expectations first\n",
                );
            }
        }
        tracing::debug!(case = %b.name, ok = outcome.is_ok(), "mdtest case");
        report.cases.push(CaseReport {
            name: b.name.clone(),
            outcome,
        });
    }
    for o in &parsed.orphans {
        let what = format!("removed orphan snapshot at line {}", o.open_line);
        match mode {
            SnapshotMode::Update => {
                tracing::info!(line = o.open_line, "orphan inline snapshot removed");
                edits.push(removal(&lines, o.open_line, o.close_line, what));
            }
            SnapshotMode::Check => report.cases.push(CaseReport {
                name: format!("orphan snapshot (line {})", o.open_line),
                outcome: Err(format!(
                    "    orphan inline snapshot (line {}): no case of its section precedes it; {UPDATE_ENV}=1 removes it\n",
                    o.open_line
                )),
            }),
        }
    }
    if !edits.is_empty() {
        let whats: Vec<String> = edits.iter().map(|e| e.what.clone()).collect();
        let mut lines = lines;
        let text = apply_edits(&mut lines, edits);
        match std::fs::write(path, text) {
            Ok(()) => report.updated = whats,
            Err(e) => report.cases.push(CaseReport {
                name: "inline snapshot update".into(),
                outcome: Err(format!(
                    "    cannot write {}: {e}\n",
                    gob_path::Shown::with_home(path, None)
                )),
            }),
        }
    }
    report.missing = controls(&parsed.blocks);
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

//! Text renderer: findings grouped by file with snippets and a summary.

use std::borrow::Cow;
use std::collections::{BTreeMap, HashMap};
use std::fmt::Write as _;
use std::io::IsTerminal;

use anstyle::{AnsiColor, Style};
use gob_rules::{
    Applicability, Finding, Fingerprint, Fix, Registry, Severity, TextEdit, UnresolvedReason,
};
use gob_text::{Span, TextSize, render_snippet};

use crate::escape::{escape_for_origin, escape_text};
use crate::record::{SecurityDecisionKind, Summary, TextOrigin};
use crate::source::SourceProvider;

/// Whether the renderer emits ANSI color; the caller decides (TTY, `NO_COLOR`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ColorChoice {
    /// Always emit ANSI escapes.
    Always,
    /// Never emit ANSI escapes.
    Never,
}

/// Options for [`render_text`].
#[derive(Debug, Clone, Copy)]
pub struct TextOptions {
    /// Color policy.
    pub color: ColorChoice,
    /// Include source snippets under each located finding.
    pub snippets: bool,
}

/// Findings plus the sources needed to locate them.
pub struct Report<'a> {
    /// Findings to render.
    pub findings: &'a [Finding],
    /// Source lookup for paths, lines and snippets.
    pub sources: &'a dyn SourceProvider,
}

/// True when `stream` is a terminal (callers also honor `NO_COLOR`).
pub fn is_tty(stream: &impl IsTerminal) -> bool {
    stream.is_terminal()
}

/// Lowercase label for a severity.
pub const fn severity_label(s: Severity) -> &'static str {
    match s {
        Severity::Unresolved => "unresolved",
        Severity::Advisory => "advisory",
        Severity::Warn => "warning",
        Severity::Error => "error",
    }
}

fn style_for(s: Severity) -> Style {
    let color = match s {
        Severity::Unresolved => AnsiColor::Magenta,
        Severity::Advisory => AnsiColor::Cyan,
        Severity::Warn => AnsiColor::Yellow,
        Severity::Error => AnsiColor::Red,
    };
    Style::new().bold().fg_color(Some(color.into()))
}

/// A secondary span, usually in another file, with the label that says why it matters.
#[derive(Debug, Clone)]
pub struct SecondarySpan {
    /// Where the related code is.
    pub span: Span,
    /// Short label printed under the underline.
    pub label: String,
}

/// Teaching content for one finding (diagnostics.md section 2); every field is host text.
#[derive(Debug, Clone, Default)]
pub struct FindingNotes {
    /// Label printed after the primary underline.
    pub primary_label: Option<String>,
    /// Related spans, rendered as `:::` blocks.
    pub secondary: Vec<SecondarySpan>,
    /// Facts the user did not ask for but needs (`= note:`).
    pub notes: Vec<String>,
    /// The next action (`= help:`); dropped under `--quiet`.
    pub help: Option<String>,
    /// How to read the full explanation (`= explain:`).
    pub explain: Option<String>,
}

/// Per-finding [`FindingNotes`] keyed by fingerprint, plus the `--quiet` switch.
#[derive(Debug, Clone, Default)]
pub struct Annotations {
    /// Drop help lines (`--quiet`); message, span and code remain.
    pub quiet: bool,
    notes: HashMap<Fingerprint, FindingNotes>,
}

impl Annotations {
    /// Attach `notes` to the finding with `fingerprint`; such a finding renders in section 2 shape.
    pub fn insert(&mut self, fingerprint: Fingerprint, notes: FindingNotes) {
        tracing::debug!("finding annotated");
        self.notes.insert(fingerprint, notes);
    }
}

/// One finding resolved for display.
struct Located<'a> {
    finding: &'a Finding,
    line: u32,
}

/// Render `report` as text, showing and counting each Unresolved finding's required reason.
pub fn render_text(report: &Report<'_>, opts: &TextOptions) -> String {
    render_text_with_decisions(report, opts, &[])
}

/// Render `report` as text, also counting the run's security `decisions` in the summary (I13).
pub fn render_text_with_decisions(
    report: &Report<'_>,
    opts: &TextOptions,
    decisions: &[SecurityDecisionKind],
) -> String {
    render_text_annotated(report, opts, decisions, &Annotations::default())
}

/// Render `report` as text; findings with [`Annotations`] get the section 2 message shape.
pub fn render_text_annotated(
    report: &Report<'_>,
    opts: &TextOptions,
    decisions: &[SecurityDecisionKind],
    annotations: &Annotations,
) -> String {
    let registry = Registry::global();
    let mut groups: BTreeMap<Option<String>, Vec<Located<'_>>> = BTreeMap::new();
    for f in report.findings {
        let (path, line) = f.span.map_or((None, 0), |sp| {
            let line = report
                .sources
                .source(sp.file)
                .and_then(|s| s.line_col(sp.range.start()))
                .map_or(0, |l| l.line);
            (report.sources.path(sp.file).map(str::to_owned), line)
        });
        groups
            .entry(path)
            .or_default()
            .push(Located { finding: f, line });
    }
    // BTreeMap orders None first; the located files must come first.
    let mut ordered: Vec<_> = groups.into_iter().collect();
    ordered.sort_by(|a, b| match (&a.0, &b.0) {
        (None, None) => std::cmp::Ordering::Equal,
        (None, Some(_)) => std::cmp::Ordering::Greater,
        (Some(_), None) => std::cmp::Ordering::Less,
        (Some(x), Some(y)) => x.cmp(y),
    });

    let mut out = String::new();
    for (path, mut items) in ordered {
        items.sort_by_key(|l| l.line);
        let _ = writeln!(
            out,
            "{}",
            path.as_deref()
                .map_or(Cow::Borrowed("(no location)"), escape_text)
        );
        for item in &items {
            write_finding(&mut out, report, item, registry, *opts, annotations);
        }
        out.push('\n');
    }
    write_summary(&mut out, &Summary::of(report.findings, decisions));
    tracing::debug!(findings = report.findings.len(), "text rendered");
    match opts.color {
        ColorChoice::Always => out,
        ColorChoice::Never => anstream::adapter::strip_str(&out).to_string(),
    }
}

fn write_finding(
    out: &mut String,
    report: &Report<'_>,
    item: &Located<'_>,
    registry: &Registry,
    opts: TextOptions,
    annotations: &Annotations,
) {
    let f = item.finding;
    if let Some(notes) = annotations.notes.get(&f.fingerprint) {
        write_shaped(out, report, f, notes, registry, opts, annotations.quiet);
        return;
    }
    let st = style_for(f.severity);
    let slug = registry
        .by_id(f.rule.as_str())
        .map_or(String::new(), |m| format!(" {}", m.slug));
    let col = f
        .span
        .and_then(|sp| {
            report
                .sources
                .source(sp.file)
                .and_then(|s| s.line_col(sp.range.start()))
        })
        .map_or(String::new(), |l| format!("{}:{}: ", l.line, l.col));
    let origin = TextOrigin::of_rule(registry.provenance(f.rule.as_str()));
    let _ = writeln!(
        out,
        "  {col}{st}{}[{}{slug}]{st:#}: {}{}",
        severity_label(f.severity),
        f.rule,
        origin_prefix(&origin),
        escape_for_origin(&f.message, &origin)
    );
    if opts.snippets
        && let Some(sp) = f.span
        && let Some(src) = report.sources.source(sp.file)
        && let Some(snip) = render_snippet(src, sp.range)
    {
        let gutter = snip.line_number.to_string();
        let pad = " ".repeat(gutter.len());
        let _ = writeln!(out, "  {pad} |");
        let _ = writeln!(out, "  {gutter} | {}", escape_text(&snip.line));
        let _ = writeln!(out, "  {pad} | {st}{}{st:#}", snip.caret_line);
    }
    if let Some(reason) = f.required.as_ref() {
        let _ = writeln!(out, "  required: {}", escape_text(&reason.to_string()));
    }
    if let Some(reason) = f
        .reason
        .as_ref()
        .filter(|_| f.severity == Severity::Unresolved)
    {
        let (words, remedy) = reason_words(reason);
        let _ = writeln!(out, "  reason: {words} ({})", escape_text(reason.code()));
        let _ = writeln!(out, "  remedy: {remedy}");
    }
    if let Some(fix) = &f.fix {
        write_fix(out, report.sources, fix);
    }
}

/// Line number, column, display path and snippet for `span`, when its source is known.
fn locate(
    sources: &dyn SourceProvider,
    span: Span,
) -> Option<(String, u32, u32, gob_text::Snippet)> {
    let src = sources.source(span.file)?;
    let lc = src.line_col(span.range.start())?;
    let snip = render_snippet(src, span.range)?;
    let path = sources.path(span.file)?;
    Some((escape_text(path).into_owned(), lc.line, lc.col, snip))
}

/// Write one snippet block: gutter, source line and underline (`mark` replaces the caret glyph).
fn write_block(out: &mut String, snip: &gob_text::Snippet, width: usize, mark: char, label: &str) {
    let num = snip.line_number.to_string();
    let underline = snip.caret_line.replace('^', &mark.to_string());
    let label = if label.is_empty() {
        String::new()
    } else {
        format!(" {}", escape_text(label))
    };
    let _ = writeln!(out, "  {:>width$} | {}", num, escape_text(&snip.line));
    let _ = writeln!(out, "  {:width$} | {underline}{label}", "");
}

/// Write a finding in the diagnostics.md section 2 shape; `quiet` drops the help line.
fn write_shaped(
    out: &mut String,
    report: &Report<'_>,
    f: &Finding,
    notes: &FindingNotes,
    registry: &Registry,
    opts: TextOptions,
    quiet: bool,
) {
    let st = style_for(f.severity);
    let origin = TextOrigin::of_rule(registry.provenance(f.rule.as_str()));
    let _ = writeln!(
        out,
        "  {st}{}[{}]{st:#}: {}{}",
        severity_label(f.severity),
        f.rule,
        origin_prefix(&origin),
        escape_for_origin(&f.message, &origin)
    );
    let primary = f.span.and_then(|sp| locate(report.sources, sp));
    let secondary: Vec<_> = notes
        .secondary
        .iter()
        .filter_map(|s| locate(report.sources, s.span).map(|l| (l, s.label.as_str())))
        .collect();
    let width = primary
        .iter()
        .map(|p| p.1)
        .chain(secondary.iter().map(|s| s.0.1))
        .max()
        .map_or(1, |n| n.to_string().len());
    let blank = format!("  {:width$} |", "");
    if let Some((path, line, col, snip)) = &primary {
        let _ = writeln!(out, "  {:width$}--> {path}:{line}:{col}", "");
        if opts.snippets {
            let _ = writeln!(out, "{blank}");
            write_block(
                out,
                snip,
                width,
                '^',
                notes.primary_label.as_deref().unwrap_or(""),
            );
        }
    }
    for ((path, line, col, snip), label) in &secondary {
        let _ = writeln!(out, "{blank}");
        let _ = writeln!(out, "  {:width$}::: {path}:{line}:{col}", "");
        if opts.snippets {
            let _ = writeln!(out, "{blank}");
            write_block(out, snip, width, '-', label);
        }
    }
    let mut tail: Vec<String> = notes
        .notes
        .iter()
        .map(|n| format!("note: {}", escape_text(n)))
        .collect();
    match (&notes.help, quiet) {
        (Some(h), false) => tail.push(format!("help: {}", escape_text(h))),
        (Some(_), true) => tracing::debug!("help line dropped by --quiet"),
        _ => {}
    }
    if let Some(fix) = f.fix.as_ref()
        && let Some(lead) = fix_lead(fix.applicability)
    {
        tail.push(format!("{lead}: {}", escape_text(&fix.title)));
    }
    if let Some(e) = &notes.explain {
        tail.push(format!("explain: {}", escape_text(e)));
    }
    if !tail.is_empty() {
        let _ = writeln!(out, "{blank}");
    }
    for line in tail {
        let _ = writeln!(out, "  {:width$} = {line}", "");
    }
}

/// Lead words of the section 2 `fix` line; `None` for a fix with no machine edit to show.
const fn fix_lead(a: Applicability) -> Option<&'static str> {
    match a {
        Applicability::Machine => Some("fix"),
        Applicability::MaybeIncorrect => Some("fix (needs review)"),
        Applicability::HasPlaceholders => Some("fix (fill in the placeholders)"),
        Applicability::Manual => None,
    }
}

/// Label for text a pack wrote (`pack(NAME) says: `); empty for host and std text (security.md 2.10).
fn origin_prefix(origin: &TextOrigin) -> String {
    match origin {
        TextOrigin::Pack(name) => {
            tracing::debug!(pack = %name, "labeling pack-authored message");
            format!("pack({}) says: ", escape_for_origin(name, origin))
        }
        _ => String::new(),
    }
}

/// Words for an Unresolved reason and the remedy that would let the rule decide.
fn reason_words(reason: &UnresolvedReason) -> (&'static str, &'static str) {
    match reason {
        UnresolvedReason::AnnotationSignature => (
            "a public signature has no type annotation",
            "annotate the signature",
        ),
        UnresolvedReason::AnnotationEffects => (
            "a function has no effect declaration",
            "declare the function's effects",
        ),
        UnresolvedReason::DynamicUnresolvable => (
            "the target of dynamic dispatch or reflection is unknown",
            "make the call static or annotate its target",
        ),
        UnresolvedReason::DynamicStringCode => (
            "a region is code held as a string",
            "move the code out of the string or annotate it",
        ),
        UnresolvedReason::ExpansionBudget => (
            "macro or template expansion exceeded its step budget",
            "simplify the expansion or raise the budget",
        ),
        UnresolvedReason::NormalizationUnverified => (
            "a dependent definition was not accepted by the termination checker",
            "make the definition structurally terminating",
        ),
        UnresolvedReason::OrderUnrecorded => (
            "no execution order is recorded",
            "record the execution order",
        ),
        UnresolvedReason::Opaque(_) => ("an opaque region was not analyzed", "annotate the region"),
        UnresolvedReason::DynamicSite => (
            "a type-dependent answer sits at a site with no type (Any, dynamic, reflection)",
            "annotate the receiver with a concrete type",
        ),
        UnresolvedReason::ConflictAnnotationInference => (
            "an annotation and local inference disagree",
            "fix the annotation or the code; this is a likely bug",
        ),
        UnresolvedReason::UntrustedType => (
            "a type fact is not trusted without checker closure",
            "run the type checker in its strictest configuration",
        ),
        UnresolvedReason::NotRun => (
            "the type checker was not run",
            "run the configured type checker",
        ),
        UnresolvedReason::Hole => ("the code has a hole or parse error", "fill or fix the hole"),
        UnresolvedReason::EdgeMay => (
            "the deciding edge is only possible, not certain",
            "resolve the edge or add an exception",
        ),
        UnresolvedReason::EdgeUnknown => (
            "the deciding edge or answer is unknown",
            "supply the missing facts or add an exception",
        ),
        UnresolvedReason::Vacuous => (
            "the rule examined zero subjects",
            "point the rule at a scope with subjects or drop it",
        ),
        UnresolvedReason::Fidelity => (
            "the language support is too shallow for this rule",
            "use a richer adapter or disable the rule here",
        ),
        UnresolvedReason::ParseFailed => (
            "a file could not be read or parsed",
            "fix the file so it parses",
        ),
        UnresolvedReason::Partial => (
            "a file parsed only partially, with holes",
            "fix the parse errors",
        ),
        UnresolvedReason::Budget => (
            "the evaluation budget ran out before the answer was decided",
            "raise the budget or narrow the scope",
        ),
    }
}

/// Trailing note for a fix tier that a human must act on, if any.
const fn tier_note(a: Applicability) -> Option<&'static str> {
    match a {
        Applicability::Machine => None,
        Applicability::MaybeIncorrect => Some("unsafe: review the diff before applying"),
        Applicability::HasPlaceholders => Some("unsafe: fill in the placeholders before applying"),
        Applicability::Manual => Some("display-only: no edit is attached; apply by hand"),
    }
}

/// Write `fix` as `fix[tier]: title`, a unified diff of its edits, and a note for unsafe tiers.
fn write_fix(out: &mut String, sources: &dyn SourceProvider, fix: &Fix) {
    let _ = writeln!(
        out,
        "  fix[{}]: {}",
        fix.applicability.label(),
        escape_text(&fix.title)
    );
    for edit in &fix.edits {
        write_edit_diff(out, sources, edit);
    }
    if let Some(note) = tier_note(fix.applicability) {
        let _ = writeln!(out, "  note: {note}");
    }
}

/// Write one edit as a unified-diff hunk over the whole lines it touches.
fn write_edit_diff(out: &mut String, sources: &dyn SourceProvider, edit: &TextEdit) {
    let (Some(path), Some(src)) = (sources.path(edit.file), sources.source(edit.file)) else {
        tracing::warn!("fix edit has no resolvable source; diff omitted");
        return;
    };
    let text = src.as_str();
    let (start, end) = (edit.range.start(), edit.range.end());
    let last = if end > start {
        TextSize::new(u32::from(end) - 1)
    } else {
        end
    };
    let (Some(first_lc), Some(last_lc)) = (src.line_col(start), src.line_col(last)) else {
        tracing::warn!("fix edit range outside its source; diff omitted");
        return;
    };
    let idx = src.line_index();
    let (Some(ls), Some(le)) = (
        idx.line_start(first_lc.line),
        idx.line_end(text, last_lc.line),
    ) else {
        return;
    };
    let (Some(head), Some(tail)) = (
        text.get(ls.to_usize()..start.to_usize()),
        text.get(end.to_usize()..le.to_usize().max(end.to_usize())),
    ) else {
        tracing::warn!("fix edit not on char boundaries; diff omitted");
        return;
    };
    let old = text
        .get(ls.to_usize()..le.to_usize().max(end.to_usize()))
        .unwrap_or("");
    let new = format!("{head}{}{tail}", edit.replacement);
    let old_lines: Vec<&str> = old.split('\n').collect();
    let new_lines: Vec<&str> = new.split('\n').collect();
    let p = escape_text(path);
    let _ = writeln!(out, "    --- {p}");
    let _ = writeln!(out, "    +++ {p}");
    let _ = writeln!(
        out,
        "    @@ -{},{} +{},{} @@",
        first_lc.line,
        old_lines.len(),
        first_lc.line,
        new_lines.len()
    );
    for l in old_lines {
        let _ = writeln!(out, "    -{}", escape_text(l));
    }
    for l in new_lines {
        let _ = writeln!(out, "    +{}", escape_text(l));
    }
}

fn write_summary(out: &mut String, summary: &Summary) {
    let _ = writeln!(
        out,
        "{} errors, {} warnings, {} advisory, {} unresolved ({} required)",
        summary.errors, summary.warnings, summary.advisory, summary.unresolved, summary.required
    );
    if summary.unresolved > 0 {
        let _ = writeln!(
            out,
            "  unresolved: {} because a plugin did not finish, {} because the code is undecidable",
            summary.plugin_unfinished, summary.undecidable
        );
    }
    if !summary.security_decisions.is_empty() {
        let parts: Vec<String> = SecurityDecisionKind::ALL
            .iter()
            .filter_map(|k| {
                summary
                    .security_decisions
                    .get(k)
                    .map(|n| format!("{n} {}", k.label()))
            })
            .collect();
        let _ = writeln!(out, "  security decisions: {}", parts.join(", "));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::source::MemorySources;

    fn shaped_fixture() -> (MemorySources, Vec<Finding>, Annotations) {
        use gob_text::{FileInterner, SourceText, TextRange};
        let mut files = FileInterner::new();
        let (a, b) = (
            files.intern("src/lib.rs"),
            files.intern("design/model.grmb"),
        );
        let mut sources = MemorySources::new();
        sources.insert(
            a,
            "src/lib.rs",
            SourceText::new("pub fn run() {}\n").unwrap(),
        );
        sources.insert(
            b,
            "design/model.grmb",
            SourceText::new("  owns \"x/**\" ;\n").unwrap(),
        );
        let finding = Finding::new(
            "DOC001".parse().unwrap(),
            Severity::Error,
            Some(Span::new(a, TextRange::new(0u32.into(), 6u32.into()))),
            "unit claimed by two bindings",
            "src/lib.rs",
        )
        .with_fix(Fix {
            kind: gob_rules::FixKind::Manual,
            applicability: Applicability::MaybeIncorrect,
            title: "narrow the selector".into(),
            edits: vec![],
        });
        let mut ann = Annotations::default();
        ann.insert(
            finding.fingerprint,
            FindingNotes {
                primary_label: Some("bound by a directive".into()),
                secondary: vec![SecondarySpan {
                    span: Span::new(b, TextRange::new(2u32.into(), 13u32.into())),
                    label: "also owned through this selector".into(),
                }],
                notes: vec!["a directive outranks a selector".into()],
                help: Some("remove the directive".into()),
                explain: Some("frob explain DOC001".into()),
            },
        );
        (sources, vec![finding], ann)
    }

    fn shaped(quiet: bool) -> String {
        let (sources, findings, mut ann) = shaped_fixture();
        ann.quiet = quiet;
        let report = Report {
            findings: &findings,
            sources: &sources,
        };
        let opts = TextOptions {
            color: ColorChoice::Never,
            snippets: true,
        };
        render_text_annotated(&report, &opts, &[], &ann)
    }

    // frob:tests render_text_annotated
    #[test]
    fn secondary_span_and_review_fix_match_section_two_shape() {
        let out = shaped(false);
        let want = "\
src/lib.rs
  error[DOC001]: unit claimed by two bindings
   --> src/lib.rs:1:1
    |
  1 | pub fn run() {}
    | ^^^^^^ bound by a directive
    |
   ::: design/model.grmb:1:3
    |
  1 |   owns \"x/**\" ;
    |   ----------- also owned through this selector
    |
    = note: a directive outranks a selector
    = help: remove the directive
    = fix (needs review): narrow the selector
    = explain: frob explain DOC001
";
        assert!(out.starts_with(want), "{out}");
        assert!(out.is_ascii());
    }

    // frob:tests render_text_annotated
    #[test]
    fn quiet_drops_help_and_keeps_message_span_and_code() {
        let out = shaped(true);
        assert!(!out.contains("help:"), "{out}");
        assert!(
            out.contains("error[DOC001]: unit claimed by two bindings"),
            "{out}"
        );
        assert!(out.contains("^^^^^^"), "{out}");
        assert!(out.contains("= note:"), "{out}");
    }

    // frob:tests origin_prefix
    #[test]
    fn pack_message_is_prefixed() {
        assert_eq!(
            origin_prefix(&TextOrigin::Pack("py-safety".into())),
            "pack(py-safety) says: "
        );
    }

    // frob:tests origin_prefix
    #[test]
    fn host_and_std_messages_are_not_prefixed() {
        assert_eq!(origin_prefix(&TextOrigin::Host), "");
        assert_eq!(origin_prefix(&TextOrigin::Std), "");
    }

    // frob:ticket 01M3ZX7XS6J4SFXY7P3S761M1P
    // frob:tests write_summary
    #[test]
    fn summary_lines_separate_unresolved_and_count_decisions() {
        let mut out = String::new();
        let s = Summary::of(
            &[],
            &[
                SecurityDecisionKind::Grant,
                SecurityDecisionKind::Replacement,
            ],
        );
        write_summary(&mut out, &s);
        assert!(
            out.contains("security decisions: 1 grants, 1 replacements"),
            "{out}"
        );
    }
}

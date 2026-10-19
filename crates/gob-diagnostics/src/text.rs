//! Text renderer: findings grouped by file with snippets and a summary.

use std::borrow::Cow;
use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::io::IsTerminal;

use anstyle::{AnsiColor, Style};
use gob_rules::{Applicability, Finding, Fix, Registry, Severity, TextEdit, UnresolvedReason};
use gob_text::{TextSize, render_snippet};

use crate::escape::{escape_for_origin, escape_text};
use crate::record::TextOrigin;
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

/// One finding resolved for display.
struct Located<'a> {
    finding: &'a Finding,
    line: u32,
}

/// Render `report` as text, showing and counting each Unresolved finding's required reason.
pub fn render_text(report: &Report<'_>, opts: &TextOptions) -> String {
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
            write_finding(&mut out, report, item, registry, *opts);
        }
        out.push('\n');
    }
    write_summary(&mut out, report.findings);
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
) {
    let f = item.finding;
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

fn write_summary(out: &mut String, findings: &[Finding]) {
    let n = |s: Severity| findings.iter().filter(|f| f.severity == s).count();
    let required = findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved && f.required.is_some())
        .count();
    let _ = writeln!(
        out,
        "{} errors, {} warnings, {} advisory, {} unresolved ({required} required)",
        n(Severity::Error),
        n(Severity::Warn),
        n(Severity::Advisory),
        n(Severity::Unresolved)
    );
}

#[cfg(test)]
mod tests {
    use super::*;

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
}

//! Text renderer: findings grouped by file with snippets and a summary.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::io::IsTerminal;

use anstyle::{AnsiColor, Style};
use gob_rules::{Finding, Registry, Severity};
use gob_text::render_snippet;

use crate::required::RequiredMarks;
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

/// Render `report` as text; the summary line is always last.
pub fn render_text(report: &Report<'_>, opts: &TextOptions) -> String {
    render_text_marked(report, opts, &RequiredMarks::new())
}

/// Render `report` as text, showing and counting the `marks` on Unresolved findings.
pub fn render_text_marked(
    report: &Report<'_>,
    opts: &TextOptions,
    marks: &RequiredMarks,
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
        let _ = writeln!(out, "{}", path.as_deref().unwrap_or("(no location)"));
        for item in &items {
            write_finding(&mut out, report, item, registry, *opts, marks);
        }
        out.push('\n');
    }
    write_summary(&mut out, report.findings, marks);
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
    marks: &RequiredMarks,
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
    let _ = writeln!(
        out,
        "  {col}{st}{}[{}{slug}]{st:#}: {}",
        severity_label(f.severity),
        f.rule,
        f.message
    );
    if opts.snippets
        && let Some(sp) = f.span
        && let Some(src) = report.sources.source(sp.file)
        && let Some(snip) = render_snippet(src, sp.range)
    {
        let gutter = snip.line_number.to_string();
        let pad = " ".repeat(gutter.len());
        let _ = writeln!(out, "  {pad} |");
        let _ = writeln!(out, "  {gutter} | {}", snip.line);
        let _ = writeln!(out, "  {pad} | {st}{}{st:#}", snip.caret_line);
    }
    if let Some(reason) = marks.get(f) {
        let _ = writeln!(out, "  required: {reason}");
    }
    if let Some(fix) = &f.fix {
        let _ = writeln!(out, "  fix: {}", fix.title);
    }
}

fn write_summary(out: &mut String, findings: &[Finding], marks: &RequiredMarks) {
    let n = |s: Severity| findings.iter().filter(|f| f.severity == s).count();
    let required = findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved && marks.get(f).is_some())
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

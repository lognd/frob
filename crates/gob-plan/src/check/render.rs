//! Text rendering of diagnostics in the rustc-style shape of the goldens (grl-spec.md section 10).

use std::fmt::Write as _;

use gob_text::SourceText;

use super::{Diagnostic, Label, Severity};

/// One label resolved to a line, a column and a marker width.
struct Placed<'a> {
    line: u32,
    /// 0-based character column.
    col: usize,
    width: usize,
    mark: char,
    label: &'a str,
}

/// Print `diagnostics` for the file `path` with text `source`, ending with the summary footer.
///
/// Returns the empty string when there is nothing to print. Spans that fall outside `source`
/// are shown without a source line rather than dropped.
pub fn render(path: &str, source: &str, diagnostics: &[Diagnostic]) -> String {
    let Ok(text) = SourceText::new(source) else {
        tracing::warn!(path, "rule file too large to render diagnostics");
        return String::new();
    };
    let mut out = String::new();
    for d in diagnostics {
        render_one(&mut out, path, &text, d);
        out.push('\n');
    }
    let errors = diagnostics
        .iter()
        .filter(|d| d.severity == Severity::Error)
        .count();
    let warnings = diagnostics.len() - errors;
    let plural =
        |n: usize, one: &str, many: &str| format!("{n} {}", if n == 1 { one } else { many });
    if errors > 0 {
        let _ = write!(
            out,
            "error: aborting due to {}",
            plural(errors, "previous error", "previous errors")
        );
        if warnings > 0 {
            let _ = write!(out, "; {} emitted", plural(warnings, "warning", "warnings"));
        }
        out.push('\n');
    } else if warnings > 0 {
        let _ = writeln!(
            out,
            "warning: {} emitted",
            plural(warnings, "warning", "warnings")
        );
    }
    out
}

fn place<'a>(text: &SourceText, label: &'a Label, mark: char) -> Option<Placed<'a>> {
    let start = label.span.range.start();
    let lc = text.line_col(start)?;
    let line_text = text.line_text(lc.line)?;
    let col_bytes = (lc.col - 1) as usize;
    let col = line_text.get(..col_bytes)?.chars().count();
    let end = label.span.range.end().to_usize();
    let line_end = start.to_usize() - col_bytes + line_text.len();
    let covered = text
        .as_str()
        .get(start.to_usize()..end.min(line_end).max(start.to_usize()))?;
    Some(Placed {
        line: lc.line,
        col,
        width: covered.chars().count().max(1),
        mark,
        label: &label.text,
    })
}

fn render_one(out: &mut String, path: &str, text: &SourceText, d: &Diagnostic) {
    let mut placed: Vec<Placed<'_>> = Vec::new();
    placed.extend(place(text, &d.primary, '^'));
    for s in &d.secondary {
        placed.extend(place(text, s, '-'));
    }
    // Source order; on one line the primary comes first.
    placed.sort_by_key(|p| (p.line, p.mark != '^'));
    let w = placed
        .iter()
        .map(|p| p.line.to_string().len())
        .max()
        .unwrap_or(1);
    let pad = " ".repeat(w);
    match d.code {
        Some(c) => {
            let sev = severity_word(d.severity);
            let _ = writeln!(out, "{sev}[{}]: {}", c.as_str(), d.message);
        }
        None => {
            let _ = writeln!(out, "{}: {}", severity_word(d.severity), d.message);
        }
    }
    let loc = text.line_col(d.primary.span.range.start()).map_or_else(
        || "?:?".to_owned(),
        |lc| {
            let col = text
                .line_text(lc.line)
                .and_then(|l| l.get(..(lc.col - 1) as usize))
                .map_or(lc.col as usize, |p| p.chars().count() + 1);
            format!("{}:{col}", lc.line)
        },
    );
    let _ = writeln!(out, "{pad}--> {path}:{loc}");
    let _ = writeln!(out, "{pad} |");
    let mut last: Option<u32> = None;
    for p in &placed {
        if last.is_some_and(|l| p.line > l + 1) {
            out.push_str("...\n");
        }
        last = Some(p.line);
        let line_text = text.line_text(p.line).unwrap_or("").trim_end();
        if line_text.is_empty() {
            let _ = writeln!(out, "{:>w$} |", p.line);
        } else {
            let _ = writeln!(out, "{:>w$} | {line_text}", p.line);
        }
        let prefix: String = line_text
            .chars()
            .take(p.col)
            .map(|c| if c == '\t' { '\t' } else { ' ' })
            .collect();
        let marks = p.mark.to_string().repeat(p.width);
        if p.label.is_empty() {
            let _ = writeln!(out, "{pad} | {prefix}{marks}");
        } else {
            let _ = writeln!(out, "{pad} | {prefix}{marks} {}", p.label);
        }
    }
    let has_tail = !d.notes.is_empty() || !d.helps.is_empty() || d.code.is_some();
    if has_tail {
        let _ = writeln!(out, "{pad} |");
    }
    for n in &d.notes {
        write_extra(out, &pad, "note", n);
    }
    for h in &d.helps {
        write_extra(out, &pad, "help", h);
    }
    if let Some(c) = d.code {
        let _ = writeln!(out, "{pad} = explain: grimble explain {}", c.as_str());
    }
}

/// An `= kind: text` line; continuation lines of a multi-line text are aligned under its first line.
fn write_extra(out: &mut String, pad: &str, kind: &str, text: &str) {
    let mut lines = text.lines();
    let _ = writeln!(out, "{pad} = {kind}: {}", lines.next().unwrap_or(""));
    for l in lines {
        let _ = writeln!(out, "{pad}   {}{l}", " ".repeat(kind.len() + 2));
    }
}

const fn severity_word(s: Severity) -> &'static str {
    match s {
        Severity::Error => "error",
        Severity::Warning => "warning",
    }
}

//! Human `--text` view of `frob check`: a pure function from the verb's data to printable rows.
// frob:ticket 01M5EFE42EH8JYYRC0JXSZR52F

use frob_check::{CheckData, Explained};

use crate::text_view::table;

/// The one-line verdict: counts by severity, then suppressed and file totals.
fn headline(data: &CheckData) -> String {
    let c = &data.counts;
    let scope = data
        .ticket
        .as_ref()
        .map_or_else(String::new, |t| format!(" for {t}"));
    let files = data.stats.as_ref().map_or_else(String::new, |s| {
        format!(", {} files checked", s.files_checked)
    });
    if c.error + c.unresolved == 0 {
        return format!(
            "check{scope}: clean ({} suppressed{files})",
            data.suppressed
        );
    }
    format!(
        "check{scope}: {} error, {} unresolved ({} suppressed{files})",
        c.error, c.unresolved, data.suppressed
    )
}

/// A blank separator followed by `title` and the indented `body` rows; nothing when `body` is empty.
fn section(out: &mut Vec<String>, title: &str, body: Vec<String>) {
    if body.is_empty() {
        return;
    }
    out.push(String::new());
    out.push(title.to_owned());
    out.extend(body.into_iter().map(|l| format!("  {l}")));
}

/// The rows of one rule page: heading, summary, then the indented explanation.
fn page_rows(e: &Explained) -> Vec<String> {
    let mut rows = vec![
        format!("{} ({}, {})", e.id, e.slug, e.severity),
        e.summary.clone(),
        String::new(),
    ];
    rows.extend(e.explanation.lines().map(|l| format!("  {l}")));
    rows
}

/// The `Baselined` rows: how many findings the baseline muted and the keys it still lists per rule.
fn baselined_rows(data: &CheckData) -> Vec<String> {
    let b = &data.baselined;
    if b.count == 0 {
        return Vec::new();
    }
    let mut rows = vec![format!("{} finding(s) muted by the baseline", b.count)];
    rows.extend(
        b.remaining
            .iter()
            .map(|(rule, n)| format!("{rule}: {n} key(s) remaining")),
    );
    rows
}

/// The `--fix` section rows: what was applied, what was skipped and why, what remains.
fn fix_rows(data: &CheckData) -> Vec<String> {
    let Some(fix) = &data.fix else {
        return Vec::new();
    };
    let mut rows = vec![format!(
        "{} applied, {} skipped (overlap), {} skipped (invalid), {} rolled back, {} remaining",
        fix.applied.len(),
        fix.skipped_overlap,
        fix.skipped_invalid,
        fix.rolled_back,
        fix.remaining
    )];
    let applied: Vec<Vec<String>> = fix
        .applied
        .iter()
        .map(|a| vec![a.rule.clone(), a.file.clone(), a.title.clone()])
        .collect();
    rows.extend(table(&applied));
    for s in &fix.skipped_scope {
        let widen = if s.widen.is_empty() {
            String::new()
        } else {
            format!("  (widen: {})", s.widen)
        };
        rows.push(format!("{} {} outside scope{widen}", s.rule, s.file));
    }
    rows
}

/// The `--timing` / `-v` stage table with its budget footer.
fn timing_rows(data: &CheckData) -> Vec<String> {
    let Some(t) = &data.timing else {
        return Vec::new();
    };
    let cells: Vec<Vec<String>> = t
        .stages
        .iter()
        .map(|s| {
            vec![
                s.name.clone(),
                format!("{} ms", s.ms),
                if s.budgeted { "budgeted" } else { "tool" }.to_owned(),
            ]
        })
        .collect();
    let mut rows = table(&cells);
    rows.push(format!(
        "budget {} ms, tools {} ms",
        t.budget_ms, t.tools_ms
    ));
    rows
}

/// The `-v` fidelity table: one row per language.
fn fidelity_rows(data: &CheckData) -> Vec<String> {
    let Some(f) = &data.fidelity else {
        return Vec::new();
    };
    let cells: Vec<Vec<String>> = f
        .languages
        .iter()
        .filter(|(_, l)| l.files > 0)
        .map(|(name, l)| {
            vec![
                name.clone(),
                l.fidelity.clone(),
                format!("{}/{} files examined", l.files_examined, l.files),
            ]
        })
        .collect();
    table(&cells)
}

/// The rows of `frob check`: verdict, findings, then fix, timing, siblings, notes and rule pages.
///
/// `verbose` adds the per-language fidelity table (`-v`).
pub fn check_rows(data: &CheckData, verbose: bool) -> Vec<String> {
    if let Some(page) = &data.explain {
        return page_rows(page);
    }
    let mut out = vec![headline(data)];
    if !data.lines.is_empty() {
        out.push(String::new());
        out.extend(data.lines.iter().cloned());
    }
    if !data.elsewhere.is_empty() {
        out.push(String::new());
        out.extend(data.elsewhere.iter().cloned());
    }
    section(&mut out, "Baselined", baselined_rows(data));
    section(&mut out, "Fix", fix_rows(data));
    section(&mut out, "Timing", timing_rows(data));
    if verbose {
        section(&mut out, "Fidelity", fidelity_rows(data));
    }
    section(&mut out, "Siblings", data.sibling_lines.clone());
    section(&mut out, "Notes", data.notes.clone());
    for page in &data.taught {
        out.push(String::new());
        out.extend(page_rows(page));
    }
    tracing::debug!(rows = out.len(), "check_view: check");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use frob_check::Counts;

    /// A [`CheckData`] with every field empty, for the view tests.
    fn data() -> CheckData {
        CheckData {
            counts: Counts::default(),
            suppressed: 0,
            lines: Vec::new(),
            elsewhere: Vec::new(),
            findings: Vec::new(),
            stats: None,
            timing: None,
            profile: None,
            fidelity: None,
            siblings: Vec::new(),
            sibling_lines: Vec::new(),
            fix: None,
            ticket: None,
            fail_on: None,
            required_unresolved: 0,
            not_evaluated: 0,
            fail_on_unresolved: None,
            notes: Vec::new(),
            pending_proposals: 0,
            explain: None,
            taught: Vec::new(),
            precision: Vec::new(),
            baselined: frob_check::BaselinedSection::default(),
        }
    }

    // frob:tests crates/frob/src/check_view.rs::check_rows
    #[test]
    fn check_view_lists_baselined_count_and_remaining_per_rule() {
        let mut d = data();
        d.baselined.count = 2;
        d.baselined.remaining.insert("COV006".to_owned(), 5);
        let rows = check_rows(&d, false);
        assert!(rows.contains(&"Baselined".to_owned()));
        assert!(rows.contains(&"  2 finding(s) muted by the baseline".to_owned()));
        assert!(rows.contains(&"  COV006: 5 key(s) remaining".to_owned()));
    }

    // frob:tests crates/frob/src/check_view.rs::check_rows
    #[test]
    fn check_view_clean_run_is_one_verdict_line() {
        let rows = check_rows(&data(), false);
        assert_eq!(rows, vec!["check: clean (0 suppressed)".to_owned()]);
    }

    // frob:tests crates/frob/src/check_view.rs::check_rows
    #[test]
    fn check_view_leads_with_counts_then_findings_and_notes() {
        let mut d = data();
        d.counts.error = 1;
        d.suppressed = 2;
        d.ticket = Some("~ABC1234".to_owned());
        d.lines = vec!["a.rs:1:1: warning X001 msg".to_owned()];
        d.notes = vec!["3 proposals pending".to_owned()];
        let rows = check_rows(&d, false);
        assert_eq!(
            rows,
            vec![
                "check for ~ABC1234: 1 error, 0 unresolved (2 suppressed)",
                "",
                "a.rs:1:1: warning X001 msg",
                "",
                "Notes",
                "  3 proposals pending",
            ]
        );
    }

    // frob:tests crates/frob/src/check_view.rs::check_rows
    #[test]
    fn check_view_explain_prints_only_the_rule_page() {
        let mut d = data();
        d.explain = Some(Explained {
            id: "X001".to_owned(),
            slug: "x-rule".to_owned(),
            severity: "error".to_owned(),
            summary: "sum".to_owned(),
            explanation: "line one\nline two".to_owned(),
        });
        let rows = check_rows(&d, false);
        assert_eq!(rows[0], "X001 (x-rule, error)");
        assert_eq!(rows.last().map(String::as_str), Some("  line two"));
    }
}

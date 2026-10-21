//! Human `--text` view of `frob land`: a pure function from the verb's report to printable rows.
// frob:ticket 01M5EFE44WSM03AW4771Y53GFT

use gob_path::Shown;

use crate::plan::LandOutcome;
use crate::verb::{BatchReport, LandReport};

/// The one-line verdict of a single land.
fn verdict(o: &LandOutcome) -> String {
    let what = if o.already {
        "already landed".to_owned()
    } else if o.dry_run {
        format!("dry run, would land onto {}", o.base)
    } else if o.closed {
        format!("landed onto {}", o.base)
    } else {
        format!("not landed onto {}", o.base)
    };
    format!("{} {what}", o.handle)
}

/// The rows of one land: verdict, facts, then plan, stage timings and notices.
fn outcome_rows(o: &LandOutcome) -> Vec<String> {
    let mut out = vec![verdict(o)];
    let mut fact = |k: &str, v: String| out.push(format!("  {k:<9} {v}"));
    if let Some(c) = &o.commit {
        fact("commit", c.chars().take(10).collect());
    }
    if let Some(b) = &o.branch {
        fact("branch", b.clone());
    }
    if let Some(w) = &o.worktree {
        fact("worktree", Shown::of(w).to_string());
    }
    if let Some(m) = &o.base_merge {
        fact("base", m.clone());
    }
    if let Some(oc) = &o.outcome {
        fact("outcome", oc.to_string());
    }
    if o.attempts > 1 {
        fact("attempts", o.attempts.to_string());
    }
    if let Some(r) = &o.changelog_exempt {
        fact("changelog", format!("exempt ({r})"));
    }
    let flags: Vec<&str> = [
        (o.pushed, "pushed"),
        (o.closed, "closed"),
        (o.worktree_removed, "worktree removed"),
    ]
    .iter()
    .filter_map(|(on, name)| on.then_some(*name))
    .collect();
    if !flags.is_empty() {
        fact("done", flags.join(", "));
    }
    section(&mut out, "Plan", o.plan.iter().cloned());
    section(
        &mut out,
        "Stages",
        o.stages.iter().map(|s| format!("{}  {} ms", s.name, s.ms)),
    );
    section(&mut out, "Warnings", o.warnings.iter().cloned());
    out
}

/// A blank separator, `title`, then the indented `body`; nothing when `body` is empty.
fn section(out: &mut Vec<String>, title: &str, body: impl Iterator<Item = String>) {
    let body: Vec<String> = body.map(|l| format!("  {l}")).collect();
    if body.is_empty() {
        return;
    }
    out.push(String::new());
    out.push(title.to_owned());
    out.extend(body);
}

/// The rows of a several-ticket land: totals, then one line per ticket.
fn batch_rows(b: &BatchReport) -> Vec<String> {
    let mut out = vec![format!(
        "land: {} landed, {} did not land of {}",
        b.landed,
        b.refused,
        b.tickets.len()
    )];
    for t in &b.tickets {
        let detail = match (&t.code, &t.message) {
            (Some(c), Some(m)) => format!("  {c}: {m}"),
            (None, Some(m)) => format!("  {m}"),
            _ => String::new(),
        };
        out.push(format!("  {} {}{detail}", t.ticket, t.status));
        if let Some(r) = &t.remedy {
            out.push(format!("    fix: {r}"));
        }
    }
    out
}

/// The rows of `frob land`: a single land's verdict and facts, or a batch's per-ticket lines.
pub(crate) fn land_rows(report: &LandReport) -> Vec<String> {
    let out = match report {
        LandReport::One(o) => outcome_rows(o),
        LandReport::Batch(b) => batch_rows(b),
    };
    tracing::debug!(rows = out.len(), "land_view: land");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::verb::BatchEntry;

    /// A batch with one landed and one refused ticket.
    fn batch() -> BatchReport {
        let entry = |ticket: &str, status: &str, code: Option<&str>| BatchEntry {
            ticket: ticket.to_owned(),
            status: status.to_owned(),
            outcome: None,
            code: code.map(str::to_owned),
            message: code.map(|_| "stale".to_owned()),
            remedy: code.map(|_| "frob land ~B".to_owned()),
        };
        BatchReport {
            tickets: vec![
                entry("~A", "landed", None),
                entry("~B", "refused", Some("E-X")),
            ],
            landed: 1,
            refused: 1,
        }
    }

    // frob:tests crates/frob-land/src/land_view.rs::land_rows
    #[test]
    fn land_view_batch_lists_each_ticket_and_remedy() {
        let rows = land_rows(&LandReport::Batch(batch()));
        assert_eq!(rows[0], "land: 1 landed, 1 did not land of 2");
        assert_eq!(rows[1], "  ~A landed");
        assert_eq!(rows[2], "  ~B refused  E-X: stale");
        assert_eq!(rows[3], "    fix: frob land ~B");
    }

    // frob:tests crates/frob-land/src/land_view.rs::land_rows
    #[test]
    fn land_view_single_land_leads_with_verdict() {
        let o = LandOutcome {
            id: "01M5EFE44WSM03AW4771Y53GFT".parse().unwrap(),
            handle: "~1Y53GFT".to_owned(),
            already: false,
            dry_run: false,
            base: "main".to_owned(),
            branch: Some("ticket/x".to_owned()),
            worktree: None,
            commit: Some("0123456789abcdef".to_owned()),
            base_merge: Some("up-to-date".to_owned()),
            pushed: false,
            closed: true,
            outcome: None,
            worktree_removed: true,
            digest: None,
            plan: Vec::new(),
            attempts: 1,
            warnings: vec!["careful".to_owned()],
            pre_existing: Vec::new(),
            resolved: Vec::new(),
            changelog_exempt: None,
            stages: vec![crate::plan::StageTiming::new(
                "merge",
                std::time::Duration::from_millis(5),
            )],
            lock: None,
        };
        let rows = land_rows(&LandReport::One(o));
        assert_eq!(rows[0], "~1Y53GFT landed onto main");
        assert!(rows.contains(&"  commit    0123456789".to_owned()));
        assert!(rows.contains(&"  merge  5 ms".to_owned()));
        assert_eq!(rows.last().map(String::as_str), Some("  careful"));
    }
}

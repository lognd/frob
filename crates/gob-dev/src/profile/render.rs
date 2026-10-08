//! Markdown for the step summary and the non-blocking `--compare` deltas.

use std::collections::BTreeMap;

use super::model::{Entry, Report};

fn ms(v: Option<f64>) -> String {
    v.map_or_else(|| "-".to_owned(), |v| format!("{v:.0}"))
}

/// The markdown table of `report`: one row per leaf command.
pub fn table(report: &Report) -> String {
    let mut out = format!(
        "### Command profile ({} {}, profile `{}`, {} runs, budget factor {})\n\n",
        report.os, report.arch, report.cargo_profile, report.runs, report.budget_factor
    );
    out.push_str("| Command | Warm ms | Cold ms | Budget ms | Max RSS MiB | Exit |\n|---|---:|---:|---:|---:|---:|\n");
    for e in &report.entries {
        if let Some(reason) = &e.skipped {
            out.push_str(&format!(
                "| `{}` | skipped: {reason} | | | | |\n",
                e.command
            ));
            continue;
        }
        #[allow(
            clippy::cast_precision_loss,
            reason = "resident sets are far below 2^52 KiB"
        )]
        let rss = e.max_rss_kib.map(|k| k as f64 / 1024.0);
        out.push_str(&format!(
            "| `{}` | {} | {} | {} | {} | {} |\n",
            e.command,
            ms(e.warm_ms),
            ms(e.cold_ms),
            e.budget_ms
                .map_or_else(|| "-".to_owned(), |b| b.to_string()),
            rss.map_or_else(|| "-".to_owned(), |m| format!("{m:.0}")),
            e.exit
                .map_or_else(|| "signal".to_owned(), |c| c.to_string()),
        ));
    }
    out
}

/// Per-command warm-time deltas of `now` against `base` as markdown; informational only.
pub fn compare(base: &Report, now: &Report) -> String {
    let before: BTreeMap<&str, &Entry> = base
        .entries
        .iter()
        .map(|e| (e.command.as_str(), e))
        .collect();
    let mut out = String::from(
        "### Delta against the base report\n\n| Command | Base ms | Now ms | Delta ms | Delta % |\n|---|---:|---:|---:|---:|\n",
    );
    for e in &now.entries {
        let (Some(new), Some(old)) = (
            e.warm_ms,
            before.get(e.command.as_str()).and_then(|b| b.warm_ms),
        ) else {
            continue;
        };
        let delta = new - old;
        let pct = if old > 0.0 { delta / old * 100.0 } else { 0.0 };
        out.push_str(&format!(
            "| `{}` | {old:.0} | {new:.0} | {delta:+.0} | {pct:+.0}% |\n",
            e.command
        ));
    }
    let gone: Vec<&str> = before
        .keys()
        .copied()
        .filter(|c| !now.entries.iter().any(|e| e.command == *c))
        .collect();
    if !gone.is_empty() {
        out.push_str(&format!("\nNot in this run: {}\n", gone.join(", ")));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::profile::model::SCHEMA_VERSION;

    fn report(warm: f64) -> Report {
        let mut e = Entry::skipped("frob check", "");
        e.skipped = None;
        e.warm_ms = Some(warm);
        e.exit = Some(0);
        Report {
            schema_version: SCHEMA_VERSION,
            os: "linux".to_owned(),
            arch: "aarch64".to_owned(),
            cargo_profile: "profiling".to_owned(),
            commit: None,
            runs: 5,
            budget_factor: 1.0,
            entries: vec![e, Entry::skipped("frob land", "needs a remote")],
        }
    }

    // frob:tests crates/gob-dev/src/profile/render.rs::table
    #[test]
    fn table_lists_measured_and_skipped_rows() {
        let t = table(&report(120.0));
        assert!(t.contains("| `frob check` | 120 |"), "{t}");
        assert!(t.contains("skipped: needs a remote"), "{t}");
    }

    // frob:tests crates/gob-dev/src/profile/render.rs::compare
    #[test]
    fn compare_shows_signed_deltas() {
        let c = compare(&report(100.0), &report(150.0));
        assert!(
            c.contains("| `frob check` | 100 | 150 | +50 | +50% |"),
            "{c}"
        );
    }
}

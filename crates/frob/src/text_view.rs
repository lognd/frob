//! Human `--text` views of the everyday read verbs: pure functions from a verb's data to printable rows.
// frob:ticket 01M4CTTXC1E5MQEDFMY5JDQ45M

use std::fmt::Write as _;

use frob_ledger::ops::LinkView;

use crate::cycle_cmd::{CycleListData, CycleView};
use crate::doctor::{DoctorData, GcInfo};
use crate::ticket::read::{ListData, ListRow, ShowData};

/// The `YYYY-MM-DD` head of a timestamp rendering.
fn day(stamp: &str) -> &str {
    stamp.get(..10).unwrap_or(stamp)
}

/// Left-align `rows` into columns separated by two spaces, dropping trailing blanks.
pub(crate) fn table(rows: &[Vec<String>]) -> Vec<String> {
    let cols = rows.iter().map(Vec::len).max().unwrap_or(0);
    let widths: Vec<usize> = (0..cols)
        .map(|c| {
            rows.iter()
                .filter_map(|r| r.get(c))
                .map(|s| s.chars().count())
                .max()
                .unwrap_or(0)
        })
        .collect();
    rows.iter()
        .map(|row| {
            let mut line = String::new();
            for (i, cell) in row.iter().enumerate() {
                if i > 0 {
                    line.push_str("  ");
                }
                let _ = write!(line, "{cell:<w$}", w = widths[i]);
            }
            line.trim_end().to_owned()
        })
        .collect()
}

/// A points cell: the number, or a dash when unestimated.
fn points(p: Option<impl ToString>) -> String {
    p.map_or_else(|| "-".to_owned(), |p| p.to_string())
}

/// The rows of `ticket list` and `ticket doable`: a count line, then one aligned row per ticket.
pub fn list_rows(data: &ListData) -> Vec<String> {
    let mut out = Vec::new();
    let noun = if data.count == 1 { "ticket" } else { "tickets" };
    match &data.at {
        Some(at) => out.push(format!("{} {noun} (inbox as of {})", data.count, at)),
        None => out.push(format!("{} {noun}", data.count)),
    }
    let rows: Vec<Vec<String>> = data.tickets.iter().map(list_cells).collect();
    out.extend(table(&rows));
    for row in &data.tickets {
        if let Some(notes) = &row.start_here {
            out.push(String::new());
            out.push(format!("{} start here:", row.summary.handle));
            out.extend(notes.lines().map(|l| format!("  {l}")));
        }
    }
    tracing::debug!(rows = out.len(), "text_view: list");
    out
}

/// The cells of one listed ticket.
fn list_cells(row: &ListRow) -> Vec<String> {
    let s = &row.summary;
    let mut cells = vec![
        s.handle.clone(),
        s.priority.to_string(),
        match s.outcome {
            Some(o) => format!("{}/{o}", s.category),
            None => s.category.to_string(),
        },
        points(s.points),
        s.ty.to_string(),
        s.title.clone(),
    ];
    if s.blocked {
        cells.push("[blocked]".to_owned());
    }
    if let Some(until) = &row.snoozed_until {
        cells.push(format!("[snoozed until {}]", day(&until.to_string())));
    }
    if let Some(aliases) = row.aliases.as_ref().filter(|a| !a.is_empty()) {
        cells.push(format!("[aliases {}]", aliases.join(",")));
    }
    if let Some(events) = &row.events {
        cells.push(format!("[{} events]", events.len()));
    }
    cells
}

/// One `label  value` meta line, skipped when the value is empty.
fn meta(out: &mut Vec<String>, label: &str, value: &str) {
    if !value.is_empty() {
        out.push(format!("{label:<11}{value}"));
    }
}

/// A link as `kind  handle  title (category)`.
fn link_cells(l: &LinkView) -> Vec<String> {
    vec![
        l.kind.to_string(),
        l.handle.clone().unwrap_or_else(|| l.id.to_string()),
        l.title.clone().unwrap_or_else(|| "(missing)".to_owned()),
        l.category.map(|c| format!("({c})")).unwrap_or_default(),
    ]
}

/// The rows of `ticket show`: header, meta, then Description, Acceptance, Evidence, Links, Children and Events sections.
pub fn show_rows(data: &ShowData) -> Vec<String> {
    let t = &data.view.ticket;
    let f = &t.front;
    let s = &data.view.summary;
    let mut out = vec![format!("{}  {}", s.handle, f.title), String::new()];
    let status = match f.outcome {
        Some(o) => format!("{}/{o}", f.category),
        None if s.blocked => format!("{} (blocked)", f.category),
        None => f.category.to_string(),
    };
    meta(&mut out, "status", &status);
    meta(&mut out, "type", &f.ty.to_string());
    meta(&mut out, "priority", &f.priority.to_string());
    meta(&mut out, "class", &f.class.to_string());
    meta(
        &mut out,
        "points",
        &s.points.map(|p| p.to_string()).unwrap_or_default(),
    );
    meta(
        &mut out,
        "due",
        &f.due
            .map(|d| day(&d.to_string()).to_owned())
            .unwrap_or_default(),
    );
    meta(
        &mut out,
        "parent",
        &f.parent.map(|p| p.to_string()).unwrap_or_default(),
    );
    meta(&mut out, "reporter", &f.reporter);
    meta(
        &mut out,
        "assignee",
        f.assignee.as_deref().unwrap_or_default(),
    );
    meta(&mut out, "created", day(&f.created.to_string()));
    meta(&mut out, "updated", day(&f.updated.to_string()));
    meta(&mut out, "labels", &f.labels.join(", "));
    meta(&mut out, "scope", &f.scope.join(", "));
    meta(&mut out, "aliases", &f.aliases.join(", "));
    if !t.body.trim().is_empty() {
        out.push(String::new());
        out.push("Description".to_owned());
        out.extend(t.body.trim_end().lines().map(|l| format!("  {l}")));
    }
    if !f.acceptance.is_empty() {
        out.push(String::new());
        out.push("Acceptance".to_owned());
        for (i, a) in f.acceptance.iter().enumerate() {
            let mark = if a.bound { "x" } else { " " };
            out.push(format!("  {}. [{mark}] {}", i + 1, a.text));
        }
    }
    if !data.evidence.is_empty() {
        out.push(String::new());
        out.push("Evidence".to_owned());
        out.extend(data.evidence.iter().map(|e| format!("  {}", e.line())));
    }
    let links: Vec<Vec<String>> = data
        .view
        .outgoing
        .iter()
        .chain(&data.view.incoming)
        .map(link_cells)
        .collect();
    if !links.is_empty() {
        out.push(String::new());
        out.push("Links".to_owned());
        out.extend(table(&links).into_iter().map(|l| format!("  {l}")));
    }
    if !data.view.children.is_empty() {
        out.push(String::new());
        out.push("Children".to_owned());
        let rows: Vec<Vec<String>> = data
            .view
            .children
            .iter()
            .map(|c| {
                vec![
                    c.handle.clone(),
                    c.category.to_string(),
                    points(c.points),
                    c.title.clone(),
                ]
            })
            .collect();
        out.extend(table(&rows).into_iter().map(|l| format!("  {l}")));
    }
    if let Some(events) = &data.events {
        out.push(String::new());
        out.push("Events".to_owned());
        let rows: Vec<Vec<String>> = events
            .iter()
            .map(|e| vec![day(&e.at).to_owned(), e.actor.clone(), e.kind.clone()])
            .collect();
        out.extend(table(&rows).into_iter().map(|l| format!("  {l}")));
    }
    tracing::debug!(rows = out.len(), "text_view: ticket show");
    out
}

/// The rows of `cycle show`: header, goal and numbers, then members, carried, over-commits and retro.
pub fn cycle_rows(c: &CycleView) -> Vec<String> {
    let mut out = vec![
        format!("{}  {}  ({})", c.handle, c.alias, c.state),
        String::new(),
    ];
    meta(&mut out, "goal", &c.goal);
    if let Some(end) = &c.ended {
        meta(&mut out, "ended", end);
    }
    meta(&mut out, "capacity", &points(c.capacity_points));
    let committed: u32 = c
        .tickets
        .iter()
        .map(|t| u32::from(t.points.unwrap_or(0)))
        .sum();
    meta(&mut out, "committed", &committed.to_string());
    if let Some(r) = &c.commitment {
        let pct = r
            .ratio
            .map_or_else(|| "n/a".to_owned(), |x| format!("{:.0}%", x * 100.0));
        meta(
            &mut out,
            "ratio",
            &format!("{} of {} done ({pct})", r.done, r.committed),
        );
    }
    if !c.tickets.is_empty() {
        out.push(String::new());
        out.push("Tickets".to_owned());
        let rows: Vec<Vec<String>> = c
            .tickets
            .iter()
            .map(|t| {
                vec![
                    t.handle.clone().unwrap_or_else(|| t.id.clone()),
                    t.category.clone().unwrap_or_default(),
                    points(t.points),
                    t.title.clone().unwrap_or_default(),
                ]
            })
            .collect();
        out.extend(table(&rows).into_iter().map(|l| format!("  {l}")));
    }
    if !c.carried.is_empty() {
        out.push(String::new());
        out.push("Carried".to_owned());
        out.extend(
            c.carried
                .iter()
                .map(|x| format!("  {} -> {}", x.ticket, x.to)),
        );
    }
    if !c.over_commits.is_empty() {
        out.push(String::new());
        out.push("Over-commits".to_owned());
        for o in &c.over_commits {
            let nums = match (o.committed, o.capacity) {
                (Some(a), Some(b)) => format!("{a}/{b} points: "),
                _ => String::new(),
            };
            out.push(format!("  {nums}{}", o.reason));
        }
    }
    if let Some(retro) = &c.retro {
        out.push(String::new());
        out.push("Retro".to_owned());
        out.extend(retro.lines().map(|l| format!("  {l}")));
    }
    tracing::debug!(rows = out.len(), "text_view: cycle show");
    out
}

/// The rows of `cycle list`: a count line and one aligned row per cycle.
pub fn cycle_list_rows(data: &CycleListData) -> Vec<String> {
    let noun = if data.count == 1 { "cycle" } else { "cycles" };
    let mut out = vec![format!("{} {noun}", data.count)];
    let rows: Vec<Vec<String>> = data
        .cycles
        .iter()
        .map(|c| {
            let ratio = c
                .commitment
                .as_ref()
                .map_or_else(|| "-".to_owned(), |r| format!("{}/{}", r.done, r.committed));
            vec![
                c.handle.clone(),
                c.alias.clone(),
                c.state.clone(),
                format!("{} tickets", c.tickets.len()),
                format!("cap {}", points(c.capacity_points)),
                ratio,
                c.goal.clone(),
            ]
        })
        .collect();
    out.extend(table(&rows));
    tracing::debug!(rows = out.len(), "text_view: cycle list");
    out
}

// ---- frob doctor (~757EG2T) ----

/// A byte count as a short human size (`1.5 MiB`).
fn human_bytes(b: u64) -> String {
    const UNITS: [&str; 4] = ["KiB", "MiB", "GiB", "TiB"];
    if b < 1024 {
        return format!("{b} B");
    }
    #[allow(clippy::cast_precision_loss)]
    let mut v = b as f64 / 1024.0;
    let mut unit = 0;
    while v >= 1024.0 && unit + 1 < UNITS.len() {
        v /= 1024.0;
        unit += 1;
    }
    format!("{v:.1} {}", UNITS[unit])
}

/// A titled section: a blank line, the title, then indented `label  value` rows aligned together.
fn section(out: &mut Vec<String>, title: &str, rows: &[Vec<String>]) {
    out.push(String::new());
    out.push(title.to_owned());
    out.extend(table(rows).into_iter().map(|l| format!("  {l}")));
}

/// One `label`, `value` row, with a missing value shown as a dash.
fn kv(label: &str, value: Option<&str>) -> Vec<String> {
    vec![label.to_owned(), value.unwrap_or("-").to_owned()]
}

/// The rows of `frob doctor`: one aligned section per survey (toolchain, git, cache, ... languages).
#[allow(clippy::too_many_lines)] // one flat list of sections; splitting would only scatter it
pub fn doctor_rows(d: &DoctorData) -> Vec<String> {
    let mut out = vec!["frob doctor".to_owned()];
    section(
        &mut out,
        "Toolchain",
        &[
            kv("rustc", d.toolchain.rustc.as_deref()),
            kv("cargo", d.toolchain.cargo.as_deref()),
        ],
    );
    let g = &d.git;
    let mut git = vec![kv("discovered", Some(&g.discovered.to_string()))];
    if g.discovered {
        git.push(kv("root", g.root.as_deref()));
        git.push(kv("branch", g.branch.as_deref()));
        git.push(kv(
            "head",
            g.head.as_deref().map(|h| h.get(..12).unwrap_or(h)),
        ));
        git.push(kv(
            "worktree",
            Some(if g.linked_worktree { "linked" } else { "main" }),
        ));
    }
    if let Some(e) = &g.error {
        git.push(kv("error", Some(e)));
    }
    section(&mut out, "Git", &git);
    let c = &d.cache;
    section(
        &mut out,
        "Cache",
        &[
            kv("state", Some(&c.state)),
            kv("dir", c.dir.as_deref()),
            kv(
                "rows",
                Some(&format!(
                    "{} artifacts, {} findings, {} repo-rule",
                    c.artifacts, c.findings, c.repo_rule
                )),
            ),
        ],
    );
    let cf = &d.config;
    let config = vec![
        kv("path", Some(&cf.path)),
        kv("present", Some(&cf.present.to_string())),
        kv("missing knobs", Some(&cf.missing_knobs.to_string())),
    ];
    section(&mut out, "Config", &config);
    let l = &d.ledger;
    let mut ledger = vec![
        kv("ref", Some(&l.r#ref)),
        kv("reachable", Some(&l.reachable.to_string())),
        kv("oid", l.oid.as_deref()),
        kv("protection", Some(&l.protection)),
    ];
    if let Some(x) = &l.protection_detail {
        ledger.push(kv("detail", Some(x)));
    }
    if let Some(e) = &l.error {
        ledger.push(kv("error", Some(e)));
    }
    section(&mut out, "Ledger", &ledger);
    let dr = &d.driver;
    let mut driver = vec![
        kv("state", Some(&dr.state)),
        kv("command", dr.command.as_deref()),
    ];
    if let Some(x) = &dr.detail {
        driver.push(kv("detail", Some(x)));
    }
    if let Some(x) = &dr.fix {
        driver.push(kv("fix", Some(x)));
    }
    section(&mut out, "Merge driver", &driver);
    let siblings: Vec<Vec<String>> = d
        .siblings
        .iter()
        .flat_map(|s| {
            let mut rows = vec![vec![
                s.product.clone(),
                s.location.clone(),
                s.version.clone().unwrap_or_else(|| "-".to_owned()),
                s.path.clone().unwrap_or_default(),
            ]];
            if let Some(o) = &s.other {
                let note = if o.differs { "differs" } else { "same" };
                rows.push(vec![
                    String::new(),
                    format!("other ({note})"),
                    o.version.clone().unwrap_or_else(|| "-".to_owned()),
                    o.path.clone(),
                ]);
            }
            rows
        })
        .collect();
    section(&mut out, "Siblings", &siblings);
    gc_rows(&mut out, &d.gc);
    let ls = &d.leases;
    let mut leases = vec![
        kv("state", Some(&ls.state)),
        kv("corrupt", Some(&ls.corrupt.len().to_string())),
    ];
    if let Some(q) = &ls.quarantined {
        leases.push(kv("quarantined", Some(&q.len().to_string())));
    }
    section(&mut out, "Leases", &leases);
    let ln = &d.lands;
    let mut lands = vec![
        kv("state", Some(&ln.state)),
        kv("unpushed lands", Some(&ln.lands.len().to_string())),
        kv("evicted", Some(&ln.evicted.to_string())),
    ];
    lands.extend(ln.lands.iter().map(|x| kv("", Some(x))));
    section(&mut out, "Lands", &lands);
    if let Some(r) = &d.languages {
        let mut rows: Vec<Vec<String>> = r
            .adapters
            .iter()
            .map(|a| {
                vec![
                    a.language.clone(),
                    a.fidelity.clone(),
                    format!("{} files", a.files),
                    a.adapter.clone(),
                ]
            })
            .collect();
        rows.extend(r.unadapted.iter().map(|u| {
            vec![
                u.extension.clone(),
                u.fidelity.clone(),
                format!("{} files", u.files),
                u.unit.clone(),
            ]
        }));
        section(&mut out, "Languages", &rows);
    }
    tracing::debug!(rows = out.len(), "text_view: doctor");
    out
}

/// The garbage-collection section of `frob doctor`: last pass, usage, plan, kept and fixed.
fn gc_rows(out: &mut Vec<String>, gc: &GcInfo) {
    let mut rows = vec![
        kv("state", Some(&gc.state)),
        kv("passes", Some(&gc.passes.to_string())),
        kv(
            "reclaimed",
            Some(&format!(
                "{} last, {} total",
                human_bytes(gc.last_reclaimed_bytes),
                human_bytes(gc.total_reclaimed_bytes)
            )),
        ),
    ];
    rows.extend(gc.usage.iter().map(|u| {
        kv(
            &format!("usage {}", u.category),
            Some(&human_bytes(u.bytes)),
        )
    }));
    if !gc.would_reclaim.is_empty() {
        rows.push(kv(
            "would reclaim",
            Some(&human_bytes(gc.would_reclaim_bytes)),
        ));
        rows.extend(gc.would_reclaim.iter().map(|c| {
            kv(
                &format!("  {}", c.category),
                Some(&format!("{} items, {}", c.items, human_bytes(c.bytes))),
            )
        }));
    }
    rows.extend(
        gc.kept
            .iter()
            .map(|k| kv(&format!("kept {}", k.target), Some(&k.reason))),
    );
    if let Some(f) = &gc.fixed {
        rows.push(kv("fixed", Some(&human_bytes(f.reclaimed_bytes))));
        rows.extend(f.warnings.iter().map(|w| kv("warning", Some(w))));
    }
    section(out, "Garbage collection", &rows);
}

#[cfg(test)]
mod doctor_tests {
    use super::*;

    // frob:tests crates/frob/src/text_view.rs::human_bytes
    #[test]
    fn bytes_read_in_binary_units() {
        assert_eq!(human_bytes(12), "12 B");
        assert_eq!(human_bytes(1536), "1.5 KiB");
        assert_eq!(human_bytes(3 * 1024 * 1024), "3.0 MiB");
    }

    // frob:tests crates/frob/src/text_view.rs::section
    #[test]
    fn a_section_aligns_its_rows_under_the_title() {
        let mut out = Vec::new();
        section(
            &mut out,
            "Git",
            &[kv("root", Some("/r")), kv("branch", None)],
        );
        assert_eq!(out, ["", "Git", "  root    /r", "  branch  -"]);
    }
}

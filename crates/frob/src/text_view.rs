//! Human `--text` views of the everyday read verbs: pure functions from a verb's data to printable rows.
// frob:ticket 01M4CTTXC1E5MQEDFMY5JDQ45M

use std::fmt::Write as _;

use frob_ledger::ops::LinkView;

use crate::cycle_cmd::{CycleListData, CycleView};
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

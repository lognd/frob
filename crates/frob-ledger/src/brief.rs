//! The markdown brief of a ticket: what an agent reads before starting work.

use std::fmt::Write as _;

use crate::event::Event;
use crate::ops::{LinkView, TicketView};

/// How many trailing events a brief lists.
const RECENT_EVENTS: usize = 5;

/// Render `view` and its `events` as markdown.
pub(crate) fn render(view: &TicketView, events: &[Event]) -> String {
    let f = &view.ticket.front;
    let mut out = String::new();
    let _ = write!(out, "# {} {}\n\n", view.summary.handle, f.title);
    let outcome = f.outcome.map_or_else(String::new, |o| format!(" ({o})"));
    let _ = writeln!(out, "- type: {}", f.ty);
    let _ = writeln!(out, "- category: {}{outcome}", f.category);
    let _ = writeln!(out, "- priority: {}", f.priority);
    if let Some(p) = f.points {
        let _ = writeln!(out, "- points: {}", p.get());
    }
    if view.summary.blocked {
        out.push_str("- blocked: yes\n");
    }
    out.push('\n');
    if !view.ticket.body.is_empty() {
        let _ = write!(out, "{}\n\n", view.ticket.body);
    }
    if !f.acceptance.is_empty() {
        out.push_str("## Acceptance\n\n");
        for (i, a) in f.acceptance.iter().enumerate() {
            let state = if a.bound { "bound" } else { "unbound" };
            let _ = writeln!(out, "{}. [{state}] {}", i + 1, a.text);
        }
        out.push('\n');
    }
    if !f.scope.is_empty() {
        out.push_str("## Scope\n\n");
        for s in &f.scope {
            let _ = writeln!(out, "- `{s}`");
        }
        out.push('\n');
    }
    links(&mut out, view);
    recent(&mut out, events);
    out
}

fn links(out: &mut String, view: &TicketView) {
    let all: Vec<&LinkView> = view.outgoing.iter().chain(view.incoming.iter()).collect();
    let parent = view.ticket.front.parent;
    if all.is_empty() && parent.is_none() {
        return;
    }
    out.push_str("## Links\n\n");
    if let Some(p) = parent {
        let _ = writeln!(out, "- parent: {p}");
    }
    for l in all {
        let _ = writeln!(
            out,
            "- {}: {} {}",
            l.kind,
            l.handle.as_deref().unwrap_or("(missing)"),
            l.title.as_deref().unwrap_or("")
        );
    }
    out.push('\n');
}

fn recent(out: &mut String, events: &[Event]) {
    let skip = events.len().saturating_sub(RECENT_EVENTS);
    let tail = &events[skip..];
    if tail.is_empty() {
        return;
    }
    out.push_str("## Recent events\n\n");
    for e in tail {
        let _ = writeln!(out, "- {} {} by {}", e.at, e.kind, e.actor);
    }
}

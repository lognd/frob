//! `TOUR.md`: the repository tour in five stops (`navigation.md` section 5).
//!
//! The prose is a template shipped in the binary; the examples come from the ledger and are
//! pinned: the most recently closed ticket that has evidence and a land, the largest epic and the
//! first ready good-first ticket by id. [`resolve`] keeps a previous [`Pins`] while its tickets
//! still qualify and replaces a vanished or dropped one with a note, so the tour does not churn.
//! Nothing is model-written.
// frob:ticket 01M3ZX887RZB82G8HR5JKQ2FER

use std::collections::BTreeMap;
use std::fmt::Write as _;

use crate::event::{Event, EventBody};
use crate::id::{EventId, TicketId};
use crate::layout::EVENTS_DIR;
use crate::model::{Category, Outcome, TicketType};
use crate::reindex::{GENERATED_MARKER_PREFIX, GenInput};

use super::epic::{by_dir, top_of};
use super::good_first::is_good_first;
use super::indexes::{Row, cell, load};

/// Branch-relative path of the tour.
pub const PATH: &str = "TOUR.md";

/// The stop templates, in order.
const STOPS: [&str; 5] = [
    include_str!("../../templates/tour/1-where.md"),
    include_str!("../../templates/tour/2-epic.md"),
    include_str!("../../templates/tour/3-life.md"),
    include_str!("../../templates/tour/4-rules.md"),
    include_str!("../../templates/tour/5-turn.md"),
];

/// The command name used in the rendered tour.
const COMMAND: &str = "frob";

/// The three pinned examples (the `[tour]` knobs); `None` when no ticket qualifies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Pins {
    /// A done ticket with evidence and a land, for stop 3.
    pub closed: Option<TicketId>,
    /// The epic of stop 2.
    pub epic: Option<TicketId>,
    /// The ready good-first ticket of stop 5.
    pub good_first: Option<TicketId>,
}

/// Pins after [`resolve`], with a note for each replaced example.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Resolved {
    /// The pins to use and to write back to `[tour]`.
    pub pins: Pins,
    /// One line per pin that was replaced.
    pub notes: Vec<String>,
}

/// Everything the tour reads about the ledger.
struct Facts<'a> {
    rows: BTreeMap<TicketId, &'a Row>,
    events: BTreeMap<TicketId, Vec<Event>>,
}

/// True for the outcomes that mean the work was not done.
fn dropped(r: &Row) -> bool {
    matches!(
        r.front.outcome,
        Some(Outcome::WontFix | Outcome::Duplicate | Outcome::Invalid)
    )
}

/// Which events [`events_of`] parses.
#[derive(Clone, Copy)]
enum Want {
    /// Only evidence and land events, all that picking and qualifying read.
    Outcomes,
    /// Every event of one ticket, for the life stop.
    Ticket(TicketId),
}

/// True when the event text surely is not an evidence or land event, judged from its leading
/// `kind` line; unsure texts return false so they are parsed in full.
fn surely_other_kind(text: &str) -> bool {
    let Some(line) = text.lines().find(|l| !l.trim().is_empty()) else {
        return false;
    };
    let Some(value) = line
        .strip_prefix("kind")
        .and_then(|r| r.trim_start().strip_prefix('='))
    else {
        return false;
    };
    let kind = value.trim().trim_matches('"');
    !matches!(kind, "evidence" | "land") && !kind.contains(['\'', '\\'])
}

/// The parsed events wanted by `want`, in event order; unreadable files are skipped.
///
/// Skipping the TOML parse of events the tour never reads is the reindex speedup: a large ledger
/// holds tens of thousands of events and only a few kinds matter.
fn events_of(input: &GenInput<'_>, want: Want) -> BTreeMap<TicketId, Vec<Event>> {
    let mut out: BTreeMap<TicketId, Vec<Event>> = BTreeMap::new();
    let prefix = format!("{EVENTS_DIR}/");
    for (path, bytes) in input.tree {
        let Some(rest) = path.strip_prefix(&prefix) else {
            continue;
        };
        let Some((tid, file)) = rest.split_once('/') else {
            continue;
        };
        let Some(stem) = file.strip_suffix(".toml") else {
            continue;
        };
        let (Ok(tid), Ok(eid)) = (tid.parse::<TicketId>(), stem.parse::<EventId>()) else {
            continue;
        };
        match want {
            Want::Ticket(only) if only != tid => continue,
            _ => {}
        }
        let Ok(text) = std::str::from_utf8(bytes) else {
            continue;
        };
        if matches!(want, Want::Outcomes) && surely_other_kind(text) {
            continue;
        }
        let Ok(ev) = Event::parse(eid, text) else {
            continue;
        };
        out.entry(tid).or_default().push(ev);
    }
    for list in out.values_mut() {
        list.sort_by_key(Event::order_key);
    }
    out
}

impl Facts<'_> {
    fn has(&self, id: TicketId, pred: impl Fn(&EventBody) -> bool) -> bool {
        self.events
            .get(&id)
            .is_some_and(|l| l.iter().any(|e| pred(&e.body)))
    }

    /// Done, not dropped, with an evidence event and a land event.
    fn closed_ok(&self, r: &Row) -> bool {
        r.front.category == Category::Done
            && !dropped(r)
            && self.has(r.id, |b| matches!(b, EventBody::Evidence(_)))
            && self.has(r.id, |b| matches!(b, EventBody::Land(_)))
    }

    fn epic_ok(r: &Row) -> bool {
        r.front.ty == TicketType::Epic && !dropped(r)
    }

    fn good_first_ok(r: &Row) -> bool {
        r.front.category == Category::Todo
            && r.blockers.is_empty()
            && is_good_first(&r.front.labels)
    }

    /// Time of the ticket's newest land event, as the recency key.
    fn landed_at(&self, id: TicketId) -> Option<(gob_time::Stamp, TicketId)> {
        self.events
            .get(&id)?
            .iter()
            .rev()
            .find_map(|e| match e.body {
                EventBody::Land(_) => Some((e.at, id)),
                _ => None,
            })
    }
}

/// Pick the three examples deterministically from the ledger.
fn pick(facts: &Facts<'_>, rows: &[Row]) -> Pins {
    let closed = rows
        .iter()
        .filter(|r| facts.closed_ok(r))
        .filter_map(|r| facts.landed_at(r.id))
        .max()
        .map(|(_, id)| id);
    let dirs = by_dir(rows);
    let epic = dirs
        .iter()
        .filter_map(|(d, members)| top_of(d, members).map(|t| (members.len(), t)))
        .filter(|(_, t)| Facts::epic_ok(t) && !t.front.category.is_terminal())
        .min_by_key(|(n, t)| (std::cmp::Reverse(*n), t.id))
        .map(|(_, t)| t.id);
    let good_first = rows.iter().find(|r| Facts::good_first_ok(r)).map(|r| r.id);
    Pins {
        closed,
        epic,
        good_first,
    }
}

/// Keep each previous pin that still qualifies; replace the others and say so.
#[must_use]
pub fn resolve(input: &GenInput<'_>, previous: &Pins) -> Resolved {
    resolve_rows(input, &load(input), previous)
}

/// [`resolve`] over rows the caller already loaded.
fn resolve_rows(input: &GenInput<'_>, rows: &[Row], previous: &Pins) -> Resolved {
    let facts = Facts {
        rows: rows.iter().map(|r| (r.id, r)).collect(),
        events: events_of(input, Want::Outcomes),
    };
    let fresh = pick(&facts, rows);
    let mut notes = Vec::new();
    let mut keep = |name: &str,
                    old: Option<TicketId>,
                    new: Option<TicketId>,
                    ok: &dyn Fn(&Row) -> bool| {
        match old {
            Some(o) if facts.rows.get(&o).is_some_and(|r| ok(r)) => Some(o),
            Some(o) => {
                notes.push(match new {
                    Some(n) => format!("The {name} example {o} is gone or no longer qualifies; replaced by {n}."),
                    None => format!("The {name} example {o} is gone or no longer qualifies; no replacement exists."),
                });
                new
            }
            None => new,
        }
    };
    let pins = Pins {
        closed: keep("closed-ticket", previous.closed, fresh.closed, &|r| {
            facts.closed_ok(r)
        }),
        epic: keep("epic", previous.epic, fresh.epic, &|r| {
            Facts::epic_ok(r) && !r.front.category.is_terminal()
        }),
        good_first: keep(
            "good-first",
            previous.good_first,
            fresh.good_first,
            &Facts::good_first_ok,
        ),
    };
    Resolved { pins, notes }
}

fn link(r: &Row) -> String {
    format!(
        "[{}]({}) ({})",
        cell(&r.front.title),
        r.path.replace(' ', "%20"),
        r.handle
    )
}

fn fill(template: &str, vars: &[(&str, String)]) -> String {
    let mut out = template.replace("{{frob}}", COMMAND);
    for (k, v) in vars {
        out = out.replace(&format!("{{{{{k}}}}}"), v);
    }
    out
}

/// Render `TOUR.md` for explicit `pins` and `notes`.
#[must_use]
pub fn render_with(input: &GenInput<'_>, pins: &Pins, notes: &[String]) -> Vec<(String, Vec<u8>)> {
    render_rows(input, &load(input), pins, notes)
}

/// [`render_with`] over rows the caller already loaded.
fn render_rows(
    input: &GenInput<'_>,
    rows: &[Row],
    pins: &Pins,
    notes: &[String],
) -> Vec<(String, Vec<u8>)> {
    let by_id: BTreeMap<TicketId, &Row> = rows.iter().map(|r| (r.id, r)).collect();
    let life_events = pins
        .closed
        .map(|id| events_of(input, Want::Ticket(id)))
        .unwrap_or_default();
    let row = |id: Option<TicketId>| id.and_then(|i| by_id.get(&i).copied());

    let epic = row(pins.epic).map_or_else(
        || "not yet chosen (no epic exists)".to_owned(),
        |r| {
            let size = by_dir(rows)
                .iter()
                .find(|(d, m)| top_of(d, m).is_some_and(|t| t.id == r.id))
                .map_or(0, |(_, m)| m.len());
            format!("{} with {size} tickets", link(r))
        },
    );
    let life = row(pins.closed).map_or_else(
        || "No ticket has been closed with evidence and a land yet.".to_owned(),
        |r| {
            let mut s = format!("{} followed through its events:\n\n", link(r));
            for e in life_events
                .get(&r.id)
                .map(Vec::as_slice)
                .unwrap_or_default()
            {
                let _ = writeln!(s, "- `{}` at {} (event {})", e.kind, e.at, e.id);
                if let EventBody::Land(l) = &e.body {
                    let _ = writeln!(s, "  - landed as commit `{}` on `{}`", l.commit, l.base_ref);
                }
            }
            s
        },
    );
    let turn = row(pins.good_first).map_or_else(
        || "No good-first ticket is ready; see [the indexes](indexes/README.md).".to_owned(),
        |r| {
            let mut s = format!("{}\n\n", link(r));
            if let Some(n) = super::good_first::start_here(&r.body) {
                let _ = write!(s, "{n}\n\n");
            }
            let h = &r.handle;
            let _ = write!(
                s,
                "```\n{COMMAND} ticket show {h} --format md\n{COMMAND} work {h}\n{COMMAND} land\n```\n"
            );
            s
        },
    );
    let vars = [("epic", epic), ("life", life), ("turn", turn)];
    let mut out = format!(
        "{GENERATED_MARKER_PREFIX} v{}: DO NOT EDIT -->\n# Tour\n\nAs of event {}. Five stops through this repository, with real examples.\n\n",
        input.version,
        input.as_of.unwrap_or("none"),
    );
    for stop in STOPS {
        out.push_str(&fill(stop, &vars));
        out.push('\n');
    }
    if !notes.is_empty() {
        out.push_str("## Notes\n\n");
        for n in notes {
            let _ = writeln!(out, "- {n}");
        }
    }
    vec![(PATH.to_owned(), out.into_bytes())]
}

/// Render `TOUR.md` with examples picked from scratch (no previous pins).
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    let rows = load(input);
    let r = resolve_rows(input, &rows, &Pins::default());
    render_rows(input, &rows, &r.pins, &r.notes)
}

//! The scrumban board: tickets sorted into columns, WIP limits, an expedite lane and card ages.
//!
//! `frob board` (design: `releases.md` section 4, `pm-enforcement.md` section 6)
//! builds a typed [`Board`] with [`build`] and renders it with [`render`]; the
//! text view and the JSON view are the same data, so they cannot disagree.
//!
//! # One count
//!
//! Column limits and over-limit marks are read from the [`Wip`] the caller
//! sorted with [`wip::read`](crate::rules::wip::read), the count shared with
//! `PM013` and the `work` gate: only live standard holders count against
//! `[pm.wip] in_progress`, expedite holders count against the lane's
//! `[pm.classes] expedite_max`, and stale holders are listed but never counted.
//!
//! # Columns
//!
//! - **triage**: category `triage`;
//! - **todo**: category `todo` with no open blocker, in `doable` order first;
//! - **in-progress**: category `in-progress`, with the repository limit;
//! - **blocked**: category `todo` with an open blocker (blocked is derived,
//!   never a stored category; an in-progress ticket stays in its column so the
//!   count matches PM013);
//! - **done**: tickets done within [`DONE_DAYS`], newest first, at most
//!   [`DEFAULT_SHOWN`] cards (`Input::show`).
//!
//! The expedite lane (open when `expedite_max` is above 0) holds every live
//! expedite-class ticket that is not done, in-progress ones first. Epics are
//! left off: they cannot be worked directly. A card's age is the time since
//! it entered its current category, from the ticket's `transition` events
//! ([`entered`]) against the injected `now`.

// frob:ticket 01M4069W45P08YPC4YH4XZVMNC

use std::collections::BTreeMap;

use frob_ledger::TicketId;
use frob_ledger::event::{Event, EventBody};
use frob_ledger::index::Summary;
use frob_ledger::model::{Category, Class, Stamp, TicketType};
use schemars::JsonSchema;
use serde::Serialize;

use crate::rules::wip::{Wip, WipLimits};

/// Days a done ticket stays on the board.
pub const DONE_DAYS: i64 = 7;
/// Default cap on cards per column (`Input::show`); the rest are counted in [`Column::hidden`].
pub const DEFAULT_SHOWN: usize = 8;
/// Narrowest column the side-by-side layout accepts before stacking.
const MIN_CELL: usize = 16;
/// Gap between side-by-side columns.
const GUTTER: &str = " | ";

/// A board column.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, JsonSchema)]
#[serde(rename_all = "kebab-case")]
pub enum ColumnKind {
    /// Awaiting acceptance.
    Triage,
    /// Accepted, unblocked and queued.
    Todo,
    /// Being worked.
    InProgress,
    /// Queued behind an open blocker.
    Blocked,
    /// Recently finished.
    Done,
}

impl ColumnKind {
    /// Board order, left to right.
    pub const ALL: [Self; 5] = [
        Self::Triage,
        Self::Todo,
        Self::InProgress,
        Self::Blocked,
        Self::Done,
    ];

    /// The column title.
    pub const fn title(self) -> &'static str {
        match self {
            Self::Triage => "triage",
            Self::Todo => "todo",
            Self::InProgress => "in-progress",
            Self::Blocked => "blocked",
            Self::Done => "done",
        }
    }
}

/// One ticket on the board.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Card {
    /// Handle with its `~`.
    pub handle: String,
    /// Title.
    pub title: String,
    /// Story points, when sized.
    pub points: Option<u8>,
    /// Workflow category.
    pub category: String,
    /// Class of service.
    pub class: String,
    /// Actor holding the live lease, when there is one.
    pub holder: Option<String>,
    /// Seconds since the ticket entered its current category.
    pub age_secs: i64,
    /// The age as shown: `<1m`, `5m`, `7h` or `3d`.
    pub age: String,
    /// In progress with an expired lease (not counted against any limit).
    pub stale: bool,
    /// Due date, when set.
    pub due: Option<String>,
}

/// A column or the expedite lane: its cards, count and limit.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Column {
    /// Which column.
    pub kind: Option<ColumnKind>,
    /// The title shown in the header (`expedite` for the lane).
    pub title: String,
    /// Tickets counted: for limited columns the live holders the WIP count sees.
    pub count: usize,
    /// The limit; absent when the column is unlimited or its limit is off (0).
    pub limit: Option<u32>,
    /// True when `count` is above `limit`.
    pub over: bool,
    /// Cards shown, in order.
    pub cards: Vec<Card>,
    /// Cards left off the display (done older than the cap).
    pub hidden: usize,
}

/// The whole board: the expedite lane (when open) and the five columns.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct Board {
    /// The expedite lane; absent when `expedite_max` is 0.
    pub expedite: Option<Column>,
    /// Triage, todo, in-progress, blocked and done, in that order.
    pub columns: Vec<Column>,
}

/// Everything [`build`] needs, read by the caller.
#[derive(Debug, Clone)]
pub struct Input {
    /// Every ticket at the index.
    pub tickets: Vec<Summary>,
    /// In-progress tickets sorted by `wip::read` (the one WIP count).
    pub wip: Wip,
    /// `[pm.wip] in_progress` and `[pm.classes] expedite_max`.
    pub limits: WipLimits,
    /// When each shown ticket entered its category (see [`entered`]); missing means its creation time.
    pub entered: BTreeMap<TicketId, Stamp>,
    /// Actor of the live lease per ticket.
    pub holders: BTreeMap<TicketId, String>,
    /// Todo tickets in `doable` order; the todo column lists these first.
    pub doable_order: Vec<TicketId>,
    /// The injected clock.
    pub now: Stamp,
    /// Most cards listed per column (0 lists all); in-progress and the lane are never cut.
    pub show: usize,
}

/// When `summary`'s ticket entered its current category: its latest `transition` into it, else its creation.
pub fn entered(events: &[Event], summary: &Summary) -> Stamp {
    events
        .iter()
        .rev()
        .find_map(|e| match &e.body {
            EventBody::Transition(t) if t.to == summary.category => Some(e.at),
            _ => None,
        })
        .unwrap_or(summary.created)
}

/// True when the board shows `s` at all and, for done tickets, `now` is inside the recent window.
pub fn shown(s: &Summary, entered: Stamp, now: Stamp) -> bool {
    s.ty != TicketType::Epic
        && (s.category != Category::Done || now.unix() - entered.unix() <= DONE_DAYS * 86_400)
}

/// An age in seconds as `<1m`, `Nm`, `Nh` or `Nd` (a clock behind the event reads `<1m`).
pub fn format_age(secs: i64) -> String {
    match secs {
        s if s < 60 => "<1m".to_owned(),
        s if s < 3_600 => format!("{}m", s / 60),
        s if s < 86_400 => format!("{}h", s / 3_600),
        s => format!("{}d", s / 86_400),
    }
}

fn card(s: &Summary, input: &Input, stale: bool) -> Card {
    let at = input.entered.get(&s.id).copied().unwrap_or(s.created);
    let age_secs = (input.now.unix() - at.unix()).max(0);
    Card {
        handle: s.handle.clone(),
        title: s.title.clone(),
        points: s.points,
        category: s.category.to_string(),
        class: s.class.to_string(),
        holder: input.holders.get(&s.id).cloned(),
        age_secs,
        age: format_age(age_secs),
        stale,
        due: s.due.map(|d| d.to_string()),
    }
}

/// Build the board from `input`: sort tickets into the lane and columns, take counts and limits from the WIP count.
pub fn build(input: &Input) -> Board {
    let lane_open = input.limits.expedite_max > 0;
    let stale_ids: Vec<TicketId> = input.wip.stale.iter().map(|s| s.id).collect();
    let shown: Vec<&Summary> = input
        .tickets
        .iter()
        .filter(|s| {
            let at = input.entered.get(&s.id).copied().unwrap_or(s.created);
            shown(s, at, input.now)
        })
        .collect();
    let in_lane =
        |s: &Summary| lane_open && s.class == Class::Expedite && s.category != Category::Done;
    let mk = |s: &&Summary| card(s, input, stale_ids.contains(&s.id));

    let expedite = lane_open.then(|| {
        let mut members: Vec<&Summary> = shown.iter().copied().filter(|s| in_lane(s)).collect();
        members.sort_by_key(|s| match s.category {
            Category::InProgress => 0,
            Category::Todo => 1,
            _ => 2,
        });
        let count = input.wip.expedite.len();
        let max = input.limits.expedite_max;
        Column {
            kind: None,
            title: "expedite".to_owned(),
            count,
            limit: Some(max),
            over: count > max as usize,
            cards: members.iter().map(mk).collect(),
            hidden: 0,
        }
    });

    let columns = ColumnKind::ALL
        .iter()
        .map(|&kind| {
            let mut members: Vec<&Summary> = shown
                .iter()
                .copied()
                .filter(|s| !in_lane(s))
                .filter(|s| match kind {
                    ColumnKind::Triage => s.category == Category::Triage,
                    ColumnKind::Todo => s.category == Category::Todo && !s.blocked,
                    ColumnKind::InProgress => s.category == Category::InProgress,
                    ColumnKind::Blocked => s.category == Category::Todo && s.blocked,
                    ColumnKind::Done => s.category == Category::Done,
                })
                .collect();
            match kind {
                ColumnKind::Todo => members.sort_by_key(|s| {
                    input
                        .doable_order
                        .iter()
                        .position(|d| *d == s.id)
                        .unwrap_or(usize::MAX)
                }),
                ColumnKind::Done => members.sort_by_key(|s| {
                    std::cmp::Reverse(input.entered.get(&s.id).copied().unwrap_or(s.created))
                }),
                _ => {}
            }
            let total = members.len();
            let hidden = if input.show > 0 && kind != ColumnKind::InProgress {
                total.saturating_sub(input.show)
            } else {
                0
            };
            members.truncate(total - hidden);
            let (count, limit) = if kind == ColumnKind::InProgress {
                let lim = input.limits.in_progress;
                (input.wip.standard.len(), (lim > 0).then_some(lim))
            } else {
                (total, None)
            };
            Column {
                kind: Some(kind),
                title: kind.title().to_owned(),
                count,
                limit,
                over: limit.is_some_and(|l| count > l as usize),
                cards: members.iter().map(mk).collect(),
                hidden,
            }
        })
        .collect();
    tracing::debug!(lane = lane_open, "board built");
    Board { expedite, columns }
}

/// How to lay the board out.
#[derive(Debug, Clone, Copy)]
pub struct RenderOptions {
    /// Total line width in characters.
    pub width: usize,
    /// Wrap over-limit headers in red ANSI.
    pub color: bool,
}

/// One output line; `red` marks an over-limit header.
struct Line {
    text: String,
    red: bool,
}

impl Line {
    fn plain(text: String) -> Self {
        Self { text, red: false }
    }
}

/// `s` as ASCII only (anything else becomes `?`) with control characters turned into spaces.
fn ascii(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            ' '..='~' => c,
            _ => {
                if c.is_control() {
                    ' '
                } else {
                    '?'
                }
            }
        })
        .collect()
}

/// `s` cut to `width`, ending in `..` when it was cut.
fn fit(s: &str, width: usize) -> String {
    if s.len() <= width {
        s.to_owned()
    } else if width <= 2 {
        s[..width].to_owned()
    } else {
        format!("{}..", &s[..width - 2])
    }
}

/// `s` wrapped at word boundaries into at most `max` lines of `width`, the last cut with `..`.
fn wrap(s: &str, width: usize, max: usize) -> Vec<String> {
    let mut lines: Vec<String> = Vec::new();
    let mut cur = String::new();
    for word in s.split_whitespace() {
        let sep = usize::from(!cur.is_empty());
        if cur.len() + sep + word.len() <= width {
            if sep == 1 {
                cur.push(' ');
            }
            cur.push_str(word);
        } else {
            if !cur.is_empty() {
                lines.push(std::mem::take(&mut cur));
            }
            word.clone_into(&mut cur);
        }
    }
    if !cur.is_empty() {
        lines.push(cur);
    }
    if lines.len() > max {
        let rest = lines.split_off(max - 1).join(" ");
        lines.push(rest);
    }
    lines.iter().map(|l| fit(l, width)).collect()
}

/// The header cut to `width`: the title gives way, the count, limit and over mark (`!`) never do.
fn header(col: &Column, width: usize) -> String {
    let mut tail = match col.limit {
        Some(l) => format!(" {}/{l}", col.count),
        None => format!(" {}", col.count),
    };
    if col.over {
        tail.push_str(" !");
    }
    format!(
        "{}{tail}",
        fit(&col.title, width.saturating_sub(tail.len()))
    )
}

/// The marks line of a card: holder, `STALE`, due date.
fn marks(c: &Card) -> String {
    let mut parts: Vec<String> = Vec::new();
    if let Some(h) = &c.holder {
        parts.push(format!("@{}", ascii(h)));
    }
    if c.stale {
        parts.push("STALE".to_owned());
    }
    if let Some(d) = &c.due {
        parts.push(format!("due {}", &d[..d.len().min(10)]));
    }
    parts.join(" ")
}

fn points(c: &Card) -> String {
    c.points.map_or_else(|| "-".to_owned(), |p| format!("{p}p"))
}

/// One column as lines no wider than `width`.
fn column_lines(col: &Column, width: usize) -> Vec<Line> {
    let head = header(col, width);
    let mut out = vec![
        Line {
            text: head,
            red: col.over,
        },
        Line::plain("-".repeat(width)),
    ];
    for c in &col.cards {
        out.push(Line::plain(fit(
            &format!("{} {} {}", c.handle, points(c), c.age),
            width,
        )));
        out.extend(
            wrap(&ascii(&c.title), width, 2)
                .into_iter()
                .map(Line::plain),
        );
        let m = marks(c);
        if !m.is_empty() {
            out.push(Line::plain(fit(&m, width)));
        }
        out.push(Line::plain(String::new()));
    }
    if col.hidden == 0 {
        out.pop_if(|l| l.text.is_empty());
    } else {
        out.push(Line::plain(fit(&format!("+{} more", col.hidden), width)));
    }
    if col.cards.is_empty() && col.hidden == 0 {
        out.push(Line::plain("(none)".to_owned()));
    }
    out
}

/// A lane card on one line: handle, points, age, marks, category and title, cut to `width`.
fn lane_line(c: &Card, width: usize) -> String {
    let m = marks(c);
    let m = if m.is_empty() { m } else { format!(" {m}") };
    fit(
        &format!(
            "{} {} {} [{}]{m} {}",
            c.handle,
            points(c),
            c.age,
            c.category,
            ascii(&c.title)
        ),
        width,
    )
}

fn paint(l: &Line, pad: usize, color: bool) -> String {
    let text = format!("{:<pad$}", l.text);
    if color && l.red {
        format!("\x1b[31m{text}\x1b[0m")
    } else {
        text
    }
}

/// Render `board` as ASCII lines at `opts.width`: the expedite lane on top, then the columns side by side, or stacked when they would be narrower than 16 characters.
pub fn render(board: &Board, opts: &RenderOptions) -> Vec<String> {
    let width = opts.width.max(MIN_CELL);
    let mut out: Vec<String> = Vec::new();
    if let Some(lane) = &board.expedite {
        let head = Line {
            text: header(lane, width),
            red: lane.over,
        };
        out.push(paint(&head, 0, opts.color));
        out.push("=".repeat(width));
        if lane.cards.is_empty() {
            out.push("(none)".to_owned());
        }
        out.extend(lane.cards.iter().map(|c| lane_line(c, width)));
        out.push(String::new());
    }
    let n = board.columns.len();
    let gutters = GUTTER.len() * n.saturating_sub(1);
    let cell = width.saturating_sub(gutters) / n.max(1);
    if cell >= MIN_CELL {
        let cols: Vec<Vec<Line>> = board
            .columns
            .iter()
            .map(|c| column_lines(c, cell))
            .collect();
        let rows = cols.iter().map(Vec::len).max().unwrap_or(0);
        for r in 0..rows {
            let row: Vec<String> = cols
                .iter()
                .map(|c| {
                    c.get(r)
                        .map_or_else(|| " ".repeat(cell), |l| paint(l, cell, opts.color))
                })
                .collect();
            out.push(row.join(GUTTER).trim_end().to_owned());
        }
    } else {
        for col in &board.columns {
            for l in column_lines(col, width) {
                out.push(paint(&l, 0, opts.color).trim_end().to_owned());
            }
            out.push(String::new());
        }
    }
    while out.last().is_some_and(String::is_empty) {
        out.pop();
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn age_reads_in_the_coarsest_unit() {
        assert_eq!(format_age(-5), "<1m");
        assert_eq!(format_age(59), "<1m");
        assert_eq!(format_age(300), "5m");
        assert_eq!(format_age(7 * 3_600 + 5), "7h");
        assert_eq!(format_age(3 * 86_400 + 100), "3d");
    }

    #[test]
    fn fit_and_wrap_keep_to_the_width() {
        assert_eq!(fit("abcdefgh", 6), "abcd..");
        assert_eq!(
            wrap("one two three four five", 9, 2),
            vec!["one two", "three f.."]
        );
        assert_eq!(ascii("caf\u{e9}\tx"), "caf? x");
    }
}

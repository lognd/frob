//! `PM008` and `PM009`: ticket aging per category and the unsized ready ticket.
//!
//! A ticket "ages" from its latest transition into its current category (its
//! creation when it never moved). `PM008` fires once a ticket has stayed in
//! `in-progress` or `todo` (the ready queue) past `[pm.max_age_days]`; `PM009`
//! fires for a ready ticket with no points. The pure cores [`pm008`] and
//! [`pm009`] take one ticket's facts; [`evaluate`] walks a ledger at `now`.

// frob:ticket 01M4CT0AF76FJTWFG10SKXJZAZ

use frob_ledger::Ledger;
use frob_ledger::event::EventBody;
use frob_ledger::index::{ListFilter, Summary};
use frob_ledger::model::{Category, TicketType};
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_time::Stamp;

use crate::config::PmMaxAgeTable;
use crate::error::Result;
use crate::eval::membership::Evaluation;

/// Seconds in a day.
const DAY_SECS: i64 = 86_400;

/// A ticket has stayed in its category longer than `[pm.max_age_days]` allows.
///
/// Fires once per aged ticket, naming the category and the age in days.
/// Limits: `in_progress` (default 3) and `ready` (default 30); 0 is off.
///
/// ## Remedy
///
/// Finish or land the ticket, requeue or re-plan it, drop it with a reason, or
/// raise `[pm.max_age_days]` in `frob.toml`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM008",
    slug = "ticket-aged",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm008;

/// A ready ticket (`todo`, not an epic) has no story points.
///
/// ## Remedy
///
/// Size the ticket (`frob ticket edit --points N`) or move it out of the ready queue.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM009",
    slug = "ready-unsized",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm009;

fn id8() -> RuleId {
    Pm008
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

fn id9() -> RuleId {
    Pm009
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The limit in days for `category` under `limits`; `None` for categories that do not age or a limit of 0.
pub fn limit_days(limits: &PmMaxAgeTable, category: Category) -> Option<u32> {
    let days = match category {
        Category::InProgress => limits.in_progress,
        Category::Todo => limits.ready,
        Category::Triage | Category::Done => 0,
    };
    (days > 0).then_some(days)
}

/// Whole days from `since` to `now` (0 when `since` is in the future).
pub fn age_days(since: Stamp, now: Stamp) -> i64 {
    (now.unix() - since.unix()).max(0) / DAY_SECS
}

/// Evaluate `PM008` for one ticket: a finding when `age` days exceed the `limit` of its `category`.
pub fn pm008(handle: &str, category: Category, age: i64, limit: u32) -> Option<Finding> {
    if age <= i64::from(limit) {
        return None;
    }
    tracing::debug!(ticket = handle, %category, age, limit, "PM008: ticket aged");
    Some(Finding::new(
        id8(),
        Severity::Error,
        None,
        format!(
            "ticket {handle} has been {category} for {age} day(s), past the limit of {limit} ([pm.max_age_days]): finish, requeue or drop it"
        ),
        &format!("ticket:{handle}"),
    ))
}

/// Evaluate `PM009` for one ticket: a finding when it is ready and `points` is unset.
pub fn pm009(handle: &str, points: Option<u8>) -> Option<Finding> {
    if points.is_some() {
        return None;
    }
    tracing::debug!(ticket = handle, "PM009: ready ticket without points");
    Some(Finding::new(
        id9(),
        Severity::Error,
        None,
        format!("ready ticket {handle} has no points: size it or move it out of the ready queue"),
        &format!("ticket:{handle}"),
    ))
}

/// When `id` entered its current category: the latest transition event, else `created`.
fn entered(ledger: &Ledger, summary: &Summary) -> Result<Stamp> {
    let since = ledger
        .events(summary.id)?
        .into_iter()
        .filter(|e| matches!(&e.body, EventBody::Transition(t) if t.to == summary.category))
        .map(|e| e.at)
        .max()
        .unwrap_or(summary.created);
    Ok(since)
}

/// Run `PM008` and `PM009` over every in-progress and ready (`todo`, non-epic) ticket of `ledger` at `now`.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, limits: &PmMaxAgeTable, now: Stamp) -> Result<Evaluation> {
    let mut out = Evaluation::default();
    for category in [Category::InProgress, Category::Todo] {
        let filter = ListFilter {
            category: Some(category),
            ..ListFilter::default()
        };
        for s in ledger.list(&filter)? {
            if s.ty == TicketType::Epic {
                continue;
            }
            out.subjects += 1;
            if let Some(limit) = limit_days(limits, category) {
                let age = age_days(entered(ledger, &s)?, now);
                out.findings.extend(pm008(&s.handle, category, age, limit));
            }
            if category == Category::Todo {
                out.findings.extend(pm009(&s.handle, s.points));
            }
        }
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM008/PM009 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pm008_fires_only_past_the_limit() {
        // frob:tests crates/frob-pm/src/legacy/aging.rs::pm008
        assert!(pm008("~A", Category::InProgress, 3, 3).is_none());
        let f = pm008("~A", Category::InProgress, 4, 3).expect("fires");
        assert!(f.message.contains("4 day(s)"), "{}", f.message);
    }

    #[test]
    fn pm009_fires_without_points() {
        // frob:tests crates/frob-pm/src/legacy/aging.rs::pm009
        assert!(pm009("~A", Some(2)).is_none());
        assert!(pm009("~A", None).is_some());
    }

    #[test]
    fn zero_limit_is_off_and_age_floors() {
        // frob:tests crates/frob-pm/src/legacy/aging.rs::limit_days
        // frob:tests crates/frob-pm/src/legacy/aging.rs::age_days
        let l = PmMaxAgeTable {
            in_progress: 0,
            ready: 30,
        };
        assert_eq!(limit_days(&l, Category::InProgress), None);
        assert_eq!(limit_days(&l, Category::Todo), Some(30));
        assert_eq!(
            age_days(Stamp::from_unix(0), Stamp::from_unix(2 * 86_400 + 5)),
            2
        );
        assert_eq!(age_days(Stamp::from_unix(10), Stamp::from_unix(0)), 0);
    }
}

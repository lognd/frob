//! `PM003`-`PM007`: a story is structured, states value, has checkable criteria and fits a cycle; a user-visible task has a story.
//!
//! Designed in `pm-enforcement.md` sections 2-3. The pure cores [`pm003`] to
//! [`pm007`] each take one ticket and return at most one finding; [`evaluate`]
//! walks the open tickets of a ledger and runs them. Quality objectives
//! (`flavour = quality_objective`) have their own structure (`PM020`-`PM029`)
//! and are skipped by the user-story rules.

// frob:ticket 01M4CT054RN6SY75KRYSY14778

use std::collections::{BTreeMap, BTreeSet};

use frob_ledger::index::ListFilter;
use frob_ledger::model::{Ticket, TicketType};
use frob_ledger::{Ledger, TicketId};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::eval::membership::Evaluation;
use crate::legacy::good_first::is_gwt;

/// The `[pm] max_story_points` default: a story above it is too big to finish in one cycle.
pub const DEFAULT_MAX_STORY_POINTS: u32 = 8;

/// The fewest words each part of a user story needs.
pub const MIN_STORY_WORDS: usize = 3;

/// The share of `so_that` tokens also in `i_want` at or above which `PM004` calls it a restatement.
pub const OVERLAP_THRESHOLD: f64 = 0.8;

/// The label that records an explicit reason a task has no parent story.
pub const NO_STORY_LABEL: &str = "no-story";

/// The criterion prefix that marks an explicit free-form (non Given/When/Then) criterion.
pub const FREE_FORM_PREFIX: &str = "free-form:";

/// The flavour that exempts a story from the user-story rules.
const OBJECTIVE_FLAVOUR: &str = "quality_objective";

/// Path prefixes whose changes are not user-visible behavior.
const INTERNAL_PREFIXES: &[&str] = &[
    "docs/",
    "tests/",
    "tickets/",
    "changelog.d/",
    ".github/",
    "notes/",
    "scripts/",
];

/// A story lacks one of `as_a`, `i_want`, `so_that`, or one is shorter than three words.
///
/// A structured story is `persona` (as a), `capability` (I want) and
/// `outcome_text` (so that), each at least three words, so the goal names who
/// wants what and why.
///
/// ## Remedy
///
/// Set the missing parts, for example `frob ticket new --type story --as-a ...
/// --i-want ... --so-that ...`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM003",
    slug = "story-structure",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm003;

/// A story's `so_that` restates its `i_want`.
///
/// When most words of the value statement are already in the capability, the
/// story states the mechanism twice and no value.
///
/// ## Remedy
///
/// Rewrite `so_that` to say what the capability buys the persona.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM004",
    slug = "story-restates-want",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm004;

/// A story has no acceptance criteria, or a criterion is neither Given/When/Then nor explicit free-form.
///
/// A criterion reads `Given ..., when ..., then ...`, or starts with
/// `free-form:` and gives its reason.
///
/// ## Remedy
///
/// Add criteria, or rewrite each as Given/When/Then.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM005",
    slug = "story-criteria-shape",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm005;

/// A story is larger than `[pm] max_story_points`.
///
/// INVEST asks for a small story; one above the limit cannot finish in a cycle.
///
/// ## Remedy
///
/// Split the story, or raise `[pm] max_story_points` in `frob.toml`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM006",
    slug = "story-too-large",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm006;

/// A task with user-visible scope has no parent story and no `no-story` reason.
///
/// A task whose scope reaches beyond docs, tests and tickets changes behavior a
/// user can see; that needs a story. Bugs and chores may stand alone.
///
/// ## Remedy
///
/// Set a parent story with `frob ticket edit --parent STORY`, or label the task
/// `no-story` and state why in its body.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM007",
    slug = "task-without-story",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm007;

fn rule_id<R: Rule>(rule: &R) -> RuleId {
    rule.meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

fn finding<R: Rule>(rule: &R, handle: &str, message: String) -> Finding {
    tracing::debug!(rule = %rule.meta().id, ticket = handle, "story rule fires");
    Finding::new(rule_id(rule), Severity::Error, None, message, handle)
}

fn is_story(t: &Ticket) -> bool {
    t.front.ty == TicketType::Story
}

fn is_user_story(t: &Ticket) -> bool {
    is_story(t) && t.front.flavour.as_deref() != Some(OBJECTIVE_FLAVOUR)
}

fn words(text: Option<&String>) -> usize {
    text.map_or(0, |t| t.split_whitespace().count())
}

/// Lowercase alphanumeric tokens of `text`.
fn tokens(text: &str) -> BTreeSet<String> {
    text.split(|c: char| !c.is_alphanumeric())
        .filter(|w| !w.is_empty())
        .map(str::to_lowercase)
        .collect()
}

/// The share of `so_that` tokens that also occur in `i_want`; 0 when `so_that` has none.
pub fn overlap(i_want: &str, so_that: &str) -> f64 {
    let want = tokens(i_want);
    let so = tokens(so_that);
    if so.is_empty() {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)] // token counts are tiny
    let share = so.intersection(&want).count() as f64 / so.len() as f64;
    share
}

/// True when `glob` names a path whose change a user could see.
pub fn user_visible(glob: &str) -> bool {
    let g = glob.trim_start_matches("./");
    !(INTERNAL_PREFIXES.iter().any(|p| g.starts_with(p))
        || std::path::Path::new(g)
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("md")))
}

// frob:ticket 01M4CT054RN6SY75KRYSY14778
/// Evaluate `PM003` for one story `t` shown as `handle`: a missing or too-short part fires.
pub fn pm003(t: &Ticket, handle: &str) -> Option<Finding> {
    if !is_user_story(t) {
        return None;
    }
    let parts = [
        ("as_a", t.front.persona.as_ref()),
        ("i_want", t.front.capability.as_ref()),
        ("so_that", t.front.outcome_text.as_ref()),
    ];
    let bad: Vec<String> = parts
        .iter()
        .filter(|(_, v)| words(*v) < MIN_STORY_WORDS)
        .map(|(n, v)| {
            if v.is_none() {
                format!("{n} is missing")
            } else {
                format!("{n} is under {MIN_STORY_WORDS} words")
            }
        })
        .collect();
    if bad.is_empty() {
        return None;
    }
    Some(finding(
        &Pm003,
        handle,
        format!(
            "story {handle} is not a structured user story: {}",
            bad.join("; ")
        ),
    ))
}

// frob:ticket 01M4CT054RN6SY75KRYSY14778
/// Evaluate `PM004` for one story `t`: a `so_that` that mostly repeats `i_want` fires.
pub fn pm004(t: &Ticket, handle: &str) -> Option<Finding> {
    if !is_user_story(t) {
        return None;
    }
    let (want, so) = (t.front.capability.as_ref()?, t.front.outcome_text.as_ref()?);
    let share = overlap(want, so);
    if share < OVERLAP_THRESHOLD {
        return None;
    }
    Some(finding(
        &Pm004,
        handle,
        format!(
            "story {handle}: so_that repeats {:.0}% of i_want; state the value the capability buys",
            share * 100.0
        ),
    ))
}

// frob:ticket 01M4CT054RN6SY75KRYSY14778
/// Evaluate `PM005` for one story `t`: no criteria, or one that is neither Given/When/Then nor `free-form:`, fires.
pub fn pm005(t: &Ticket, handle: &str) -> Option<Finding> {
    if !is_user_story(t) {
        return None;
    }
    let msg = if t.front.acceptance.is_empty() {
        format!("story {handle} has no acceptance criteria")
    } else {
        let bad = t
            .front
            .acceptance
            .iter()
            .filter(|a| !is_gwt(&a.text) && !a.text.trim_start().starts_with(FREE_FORM_PREFIX))
            .count();
        if bad == 0 {
            return None;
        }
        format!(
            "story {handle} has {bad} criteria that are not Given/When/Then; rewrite them or start with `{FREE_FORM_PREFIX}` and a reason"
        )
    };
    Some(finding(&Pm005, handle, msg))
}

// frob:ticket 01M4CT054RN6SY75KRYSY14778
/// Evaluate `PM006` for one story `t` against `max` points; 0 turns the rule off.
pub fn pm006(t: &Ticket, handle: &str, max: u32) -> Option<Finding> {
    let points = u32::from(t.front.points?.get());
    if max == 0 || !is_story(t) || points <= max {
        return None;
    }
    Some(finding(
        &Pm006,
        handle,
        format!("story {handle} is {points} points, above [pm] max_story_points = {max}; split it"),
    ))
}

// frob:ticket 01M4CT054RN6SY75KRYSY14778
/// Evaluate `PM007` for one task `t`; `parent_is_story` says whether its parent is a story.
pub fn pm007(t: &Ticket, handle: &str, parent_is_story: bool) -> Option<Finding> {
    if t.front.ty != TicketType::Task
        || parent_is_story
        || t.front.labels.iter().any(|l| l == NO_STORY_LABEL)
        || !t.front.scope.iter().any(|g| user_visible(g))
    {
        return None;
    }
    Some(finding(
        &Pm007,
        handle,
        format!(
            "task {handle} has user-visible scope but no parent story; set a parent story or label it `{NO_STORY_LABEL}` with the reason in the body"
        ),
    ))
}

/// Run `PM003`-`PM007` over every open ticket of `ledger`, with `max_story_points` as the `PM006` limit.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, max_story_points: u32) -> Result<Evaluation> {
    let mut out = Evaluation::default();
    let all = ledger.list(&ListFilter::default())?;
    let stories: BTreeMap<TicketId, bool> = all
        .iter()
        .map(|s| (s.id, s.ty == TicketType::Story))
        .collect();
    for s in all.iter().filter(|s| !s.category.is_terminal()) {
        if !matches!(s.ty, TicketType::Story | TicketType::Task) {
            continue;
        }
        out.subjects += 1;
        let ticket = ledger.show(s.id)?.ticket;
        let parent_story = s
            .parent
            .is_some_and(|p| stories.get(&p).copied().unwrap_or(false));
        out.findings.extend(
            [
                pm003(&ticket, &s.handle),
                pm004(&ticket, &s.handle),
                pm005(&ticket, &s.handle),
                pm006(&ticket, &s.handle, max_story_points),
                pm007(&ticket, &s.handle, parent_story),
            ]
            .into_iter()
            .flatten(),
        );
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM003-PM007 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn overlap_is_the_share_of_so_that_tokens_in_i_want() {
        // frob:tests crates/frob-pm/src/legacy/story.rs::overlap
        assert!((overlap("land refuses stale base", "Land refuses stale base") - 1.0).abs() < 1e-9);
        assert!(overlap("a b c d", "e f") < 1e-9);
        assert!(overlap("a b", "") < 1e-9);
    }

    #[test]
    fn user_visible_skips_docs_tests_and_markdown() {
        // frob:tests crates/frob-pm/src/legacy/story.rs::user_visible
        assert!(user_visible("crates/frob/src/**"));
        assert!(!user_visible("docs/design/x.rs"));
        assert!(!user_visible("README.md"));
        assert!(!user_visible("./tests/it/a.rs"));
    }
}

//! `PM031`: a ticket labelled `good-first` is not ready for a newcomer.
//!
//! A good-first ticket must have at most `[tickets] good_first_max_points` points, a scope,
//! Given/When/Then acceptance and a `## Start here` section (navigation.md section 4.2).
//! The pure core [`missing_parts`] takes one ticket; [`evaluate`] walks the labelled tickets.

// frob:ticket 01M3ZX87KRP6G49GHANMAK5JA8

use frob_ledger::index::ListFilter;
use frob_ledger::model::{Category, Ticket};
use frob_ledger::{Ledger, TicketId};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::error::Result;
use crate::eval::membership::Evaluation;

/// The label that opts a ticket into the good-first checks.
pub const GOOD_FIRST_LABEL: &str = "good-first";

// frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
/// The marker every unfilled placeholder of [`START_HERE_SCAFFOLD`] starts with.
pub const PLACEHOLDER: &str = "<TODO";

/// The `## Start here` body `ticket new --good-first` writes: files to read, the test command and who to ask.
pub const START_HERE_SCAFFOLD: &str = "## Start here\n\n- Files to read first: <TODO: list the files>\n- Test command: <TODO: the command that runs the tests>\n- Who to ask: <TODO: a handle or channel>\n";

/// The `[tickets] good_first_max_points` default.
pub const DEFAULT_MAX_POINTS: u32 = 2;

/// A ticket labelled `good-first` is missing something a newcomer needs.
///
/// Names each missing part: points above the maximum or unset, no scope, a
/// criterion that is not Given/When/Then, or no `## Start here` section.
///
/// ## Remedy
///
/// Fill in the named parts, split the ticket to fit the point limit, or remove the
/// `good-first` label.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "PM031",
    slug = "good-first-incomplete",
    family = "PM",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Pm031;

fn rule_id() -> RuleId {
    Pm031
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The `[tickets] good_first_max_points` of the `frob.toml` in `root`; the default when the file, table or key is absent or unreadable (the config loader reports a malformed file elsewhere).
pub fn max_points(root: &std::path::Path) -> u32 {
    std::fs::read_to_string(root.join("frob.toml"))
        .ok()
        .and_then(|t| t.parse::<toml::Table>().ok())
        .and_then(|t| t.get("tickets")?.get("good_first_max_points")?.as_integer())
        .and_then(|n| u32::try_from(n).ok())
        .unwrap_or(DEFAULT_MAX_POINTS)
}

/// True when `text` reads as Given ... when ... then.
pub(crate) fn is_gwt(text: &str) -> bool {
    let t = text.to_ascii_lowercase();
    let Some(g) = t.find("given") else {
        return false;
    };
    t[g..]
        .find("when")
        .is_some_and(|w| t[g + w..].contains("then"))
}

/// True when the body has a `## Start here` heading.
fn has_start_here(body: &str) -> bool {
    body.lines()
        .any(|l| l.trim_end().eq_ignore_ascii_case("## start here"))
}

/// What a good-first `ticket` lacks, one phrase per missing part; empty when it is complete.
pub fn missing_parts(ticket: &Ticket, max_points: u32) -> Vec<String> {
    let mut out = Vec::new();
    match ticket.front.points {
        None => out.push("points are not set".to_owned()),
        Some(p) if u32::from(p.get()) > max_points => {
            out.push(format!(
                "{} points exceed the maximum of {max_points}",
                p.get()
            ));
        }
        Some(_) => {}
    }
    if ticket.front.scope.is_empty() {
        out.push("no scope".to_owned());
    }
    if ticket.front.acceptance.is_empty() {
        out.push("no acceptance criteria".to_owned());
    } else if ticket.front.acceptance.iter().any(|a| !is_gwt(&a.text)) {
        out.push("acceptance is not Given/When/Then".to_owned());
    }
    // frob:ticket 01M3ZX883TDB46GGDYS92KDR1Q
    if !has_start_here(&ticket.body) {
        out.push("no `## Start here` section".to_owned());
    } else if ticket.body.contains(PLACEHOLDER) {
        out.push("`## Start here` has unfilled placeholders".to_owned());
    }
    out
}

/// One finding for good-first ticket `id` (shown as `handle`) missing `parts`.
fn finding(handle: &str, id: TicketId, parts: &[String]) -> Finding {
    Finding::new(
        rule_id(),
        Severity::Error,
        None,
        format!(
            "good-first ticket {handle} is incomplete: {}",
            parts.join("; ")
        ),
        &id.to_string(),
    )
}

/// Run `PM031` over every open ticket of `ledger` labelled `good-first`, with `max_points` as the point limit.
///
/// # Errors
///
/// Ledger read failures.
pub fn evaluate(ledger: &Ledger, max_points: u32) -> Result<Evaluation> {
    let mut out = Evaluation::default();
    let filter = ListFilter {
        label: Some(GOOD_FIRST_LABEL.to_owned()),
        ..ListFilter::default()
    };
    for summary in ledger.list(&filter)? {
        if matches!(summary.category, Category::Done) {
            continue;
        }
        out.subjects += 1;
        let view = ledger.show(summary.id)?;
        let parts = missing_parts(&view.ticket, max_points);
        if !parts.is_empty() {
            tracing::debug!(ticket = %summary.handle, ?parts, "PM031 fires");
            out.findings
                .push(finding(&summary.handle, summary.id, &parts));
        }
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        "PM031 evaluated"
    );
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gwt_needs_all_three_words_in_order() {
        // frob:tests crates/frob-pm/src/legacy/good_first.rs::is_gwt
        assert!(is_gwt("Given a, when b, then c"));
        assert!(!is_gwt("then c, when b, Given a"));
        assert!(!is_gwt("it works"));
    }

    #[test]
    fn start_here_heading_is_matched_exactly() {
        // frob:tests crates/frob-pm/src/legacy/good_first.rs::has_start_here
        assert!(has_start_here("intro\n\n## Start here\nread x"));
        assert!(!has_start_here("### Start here later"));
    }

    #[test]
    fn scaffold_is_a_start_here_section_full_of_placeholders() {
        // frob:tests crates/frob-pm/src/legacy/good_first.rs::START_HERE_SCAFFOLD
        assert!(has_start_here(START_HERE_SCAFFOLD));
        assert_eq!(START_HERE_SCAFFOLD.matches(PLACEHOLDER).count(), 3);
    }
}

//! Built-in evidence providers for release exit criteria: `epic-closed`, `ci-green`, plus the
//! attester and circularity checks that keep a criterion from being unmeasurable.
//!
//! Design: `pm-and-releases.md` sections 13 and 14. Everything here is pure: the CLI gathers the
//! epic ticket states, the CI facts and the committer identities, and [`bind_builtin`] turns
//! criteria text of the shapes below into bound [`CriterionStatus`] entries (or leaves them
//! unbound with the reason). Nothing is ever assumed green.

// frob:ticket 01M7AV6DCR4Z15F1G4NSKSTFYN
use crate::ci::{CiFacts, CiState};
use crate::status::{CriterionStatus, EvidenceRef};

/// Provider name recorded on evidence bound by [`epic_closed`].
pub const EPIC_CLOSED: &str = "epic-closed";
/// Provider name recorded on evidence bound by [`ci_green`].
pub const CI_GREEN: &str = "ci-green";

/// The ticket state of one epic, as gathered by the caller.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EpicState {
    /// Handle with `~`.
    pub handle: String,
    /// Handles of the epic's tickets that are not done (dropped counts as done).
    pub open: Vec<String>,
    /// How many tickets the epic has in total.
    pub total: usize,
}

/// The canonical criterion text for an epic, the one [`parse_epic`] recognises.
#[must_use]
pub fn epic_criterion_text(handle: &str) -> String {
    format!("every ticket under epic {handle} is done")
}

/// Extract the epic handle from a criterion of the form `every ticket under epic ~X is done`.
#[must_use]
pub fn parse_epic(text: &str) -> Option<&str> {
    let rest = text.trim().strip_prefix("every ticket under epic ")?;
    let handle = rest.strip_suffix(" is done")?.trim();
    (handle.starts_with('~') && handle.len() > 1 && !handle.contains(char::is_whitespace))
        .then_some(handle)
}

/// True when the criterion text names the CI verdict on the release commit.
#[must_use]
pub fn is_ci_criterion(text: &str) -> bool {
    let t = text.to_ascii_lowercase();
    t.starts_with("ci is green")
}

/// True when the criterion is the readiness report itself, which can never bind (circular).
#[must_use]
pub fn is_circular(text: &str) -> bool {
    text.to_ascii_lowercase().contains("frob release status")
}

/// Provider `epic-closed`: passes when the epic has tickets and none is open.
///
/// # Errors
/// The reason the epic is not closed (open tickets listed, or an empty epic).
pub fn epic_closed(epic: &EpicState) -> Result<EvidenceRef, String> {
    if epic.total == 0 {
        return Err(format!(
            "epic {} has no tickets; nothing is measured",
            epic.handle
        ));
    }
    if !epic.open.is_empty() {
        return Err(format!(
            "epic {} has {} open ticket(s): {}",
            epic.handle,
            epic.open.len(),
            epic.open.join(", ")
        ));
    }
    Ok(EvidenceRef {
        provider: EPIC_CLOSED.to_owned(),
        reference: format!("{} ({} tickets done)", epic.handle, epic.total),
        label: None,
    })
}

/// Provider `ci-green`: passes when CI is green on the inspected release commit.
///
/// # Errors
/// The reason CI is not known green (red, pending, unknown, or no commit resolved).
pub fn ci_green(ci: &CiFacts) -> Result<EvidenceRef, String> {
    let Some(sha) = &ci.sha else {
        return Err("the release commit did not resolve".to_owned());
    };
    match &ci.state {
        CiState::Green { checks } => Ok(EvidenceRef {
            provider: CI_GREEN.to_owned(),
            reference: format!("{sha} ({checks} checks)"),
            label: None,
        }),
        CiState::Red { failures } => Err(format!("CI is red on {sha}: {} failing", failures.len())),
        CiState::Pending { running } => {
            Err(format!("CI is pending on {sha}: {} running", running.len()))
        }
        CiState::Unknown(u) => Err(format!("CI is unknown on {sha}: {}", u.reason)),
    }
}

/// Criteria for epics that have none yet, so an epic added to a milestone is never unmeasured.
#[must_use]
pub fn derive_epic_criteria(epics: &[String], existing: &[CriterionStatus]) -> Vec<String> {
    let covered: Vec<&str> = existing
        .iter()
        .filter_map(|c| parse_epic(&c.text))
        .collect();
    let out: Vec<String> = epics
        .iter()
        .filter(|e| !covered.contains(&e.as_str()))
        .map(|e| epic_criterion_text(e))
        .collect();
    tracing::debug!(derived = out.len(), "derived epic-closed criteria");
    out
}

/// Bind every unbound criterion of a recognised shape; returns `(position, reason)` for each
/// recognised criterion that could not bind, and for each circular one.
pub fn bind_builtin(
    criteria: &mut [CriterionStatus],
    epics: &[EpicState],
    ci: &CiFacts,
) -> Vec<(usize, String)> {
    let mut failed = Vec::new();
    for c in criteria.iter_mut().filter(|c| c.state != "bound") {
        let result = if is_circular(&c.text) {
            Err("circular: the criterion is the readiness report itself".to_owned())
        } else if let Some(h) = parse_epic(&c.text) {
            match epics.iter().find(|e| e.handle == h) {
                Some(e) => epic_closed(e),
                None => Err(format!("epic {h} is not part of the gathered facts")),
            }
        } else if is_ci_criterion(&c.text) {
            ci_green(ci)
        } else {
            continue;
        };
        match result {
            Ok(ev) => {
                tracing::info!(position = c.position, provider = %ev.provider, "criterion bound");
                "bound".clone_into(&mut c.state);
                c.evidence.push(ev);
            }
            Err(why) => {
                tracing::warn!(position = c.position, %why, "criterion not bound");
                failed.push((c.position, why));
            }
        }
    }
    failed
}

/// Doctor check: every configured attester must match a committer seen in history, otherwise
/// attestation is dead. Returns one message per attester that matches nobody.
#[must_use]
pub fn attester_problems(attesters: &[String], committers: &[String]) -> Vec<String> {
    attesters
        .iter()
        .filter(|a| !committers.iter().any(|c| c.eq_ignore_ascii_case(a)))
        .map(|a| {
            format!(
                "attester `{a}` matches no committer in history (seen: {}); attestation can never verify",
                if committers.is_empty() { "none".to_owned() } else { committers.join(", ") }
            )
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ci::CiUnknown;

    fn crit(n: usize, text: &str) -> CriterionStatus {
        CriterionStatus {
            position: n,
            text: text.to_owned(),
            state: "unbound".to_owned(),
            evidence: Vec::new(),
        }
    }

    fn ci(state: CiState) -> CiFacts {
        CiFacts {
            sha: Some("abc123".to_owned()),
            state,
            require: true,
        }
    }

    fn epic(open: &[&str], total: usize) -> EpicState {
        EpicState {
            handle: "~E1".to_owned(),
            open: open.iter().map(|s| (*s).to_owned()).collect(),
            total,
        }
    }

    // frob:tests crates/frob-release/src/criteria.rs::epic_closed
    #[test]
    fn epic_closed_needs_tickets_all_done() {
        assert!(epic_closed(&epic(&[], 3)).is_ok());
        assert!(epic_closed(&epic(&["~T1"], 3)).unwrap_err().contains("~T1"));
        assert!(epic_closed(&epic(&[], 0)).is_err());
    }

    // frob:tests crates/frob-release/src/criteria.rs::ci_green
    #[test]
    fn ci_green_only_for_green() {
        assert!(ci_green(&ci(CiState::Green { checks: 2 })).is_ok());
        assert!(ci_green(&ci(CiState::Pending { running: vec![] })).is_err());
        let u = CiState::Unknown(CiUnknown {
            reason: "r".into(),
            remedy: "m".into(),
        });
        assert!(ci_green(&ci(u)).is_err());
        let mut f = ci(CiState::Green { checks: 1 });
        f.sha = None;
        assert!(ci_green(&f).is_err());
    }

    // frob:tests crates/frob-release/src/criteria.rs::parse_epic
    #[test]
    fn parse_epic_round_trips_the_canonical_text() {
        assert_eq!(
            parse_epic(&epic_criterion_text("~D05GDWP")),
            Some("~D05GDWP")
        );
        assert_eq!(parse_epic("every ticket under epic is done"), None);
        assert_eq!(parse_epic("something else"), None);
    }

    // frob:tests crates/frob-release/src/criteria.rs::bind_builtin
    #[test]
    fn bind_builtin_binds_epic_and_ci_and_flags_circular() {
        let mut cs = vec![
            crit(1, &epic_criterion_text("~E1")),
            crit(2, "CI is green on the release commit"),
            crit(3, "frob release status reports no unresolved items"),
            crit(4, "the owner is happy"),
        ];
        let failed = bind_builtin(&mut cs, &[epic(&[], 2)], &ci(CiState::Green { checks: 1 }));
        assert_eq!(cs[0].state, "bound");
        assert_eq!(cs[1].state, "bound");
        assert_eq!(cs[2].state, "unbound");
        assert_eq!(cs[3].state, "unbound");
        assert_eq!(failed.len(), 1);
        assert_eq!(failed[0].0, 3);
    }

    // frob:tests crates/frob-release/src/criteria.rs::derive_epic_criteria
    #[test]
    fn derive_adds_only_missing_epics() {
        let existing = vec![crit(1, &epic_criterion_text("~A"))];
        let out = derive_epic_criteria(&["~A".to_owned(), "~B".to_owned()], &existing);
        assert_eq!(out, vec![epic_criterion_text("~B")]);
    }

    // frob:tests crates/frob-release/src/criteria.rs::attester_problems
    #[test]
    fn attester_must_match_a_committer() {
        let c = vec!["logan@logandapp.com".to_owned()];
        assert!(attester_problems(&["Logan@logandapp.com".to_owned()], &c).is_empty());
        let p = attester_problems(&["logan@logand.app".to_owned()], &c);
        assert_eq!(p.len(), 1);
        assert!(p[0].contains("logandapp.com"));
    }
}

//! Privacy for published projections (mirror.md 3.6): redaction and worktree-path scrubbing.
//!
//! Publication is irreversible, so every text field is scrubbed before `project` folds it:
//! secret-shaped text is masked with `gob-log`, registered secrets are masked literally, and
//! lease worktree paths are replaced. `[mirror] exclude` is applied by `project` itself.

// frob:ticket 01M3ZX859CDHNPW8ER1NWMYK7M

use std::collections::BTreeSet;

use gob_log::REDACTED;
use tracing::{debug, trace};

use crate::projection::{IssueProjection, TicketFacts, project};

/// Replacement for a lease worktree path.
pub const WORKTREE_PLACEHOLDER: &str = "[worktree]";

/// What must never leave the machine: registered secret values and lease worktree paths.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Sensitive {
    /// Literal secret values to mask wherever they appear.
    pub secrets: Vec<String>,
    /// Worktree paths held by leases, never published.
    pub worktree_paths: Vec<String>,
}

/// Scrub one text: worktree paths, registered secrets, then secret-shaped patterns.
pub fn scrub(text: &str, sensitive: &Sensitive) -> String {
    let mut out = text.to_owned();
    for path in sensitive.worktree_paths.iter().filter(|p| !p.is_empty()) {
        if out.contains(path.as_str()) {
            trace!("privacy: worktree path scrubbed");
            out = out.replace(path.as_str(), WORKTREE_PLACEHOLDER);
        }
    }
    for secret in sensitive.secrets.iter().filter(|s| !s.is_empty()) {
        if out.contains(secret.as_str()) {
            trace!("privacy: registered secret masked");
            out = out.replace(secret.as_str(), REDACTED);
        }
    }
    gob_log::redact(&out).into_owned()
}

/// Return `facts` with every free-text field scrubbed.
pub fn sanitize(facts: &TicketFacts, sensitive: &Sensitive) -> TicketFacts {
    let mut f = facts.clone();
    f.title = scrub(&f.title, sensitive);
    f.summary = scrub(&f.summary, sensitive);
    for c in &mut f.acceptance {
        c.text = scrub(&c.text, sensitive);
    }
    for s in &mut f.scope {
        *s = scrub(s, sensitive);
    }
    for e in &mut f.evidence {
        e.reference = scrub(&e.reference, sensitive);
        e.verdict = scrub(&e.verdict, sensitive);
    }
    if let Some(r) = f.state.reason.take() {
        f.state.reason = Some(scrub(&r, sensitive));
    }
    debug!(ulid = %f.identity.ulid, "privacy: facts sanitized");
    f
}

/// Sanitize `facts` then project them, withholding fields named in `exclude`.
pub fn project_private(
    facts: &TicketFacts,
    exclude: &BTreeSet<String>,
    sensitive: &Sensitive,
    producer_version: &str,
) -> IssueProjection {
    project(&sanitize(facts, sensitive), exclude, producer_version)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::projection::{Category, Classification, EvidenceItem, Identity, People, State};

    fn facts(evidence_ref: &str, summary: &str) -> TicketFacts {
        TicketFacts {
            identity: Identity {
                ulid: "01M3ZX859CDHNPW8ER1NWMYK7M".into(),
                handle: "~NWMYK7M".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/x".into(),
            },
            title: "T".into(),
            summary: summary.into(),
            acceptance: vec![],
            scope: vec![],
            evidence: vec![EvidenceItem {
                reference: evidence_ref.into(),
                verdict: "pass".into(),
            }],
            classification: Classification::default(),
            state: State {
                category: Category::Doing,
                outcome: None,
                reason: None,
            },
            relations: vec![],
            people: People::default(),
            last_event: "01M3ZX859CDHNPW8ER1NWMYK7M".into(),
        }
    }

    fn all_markdown(p: &IssueProjection) -> String {
        p.sections
            .iter()
            .map(|s| s.markdown.as_str())
            .collect::<Vec<_>>()
            .join("\n")
    }

    // frob:tests project_private
    #[test]
    fn registered_secret_in_evidence_is_redacted() {
        let s = Sensitive {
            secrets: vec!["hunter2-registered".into()],
            worktree_paths: vec![],
        };
        let f = facts(
            "cargo test hunter2-registered ghp_0123456789abcdefghijklmnopqrstuvwxyz",
            "b",
        );
        let p = project_private(&f, &BTreeSet::new(), &s, "v");
        let md = all_markdown(&p);
        assert!(!md.contains("hunter2-registered"));
        assert!(!md.contains("ghp_0123"));
        assert!(md.contains(REDACTED));
    }

    // frob:tests project_private
    #[test]
    // frob:accept PATH001 because="asserts a worktree path never reaches the mirror; the literal is the leak probe"
    fn worktree_path_never_appears() {
        let wt = "/home/logan/projects/frob-wt/NWMYK7M";
        let s = Sensitive {
            secrets: vec![],
            worktree_paths: vec![wt.into()],
        };
        let f = facts(&format!("{wt}/target/log"), &format!("work in {wt}"));
        let p = project_private(&f, &BTreeSet::new(), &s, "v");
        let json = serde_json::to_string(&p).unwrap();
        assert!(!json.contains(wt));
        assert!(json.contains(WORKTREE_PLACEHOLDER));
    }

    // frob:tests project_private
    #[test]
    fn excluded_field_is_never_sent() {
        let ex: BTreeSet<String> = ["evidence".to_owned()].into();
        let f = facts("secret-ref", "b");
        let p = project_private(&f, &ex, &Sensitive::default(), "v");
        assert!(!serde_json::to_string(&p).unwrap().contains("secret-ref"));
        assert_eq!(p.private, vec!["evidence".to_owned()]);
    }
}

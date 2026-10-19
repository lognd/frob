//! Render an `IssueProjection` to GitHub markdown, the managed label and the hidden marker.
//!
//! Section kinds map to headings; the body is a pure function of the projection and the marker
//! string, so rendering twice is byte-identical. Task-list checkboxes are never emitted.
//! Neutralisation and render limits are separate layers on top of this renderer.

// frob:ticket 01M3ZX83T22GTC94BW4PM742G1

use tracing::debug;

use crate::projection::IssueProjection;

/// The one managed label applied to every mirrored issue (never a label per ULID).
pub const MANAGED_LABEL: &str = "frob:managed";

/// A projection rendered for GitHub.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RenderedIssue {
    /// Issue title.
    pub title: String,
    /// Issue body: headed sections, then the hidden marker.
    pub body: String,
    /// Labels to ensure present (only `frob:managed`).
    pub labels: Vec<String>,
    /// The projection render digest, carried unchanged for divergence detection.
    pub digest: String,
}

/// Turn a task-list line (`- [x] text`) into plain list text so GitHub renders no checkbox.
fn defang_task_line(line: &str) -> String {
    if let Some(rest) = line.strip_prefix("- [x] ") {
        format!("- Bound: {rest}")
    } else if let Some(rest) = line.strip_prefix("- [ ] ") {
        format!("- Unbound: {rest}")
    } else {
        line.to_owned()
    }
}

/// Render `p` to a GitHub issue; `marker` is the hidden body marker string from the marker keyring.
pub fn render(p: &IssueProjection, marker: &str) -> RenderedIssue {
    let mut body = String::new();
    for s in &p.sections {
        body.push_str("## ");
        body.push_str(&s.heading);
        body.push_str("\n\n");
        for line in s.markdown.lines() {
            body.push_str(&defang_task_line(line));
            body.push('\n');
        }
        body.push('\n');
    }
    body.push_str(marker);
    body.push('\n');
    debug!(ulid = %p.identity.ulid, bytes = body.len(), "github: rendered projection");
    RenderedIssue {
        title: p.title.clone(),
        body,
        labels: vec![MANAGED_LABEL.to_owned()],
        digest: p.provenance.render_digest.clone(),
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;

    use super::*;
    use crate::projection::{
        Category, Classification, Criterion, EvidenceItem, Identity, People, State, TicketFacts,
        project,
    };

    const MARKER: &str = "<!-- frob:marker v1 kid=k1 mac=abc -->";

    fn proj() -> IssueProjection {
        let facts = TicketFacts {
            identity: Identity {
                ulid: "01M3ZX83T22GTC94BW4PM742G1".into(),
                handle: "~PM742G1".into(),
                aliases: vec![],
                repository: "https://example.invalid/r".into(),
                ledger_path: "tickets/x".into(),
            },
            title: "T".into(),
            summary: "Sum".into(),
            acceptance: vec![
                Criterion {
                    text: "a".into(),
                    bound: true,
                },
                Criterion {
                    text: "b".into(),
                    bound: false,
                },
            ],
            scope: vec!["src/**".into()],
            evidence: vec![EvidenceItem {
                reference: "t1".into(),
                verdict: "pass".into(),
            }],
            classification: Classification::default(),
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![],
            people: People::default(),
            last_event: "EV".into(),
        };
        project(&facts, &BTreeSet::new(), "1")
    }

    // frob:tests render
    #[test]
    fn body_has_sections_notice_marker_label_and_digest() {
        let p = proj();
        let r = render(&p, MARKER);
        for h in [
            "## Summary",
            "## Acceptance",
            "## Scope",
            "## Evidence",
            "## Links",
        ] {
            assert!(r.body.contains(h), "missing {h}");
        }
        assert!(
            r.body
                .contains("## Managed by frob\n\nThis issue is generated")
        );
        assert!(r.body.ends_with(&format!("{MARKER}\n")));
        assert!(!r.body.contains("[x]") && !r.body.contains("[ ]"));
        assert!(r.body.contains("- Bound: a") && r.body.contains("- Unbound: b"));
        assert_eq!(r.labels, [MANAGED_LABEL]);
        assert_eq!(r.digest, p.provenance.render_digest);
        assert_eq!(r.title, "T");
    }

    // frob:tests render
    #[test]
    fn rendering_twice_is_byte_identical() {
        let p = proj();
        assert_eq!(render(&p, MARKER), render(&p, MARKER));
        assert_eq!(
            render(&p, MARKER).body.as_bytes(),
            render(&p, MARKER).body.as_bytes()
        );
    }
}

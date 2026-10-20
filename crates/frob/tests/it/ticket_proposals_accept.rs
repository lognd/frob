//! `ticket proposals accept` guards and effects, against fixture ledgers and a fake tracker.
// frob:ticket 01M4052TKZWKG1QBB3CWHQ9MVM

use std::collections::BTreeMap;
use std::path::Path;

use frob_cli::ticket::proposals_accept::{AcceptResult, TrackerValues, accept_with};
use frob_ledger::event::{EventBody, ProposalData};
use frob_ledger::proposal::{ProposalState, fold_proposals};
use frob_ledger::{Ledger, TicketId};
use serde_json::Value;

use crate::common;

/// A tracker that returns one fixed value (or none).
struct Fake(Option<String>);

impl TrackerValues for Fake {
    fn fetch(&self, _item: &str, _field: &str) -> Result<Option<String>, String> {
        Ok(self.0.clone())
    }
}

fn ok(p: &Path, args: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(p)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob");
    assert_eq!(out.status.code(), Some(0), "{args:?}");
    serde_json::from_slice(&out.stdout).expect("json")
}

/// A repo with one ticket and a pending proposal by tracker user 42 on `field`.
fn fixture(field: &str, actor: &str) -> (tempfile::TempDir, Ledger, TicketId) {
    let dir = common::git_repo();
    let p = dir.path();
    ok(p, &["init"]);
    let id: TicketId = ok(p, &["ticket", "new", "--title", "Old title"])["data"]["id"]
        .as_str()
        .expect("id")
        .parse()
        .expect("ulid");
    let cfg = frob_cli::config::FrobConfig::load(p).expect("config");
    let ledger = Ledger::open(
        gob_git::Repo::discover(p).expect("discover"),
        cfg.ledger(),
        std::sync::Arc::new(gob_time::SystemClock),
    );
    let data = ProposalData {
        tracker_event: "T_1".into(),
        item: "I_9".into(),
        field: field.into(),
        actor_id: actor.into(),
        time: "2026-11-01T00:00:00Z".parse().expect("stamp"),
        digest: frob_mirror::journal::value_digest("New title"),
        excerpt: "New title".into(),
        origin: "tracker".into(),
        supersedes: None,
    };
    ledger
        .append(id, EventBody::Proposal(data))
        .expect("append");
    (dir, ledger, id)
}

fn mapped() -> BTreeMap<String, u64> {
    BTreeMap::from([("alice".to_owned(), 42)])
}

fn state(ledger: &Ledger, id: TicketId) -> ProposalState {
    fold_proposals(&ledger.events(id).expect("events"))[0].state
}

fn title(ledger: &Ledger, id: TicketId) -> String {
    ledger.show(id).expect("show").summary.title
}

#[test]
fn an_unmapped_identity_is_refused_and_nothing_changes() {
    // frob:tests crates/frob/src/ticket/proposals_accept.rs::accept_with
    let (_d, ledger, id) = fixture("title", "999");
    let fake = Fake(Some("New title".into()));
    let r = accept_with(&ledger, id, "T_1", &mapped(), &fake, &mut |_| true);
    assert!(r.is_err());
    assert_eq!(state(&ledger, id), ProposalState::Pending);
    assert_eq!(title(&ledger, id), "Old title");
}

#[test]
fn a_proposal_on_a_forbidden_field_is_refused() {
    // frob:tests crates/frob/src/ticket/proposals_accept.rs::accept_with
    for field in ["scope", "acceptance", "evidence", "links"] {
        let (_d, ledger, id) = fixture(field, "42");
        let fake = Fake(Some("New title".into()));
        let r = accept_with(&ledger, id, "T_1", &mapped(), &fake, &mut |_| true);
        assert!(r.is_err(), "{field}");
        assert_eq!(state(&ledger, id), ProposalState::Pending, "{field}");
    }
}

#[test]
fn a_value_gone_from_the_tracker_closes_the_proposal_as_unavailable() {
    // frob:tests crates/frob/src/ticket/proposals_accept.rs::accept_with
    let (_d, ledger, id) = fixture("title", "42");
    let r = accept_with(&ledger, id, "T_1", &mapped(), &Fake(None), &mut |_| {
        panic!("no diff for a gone value")
    })
    .expect("closes");
    assert_eq!(r.result, AcceptResult::Unavailable);
    assert_eq!(state(&ledger, id), ProposalState::Expired);
    assert_eq!(title(&ledger, id), "Old title");
}

#[test]
fn a_declined_confirmation_changes_nothing() {
    // frob:tests crates/frob/src/ticket/proposals_accept.rs::accept_with
    let (_d, ledger, id) = fixture("title", "42");
    let fake = Fake(Some("New title".into()));
    let r = accept_with(&ledger, id, "T_1", &mapped(), &fake, &mut |_| false);
    assert!(r.is_err());
    assert_eq!(state(&ledger, id), ProposalState::Pending);
}

#[test]
fn a_valid_proposal_is_applied_after_the_diff_and_closes_as_accepted() {
    // frob:tests crates/frob/src/ticket/proposals_accept.rs::accept_with
    let (_d, ledger, id) = fixture("title", "42");
    let fake = Fake(Some("New title".into()));
    let mut shown = None;
    let r = accept_with(&ledger, id, "T_1", &mapped(), &fake, &mut |d| {
        shown = Some(d.render());
        true
    })
    .expect("accepted");
    assert_eq!(r.result, AcceptResult::Accepted);
    assert!(
        shown
            .expect("diff shown")
            .contains("- Old title\n+ New title")
    );
    assert_eq!(state(&ledger, id), ProposalState::Accepted);
    assert_eq!(title(&ledger, id), "New title");
}

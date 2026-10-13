//! The capabilities record covers every audit U-fact with a verdict and a replayable live fixture.

use frob_gh::FixtureTransport;
use frob_gh::capabilities::facts;

// frob:ticket 01M4059ZDWQRK47QXG5K0KYHP2
#[test]
fn every_unverified_fact_has_request_response_and_verdict() {
    let facts = facts();
    assert_eq!(facts.len(), 16);
    for n in 1..=16 {
        let id = format!("U{n}");
        let f = facts
            .iter()
            .find(|f| f.id == id)
            .unwrap_or_else(|| panic!("{id} missing"));
        assert!(
            ["verified", "partial", "unmeasurable"].contains(&f.verdict.as_str()),
            "{id}"
        );
        assert!(
            !f.finding.is_empty() && !f.request.is_empty() && !f.response.is_empty(),
            "{id}"
        );
        let path = format!(
            "{}/tests/fixtures/{}",
            env!("CARGO_MANIFEST_DIR"),
            f.fixture
        );
        let text = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"));
        assert!(
            FixtureTransport::from_json(&text).is_ok(),
            "{id} fixture parses"
        );
    }
}

//! Culprit finding over today's real shape: green, a docs land goes red, the next land stays red.

// frob:ticket 01M4GRXFQYZRDJ2TP68WFY48QC
use frob_gh::{
    BLOCKS_LANDS_LABEL, Client, Commit, CulpritError, FixtureTransport, Token, Verdict,
    find_culprit,
};

const RUNS: &str = include_str!("fixtures/runs_red_after_docs_land.json");

fn commit(sha: &str, subject: &str) -> Commit {
    Commit {
        sha: sha.to_owned(),
        subject: subject.to_owned(),
    }
}

fn history() -> Vec<Commit> {
    vec![
        commit("ec63b582", "tickets(land): ~FSW5067"),
        commit("aaaaaaaa1", "tickets(cycle-member): ~XAFQ008"),
        commit("73d3aa71f", "tickets(land): ~2SM2G7J"),
        commit("6ac157fde", "tickets(land): ~OLD"),
    ]
}

async fn runs() -> Vec<frob_gh::RunRecord> {
    let c = Client::new(
        FixtureTransport::from_json(RUNS).unwrap(),
        Token::new("placeholder"),
    );
    c.workflow_runs("o", "r", "experimental").await.unwrap()
}

// frob:tests crates/frob-gh/src/culprit.rs::find_culprit
#[tokio::test(flavor = "current_thread")]
async fn names_the_range_between_last_green_and_first_red() {
    let runs = runs().await;
    assert_eq!(runs[4].verdict, Verdict::Unknown);
    let c = find_culprit(&runs, &history()).unwrap();
    assert_eq!(c.last_green.as_deref(), Some("6ac157fde"));
    assert_eq!(c.first_red, "73d3aa71f");
    let shas: Vec<&str> = c.lands.iter().map(|l| l.sha.as_str()).collect();
    assert_eq!(shas, ["73d3aa71f"]);
    assert!(c.fix.labels.contains(&BLOCKS_LANDS_LABEL.to_owned()));
}

// frob:tests crates/frob-gh/src/culprit.rs::find_culprit
#[tokio::test(flavor = "current_thread")]
async fn key_is_stable_across_later_red_lands() {
    let runs = runs().await;
    let first = find_culprit(&runs, &history()).unwrap();
    let again = find_culprit(&runs, &history()).unwrap();
    assert_eq!(first.fix.idempotency_key, "culprit-73d3aa71f");
    assert_eq!(first.fix, again.fix);
}

// frob:tests crates/frob-gh/src/culprit.rs::find_culprit
#[tokio::test(flavor = "current_thread")]
async fn green_tip_and_foreign_runs_are_refused() {
    let runs = runs().await;
    let green_only: Vec<_> = runs
        .iter()
        .filter(|r| r.sha == "6ac157fde")
        .cloned()
        .collect();
    assert_eq!(
        find_culprit(&green_only, &history()[3..]),
        Err(CulpritError::NotRed)
    );
    let short = &history()[..1];
    assert!(matches!(
        find_culprit(&runs, short),
        Err(CulpritError::NotInHistory(_))
    ));
}

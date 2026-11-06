//! Polarity-conformance corpus: one standard small repository per polarity situation (a Must edge,
//! a May-only edge, an opaque region, an Unknown visibility) run against every shipped rule.
//!
//! The premise-false oracle (universal-model.md 4.5, Theorem 3): in a repository where the
//! evidence for "absent" is only May, opaque or Unknown, no P- rule may emit an `Error`
//! finding. A P- rule fires on certain absence only; on possible presence it answers `Unresolved`.

mod common;

use frob_obligations::InvariantsConfig;
use gob_rules::{Finding, Polarity, Registry, Severity};

// frob:ticket 01M48PC09SX0KFAM4B3V88AAXW
/// A standard repository: its name, files, and the rules allowed to fire a certain finding in it.
struct Repo {
    name: &'static str,
    files: &'static [(&'static str, &'static str)],
    /// Items on which a P- rule MAY legitimately fire (certain absence); empty when none.
    certain: &'static [&'static str],
}

const TWO_TYPES: &str = "/// A.\npub struct A;\n\nimpl A {\n    /// Makes.\n    pub fn new() -> A { A }\n}\n\n/// Free.\npub fn run() {}\n\n/// A method named run.\npub struct R;\n\nimpl R {\n    /// Runs.\n    pub fn run(&self) {}\n}\n";

/// The Must-edge repository: a test calls the target directly, so nothing is uncovered.
const MUST: Repo = Repo {
    name: "must",
    files: &[(
        "src/lib.rs",
        "/// Target.\npub fn target() {}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    #[test]\n    fn t() {\n        target();\n    }\n}\n",
    )],
    certain: &[],
};

/// The May-only repository: the only test reaches the item through an unknown receiver.
const MAY: Repo = Repo {
    name: "may-only",
    files: &[(
        "src/lib.rs",
        concat!(
            "/// Free.\npub fn run() {}\n\n/// A method named run.\npub struct R;\n\nimpl R {\n    /// Runs.\n    pub fn run(&self) {}\n}\n\n",
            "#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        make().run();\n    }\n}\n"
        ),
    )],
    // A method call can never be the free function, so its absence of reach is certain.
    certain: &["::run`"],
};

/// The opaque-region repository: the test body is a macro the model cannot expand; its argument still names a call.
const OPAQUE: Repo = Repo {
    name: "opaque",
    files: &[(
        "src/lib.rs",
        "/// Target.\npub fn target() {}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        unexpanded!(target());\n    }\n}\n",
    )],
    certain: &[],
};

/// The Unknown-visibility repository: the item is reachable from other crates only if re-exported.
const UNKNOWN_VISIBILITY: Repo = Repo {
    name: "unknown-visibility",
    files: &[
        (
            "src/lib.rs",
            "mod inner;\n\n/// Re-export.\npub use inner::hidden;\n",
        ),
        ("src/inner.rs", "/// Hidden.\npub(crate) fn hidden() {}\n"),
        (
            "tests/it.rs",
            "#[test]\nfn t() {\n    other::hidden();\n}\n",
        ),
    ],
    certain: &[],
};

const REPOS: [Repo; 4] = [MUST, MAY, OPAQUE, UNKNOWN_VISIBILITY];

/// The findings of every rule over `repo`.
fn findings(repo: &Repo) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), repo.files);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    common::evaluate_tree(dir.path(), None, &config, None).findings
}

/// The polarity of a declared (two-file) rule of this crate, which the legacy registry no longer lists.
fn declared_polarity(id: &str) -> Option<Polarity> {
    frob_obligations::rules::METAS
        .iter()
        .find(|d| d.id == id)
        .map(|d| d.polarity)
}

/// Findings that break the P- contract: a certain (`Error`) finding from a P- rule that
/// the repository does not list as a true positive.
fn premise_violations<'a>(repo: &Repo, found: &'a [Finding], reg: &Registry) -> Vec<&'a Finding> {
    found
        .iter()
        .filter(|f| {
            let id = f.rule.as_str();
            reg.by_id(id)
                .map(|m| m.polarity)
                .or_else(|| declared_polarity(id))
                == Some(Polarity::Pminus)
        })
        .filter(|f| f.severity == Severity::Error)
        .filter(|f| !repo.certain.iter().any(|c| f.message.contains(c)))
        .collect()
}

// frob:tests crates/frob-obligations/src/rules/cov001.rs::Cov001
#[test]
fn every_shipped_p_minus_rule_stays_unfired_on_the_polarity_repos() {
    let reg = Registry::global();
    assert!(
        reg.iter().any(|m| m.polarity == Polarity::Pminus),
        "the registry has P- rules to check"
    );
    for repo in &REPOS {
        let found = findings(repo);
        let bad = premise_violations(repo, &found, reg);
        assert!(
            bad.is_empty(),
            "repo {}: a P- rule fired on a non-certain absence: {:?}",
            repo.name,
            bad.iter()
                .map(|f| format!("{} {}", f.rule, f.message))
                .collect::<Vec<_>>()
        );
    }
}

// frob:tests crates/frob-obligations/src/rules/cov001.rs::Cov001
#[test]
fn the_may_only_repository_answers_unresolved_not_error() {
    let found = findings(&MAY);
    let cov: Vec<_> = found
        .iter()
        .filter(|f| f.rule.as_str() == "COV001")
        .collect();
    let run = cov
        .iter()
        .find(|f| f.message.contains("R.run"))
        .expect("R.run");
    assert_eq!(run.severity, Severity::Unresolved, "{}", run.message);
}

#[test]
fn a_p_minus_rule_firing_on_may_only_reach_fails_the_oracle() {
    // The control: a repository whose May-only item is reported as a certain Error is caught.
    let reg = Registry::global();
    let mut found = findings(&MAY);
    let mut forged = found
        .iter()
        .find(|f| f.rule.as_str() == "COV001" && f.severity == Severity::Unresolved)
        .expect("an Unresolved COV001 finding exists")
        .clone();
    forged.severity = Severity::Error;
    found.push(forged);
    assert_eq!(
        premise_violations(&MAY, &found, reg).len(),
        1,
        "a forged certain P- finding on May-only reach must be flagged"
    );
}

#[test]
fn the_must_edge_repository_is_clean_of_cov001() {
    let found = findings(&MUST);
    assert!(
        !found.iter().any(|f| f.rule.as_str() == "COV001"),
        "{:?}",
        common::ids(&found)
    );
}

// frob:tests crates/frob-obligations/src/rules/cov001.rs::Cov001
#[test]
fn the_two_types_helper_repo_still_fires_where_absence_is_certain() {
    // Sanity: the oracle is not vacuous; with no test at all the P- rule does fire.
    let repo = Repo {
        name: "no-test",
        files: &[("src/lib.rs", TWO_TYPES)],
        certain: &["A.new", "run", "R.run"],
    };
    let found = findings(&repo);
    assert!(
        found
            .iter()
            .any(|f| f.rule.as_str() == "COV001" && f.severity == Severity::Error),
        "{:?}",
        common::ids(&found)
    );
}

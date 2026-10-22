//! Every leaf command of frob, grimble and crunk has a profile scenario or a skip reason.
// frob:ticket 01M4CS7ZMEY096RVK91RWD03DW

use std::collections::BTreeSet;

use gob_dev::profile::scenarios::ScenarioFile;

/// Leaf commands of the three product CLIs, as `product verb...`, from their clap trees, without
/// the deprecated aliases (hidden from help and removed next minor; their target is profiled).
fn leaves() -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for (product, cli) in [
        ("frob", frob_cli::cli()),
        ("grimble", grimble::cli()),
        ("crunk", crunk::cli()),
    ] {
        for verb in cli.verb_flags().into_keys() {
            let alias = gob_cli::all_commands()
                .any(|m| m.product == product && m.verb == verb && m.deprecated_form().is_some());
            if !alias {
                out.insert(format!("{product} {verb}"));
            }
        }
    }
    out
}

// frob:tests crates/gob-dev/src/profile.rs::check_coverage
#[test]
fn every_leaf_command_has_a_scenario_or_a_skip_reason() {
    let file = ScenarioFile::builtin().expect("profile.toml parses");
    let leaves = leaves();
    assert!(
        leaves.len() > 60,
        "tree walk found only {} leaves",
        leaves.len()
    );
    let missing: Vec<&String> = leaves
        .iter()
        .filter(|l| !file.scenario.contains_key(*l))
        .collect();
    assert!(
        missing.is_empty(),
        "leaf commands with no scenario and no skip reason in crates/gob-dev/profile.toml: {missing:?}"
    );
    let stale: Vec<&String> = file
        .scenario
        .keys()
        .filter(|k| !leaves.contains(*k))
        .collect();
    assert!(
        stale.is_empty(),
        "profile.toml scenarios for commands that do not exist: {stale:?}"
    );
}

// frob:tests crates/gob-dev/src/profile/scenarios.rs::ScenarioFile.parse
#[test]
fn skips_carry_a_reason_and_measured_scenarios_a_budget() {
    let file = ScenarioFile::builtin().expect("profile.toml parses");
    for (command, s) in &file.scenario {
        assert!(
            s.skip.is_some() || s.budget_ms.is_some_and(|b| b >= 500),
            "{command}: budget_ms must be at least 500 (the floor) unless skipped"
        );
    }
}

//! COH002 as a registered rule: its mdtest corpus and the `[coh]` vocabularies through `grimble check`.

// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C

#![allow(unused_crate_dependencies)]

use std::path::Path;

use gob_languages::Language;
use gob_rules::Finding;
use gob_text::FileInterner;
use grimble_check::coh_pass::{CohPassOptions, analyze};
use grimble_check::coh002::Coh002Options;
use grimble_check::config::CohTable;
use grimble_check::{CheckOptions, run, sibling_document};
use grimble_lints::pass::PathFile;

/// A function that decides on computed data and calls `callee` in the branch.
fn unit_calling(callee: &str) -> String {
    format!(
        "def f(a, sink):\n    x = compute(a)\n    if x > 3:\n        sink.{callee}(x)\n    return x\n"
    )
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// The COH002 findings of a repo holding `grimble.toml` and `app/a.py`.
fn coh_findings(config: &str, source: &str) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", config);
    write(dir.path(), "app/a.py", source);
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "COH002")
        .cloned()
        .collect()
}

/// Run one mdtest example through the COH pass with the built-in vocabularies; the case's `file=` blocks join the run.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-check/src/coh_pass.rs::analyze
    // frob:tests crates/grimble-check/src/rules/coh002.rs::Coh002
    // frob:tests crates/grimble-check/src/rules/coh003.rs::Coh003
    let mut files = FileInterner::new();
    // Intern in case order so a finding's `FileId::index()` is the file's place in `case.files`.
    for f in &case.files {
        files.intern(&f.file_name);
    }
    let inputs: Vec<PathFile<'_>> = case
        .files
        .iter()
        .map(|f| PathFile {
            path: &f.file_name,
            language: Language::detect(&f.file_name).expect("a known extension"),
            text: &f.text,
        })
        .collect();
    analyze(&inputs, &CohPassOptions::default())
        .findings
        .into_iter()
        .filter(|f| f.rule == case.rule.as_str())
        .filter_map(|f| f.into_finding(&mut files))
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);

// frob:tests crates/grimble-check/src/product.rs::Grimble
// frob:tests crates/grimble-check/src/config.rs::CohTable
#[test]
fn configured_names_add_to_the_adapter_capability() {
    let config = "[coh]\neffect_calls = [\"transmit\"]\n";
    let custom = coh_findings(config, &unit_calling("transmit"));
    assert_eq!(custom.len(), 1, "{custom:?}");
    assert_eq!(custom[0]["severity"], "error", "{custom:?}");
    // The capability still knows `send`: the list adds to it, it does not replace it.
    let known = coh_findings(config, &unit_calling("send"));
    assert_eq!(known[0]["severity"], "error", "{known:?}");
    // A trivial override silences a name the capability cannot place.
    let quiet = coh_findings("[coh]\ntrivial = [\"mystery\"]\n", &unit_calling("mystery"));
    assert!(quiet.is_empty(), "{quiet:?}");
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
// frob:tests crates/grimble-check/src/coh002.rs::default_effect_calls
#[test]
fn without_a_coh_table_the_adapter_capability_decides() {
    let found = coh_findings("[check]\n", &unit_calling("send"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "error", "{found:?}");
    let table_free = coh_findings("[check]\n", &unit_calling("transmit"));
    assert_eq!(table_free[0]["severity"], "unresolved", "{table_free:?}");
}

// frob:tests crates/grimble-check/src/coh002.rs::default_effect_calls
#[test]
fn an_empty_effect_list_no_longer_turns_the_rule_off() {
    let found = coh_findings("[coh]\neffect_calls = []\n", &unit_calling("send"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "error", "{found:?}");
}

// frob:tests crates/grimble-check/src/coh002.rs::default_trivial
#[test]
fn an_empty_trivial_list_keeps_the_capability_trivial_calls() {
    let src = "def f(a):\n    x = compute(a)\n    if x > 3:\n        log(x)\n    return x\n";
    assert!(coh_findings("[check]\n", src).is_empty());
    assert!(coh_findings("[coh]\ntrivial = []\n", src).is_empty());
}

// frob:tests crates/grimble-check/src/coh002.rs::default_trivial
#[test]
fn a_name_in_both_lists_is_trivial_and_duplicates_are_harmless() {
    let config = "[coh]\neffect_calls = [\"send\", \"send\"]\ntrivial = [\"send\"]\n";
    let found = coh_findings(config, &unit_calling("send"));
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests crates/grimble-check/src/coh_pass.rs::analyze
#[test]
fn a_file_without_decisions_is_clean() {
    let src = "def f(a, sink):\n    sink.send(a)\n    return a\n";
    assert!(coh_findings("[check]\n", src).is_empty());
}

// frob:tests crates/grimble-check/src/config.rs::CohTable
#[test]
fn an_unknown_coh_key_is_rejected() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[coh]\neffects = [\"send\"]\n");
    let err = CohTable::load(dir.path()).expect_err("unknown key");
    assert!(err.to_string().contains("effects"), "{err}");
}

// frob:tests crates/grimble-check/src/coh002.rs::default_effect_calls
#[test]
fn the_table_converts_to_options_and_defaults_match() {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    let table = CohTable::load(dir.path()).unwrap();
    assert_eq!(Coh002Options::from(&table), Coh002Options::default());
}

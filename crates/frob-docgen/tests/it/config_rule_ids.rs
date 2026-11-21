//! Every rule id named in a shipped config exists or redirects.
// frob:ticket 01M48NKS4C0ZDYQCADX7WRK7XC

use std::collections::BTreeSet;
use std::path::PathBuf;

use gob_rules::{Redirects, Registry, RuleIndex};

/// Every product's `#[rule]` indexes: frob, grimble and crunk.
fn indexes() -> Vec<&'static RuleIndex> {
    [
        frob_check::product_rules::RULE_INDEXES,
        grimble_check::product_rules::RULE_INDEXES,
        crunk_check::product_rules::RULE_INDEXES,
    ]
    .into_iter()
    .flat_map(|ix| ix.iter().copied())
    .collect()
}

/// The ids live in the legacy inventory and in the `#[rule]` indexes.
fn live_ids(indexes: &[&RuleIndex]) -> BTreeSet<String> {
    let mut ids: BTreeSet<String> = Registry::global().iter().map(|m| m.id.to_owned()).collect();
    ids.extend(
        indexes
            .iter()
            .flat_map(|ix| ix.metas.iter().map(|d| d.id.to_owned())),
    );
    ids
}

/// The `[rules.<ID>]` keys of config `text` that are neither a live id nor renamed to one.
fn unknown_rule_ids(
    text: &str,
    live: &BTreeSet<String>,
    redirects: &Redirects,
) -> Result<Vec<String>, String> {
    let doc: toml::Table = text.parse().map_err(|e: toml::de::Error| e.to_string())?;
    let Some(toml::Value::Table(rules)) = doc.get("rules") else {
        return Ok(Vec::new());
    };
    Ok(rules
        .iter()
        .filter(|(key, value)| key.as_str() != "ramp" && value.is_table())
        .map(|(key, _)| key.as_str())
        .filter(|id| {
            let current = redirects.resolve_id(id).unwrap_or(id);
            !live.contains(current)
        })
        .map(str::to_owned)
        .collect())
}

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(std::path::Path::parent)
        .expect("workspace root")
        .to_path_buf()
}

// frob:tests crates/gob-rules/src/redirects.rs::Redirects.resolve_id
#[test]
fn every_rule_id_named_in_a_shipped_config_exists_or_redirects() {
    let indexes = indexes();
    let live = live_ids(&indexes);
    assert!(live.contains("DUP005"), "the frob rules are linked");
    assert!(live.contains("TIME001"), "the grimble rules are linked");
    let redirects = Redirects::builtin().with_indexes(&indexes);
    let mut named = 0;
    for file in [
        "frob.toml",
        "grimble.toml",
        "crunk.toml",
        "frob-baseline.toml",
    ] {
        let path = root().join(file);
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let unknown = unknown_rule_ids(&text, &live, &redirects).expect("config parses");
        assert!(
            unknown.is_empty(),
            "{file} names rule ids that are neither live nor redirected: {unknown:?}"
        );
        named += 1;
    }
    assert!(named >= 2, "the shipped configs were read");
}

// frob:tests crates/gob-rules/src/redirects.rs::Redirects.resolve_id
#[test]
fn an_unknown_rule_id_is_reported_and_a_renamed_one_resolves() {
    let live: BTreeSet<String> = ["NEW001".to_owned()].into();
    let redirects = Redirects::from_pairs([("OLD001", "NEW001")], [], []);
    let text = "[rules.OLD001]\nseverity = \"off\"\n[rules.NEW001]\nseverity = \"off\"\n[rules.NOPE999]\nseverity = \"off\"\n";
    let unknown = unknown_rule_ids(text, &live, &redirects).expect("parses");
    assert_eq!(unknown, ["NOPE999"]);
}

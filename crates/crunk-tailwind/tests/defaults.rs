//! Default key tables against the Python crunk `tw_defaults` key sets.

// frob:ticket 01M43ARVZPN52N6NMB7VRKZYGS

use std::collections::{BTreeMap, BTreeSet};

use crunk_tailwind::defaults::{self, is_v4_spacing_key};

/// `table name -> keys` from the fixture dumped out of the Python module.
fn python_keys() -> BTreeMap<String, BTreeSet<String>> {
    let text = include_str!("fixtures/python_v3_keys.txt");
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for line in text.lines() {
        let (table, key) = line.split_once(' ').expect("table key");
        out.entry(table.to_owned())
            .or_default()
            .insert(key.to_owned());
    }
    out
}

fn set(keys: &[&str]) -> BTreeSet<String> {
    keys.iter().map(|k| (*k).to_owned()).collect()
}

#[test]
fn v3_key_sets_equal_python() {
    let py = python_keys();
    let tables: [(&str, &[&str]); 5] = [
        ("V3_SPACING_KEYS", defaults::V3_SPACING_KEYS),
        ("V3_BORDER_RADIUS_KEYS", defaults::V3_BORDER_RADIUS_KEYS),
        ("V3_Z_INDEX_KEYS", defaults::V3_Z_INDEX_KEYS),
        ("V3_FONT_SIZE_KEYS", defaults::V3_FONT_SIZE_KEYS),
        ("V3_COLOR_NAMES", defaults::V3_COLOR_NAMES),
    ];
    for (name, table) in tables {
        assert_eq!(set(table), py[name], "{name}");
        assert_eq!(table.len(), py[name].len(), "{name} has duplicates");
    }
    let hex_names: BTreeSet<String> = defaults::V3_COLOR_HEXES
        .iter()
        .map(|(k, _)| (*k).to_owned())
        .collect();
    assert_eq!(hex_names, py["V3_COLOR_HEXES"]);
    assert_eq!(hex_names, set(defaults::V3_COLOR_NAMES));
}

#[test]
fn v4_tables_have_the_documented_shape() {
    assert_eq!(defaults::V4_BORDER_RADIUS_KEYS.len(), 8);
    assert!(defaults::V4_FONT_SIZE_KEYS.contains(&"base"));
    assert!(defaults::V4_Z_INDEX_KEYS.is_empty());
    assert_eq!(defaults::V4_COLOR_NAMES.len(), 22 * 11 + 2);
    assert!(is_v4_spacing_key("px") && is_v4_spacing_key("0.5") && is_v4_spacing_key("13"));
    assert!(!is_v4_spacing_key("0.3") && !is_v4_spacing_key("") && !is_v4_spacing_key("sm"));
}

#[test]
fn v4_fixture_theme_keys_collide_only_where_expected() {
    let css = include_str!("fixtures/tailwind_v4.css");
    let theme_key = |prefix: &str| -> Vec<String> {
        css.lines()
            .filter_map(|l| l.trim().strip_prefix(prefix))
            .filter_map(|l| l.split_once(':').map(|(k, _)| k.to_owned()))
            .collect()
    };
    // `--radius-md` redefines a v4 default key; `--spacing-sm` is not a spacing key.
    assert!(
        theme_key("--radius-")
            .iter()
            .all(|k| defaults::has_key(defaults::V4_BORDER_RADIUS_KEYS, k))
    );
    assert!(
        theme_key("--spacing-")
            .iter()
            .all(|k| !is_v4_spacing_key(k))
    );
    assert!(defaults::has_key(
        defaults::V4_FONT_SIZE_KEYS,
        &theme_key("--text-")[0]
    ));
}

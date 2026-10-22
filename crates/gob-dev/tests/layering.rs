//! Dependency layering (boundaries.md 6.1): every workspace crate sits in one layer of the table in
//! `docs/design/boundaries.md`, and `cargo metadata` edges may only point to a strictly lower layer
//! within the allowed products. Known violations are listed with the ticket that removes each.
// frob:ticket 01M4CTE1SS9RQ0JB8BNCJXZJ2V

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::path::PathBuf;
use std::process::Command;

/// Edges that break the table today: (from, to, ticket that removes it). A fixed edge turns its
/// row stale, and a stale row fails the test.
const ALLOWED: &[(&str, &str, &str)] = &[
    ("gob-ir", "gob-rules", "~3CCNEW9"),
    ("frob-lease", "frob-release", "~NRMXHHR"),
    ("gob-dev", "crunk-check", "~M8WETW7"),
    ("gob-dev", "crunk-spec", "~M8WETW7"),
    ("gob-dev", "frob-check", "~MQE4F44"),
    ("gob-dev", "frob-cli", "~MQE4F44"),
    ("gob-dev", "frob-mirror", "~MQE4F44"),
    ("gob-dev", "grimble-check", "~M8WETW7"),
];

/// Crates the table lists ahead of their code (boundaries.md: Milestone 2 or later, D36); each
/// must leave this list the day its crate joins the workspace.
const PLANNED: &[&str] = &["frob-gh"];

/// A layer's number and name from the boundaries.md table.
#[derive(Clone, Debug, PartialEq, Eq)]
struct Layer {
    number: u32,
    name: String,
}

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The crate-to-layer map parsed from the `| Layer | Name | Crates |` table; errors name the row.
fn parse_table(doc: &str) -> Result<BTreeMap<String, Layer>, String> {
    let mut layers = BTreeMap::new();
    for line in doc.lines() {
        let cells: Vec<&str> = line
            .trim()
            .trim_matches('|')
            .split('|')
            .map(str::trim)
            .collect();
        let [number, name, crates] = cells[..] else {
            continue;
        };
        let Ok(number) = number.parse::<u32>() else {
            continue;
        };
        for krate in crates.split(',').map(str::trim).filter(|c| !c.is_empty()) {
            let layer = Layer {
                number,
                name: name.to_string(),
            };
            if layers.insert(krate.to_string(), layer).is_some() {
                return Err(format!("crate `{krate}` appears twice in the layer table"));
            }
        }
    }
    Ok(layers)
}

/// The product a crate belongs to: `gob`, or `frob`, `grimble` or `crunk` by name prefix.
fn product(krate: &str) -> &str {
    krate.split('-').next().unwrap_or(krate)
}

/// Why `from -> to` breaks the table, or None when it is allowed by the table.
fn broken(layers: &BTreeMap<String, Layer>, from: &str, to: &str) -> Option<String> {
    let (lf, lt) = (&layers[from], &layers[to]);
    let describe = |k: &str, l: &Layer| format!("{k} (layer {} {})", l.number, l.name);
    if lt.number >= lf.number {
        return Some(format!(
            "{} -> {}: goes up a layer",
            describe(from, lf),
            describe(to, lt)
        ));
    }
    let (pf, pt) = (product(from), product(to));
    if pf != pt && pt != "gob" {
        return Some(format!(
            "{} -> {}: crosses products ({pf} -> {pt})",
            describe(from, lf),
            describe(to, lt)
        ));
    }
    None
}

/// Every failure for `edges` against `layers` and the allow-list: unknown crates, new violations
/// and stale allow rows. Empty means the layering holds.
fn failures(
    layers: &BTreeMap<String, Layer>,
    edges: &BTreeSet<(String, String)>,
    allowed: &[(&str, &str, &str)],
) -> Vec<String> {
    let mut out = Vec::new();
    let members: BTreeSet<&String> = edges.iter().flat_map(|(a, b)| [a, b]).collect();
    for krate in members {
        if !layers.contains_key(krate) {
            out.push(format!("crate `{krate}` has no layer in boundaries.md 6.1"));
        }
    }
    if !out.is_empty() {
        return out;
    }
    let allow: BTreeSet<(&str, &str)> = allowed.iter().map(|(a, b, _)| (*a, *b)).collect();
    for (from, to) in edges {
        if let Some(why) = broken(layers, from, to)
            && !allow.contains(&(from.as_str(), to.as_str()))
        {
            out.push(why);
        }
    }
    for (from, to, ticket) in allowed {
        let live = edges.contains(&(from.to_string(), to.to_string()))
            && broken(layers, from, to).is_some();
        if !live {
            out.push(format!(
                "stale allow-list row {from} -> {to} ({ticket}): remove it"
            ));
        }
    }
    out
}

/// Normal and build edges between workspace crates, from `cargo metadata --no-deps`.
fn workspace_edges() -> (BTreeSet<String>, BTreeSet<(String, String)>) {
    let cargo = std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_string());
    let out = Command::new(cargo)
        .args([
            "metadata",
            "--format-version",
            "1",
            "--no-deps",
            "--offline",
        ])
        .current_dir(root())
        .output()
        .expect("cargo metadata runs");
    assert!(
        out.status.success(),
        "cargo metadata failed: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let meta: serde_json::Value = serde_json::from_slice(&out.stdout).expect("metadata is json");
    let packages = meta["packages"].as_array().expect("packages");
    let names: BTreeSet<String> = packages
        .iter()
        .map(|p| p["name"].as_str().unwrap().to_string())
        .collect();
    let mut edges = BTreeSet::new();
    for p in packages {
        for d in p["dependencies"].as_array().expect("dependencies") {
            let name = d["name"].as_str().unwrap();
            if d["kind"].as_str() != Some("dev") && names.contains(name) {
                edges.insert((p["name"].as_str().unwrap().to_string(), name.to_string()));
            }
        }
    }
    (names, edges)
}

fn table(rows: &[(u32, &str, &str)]) -> BTreeMap<String, Layer> {
    let mut doc = String::new();
    for (n, name, c) in rows {
        writeln!(doc, "| {n} | {name} | {c} |").unwrap();
    }
    parse_table(&doc).unwrap()
}

fn edge(a: &str, b: &str) -> BTreeSet<(String, String)> {
    BTreeSet::from([(a.to_string(), b.to_string())])
}

#[test]
fn workspace_layering_holds_and_every_crate_has_a_layer() {
    let doc = std::fs::read_to_string(root().join("docs/design/boundaries.md")).unwrap();
    let layers = parse_table(&doc).unwrap();
    let (names, edges) = workspace_edges();
    let missing: Vec<&String> = names.iter().filter(|n| !layers.contains_key(*n)).collect();
    let extra: Vec<&String> = layers
        .keys()
        .filter(|k| !names.contains(*k) && !PLANNED.contains(&k.as_str()))
        .collect();
    assert!(
        missing.is_empty() && extra.is_empty(),
        "layer table out of date: missing {missing:?}, unknown {extra:?}"
    );
    let bad = failures(&layers, &edges, ALLOWED);
    assert!(bad.is_empty(), "layering violations:\n{}", bad.join("\n"));
}

#[test]
fn an_edge_up_a_layer_fails_naming_both_crates_and_layers() {
    let layers = table(&[(0, "base", "gob-text"), (1, "io", "gob-fs")]);
    let bad = failures(&layers, &edge("gob-text", "gob-fs"), &[]);
    assert_eq!(bad.len(), 1, "{bad:?}");
    for want in [
        "gob-text",
        "layer 0 base",
        "gob-fs",
        "layer 1 io",
        "goes up a layer",
    ] {
        assert!(bad[0].contains(want), "{want} missing from {}", bad[0]);
    }
    assert!(failures(&layers, &edge("gob-fs", "gob-text"), &[]).is_empty());
}

#[test]
fn an_edge_across_products_fails_even_when_it_points_down() {
    let layers = table(&[(0, "base", "frob-a"), (1, "io", "grimble-b, gob-c")]);
    let bad = failures(&layers, &edge("grimble-b", "frob-a"), &[]);
    assert!(
        bad.len() == 1 && bad[0].contains("crosses products"),
        "{bad:?}"
    );
    let bad = failures(&layers, &edge("gob-c", "frob-a"), &[]);
    assert!(
        bad.len() == 1 && bad[0].contains("crosses products"),
        "{bad:?}"
    );
    assert!(
        failures(
            &table(&[(0, "b", "gob-c"), (1, "p", "frob-a")]),
            &edge("frob-a", "gob-c"),
            &[]
        )
        .is_empty()
    );
}

#[test]
fn a_listed_violation_passes_until_it_is_fixed_then_the_stale_row_fails() {
    let layers = table(&[(0, "base", "gob-text"), (1, "io", "gob-fs")]);
    let allow = [("gob-text", "gob-fs", "~T")];
    assert!(failures(&layers, &edge("gob-text", "gob-fs"), &allow).is_empty());
    let fixed = failures(&layers, &edge("gob-fs", "gob-text"), &allow);
    assert_eq!(fixed.len(), 1, "{fixed:?}");
    assert!(
        fixed[0].contains("stale allow-list row gob-text -> gob-fs (~T)"),
        "{fixed:?}"
    );
    let gone = failures(&layers, &BTreeSet::new(), &allow);
    assert!(gone[0].contains("stale"), "{gone:?}");
}

#[test]
fn a_crate_missing_from_the_table_fails() {
    let layers = table(&[(0, "base", "gob-text")]);
    let bad = failures(&layers, &edge("gob-text", "gob-new"), &[]);
    assert!(bad[0].contains("`gob-new` has no layer"), "{bad:?}");
}

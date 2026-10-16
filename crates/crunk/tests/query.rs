//! `crunk query`, `map` and `explain` end to end over a small project.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111"
accent = "#ff0000"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base", "components"]

[tokens]
json_file = "tokens.json"

[tailwind]
tokens_file = "tailwind.tokens.json"
namespace_keys = true
"##;

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), SPEC).expect("write spec");
    let (code, out, err) = crunk(dir.path(), &["tokens"]);
    assert_eq!(code, 0, "{out} {err}");
    std::fs::create_dir_all(dir.path().join("styles/components")).expect("mkdir");
    std::fs::write(
        dir.path().join("styles/components/card.css"),
        ".card { color: var(--color-ink); }\n.card__title { margin: 0; }\n",
    )
    .expect("write card");
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn json(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not json ({e}): {out}"))
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn unused_lists_tokens_nothing_references() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["query", "unused", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let env = json(&out);
    assert_eq!(env["data"]["kind"], "unused");
    let names: Vec<&str> = env["data"]["results"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r["name"].as_str().unwrap())
        .collect();
    assert!(names.contains(&"--color-accent"), "{names:?}");
    assert!(!names.contains(&"--color-ink"), "{names:?}");
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn uses_and_find_see_the_var_reference() {
    let dir = project();
    let (code, out, _) = crunk(dir.path(), &["query", "uses", "color-ink", "--json"]);
    assert_eq!(code, 0, "{out}");
    let rows = json(&out)["data"]["results"].clone();
    assert_eq!(rows[0]["path"], "styles/components/card.css");
    assert_eq!(rows[0]["line"], 1);

    let (code, out, _) = crunk(dir.path(), &["query", "find", "ink", "--json"]);
    assert_eq!(code, 0, "{out}");
    assert!(!json(&out)["data"]["results"].as_array().unwrap().is_empty());
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn color_ranks_the_whole_palette_by_distance() {
    let dir = project();
    let (code, out, _) = crunk(dir.path(), &["query", "color", "ff0000", "--json"]);
    assert_eq!(code, 0, "{out}");
    let rows = json(&out)["data"]["results"].clone();
    assert_eq!(rows[0]["name"], "accent");
    assert_eq!(rows[0]["exact"], true);
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn component_unknown_and_bad_color_are_usage_errors() {
    let dir = project();
    let (code, _, _) = crunk(dir.path(), &["query", "component", "nope"]);
    assert_eq!(code, 2);
    let (code, _, _) = crunk(dir.path(), &["query", "color", "not-a-color"]);
    assert_eq!(code, 2);
    let (code, _, _) = crunk(dir.path(), &["query", "dupes", "--threshold", "9"]);
    assert_eq!(code, 2);
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn component_reports_bem_structure() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["query", "component", "card", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let row = json(&out)["data"]["results"][0].clone();
    assert_eq!(row["name"], "card");
    assert_eq!(row["elements"][0]["name"], "title");
}

// frob:tests crates/crunk/src/query.rs::Query
#[test]
fn violations_exit_zero_even_with_findings() {
    let dir = project();
    std::fs::write(
        dir.path().join("styles/components/bad.css"),
        ".bad { color: #123456; }\n",
    )
    .unwrap();
    let (code, out, err) = crunk(dir.path(), &["query", "violations", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let rows = json(&out)["data"]["results"].clone();
    assert!(rows.is_array());
}

// frob:tests crates/crunk/src/map.rs::Map
#[test]
fn map_lists_buckets_in_org_order_and_strays() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["map", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let data = json(&out)["data"].clone();
    assert!(data["buckets"].is_object());
    assert!(data["strays"].is_array());
}

// frob:tests crates/crunk/src/explain.rs::Explain
#[test]
fn explain_known_token_reports_value_and_group() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["explain", "color-ink", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let row = json(&out)["data"]["results"][0].clone();
    assert_eq!(row["name"], "--color-ink");
    assert_eq!(row["sites"][0]["path"], "styles/components/card.css");
}

// frob:tests crates/crunk/src/explain.rs::Explain
#[test]
fn explain_unknown_token_exits_two_and_names_close_matches() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["explain", "color-ik"]);
    assert_eq!(code, 2, "{out} {err}");
    let text = format!("{out}{err}");
    assert!(text.contains("token name not found"), "{text}");
    assert!(text.contains("color-ink"), "{text}");
}

// frob:tests crates/crunk/src/explain.rs::Explain
#[test]
fn explain_rule_id_prints_each_tells_date_and_source() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["explain", "SLOP060", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let tells = json(&out)["data"]["tells"].clone();
    let first = tells[0].as_str().unwrap();
    assert!(
        first.contains("added 2026-10-08") && first.contains("source:"),
        "{first}"
    );
}

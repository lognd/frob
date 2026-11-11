//! `crunk check --report slop`: the evidence vector, with tiers that did not run.

// frob:ticket 01M4CXTBPEVSYD93X6S90ZRDZ9

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

fn crunk(dir: &Path, args: &[&str]) -> (i32, Value) {
    let (code, out, _) = run_for_test(&crunk::cli(), args, dir);
    let env: Value = serde_json::from_str(&out).unwrap_or(Value::Null);
    (code, env)
}

fn project(css: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::presets::preset("default").expect("default preset");
    std::fs::write(dir.path().join("crunk.toml"), spec).expect("write config");
    std::fs::create_dir_all(dir.path().join("styles")).expect("mkdir");
    std::fs::write(dir.path().join("styles/a.css"), css).expect("write css");
    dir
}

fn report(dir: &Path) -> Value {
    let (_, env) = crunk(dir, &["check", "--report", "slop", "--json"]);
    env["data"]["slop_report"].clone()
}

fn signal<'a>(rep: &'a Value, id: &str) -> &'a Value {
    rep["signals"]
        .as_array()
        .expect("signals")
        .iter()
        .find(|s| s["rule"] == id)
        .unwrap_or_else(|| panic!("signal {id} listed in {rep}"))
}

// frob:tests crates/crunk/src/slop_report.rs::build
#[test]
fn slop_report_lists_every_signal_with_evidence_and_tier_and_no_aggregate() {
    let dir = project(".cta { background: #6366f1; }\n");
    let rep = report(dir.path());
    let ids: Vec<String> = rep["signals"]
        .as_array()
        .expect("signals")
        .iter()
        .map(|s| s["rule"].as_str().expect("rule").to_owned())
        .collect();
    let expected = crunk_rules::registry::entries(crunk_check::product_rules::RULE_INDEXES)
        .into_iter()
        .filter(|e| e.family == "SLOP")
        .map(|e| e.id.to_owned())
        .collect::<Vec<_>>();
    assert!(!ids.is_empty());
    assert_eq!(ids, expected, "every SLOP rule is a signal, sorted by id");
    for s in rep["signals"].as_array().expect("signals") {
        assert_eq!(s["tiers"][0], "T0", "{s}");
        assert!(s["evidence"].is_array(), "{s}");
        assert!(s["status"].is_string(), "{s}");
    }
    let flagged = signal(&rep, "SLOP001");
    assert_eq!(flagged["status"], "flagged", "{flagged}");
    assert_eq!(flagged["evidence"][0]["file"], "styles/a.css");
    assert!(
        rep.get("score").is_none() && rep["counts"].get("score").is_none(),
        "no single score"
    );
    assert_eq!(rep["counts"]["signals"], ids.len());
}

// frob:tests crates/crunk/src/slop_report.rs::build
#[test]
fn tiers_that_did_not_run_are_listed_not_run_never_zero() {
    let dir = project(".a { margin: 0; }\n");
    let rep = report(dir.path());
    let tiers = rep["tiers"].as_array().expect("tiers");
    assert_eq!(tiers.len(), 4);
    for t in &tiers[1..] {
        assert_eq!(t["ran"], false, "{t}");
        assert!(t["reason"].is_string(), "{t}");
    }
    let counts = &rep["counts"];
    let parts = counts["flagged"].as_u64().unwrap_or(0)
        + counts["clear"].as_u64().unwrap_or(0)
        + counts["not_run"].as_u64().unwrap_or(0);
    assert_eq!(Some(parts), counts["signals"].as_u64(), "parts add up");
    for s in rep["signals"].as_array().expect("signals") {
        if s["status"] == "not_run" {
            assert!(s["reason"].is_string(), "a not-run signal says why: {s}");
        } else {
            assert!(s["reason"].is_null(), "{s}");
        }
    }
}

// frob:tests crates/crunk/src/slop_report.rs::build
#[test]
fn evidence_order_is_stable_and_plain_check_has_no_slop_report() {
    let dir = project(".a { color: #6366f1; }\n.b { color: #8b5cf6; }\n");
    let first = report(dir.path());
    let second = report(dir.path());
    assert_eq!(first, second);
    let ev = signal(&first, "SLOP001")["evidence"]
        .as_array()
        .expect("evidence")
        .clone();
    assert!(ev.len() >= 2, "{ev:?}");
    let lines: Vec<u64> = ev
        .iter()
        .map(|e| e["line"].as_u64().expect("line"))
        .collect();
    let mut sorted = lines.clone();
    sorted.sort_unstable();
    assert_eq!(lines, sorted);
    let (_, env) = crunk(dir.path(), &["check", "--json"]);
    assert!(env["data"].get("slop_report").is_none());
}

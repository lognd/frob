//! `grimble graph` end to end: planning status, level and obligations in the strict sibling schema.

// frob:ticket 01M4FDBBXG990QVX35HERF5VCQ

use std::path::{Path, PathBuf};

use gob_cli::run_for_test;
use jsonschema::{Registry, Resource};
use serde_json::Value;

const SIBLING_ID: &str = "https://schemas.test/sibling.json";
const ENVELOPE_ID: &str = "https://schemas.test/envelope.json";

fn schemas_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/schemas")
}

fn load(name: &str) -> Value {
    let text = std::fs::read_to_string(schemas_dir().join(name)).expect("read schema");
    serde_json::from_str(&text).expect("schema is JSON")
}

/// Errors of the whole envelope against sibling.json (which composes envelope.json).
fn sibling_errors(envelope: &Value) -> Vec<String> {
    let mut sibling = load("sibling.json");
    sibling["$id"] = Value::String(SIBLING_ID.to_owned());
    let mut env = load("envelope.json");
    env["$id"] = Value::String(ENVELOPE_ID.to_owned());
    let registry = Registry::new()
        .add(ENVELOPE_ID, Resource::from_contents(env.clone()))
        .expect("register envelope")
        .prepare()
        .expect("prepare registry");
    let sibling_validator = jsonschema::options()
        .with_registry(&registry)
        .build(&sibling)
        .expect("compile sibling schema");
    sibling_validator
        .iter_errors(envelope)
        .map(|e| format!("{e} at {}", e.instance_path()))
        .collect()
}

/// Validate the envelope against sibling.json and envelope.json.
fn assert_valid_sibling(envelope: &Value) {
    let errors = sibling_errors(envelope);
    assert!(errors.is_empty(), "sibling document invalid: {errors:#?}");
    let mut env = load("envelope.json");
    env["$id"] = Value::String(ENVELOPE_ID.to_owned());
    let envelope_validator = jsonschema::options()
        .build(&env)
        .expect("compile envelope schema");
    assert!(
        envelope_validator.is_valid(envelope),
        "the envelope itself is invalid"
    );
}

const CORPUS: &str = "../grimble-model/tests/corpus/plan/web_app";

fn repo() -> tempfile::TempDir {
    tempfile::tempdir().expect("tempdir")
}

fn grimble(dir: &Path, args: &[&str]) -> (i32, Value, String) {
    let cli = grimble::cli();
    let (code, out, err) = run_for_test(&cli, args, dir);
    let json = serde_json::from_str(&out).unwrap_or(Value::Null);
    (code, json, err)
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn corpus(rel: &str) -> String {
    std::fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join(CORPUS).join(rel))
        .expect("read corpus file")
}

// frob:tests crates/grimble/src/graph_cmd.rs::Graph
// frob:tests crates/grimble-bind/src/plan.rs::report
#[test]
fn the_web_example_graph_carries_status_level_and_the_documented_obligations() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"model.grmb\"]\n",
    );
    for rel in [
        "model.grmb",
        "web_app/goals.grmb",
        "web_app/customer_flow.grmb",
    ] {
        write(dir.path(), rel, &corpus(rel));
    }
    let (code, env, err) = grimble(dir.path(), &["graph", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    assert_valid_sibling(&env);
    let doc = &env["data"];
    assert_eq!(doc["schema_version"], "grimble.graph/1");
    let planning = [
        "system", "actor", "goal", "scenario", "step", "page", "impl",
    ];
    let rows: Vec<&Value> = doc["entities"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|e| planning.contains(&e["kind"].as_str().unwrap_or("")))
        .collect();
    assert!(!rows.is_empty(), "no planning entities: {doc}");
    for e in &rows {
        for key in ["status", "status_hi", "level"] {
            assert!(e.get(key).is_some(), "{key} missing on {e}");
        }
    }
    let rules: Vec<&str> = doc["obligations"]
        .as_array()
        .expect("obligations")
        .iter()
        .map(|o| o["rule"].as_str().unwrap())
        .collect();
    for want in ["PLAN001", "PLAN003", "PLAN005"] {
        assert!(rules.contains(&want), "{want} missing in {rules:?}");
    }
}

// frob:tests crates/grimble-bind/src/eval.rs::sys004_plan
// frob:tests crates/grimble-bind/src/plan.rs::report
#[test]
fn an_impl_matching_nothing_is_one_sys004_and_an_unbound_impl_obligation() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"m.grmb\"]\n",
    );
    write(
        dir.path(),
        "m.grmb",
        "grimble = \"2\";\nmodule m;\nsystem s {\n  actor customer : human;\n  goal customer as action { buy; }\n  step customer.pays;\n  scenario checkout realizes customer.buy { customer.pays -> end ok; }\n  impl customer.pays for checkout { handler = \"src/lib.rs::pay\"; }\n}\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn other() {}\n");
    let (_, env, err) = grimble(dir.path(), &["check", "--json"]);
    assert_valid_sibling(&env);
    let sys004: Vec<&Value> = env["data"]["findings"]
        .as_array()
        .unwrap_or_else(|| panic!("{env} {err}"))
        .iter()
        .filter(|f| f["rule"] == "SYS004")
        .collect();
    assert_eq!(sys004.len(), 1, "{sys004:#?}");
    let (_, graph, _) = grimble(dir.path(), &["graph", "--json"]);
    assert_valid_sibling(&graph);
    let unbound = graph["data"]["obligations"]
        .as_array()
        .expect("obligations")
        .iter()
        .filter(|o| o["kind"] == "unbound_impl")
        .count();
    assert_eq!(unbound, 1, "{graph}");
    assert!(
        graph["findings"]
            .as_array()
            .is_none_or(|f| f.iter().all(|x| x["rule"] != "SYS004")),
        "graph must not repeat the finding"
    );
}

/// The ids of every `grimble check` finding on `dir`.
fn check_rule_ids(dir: &Path) -> Vec<String> {
    let (_, env, err) = grimble(dir, &["check", "--json"]);
    assert_valid_sibling(&env);
    env["data"]["findings"]
        .as_array()
        .unwrap_or_else(|| panic!("{env} {err}"))
        .iter()
        .filter_map(|f| f["rule"].as_str().map(str::to_owned))
        .collect()
}

// frob:ticket 01M69AXE9FSCASMNDSMA1A7YMH
// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn the_web_example_check_reports_plan001_plan003_and_plan005() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"model.grmb\"]\n",
    );
    for rel in [
        "model.grmb",
        "web_app/goals.grmb",
        "web_app/customer_flow.grmb",
    ] {
        write(dir.path(), rel, &corpus(rel));
    }
    let ids = check_rule_ids(dir.path());
    for rule in ["PLAN001", "PLAN003", "PLAN005"] {
        assert!(ids.iter().any(|r| r == rule), "{rule} missing in {ids:?}");
    }
}

// frob:ticket 01M69AXE9FSCASMNDSMA1A7YMH
// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn an_impl_matching_nothing_is_not_also_a_plan004_finding() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"m.grmb\"]\n",
    );
    write(
        dir.path(),
        "m.grmb",
        "grimble = \"2\";\nmodule m;\nsystem s {\n  actor customer : human;\n  goal customer as action { buy; }\n  step customer.pays;\n  scenario checkout realizes customer.buy { customer.pays -> end ok; }\n  impl customer.pays for checkout { handler = \"src/lib.rs::pay\"; }\n}\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn other() {}\n");
    let ids = check_rule_ids(dir.path());
    assert!(ids.iter().any(|r| r == "SYS004"), "{ids:?}");
    assert!(ids.iter().all(|r| r != "PLAN004"), "{ids:?}");
}

const NEW_PLAN_RULES: [&str; 5] = ["PLAN002", "PLAN007", "PLAN008", "PLAN009", "PLAN010"];

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF
// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn the_web_example_is_silent_for_plan002_and_plan007_to_plan010() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"model.grmb\"]\n",
    );
    for rel in [
        "model.grmb",
        "web_app/goals.grmb",
        "web_app/customer_flow.grmb",
    ] {
        write(dir.path(), rel, &corpus(rel));
    }
    let ids = check_rule_ids(dir.path());
    for rule in NEW_PLAN_RULES {
        assert!(ids.iter().all(|r| r != rule), "{rule} fired in {ids:?}");
    }
}

/// The rule ids `grimble check` reports for the one model `text` plus `src/lib.rs`.
fn ids_of_model(text: &str) -> Vec<String> {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"m.grmb\"]\n",
    );
    write(dir.path(), "m.grmb", text);
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    check_rule_ids(dir.path())
}

const PLAN_BASE: &str = "grimble = \"2\";\nmodule m;\nsystem s { title \"S\"; }\nactor customer : human;\ngoal customer as action { buy; }\nstep customer.lands;\n";

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF
// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn each_new_plan_rule_fires_on_its_documented_example() {
    let cases: [(&str, String); 5] = [
        (
            "PLAN002",
            format!(
                "{PLAN_BASE}goal customer.buy as path {{ card; cash; }}\nscenario sc realizes customer.buy {{ customer.lands -> end ok; }}\n"
            ),
        ),
        (
            "PLAN007",
            format!(
                "{PLAN_BASE}scenario sc realizes customer.buy {{ customer.lands -> end ok; }}\nimpl customer.lands for sc {{ handler = \"src/lib.rs::run\"; }}\n"
            ),
        ),
        (
            "PLAN008",
            "grimble = \"2\";\nmodule m;\nsystem s { title \"S\"; }\npage home { ui = \"src/lib.rs::run\"; }\n"
                .to_owned(),
        ),
        (
            "PLAN009",
            format!(
                "{PLAN_BASE}scenario sc realizes customer.buy {{ customer.lands -> end ok; }}\nimpl customer.lands for sc {{ handler = \"src/lib.rs::run\"; in node b; }}\nnode a : trusted {{ owns \"src/**\"; }}\nnode b : trusted {{ owns \"b/**\"; }}\n"
            ),
        ),
        (
            "PLAN010",
            format!("{PLAN_BASE}scenario orphan {{ customer.lands -> end ok; }}\n"),
        ),
    ];
    for (rule, model) in cases {
        let ids = ids_of_model(&model);
        assert!(ids.iter().any(|r| r == rule), "{rule} missing in {ids:?}");
    }
}

// frob:ticket 01M69AXECHS0CVMJ58HWR05MGF
// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn a_timer_started_system_step_may_use_an_isr_but_a_human_started_one_may_not() {
    let timed = "grimble = \"2\";\nmodule m;\nsystem s { title \"S\"; }\nactor tick : timer;\ngoal tick as action { sample; }\nstep tick.fires;\nstep system.read;\nscenario sc realizes tick.sample { tick.fires -> system.read -> end ok; }\nimpl system.read for sc { isr = \"src/lib.rs::run\"; }\n";
    assert!(ids_of_model(timed).iter().all(|r| r != "PLAN007"));
    let human = "grimble = \"2\";\nmodule m;\nsystem s { title \"S\"; }\nactor customer : human;\ngoal customer as action { buy; }\nstep customer.lands;\nstep system.read;\nscenario sc realizes customer.buy { customer.lands -> system.read -> end ok; }\nimpl system.read for sc { isr = \"src/lib.rs::run\"; }\n";
    assert!(ids_of_model(human).iter().any(|r| r == "PLAN007"));
}

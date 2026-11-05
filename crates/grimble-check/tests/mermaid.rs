//! Snapshot tests for the mermaid planning renderings (grmb-spec 17.7).

// frob:ticket 01M4FDBG95B8D1NERFERXC0PXF

use grimble_model::ModelFiles;

const CORPUS: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../grimble-model/tests/corpus/plan/"
);

/// Build a `ModelFiles` from corpus files under `dir`, rooted at `model.grmb`.
fn corpus(dir: &str, files: &[&str]) -> ModelFiles {
    let mut m = ModelFiles::new().with_root("model.grmb");
    for f in files {
        let bytes = std::fs::read_to_string(format!("{CORPUS}{dir}/{f}")).expect("corpus file");
        m = m.with_file(f, bytes.into_bytes());
    }
    m
}

fn web_app() -> String {
    grimble_check::mermaid::render(&corpus(
        "web_app",
        &[
            "model.grmb",
            "web_app/goals.grmb",
            "web_app/customer_flow.grmb",
        ],
    ))
}

fn thermostat() -> String {
    grimble_check::mermaid::render(&corpus("thermostat", &["model.grmb", "fw/thermostat.grmb"]))
}

// frob:tests crates/grimble-check/src/mermaid.rs::render
#[test]
fn web_app_diagrams_are_stable() {
    insta::assert_snapshot!(web_app());
}

// frob:tests crates/grimble-check/src/mermaid.rs::render
#[test]
fn thermostat_diagrams_are_stable() {
    insta::assert_snapshot!(thermostat());
}

// frob:tests crates/grimble-check/src/mermaid.rs::render
#[test]
fn every_arm_and_retry_bound_appears() {
    let w = web_app();
    for want in [
        "no_item_found",
        "out_of_stock",
        "declined",
        "timeout",
        "retry max 3",
        "end err(timeout)",
        "end ok",
    ] {
        assert!(w.contains(want), "{want} missing in web_app:\n{w}");
    }
    let t = thermostat();
    for want in [
        "crc_error",
        "overcurrent",
        "retry max 2",
        "retries exhausted",
        "end err(overcurrent)",
    ] {
        assert!(t.contains(want), "{want} missing in thermostat:\n{t}");
    }
    assert_eq!(w.matches("sequenceDiagram").count(), 2);
    assert_eq!(w.matches("flowchart TD").count(), 2);
    assert_eq!(w.matches("flowchart LR").count(), 1);
}

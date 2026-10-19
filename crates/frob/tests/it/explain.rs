//! `frob explain` end to end: the embedded page equals the generated one, unknown ids exit 2.

// frob:ticket 01M3ZX7ZD77ZW385N5B992NX3A

use std::path::Path;

use gob_cli::run_for_test;

fn page_on_disk(id: &str) -> String {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../docs/reference/rules")
        .join(format!("{id}.md"));
    std::fs::read_to_string(path).expect("generated page")
}

// frob:tests crates/frob/src/explain_cmd.rs::Explain
#[test]
fn explain_prints_the_embedded_page_matching_the_generated_one() {
    let cwd = std::env::temp_dir();
    let cli = frob_cli::cli();
    let (code, stdout, _) = run_for_test(&cli, &["explain", "TODO001", "--text"], &cwd);
    assert_eq!(code, 0, "{stdout}");
    assert_eq!(stdout.trim_end(), page_on_disk("TODO001").trim_end());
    let (code, json, _) = run_for_test(&cli, &["explain", "todo001", "--json"], &cwd);
    assert_eq!(code, 0, "{json}");
    let doc: serde_json::Value = serde_json::from_str(&json).expect("json");
    assert_eq!(doc["data"]["id"], "TODO001");
    assert_eq!(
        doc["data"]["page"].as_str().expect("page"),
        page_on_disk("TODO001")
    );
}

// frob:tests crates/frob/src/explain_cmd.rs::Explain
#[test]
fn explain_of_an_unknown_id_suggests_the_closest_and_exits_2() {
    let cwd = std::env::temp_dir();
    let cli = frob_cli::cli();
    let (code, stdout, stderr) = run_for_test(&cli, &["explain", "TODO00", "--text"], &cwd);
    assert_eq!(code, 2, "{stdout}{stderr}");
    let all = format!("{stdout}{stderr}");
    assert!(
        all.contains("did you mean") && all.contains("TODO001"),
        "{all}"
    );
}

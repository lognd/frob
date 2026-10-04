//! A stand-in sibling binary for the sibling-stage tests.
//!
//! It ignores its argv except to echo it into a finding message, and reads its
//! behaviour from `.fake-sibling` in the working directory (the repository root):
//! `valid <ticket>`, `incompatible`, `baddigest`, `flood`, `badproduct`, `malformed`, `nomark`, `hang`,
//! `exit3` or `failenv`.
//!
//! It answers as `crunk` when its executable is named `crunk` (a test copies it there),
//! and as `grimble` under any other name.

use serde_json::{Value, json};

fn finding(
    rule: &str,
    severity: &str,
    file: &str,
    message: &str,
    fp: char,
    required: &Value,
) -> Value {
    json!({
        "rule": rule, "slug": null, "severity": severity, "polarity": "P+",
        "subjects_examined": 3, "reason": null, "maybe": [], "required": required,
        "file": file, "line": 1, "column": 1, "range": {"start": 0, "end": 3},
        "anchor": null, "entity": null, "message": message, "remedy": null,
        "fix": null, "fingerprint": fp.to_string().repeat(64),
    })
}

/// The product this copy answers as: `crunk` when run under that name, else `grimble`.
fn product() -> &'static str {
    let exe = std::env::current_exe().unwrap_or_default();
    if exe.file_stem().is_some_and(|n| n == "crunk") {
        "crunk"
    } else {
        "grimble"
    }
}

/// The digest of the `[compute]` knobs the repository's config files resolve to.
fn own_digest() -> String {
    let (table, _) =
        gob_config::ComputeTable::load_for_product(std::path::Path::new("."), product())
            .expect("compute knobs load");
    gob_config::compute_digest(&table)
}

fn valid(ticket: &Value, args: &str) -> Value {
    let required = json!({"kind": "annotation_required", "code": "x", "public_surface": false});
    let mut unresolved = finding(
        "SYS003",
        "unresolved",
        "a.txt",
        "opaque cone",
        'b',
        &required,
    );
    unresolved["reason"] = json!("annotation-required");
    json!({
        "schema_version": "gob.sibling/1", "product": product(), "product_version": "0.0.0",
        "compute_digest": own_digest(),
        "compute": {}, "invocation": {"verb": "check", "root": ".", "ticket_scope": null, "base": null},
        "fidelity": [{"language": "grmb", "adapter": "grimble", "adapter_version": "0", "level": "F3",
                      "capabilities": {}, "not_applicable_rules": ["SYS009"]}],
        "rules": [
            {"rule": "SYS006", "polarity": "P+", "subjects_examined": 3, "findings": 1, "suppressed": 1, "unresolved": 0},
            {"rule": "SYS003", "polarity": "P+", "subjects_examined": 3, "findings": 1, "suppressed": 0, "unresolved": 1}
        ],
        "findings": [finding("SYS006", "warning", "a.txt", &format!("two owners ({args})"), 'a', &Value::Null), unresolved],
        "suppressed": [{"finding": finding("SYS006", "warning", "b.txt", "parked", 'c', &Value::Null), "exception": "ex1"}],
        "exceptions": [{"id": "ex1", "kind": "defer", "rule": "SYS006", "on": "node/x", "file": "model/a.grmb",
                        "line": 1, "because": "waiting on the split", "until": null, "ticket": ticket,
                        "exit_state": "unresolved_exit", "status": null, "suppresses": 1}],
        "entities": [], "bindings": [], "timing": {"elapsed_ms": 1},
    })
}

fn envelope(data: &Value) -> String {
    json!({"verb": "check", "already": false, "ok": true, "data": data, "findings": [],
           "warnings": [], "error": null, "schema_version": 1})
    .to_string()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mode = std::fs::read_to_string(".fake-sibling").unwrap_or_default();
    let mut words = mode.split_whitespace();
    match words.next().unwrap_or("") {
        "valid" => {
            let ticket = words
                .next()
                .filter(|t| *t != "-")
                .map_or(Value::Null, Value::from);
            println!("{}", envelope(&valid(&ticket, &args.join(" "))));
        }
        "incompatible" => {
            let mut doc = valid(&Value::Null, "");
            doc["schema_version"] = json!("gob.sibling/9");
            println!("{}", envelope(&doc));
        }
        "baddigest" => {
            let mut doc = valid(&Value::Null, "");
            doc["compute_digest"] = json!(format!("blake3:{}", "0".repeat(64)));
            println!("{}", envelope(&doc));
        }
        "badproduct" => {
            let mut doc = valid(&Value::Null, "");
            doc["product"] = json!(if product() == "crunk" {
                "grimble"
            } else {
                "crunk"
            });
            println!("{}", envelope(&doc));
        }
        "nomark" => {
            let mut doc = valid(&Value::Null, "");
            doc["findings"][0]
                .as_object_mut()
                .expect("object")
                .remove("required");
            println!("{}", envelope(&doc));
        }
        "flood" => {
            let line = "x".repeat(1023);
            for _ in 0..4096 {
                println!("{line}");
            }
        }
        "malformed" => println!("this is not json"),
        "hang" => std::thread::sleep(std::time::Duration::from_secs(60)),
        "failenv" => {
            println!(
                "{}",
                json!({"verb": "check", "already": false, "ok": false, "data": null, "findings": [],
                       "warnings": [], "error": {"code": "E-X", "message": "model unreadable",
                       "remedy": "grimble fmt --check", "retryable": false}, "schema_version": 1})
            );
            std::process::exit(4);
        }
        _ => std::process::exit(3),
    }
}

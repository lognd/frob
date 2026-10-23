//! `grimble status` end to end: grant count, breadth per node and the delta since the lock.

// frob:ticket 01M4GYBTXAPBEX9QYWYX5FKR67

use std::path::Path;
use std::process::Command;

use gob_cli::run_for_test;
use serde_json::Value;

const BASE: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n  may fs.read at \"src/a/**\" because=\"reads config\";\n}\nnode b : trusted {\n  owns \"lib/**\";\n  may fs.write at \"lib/**\" ticket=\"T-1\";\n}\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn git(dir: &Path, args: &[&str]) {
    let ok = Command::new("git")
        .args(["-c", "user.name=t", "-c", "user.email=t@example.com"])
        .args(args)
        .current_dir(dir)
        .status()
        .unwrap()
        .success();
    assert!(ok, "git {args:?}");
}

fn status(dir: &Path) -> Value {
    let (code, out, err) = run_for_test(&grimble::cli(), &["status", "--json"], dir);
    assert_eq!(code, 0, "{out} {err}");
    serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out} {err}"))
}

fn repo(model: &str, lock: bool) -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    let p = dir.path();
    git(p, &["init", "-q"]);
    write(
        p,
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(p, "design/m.grmb", model);
    for f in ["src/a/x.py", "src/a/y.py", "src/b/z.py", "lib/q.py"] {
        write(p, f, "x = 1\n");
    }
    if lock {
        write(p, "grimble.lock", "{}\n");
    }
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    dir
}

fn node<'a>(doc: &'a Value, name: &str) -> &'a Value {
    doc["data"]["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .find(|n| n["node"].as_str().unwrap().ends_with(name))
        .unwrap_or_else(|| panic!("no node {name}: {doc}"))
}

// frob:tests crates/grimble/src/status_cmd.rs::Status
#[test]
fn status_reports_counts_breadth_delta_and_names_the_widening() {
    let dir = repo(BASE, true);
    let p = dir.path();
    let doc = status(p);
    assert_eq!(doc["data"]["grants"], 2, "{doc}");
    assert_eq!(node(&doc, "a")["breadth"], 2);
    assert_eq!(doc["data"]["changes"].as_array().unwrap().len(), 0);

    // Widen a's read to all of src, add a grant to b, narrow nothing yet.
    let wide = BASE
        .replace("at \"src/a/**\"", "at \"src/**\"")
        .replace("ticket=\"T-1\";", "ticket=\"T-1\";\n  may net.listen;");
    write(p, "design/m.grmb", &wide);
    let doc = status(p);
    assert_eq!(doc["data"]["grants"], 3, "{doc}");
    assert_eq!(doc["data"]["base_grants"], 2);
    let a = node(&doc, "a");
    assert_eq!(
        (a["breadth"].clone(), a["base_breadth"].clone()),
        (3.into(), 2.into())
    );
    let widened = doc["data"]["widened"].as_array().unwrap();
    assert_eq!(widened.len(), 1, "{doc}");
    assert!(widened[0].as_str().unwrap().contains("fs.read"), "{doc}");
    let changes: Vec<&str> = doc["data"]["changes"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["change"].as_str().unwrap())
        .collect();
    assert_eq!(changes, ["widened", "added"]);
    assert_eq!(doc["data"]["unreasoned"].as_array().unwrap().len(), 1);

    // Narrowing is reported but is not a widening.
    let narrow = BASE.replace("at \"src/a/**\"", "at \"src/a/x.py\"");
    write(p, "design/m.grmb", &narrow);
    let doc = status(p);
    assert!(
        doc["data"]["widened"].as_array().unwrap().is_empty(),
        "{doc}"
    );
    assert_eq!(doc["data"]["changes"][0]["change"], "narrowed");
}

// frob:tests crates/grimble/src/status_cmd.rs::Status
#[test]
fn status_without_a_lock_has_counts_and_no_delta() {
    let dir = repo(BASE, false);
    let doc = status(dir.path());
    assert!(doc["data"]["baseline"].is_null(), "{doc}");
    assert_eq!(doc["data"]["grants"], 2);
    assert!(doc["data"]["changes"].as_array().unwrap().is_empty());
    assert!(node(&doc, "b")["base_grants"].is_null());
}

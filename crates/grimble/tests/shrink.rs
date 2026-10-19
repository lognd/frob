//! `grimble shrink` end to end: dry run prints the diff, `--apply` writes the removal.

// frob:ticket 01M5A5F8CN6EKHGV1C4QZCQZMP

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const PY: &str = "import socket\nimport subprocess\n\ndef go():\n    with open(\"/etc/hosts\") as f:\n        f.read()\n    subprocess.run([\"ls\"])\n    s = socket.socket()\n    s.listen()\n";
const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n  may fs.read;\n  may exec;\n  may net.listen;\n  may fs.write;\n}\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn grimble(dir: &Path, args: &[&str]) -> (i32, Value) {
    let (code, out, err) = run_for_test(&grimble::cli(), args, dir);
    let doc = serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out} {err}"));
    (code, doc)
}

// frob:tests crates/grimble/src/shrink_cmd.rs::Shrink
#[test]
fn shrink_prints_the_diff_and_writes_only_with_apply() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(dir.path(), "design/m.grmb", MODEL);
    write(dir.path(), "src/x.py", PY);
    let path = dir.path().join("design/m.grmb");

    let (code, doc) = grimble(dir.path(), &["shrink", "--json"]);
    assert_eq!(code, 0, "{doc}");
    assert_eq!(doc["data"]["applied"], false);
    assert_eq!(
        doc["data"]["removals"][0]["clause"], "may fs.write;",
        "{doc}"
    );
    assert!(
        doc["data"]["diff"]
            .as_str()
            .unwrap()
            .contains("-  may fs.write;")
    );
    assert_eq!(std::fs::read_to_string(&path).unwrap(), MODEL);

    let (code, doc) = grimble(dir.path(), &["shrink", "--apply", "--json"]);
    assert_eq!(code, 0, "{doc}");
    assert_eq!(doc["data"]["applied"], true);
    let after = std::fs::read_to_string(&path).unwrap();
    assert_eq!(after, MODEL.replace("  may fs.write;\n", ""));

    let (_, doc) = grimble(dir.path(), &["shrink", "--json"]);
    assert!(
        doc["data"]["removals"].as_array().unwrap().is_empty(),
        "{doc}"
    );
}

//! SYS003 end-owner findings fold once per clause and MDL005 once per selector (the flood fix).

// frob:ticket 01M4FGYNKKP10PVPT90AKKMHBY

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// A repo whose consumer clause `pkg/**` is owned by `a` over `units` units, but the flow ends at `b`.
fn wrong_owner_repo(units: usize) -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"pkg/**\"; owns \"a/**\"; }\nnode b : trusted { owns \"b/**\"; }\nnode d : trusted { owns \"design/**\"; }\n\nflow bad : a -> b {\n  producer \"a/lib.rs::send\";\n  consumer \"pkg/**\";\n}\n",
    );
    write(dir.path(), "a/lib.rs", "pub fn send() {}\n");
    write(dir.path(), "b/lib.rs", "pub fn recv() {}\n");
    for i in 0..units {
        write(dir.path(), &format!("pkg/f{i}.rs"), "// no symbols\n");
    }
    dir
}

fn messages(doc: &serde_json::Value, rule: &str) -> Vec<String> {
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == rule)
        .map(|f| f["message"].as_str().unwrap().to_owned())
        .collect()
}

// frob:tests crates/grimble-bind/src/eval.rs::end_owner
#[test]
fn seven_wrong_owner_units_fold_into_one_sys003() {
    let dir = wrong_owner_repo(7);
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let msgs = messages(&doc, "SYS003");
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    let m = &msgs[0];
    assert!(m.contains("flow/bad"), "{m}");
    assert!(m.contains("7 units"), "{m}");
    assert!(m.contains("+4 more"), "{m}");
    assert!(m.contains("`node/a`"), "{m}");
}

// frob:tests crates/grimble-bind/src/eval.rs::end_owner
#[test]
fn one_unit_keeps_the_per_unit_message_and_the_sample_bound_is_exact() {
    let one = wrong_owner_repo(1);
    let doc = sibling_document(&run(one.path(), &CheckOptions::default()).unwrap());
    let msgs = messages(&doc, "SYS003");
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    assert!(
        msgs[0].contains("owned by `node/a`, not by `node/b`"),
        "{}",
        msgs[0]
    );

    let three = wrong_owner_repo(3);
    let doc = sibling_document(&run(three.path(), &CheckOptions::default()).unwrap());
    let msgs = messages(&doc, "SYS003");
    assert_eq!(msgs.len(), 1, "{msgs:?}");
    assert!(msgs[0].contains("3 units"), "{}", msgs[0]);
    assert!(!msgs[0].contains("more"), "{}", msgs[0]);
}

// frob:tests crates/grimble-model/src/check.rs::Checker.selector
#[test]
fn a_selector_in_three_clauses_gets_one_mdl005_listing_the_sites() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; owns \"future3/**\"; }\nnode b : trusted { owns \"b/**\"; owns \"future3/**\"; }\nnode c : trusted { owns \"c/**\"; owns \"future3/**\"; owns \"other9/**\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    write(dir.path(), "b/lib.rs", "pub fn b() {}\n");
    write(dir.path(), "c/lib.rs", "pub fn c() {}\n");
    let doc = sibling_document(&run(dir.path(), &CheckOptions::default()).unwrap());
    let msgs = messages(&doc, "MDL005");
    let fut: Vec<&String> = msgs.iter().filter(|m| m.contains("future3/**")).collect();
    assert_eq!(fut.len(), 1, "{msgs:?}");
    assert!(fut[0].contains("3 clauses"), "{}", fut[0]);
    assert_eq!(fut[0].matches("design/m.grmb:").count(), 3, "{}", fut[0]);
    assert_eq!(msgs.iter().filter(|m| m.contains("other9/**")).count(), 1);
}

// frob:tests crates/grimble-check/src/sibling.rs::sibling_document
#[test]
fn check_json_keeps_every_per_unit_binding_row() {
    let dir = wrong_owner_repo(7);
    let doc = sibling_document(&run(dir.path(), &CheckOptions::default()).unwrap());
    let rows = doc["bindings"].as_array().unwrap();
    for i in 0..7 {
        let id = format!("pkg/f{i}.rs");
        assert!(
            rows.iter()
                .any(|b| b["identity"] == id.as_str() && b["entity"] == "node/a"),
            "missing binding row for {id}"
        );
    }
}

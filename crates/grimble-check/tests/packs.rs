//! Repository packs (tier 1, atoms only): `packs/NAME.toml` enabled by `local/NAME` supplies
//! atoms and satisfies the `pack` entity. Repro 03 of the logand adoption run.

// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

const PACK: &str = "format = 1\n\n[pack]\nname = \"logand-effects\"\nversion = \"1.0.0\"\ndescription = \"d\"\nlicence = \"MIT\"\n\n[[atom]]\nname = \"fetch_url\"\ndoc = \"Fetches a URL.\"\nargs = \"host\"\n";
const MODEL: &str = "grimble = \"2\";\nmodule m;\npack le { ref \"local/logand-effects\"; version \"1.0.0\"; }\nnode a : trusted { owns \"src/**\"; may fetch_url at \"src/**\"; }\n";

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

fn repo(pack: Option<&str>) -> (tempfile::TempDir, serde_json::Value) {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/model.grmb\"]\n[packs]\nenabled = [\"local/logand-effects\"]\n",
    );
    write(dir.path(), "design/model.grmb", MODEL);
    write(dir.path(), "src/x.py", "def go():\n    pass\n");
    if let Some(p) = pack {
        write(dir.path(), "packs/logand-effects.toml", p);
    }
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    (dir, doc)
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

// frob:tests crates/grimble-check/src/packs.rs::load
#[test]
fn an_enabled_repo_pack_supplies_atoms_and_satisfies_the_pack_entity() {
    let (_d, doc) = repo(Some(PACK));
    assert!(messages(&doc, "MDL016").is_empty(), "{}", doc["findings"]);
    assert!(messages(&doc, "MDL004").is_empty(), "{}", doc["findings"]);
    let packs = doc["packs"].as_array().unwrap();
    assert_eq!(packs.len(), 1);
    assert_eq!(packs[0]["name"], "local/logand-effects");
    assert_eq!(packs[0]["version"], "1.0.0");
    assert!(packs[0]["digest"].as_str().unwrap().starts_with("blake3:"));
}

// frob:tests crates/grimble-check/src/lib.rs::run
#[test]
fn a_loaded_repo_pack_clears_the_not_loaded_warning() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/model.grmb\"]\n[packs]\nenabled = [\"local/logand-effects\"]\n",
    );
    write(dir.path(), "design/model.grmb", MODEL);
    write(dir.path(), "packs/logand-effects.toml", PACK);
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(
        r.warnings.iter().all(|w| !w.contains("loads only")),
        "{:?}",
        r.warnings
    );
}

// frob:tests crates/grimble-check/src/packs.rs::load
#[test]
fn a_missing_pack_file_is_mdl004_naming_the_path() {
    let (_d, doc) = repo(None);
    let m = messages(&doc, "MDL004");
    assert_eq!(m.len(), 1, "{}", doc["findings"]);
    assert!(m[0].contains("packs/logand-effects.toml"), "{m:?}");
    assert_eq!(messages(&doc, "MDL016").len(), 1);
}

// frob:tests crates/grimble-check/src/packs.rs::load
#[test]
fn a_malformed_pack_file_is_mdl004() {
    let (_d, doc) = repo(Some("not = [valid"));
    let m = messages(&doc, "MDL004");
    assert!(m.iter().any(|x| x.contains("malformed")), "{m:?}");
}

#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! Repository packs (tier 1, atoms only): `packs/NAME.toml` enabled by `local/NAME` supplies
//! atoms and satisfies the `pack` entity. Repro 03 of the logand adoption run.

// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82
// frob:ticket 01M4H4WTSTB7X4A6STFEF8K8S3
// frob:ticket 01M61Y35AKW4QDRE70W6HFQAJ5

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

#[test]
fn the_packs_table_doc_and_generated_references_describe_what_loads() {
    use gob_config::ConfigTable;
    let doc = grimble_check::config::PacksTable::describe().doc;
    assert!(!doc.contains("not loaded yet"), "stale doc: {doc}");
    assert!(
        doc.contains("local/") && doc.contains("atoms"),
        "doc: {doc}"
    );
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for rel in ["docs/schemas/config.json", "docs/reference/config.md"] {
        let text = std::fs::read_to_string(root.join(rel)).unwrap();
        assert!(!text.contains("Packs are not loaded yet"), "{rel} is stale");
        assert!(
            text.contains("Only `local/` packs"),
            "{rel} lacks the new doc"
        );
    }
}

// frob:ticket 01M4HEMAM737MTY3385G7VKXQ4
const DETECTED_PACK: &str = "format = 1\n\n[pack]\nname = \"logand-effects\"\nversion = \"1.0.0\"\ndescription = \"d\"\nlicence = \"MIT\"\n\n[[atom]]\nname = \"fetch_url\"\ndoc = \"Fetches a URL.\"\n\n[[vocab]]\nlang = \"python\"\nclass = \"fetch_url\"\nnames = [\"fetchlib.get\", \"requests.get\"]\n\n[[vocab]]\nlang = \"typescript\"\nclass = \"fetch_url\"\nnames = [\"fetch\"]\n\n[[detector]]\natom = \"fetch_url\"\nlangs = [\"python\", \"typescript\"]\nkind = \"callee\"\n";
const GRANTED: &str = "grimble = \"2\";\nmodule m;\npack le { ref \"local/logand-effects\"; version \"1.0.0\"; }\nnode a : trusted { owns \"src/**\"; may fetch_url at \"src/**\"; }\n";
const UNGRANTED: &str = "grimble = \"2\";\nmodule m;\npack le { ref \"local/logand-effects\"; version \"1.0.0\"; }\nnode a : trusted { owns \"src/**\"; }\n";

fn check(
    pack: &str,
    model: &str,
    files: &[(&str, &str)],
) -> (tempfile::TempDir, serde_json::Value) {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/model.grmb\"]\n[packs]\nenabled = [\"local/logand-effects\"]\n",
    );
    write(dir.path(), "design/model.grmb", model);
    write(dir.path(), "packs/logand-effects.toml", pack);
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    (dir, doc)
}

const PY_USE: &str = "import fetchlib\n\ndef go():\n    return fetchlib.get('u')\n";
const PY_IDLE: &str = "def go():\n    pass\n";

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_pack_atom_use_without_a_grant_is_cap001() {
    let (_d, doc) = check(DETECTED_PACK, UNGRANTED, &[("src/x.py", PY_USE)]);
    let m = messages(&doc, "CAP001");
    assert!(
        m.iter().any(|x| x.contains("fetch_url")),
        "{}",
        doc["findings"]
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_granted_pack_atom_use_is_clean() {
    let (_d, doc) = check(DETECTED_PACK, GRANTED, &[("src/x.py", PY_USE)]);
    assert!(messages(&doc, "CAP001").is_empty(), "{}", doc["findings"]);
    assert!(messages(&doc, "CAP002").is_empty(), "{}", doc["findings"]);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn an_unused_pack_atom_grant_is_cap002() {
    let (_d, doc) = check(DETECTED_PACK, GRANTED, &[("src/x.py", PY_IDLE)]);
    let m = messages(&doc, "CAP002");
    assert!(
        m.iter().any(|x| x.contains("fetch_url")),
        "{}",
        doc["findings"]
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_granted_pack_atom_with_no_detector_for_a_language_is_unresolved_once_per_node() {
    let pack = DETECTED_PACK.replace("langs = [\"python\", \"typescript\"]", "lang = \"python\"");
    let (_d, doc) = check(
        &pack,
        GRANTED,
        &[
            ("src/x.py", PY_USE),
            ("src/a.ts", "export const a = 1;\n"),
            ("src/b.ts", "export const b = 2;\n"),
        ],
    );
    let hits: Vec<_> = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "CAP002" && f["severity"] == "unresolved")
        .collect();
    assert_eq!(hits.len(), 1, "{}", doc["findings"]);
    let msg = hits[0]["message"].as_str().unwrap();
    assert!(
        msg.contains("fetch_url") && msg.contains("typescript"),
        "{msg}"
    );
}

// frob:ticket 01M61Y35AKW4QDRE70W6HFQAJ5
const HOST_PACK: &str = "format = 1\n\n[pack]\nname = \"logand-effects\"\nversion = \"1.0.0\"\ndescription = \"d\"\nlicence = \"MIT\"\n\n[[atom]]\nname = \"fetch_url\"\ndoc = \"Fetches a URL.\"\nargs = \"host\"\n\n[[atom]]\nname = \"plain\"\ndoc = \"Takes none.\"\n\n[[vocab]]\nlang = \"python\"\nclass = \"fetch_url\"\nnames = [\"fetchlib.get\"]\n\n[[detector]]\natom = \"fetch_url\"\nlang = \"python\"\nkind = \"callee\"\n";

fn model_with(grant: &str) -> String {
    format!(
        "grimble = \"2\";\nmodule m;\npack le {{ ref \"local/logand-effects\"; version \"1.0.0\"; }}\nnode a : trusted {{ owns \"src/**\"; {grant} }}\n"
    )
}

// frob:tests crates/grimble-model/src/check.rs::grant_args
#[test]
fn a_pack_atom_grant_argument_is_validated_against_its_declared_kind() {
    let bad = model_with("may fetch_url(\"https://api.example.com/v1\") because=\"w\";");
    let (_d, doc) = check(HOST_PACK, &bad, &[("src/x.py", PY_IDLE)]);
    let m = messages(&doc, "MDL008");
    assert!(
        m.iter().any(|x| x.contains("a host pattern is expected")),
        "{}",
        doc["findings"]
    );
    let good = model_with("may fetch_url(\"api.example.com\") because=\"w\";");
    let (_d, doc) = check(HOST_PACK, &good, &[("src/x.py", PY_IDLE)]);
    assert!(messages(&doc, "MDL008").is_empty(), "{}", doc["findings"]);
}

// frob:tests crates/grimble-model/src/check.rs::grant_args
#[test]
fn a_pack_atom_that_declares_no_args_takes_no_grant_arguments() {
    let model = model_with("may plain(\"x\") because=\"w\";");
    let (_d, doc) = check(HOST_PACK, &model, &[("src/x.py", PY_IDLE)]);
    let m = messages(&doc, "MDL008");
    assert!(
        m.iter().any(|x| x.contains("takes no arguments")),
        "{}",
        doc["findings"]
    );
}

// frob:tests crates/grimble-check/src/packs.rs::load
#[test]
fn a_pack_atom_with_an_unknown_args_kind_is_mdl004() {
    let pack = HOST_PACK.replace("args = \"host\"", "args = \"regex\"");
    let (_d, doc) = check(&pack, &model_with(""), &[("src/x.py", PY_IDLE)]);
    let m = messages(&doc, "MDL004");
    assert!(m.iter().any(|x| x.contains("regex")), "{}", doc["findings"]);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_pack_atom_call_is_judged_against_its_grant_argument() {
    let model = model_with("may fetch_url(\"good.example.com\") because=\"w\";");
    let evil = "import fetchlib\n\ndef go():\n    return fetchlib.get('evil.example.com')\n";
    let (_d, doc) = check(HOST_PACK, &model, &[("src/x.py", evil)]);
    assert!(
        messages(&doc, "CAP001")
            .iter()
            .any(|x| x.contains("fetch_url")),
        "{}",
        doc["findings"]
    );
    let fine = "import fetchlib\n\ndef go():\n    return fetchlib.get('good.example.com')\n";
    let (_d, doc) = check(HOST_PACK, &model, &[("src/x.py", fine)]);
    assert!(messages(&doc, "CAP001").is_empty(), "{}", doc["findings"]);
}

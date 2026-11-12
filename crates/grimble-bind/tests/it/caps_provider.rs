//! `provides C via S` as a capability boundary in cross-node propagation (ticket
//! 01M666NX8TN1R3X13Q4S9CTJ1V, grimble-capabilities-v3.md 5.3): the walk stops at S, and a
//! symbol no node declared a provider still propagates.

// frob:ticket 01M666NX8TN1R3X13Q4S9CTJ1V

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const BASE: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n}\nnode b : trusted {\n  owns \"src/b/**\";\n  may fs.write;\n";
const PROVIDES: &str =
    "  provides fs.write via \"src/b/store.rs::put\" because=\"the one writer\";\n";

fn bind_with(model_text: &str, files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    std::fs::write(dir.path().join("design/model.grmb"), model_text).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", model_text.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// True when node `a` has a CAP001 finding for an `fs.write` atom, for a model with/without the provider.
fn a_needs_fs_write(provider: bool, files: &[(&str, &str)]) -> bool {
    let text = format!("{BASE}{}}}\n", if provider { PROVIDES } else { "" });
    bind_with(&text, files)
        .findings
        .iter()
        .any(|f| f.rule == "CAP001" && f.anchor.starts_with("cap/node/a/fs.write"))
}

/// `put` reaches the write only through `inner`; `other` is no provider and calls `inner` too.
const STORE: (&str, &str) = (
    "src/b/store.rs",
    "pub fn put(p: &str) {\n    inner(p);\n}\n\npub fn other(p: &str) {\n    inner(p);\n}\n\nfn inner(p: &str) {\n    let _ = std::fs::write(p, \"x\");\n}\n",
);

fn caller(f: &str) -> (&'static str, String) {
    (
        "src/a/user.rs",
        format!("pub fn go() {{\n    b::store::{f}(\"p\");\n}}\n"),
    )
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn without_provides_the_wrapper_leaks_its_interior_write() {
    let (cp, ct) = caller("put");
    assert!(a_needs_fs_write(false, &[STORE, (cp, ct.as_str())]));
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_declared_provider_stops_the_walk_at_the_boundary() {
    let (cp, ct) = caller("put");
    assert!(!a_needs_fs_write(true, &[STORE, (cp, ct.as_str())]));
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_non_provider_symbol_still_propagates_beside_a_provider() {
    let (cp, ct) = caller("other");
    assert!(a_needs_fs_write(true, &[STORE, (cp, ct.as_str())]));
}

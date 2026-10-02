//! Selector behaviour over models: specificity, owner, statuses and hidden placeholders
//! (grmb-spec 6.4, 6.5 and 10), with the .grmb files themselves as the code term.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::collections::BTreeSet;

use gob_ir::{HiddenReason, Status, select};
use gob_walk::{
    Digest, EntityName, FileEntry, LanguageHint, Owner, Selector, WalkResult, owner_of_path,
};
use grimble_model::binding::{explicit_binds, owner_inputs};
use grimble_model::fold::fold_file;
use grimble_model::model::{ModelFiles, load_roots};
use grimble_model::parse::parse_file;

fn corpus(path: &str) -> Vec<u8> {
    std::fs::read(std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus").join(path))
        .expect("corpus file")
}

fn root_of(path: &str) -> grimble_model::model::LoadedRoot {
    let name = path.rsplit('/').next().expect("name").to_owned();
    let mf = ModelFiles::new().with_file(&name, corpus(path));
    load_roots(&mf).remove(0)
}

fn walk_of(path: &str, text: &[u8]) -> WalkResult {
    WalkResult {
        files: vec![FileEntry {
            path: path.to_owned(),
            size: text.len() as u64,
            digest: Digest::of(text),
            language: LanguageHint::from_path(path),
        }],
        oversized: vec![],
    }
}

#[test]
fn specificity_is_a_total_order_and_ties_are_unknown() {
    let root = root_of("selector/specificity.grmb");
    let inputs = owner_inputs(&root);
    let narrow = owner_of_path("src/x/mod.rs", &inputs, false);
    assert_eq!(narrow.owner, Owner::Must(EntityName::from("narrow")));
    let broad = owner_of_path("src/x/y.rs", &inputs, false);
    assert_eq!(broad.owner, Owner::Must(EntityName::from("broad")));
    let tie = owner_of_path("lib/a.rs", &inputs, false);
    let want: BTreeSet<EntityName> = ["tie_a", "tie_b"].into_iter().map(EntityName::from).collect();
    assert_eq!(tie.owner, Owner::Unknown(want), "a tie is never broken arbitrarily");
}

#[test]
fn owner_distinguishes_owned_foreign_and_unknown() {
    let root = root_of("selector/owner.grmb");
    let inputs = owner_inputs(&root);
    assert_eq!(
        owner_of_path("crates/b/src/lib.rs", &inputs, false).owner,
        Owner::Must(EntityName::from("other"))
    );
    assert_eq!(owner_of_path("docs/readme.md", &inputs, false).owner, Owner::Foreign);
    assert!(
        matches!(owner_of_path("docs/readme.md", &inputs, true).owner, Owner::Unknown(_)),
        "an unseen remainder makes the answer Unknown, never FOREIGN"
    );
    let binds = explicit_binds(&root);
    assert_eq!(binds.len(), 1);
    assert_eq!(binds[0].entity, "node/explicit");
    assert_eq!(binds[0].symref, "crates/b/src/lib.rs::g");
    assert!(!binds[0].manual, "`via` is optional; rank 1 beats the owns of `other` (applied by G10)");
}

#[test]
fn literal_selectors_are_must_and_holes_add_a_hidden_placeholder() {
    let text = b"grimble = \"2\";\nmodule m;\nnode cli : trusted {\n  kind component;\n}\n";
    let parsed = parse_file("model.grmb", text);
    let folded = fold_file(&parsed, "").expect("fold");
    let files = walk_of("model.grmb", text);
    let lit = Selector::parse("\"model.grmb::cli\"").expect("selector");
    let sel = select(&lit, &folded.term, &folded.scopes, &files);
    assert_eq!(sel.matches.len(), 1);
    assert_eq!(sel.matches[0].status, Status::Must);
    assert!(sel.hidden.is_empty());
    let nodes = Selector::parse("kind(node) & lang(grmb)").expect("selector");
    assert_eq!(select(&nodes, &folded.term, &folded.scopes, &files).matches.len(), 1);

    let holey = b"grimble = \"2\";\nmodule m;\nnode cli : trusted {\n  owns ;\n}\n";
    let parsed = parse_file("model.grmb", holey);
    let folded = fold_file(&parsed, "").expect("fold");
    let files = walk_of("model.grmb", holey);
    let any = Selector::parse("\"model.grmb::**\"").expect("selector");
    let sel = select(&any, &folded.term, &folded.scopes, &files);
    assert!(
        sel.hidden.iter().any(|h| h.reason == HiddenReason::Hole),
        "a hole may hide units: {sel:?}"
    );
}

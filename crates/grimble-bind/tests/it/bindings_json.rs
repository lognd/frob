//! `Binding::bindings_json` serialises every row of the relation for the sibling document.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use grimble_bind::{BindInput, bind};
use grimble_model::ModelFiles;

// frob:tests crates/grimble-bind/src/lib.rs::Binding.bindings_json
#[test]
fn one_json_item_per_row_names_the_entity_and_its_status() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
    std::fs::write(dir.path().join("src/a.py"), "def go():\n    return 1\n").unwrap();
    let text = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n";
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", text.as_bytes().to_vec());
    let binding = bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    });
    let items = binding.bindings_json();
    assert_eq!(items.len(), binding.rows.len());
    assert!(!items.is_empty(), "the owns clause binds src/a.py");
    for (item, row) in items.iter().zip(&binding.rows) {
        assert_eq!(item["entity"], row.entity.as_str());
        assert_eq!(item["status"], row.status.as_str());
    }
    assert!(
        items
            .iter()
            .any(|i| i["entity"].as_str().is_some_and(|e| e.ends_with('a')))
    );
}

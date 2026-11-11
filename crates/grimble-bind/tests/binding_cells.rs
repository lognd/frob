//! `Binding` exposes the capability matrix cells: grant cells plus CAP001 undeclared ones.

// frob:ticket 01M6VRR46TR8D8C4TG0GYNK2NK

use grimble_bind::{BindInput, Binding};
use grimble_capabilities::Cell;
use grimble_model::ModelFiles;

/// Bind one python file under a node with the given grant lines.
fn bind_one(src: &str, grants: &str) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
    std::fs::write(dir.path().join("src/a.py"), src).unwrap();
    let text = format!(
        "grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n{grants}}}\n"
    );
    // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
    std::fs::write(dir.path().join("design/model.grmb"), &text).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", text.into_bytes());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

// frob:ticket 01M6VRR46TR8D8C4TG0GYNK2NK
// frob:tests crates/grimble-bind/src/caps.rs::push_flagged
// frob:tests crates/grimble-bind/src/caps.rs::grant_cells
#[test]
fn binding_exposes_grant_and_undeclared_cells() {
    let src =
        "import urllib.request\n\ndef go():\n    return urllib.request.urlopen(\"http://x\")\n";
    let binding = bind_one(src, "  may fs.read;\n");
    let cells = &binding.cells;
    let undeclared: Vec<_> = cells
        .iter()
        .filter(|c| c.cell == Cell::Undeclared)
        .collect();
    assert_eq!(undeclared.len(), 1, "{cells:?}");
    assert_eq!(undeclared[0].atom, "net.connect");
    assert!(undeclared[0].node.ends_with('a'), "{:?}", undeclared[0]);
    assert_eq!(undeclared[0].written, "net.connect");
    let grant = cells
        .iter()
        .find(|c| c.atom == "fs.read")
        .unwrap_or_else(|| panic!("no fs.read grant cell in {cells:?}"));
    assert!(
        matches!(grant.cell, Cell::DeclaredUnused | Cell::Unknown),
        "{grant:?}"
    );
}

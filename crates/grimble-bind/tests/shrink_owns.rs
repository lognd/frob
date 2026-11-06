//! `grimble shrink` proposes `owns` selectors for directories SYS001 reports unowned.

// frob:ticket 01M5A7E4S1CQJ834X4409EPWW0

use grimble_bind::{BindInput, shrink};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n}\n";

fn plan_for(extra_dirs: &[&str]) -> (shrink::Plan, String) {
    let dir = tempfile::tempdir().unwrap();
    for d in ["src/a", "design"].iter().chain(extra_dirs) {
        std::fs::create_dir_all(dir.path().join(d)).unwrap();
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(dir.path().join(d).join("f.py"), "def go():\n    return 1\n").unwrap();
    }
    // frob:accept LOG001 because="test fixture writes a temp model file, not log output"
    std::fs::write(dir.path().join("design/model.grmb"), MODEL).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", MODEL.as_bytes().to_vec());
    let b = grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &["design/**".to_owned()],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    });
    let mut read = |_: &str| Some(MODEL.to_owned());
    (
        shrink::plan_with_owns(&b.findings, &b.owns_sites, &mut read),
        MODEL.to_owned(),
    )
}

// frob:tests crates/grimble-bind/src/shrink.rs::plan_with_owns
#[test]
fn unowned_sibling_directory_gets_an_owns_clause_on_the_nearest_node() {
    let (plan, old) = plan_for(&["src/b"]);
    assert_eq!(
        plan.additions.len(),
        1,
        "{:?} {:?}",
        plan.additions,
        plan.skipped
    );
    assert_eq!(plan.additions[0].dir, "src/b");
    assert_eq!(plan.additions[0].node, "a");
    let new = &plan.edited["design/model.grmb"];
    assert!(
        new.contains("  owns \"src/a/**\";\n  owns \"src/b/**\";\n"),
        "{new}"
    );
    assert_ne!(new, &old);
    assert!(plan.diff.contains("+  owns \"src/b/**\";"), "{}", plan.diff);
}

// frob:tests crates/grimble-bind/src/shrink.rs::plan_with_owns
#[test]
fn directory_with_no_nearby_node_is_skipped_not_guessed() {
    let (plan, _) = plan_for(&["other"]);
    assert!(plan.additions.is_empty());
    assert!(
        plan.skipped.iter().any(|s| s.starts_with("other:")),
        "{:?}",
        plan.skipped
    );
}

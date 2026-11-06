//! The `[grimble] profile` key: a configured profile replaces the per-file test/prod guess
//! when judging `profile=` grants (ticket 01M6QD4EKJ72F7J6CGQ9AK1STA).

// frob:ticket 01M6QD4EKJ72F7J6CGQ9AK1STA

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const WRITE: &str = "pub fn go(p: &str) {\n    let _ = std::fs::write(p, \"x\");\n}\n";
const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n  may fs.write profile=staging;\n}\n";

fn bind_under(profile: Option<&str>) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::write(dir.path().join("src/w.rs"), WRITE).unwrap();
    std::fs::write(dir.path().join("design/model.grmb"), MODEL).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let mut model = ModelFiles::new().with_file("design/model.grmb", MODEL.as_bytes().to_vec());
    if let Some(p) = profile {
        model = model.with_profile(p);
    }
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

fn cap001(b: &Binding) -> usize {
    b.findings.iter().filter(|f| f.rule == "CAP001").count()
}

// frob:tests crates/grimble-bind/src/caps.rs::profile_of
#[test]
fn a_configured_profile_selects_the_grants_that_cover() {
    if std::env::var_os("GRIMBLE_PROFILE").is_some() {
        return;
    }
    let staging = bind_under(Some("staging"));
    assert_eq!(cap001(&staging), 0, "{:?}", staging.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::profile_of
#[test]
fn without_a_configured_profile_the_path_decides() {
    if std::env::var_os("GRIMBLE_PROFILE").is_some() {
        return;
    }
    let unset = bind_under(None);
    assert!(cap001(&unset) > 0, "{:?}", unset.findings);
    let other = bind_under(Some("prod"));
    assert!(cap001(&other) > 0, "{:?}", other.findings);
}

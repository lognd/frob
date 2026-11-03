//! `Model` queries over the default preset's tokens and a project with no stylesheets.

// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use std::path::Path;

use crunk_ingest::ProjectStyles;
use crunk_query::Model;
use crunk_tokens::TokenSet;

fn tokens() -> TokenSet {
    let spec = crunk_spec::parse_spec(
        crunk_spec::presets::DEFAULT,
        Path::new("crunk.toml"),
        Path::new("/proj"),
    )
    .expect("default preset parses");
    TokenSet::from_spec(&spec).expect("tokens derive")
}

// frob:tests crates/crunk-query/src/lib.rs::Model.relative
#[test]
fn relative_strips_the_root_and_uses_forward_slashes() {
    let (styles, set) = (ProjectStyles::default(), tokens());
    let model = Model::new(&styles, &set, Path::new("/proj"));
    assert_eq!(
        Model::relative(&model, Path::new("/proj/css/app.css")),
        "css/app.css"
    );
}

// frob:tests crates/crunk-query/src/lib.rs::Model.find
// frob:tests crates/crunk-query/src/lib.rs::Model.component
// frob:tests crates/crunk-query/src/lib.rs::Model.dupes
// frob:tests crates/crunk-query/src/lib.rs::Model.uses
// frob:tests crates/crunk-query/src/lib.rs::Model.map
#[test]
fn a_project_without_stylesheets_has_nothing_to_find() {
    let (styles, set) = (ProjectStyles::default(), tokens());
    let model = Model::new(&styles, &set, Path::new("/proj"));
    assert!(Model::find(&model, "no-such-class-anywhere").is_empty());
    assert!(Model::component(&model, "NoSuchComponent").is_none());
    assert!(Model::dupes(&model, 0.9).is_empty());
    assert!(Model::uses(&model, "color-ink").is_empty());
    assert!(Model::map(&model).strays.is_empty());
}

// frob:tests crates/crunk-query/src/lib.rs::Model.unused
// frob:tests crates/crunk-query/src/lib.rs::Model.color
// frob:tests crates/crunk-query/src/lib.rs::Model.explain
#[test]
fn with_no_stylesheets_every_token_is_unused_and_explain_names_it() {
    let (styles, set) = (ProjectStyles::default(), tokens());
    let model = Model::new(&styles, &set, Path::new("/proj"));
    assert_eq!(Model::unused(&model).len(), set.len());
    assert!(Model::color(&model, "not a color").is_none());
    assert!(Model::color(&model, "#ffffff").is_some());
    let first = set.iter().next().expect("a token").name.clone();
    let row = Model::explain(&model, &first, None).expect("known token");
    assert_eq!(row.name, first);
    assert!(Model::explain(&model, "zzzz-not-a-token", None).is_err());
}

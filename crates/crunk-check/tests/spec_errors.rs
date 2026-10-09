//! A `crunk.toml` that does not load fails the check with a config error naming the table or key,
//! instead of every rule quietly turning inapplicable.

// frob:ticket 01M4FH779H9X6S28KT1M8SFZ1N

use crunk_check::{CheckOptions, run};
use gob_check::CheckError;
use gob_config::ConfigError;

fn spec() -> &'static str {
    crunk_spec::presets::preset("default").expect("default preset")
}

fn refused(spec_text: &str) -> ConfigError {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), spec_text).expect("write");
    match run(dir.path(), &CheckOptions::default()) {
        Err(CheckError::Config(e)) => e,
        Err(other) => panic!("expected a config error, got {other}"),
        Ok(_) => panic!("expected a config error, the check ran"),
    }
}

// frob:tests crates/crunk-spec/src/error.rs::SpecError.into_config_error
// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn an_unknown_table_fails_the_load_naming_it() {
    let e = refused(&format!("{}\n[bogus]\nx = 1\n", spec()));
    assert!(
        matches!(&e, ConfigError::UnknownKey { key, .. } if key == "bogus"),
        "{e}"
    );
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn an_unknown_key_in_a_known_table_fails_naming_table_and_key() {
    let text = spec().replace("[org]\n", "[org]\nmystery = 1\n");
    let e = refused(&text);
    assert!(
        matches!(&e, ConfigError::UnknownKey { table, key, .. } if table == "org" && key == "mystery"),
        "{e}"
    );
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn v1_shaped_layers_content_fails_the_load() {
    let text = spec().replace("[layers]\n", "[layers]\nmodal = { z = 10 }\n");
    let e = refused(&text);
    assert!(e.to_string().contains("layers"), "{e}");
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn malformed_toml_fails_the_load() {
    assert!(matches!(refused("[project\n"), ConfigError::Parse { .. }));
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn a_repository_without_crunk_toml_still_runs() {
    let dir = tempfile::tempdir().expect("tempdir");
    assert!(run(dir.path(), &CheckOptions::default()).is_ok());
}

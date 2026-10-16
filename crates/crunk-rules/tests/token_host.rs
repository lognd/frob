//! The TOKEN rules' host plumbing: input gates, subject count, loaded token files and used vars.

// frob:ticket 01M51N0ZN8BWH8C6RYGJBJQ73T

use crunk_rules::CrunkHost;
use crunk_rules::host::{missing_token_inputs, missing_token_style_inputs, token_subjects};
use crunk_rules::token_files::{TokenFacts, used_vars};
use crunk_spec::DesignSpec;

struct Host {
    spec: DesignSpec,
    tokens: Option<TokenFacts>,
}

impl CrunkHost for Host {
    fn spec(&self) -> Option<&DesignSpec> {
        Some(&self.spec)
    }
    fn tokens(&self) -> Option<&TokenFacts> {
        self.tokens.as_ref()
    }
}

fn project(token_files: &[(&str, &str)]) -> (tempfile::TempDir, Host) {
    let dir = tempfile::tempdir().expect("tempdir");
    let tokens_dir = dir.path().join("design/tokens");
    std::fs::create_dir_all(&tokens_dir).expect("mkdir");
    for (name, text) in token_files {
        std::fs::write(tokens_dir.join(name), text).expect("write");
    }
    let spec = crunk_spec::parse_spec(
        crunk_spec::presets::DEFAULT,
        std::path::Path::new("crunk.toml"),
        dir.path(),
    )
    .expect("default preset parses");
    let tokens = Some(TokenFacts::load(&spec));
    (dir, Host { spec, tokens })
}

// frob:tests crates/crunk-rules/src/host.rs::missing_token_inputs
// frob:tests crates/crunk-rules/src/host.rs::missing_token_style_inputs
// frob:tests crates/crunk-rules/src/host.rs::token_subjects
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.tokens
#[test]
fn token_rules_need_authored_token_files_and_styles() {
    let (_dir, empty) = project(&[]);
    assert_eq!(
        missing_token_inputs(&empty).as_deref(),
        Some("no design/tokens/*.toml files")
    );
    assert_eq!(token_subjects(&empty), 0);

    let (_dir, host) = project(&[("a.toml", "[color]\nink = \"#101010\"\n")]);
    assert_eq!(missing_token_inputs(&host), None);
    assert_eq!(token_subjects(&host), 1);
    assert_eq!(
        missing_token_style_inputs(&host).as_deref(),
        Some("no stylesheets were ingested")
    );
}

// frob:tests crates/crunk-rules/src/token_files.rs::TokenFacts.ok_sets
// frob:tests crates/crunk-rules/src/token_files.rs::TokenFacts.fingerprint
#[test]
fn only_compiling_files_have_sets_and_the_fingerprint_follows_the_text() {
    let (_d1, a) = project(&[
        ("a.toml", "[color]\nink = \"#101010\"\n"),
        ("b.toml", "not = [valid"),
    ]);
    let facts = a.tokens().expect("facts");
    assert_eq!(facts.files.len(), 2);
    let ok: Vec<&str> = facts.ok_sets().map(|(f, _)| f.path.as_str()).collect();
    assert_eq!(ok, ["design/tokens/a.toml"]);

    let (_d2, b) = project(&[
        ("a.toml", "[color]\nink = \"#111111\"\n"),
        ("b.toml", "not = [valid"),
    ]);
    let (fa, fb) = (
        a.tokens().unwrap().fingerprint(),
        b.tokens().unwrap().fingerprint(),
    );
    assert_ne!(fa, fb);
    assert_eq!(fa, a.tokens().unwrap().fingerprint());
}

// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.reviews
#[test]
fn a_host_without_reviews_reports_none() {
    let (_dir, host) = project(&[]);
    assert!(host.reviews().is_none());
}

// frob:tests crates/crunk-rules/src/token_files.rs::used_vars
#[test]
fn no_stylesheets_read_no_vars() {
    let styles = crunk_ingest::ProjectStyles::default();
    assert!(used_vars(&styles).is_empty());
}

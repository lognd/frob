//! Authored `design/tokens/*.toml` tokens reach the managed exports, and a name clash refuses.

// frob:ticket 01M5XK12082GJW5KQTMK4DJXGN

use std::path::Path;

use crunk_spec::{DesignSpec, parse_spec};
use crunk_tokens::TokenSet;
use crunk_tokens::export::{Target, render_managed, render_target};

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "styles/tokens.css"
root_font_size = 16

[palette]
ink = "#111111"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[tokens]
json_file = "styles/tokens.json"

[tailwind]
tokens_file = "styles/tailwind.tokens.json"
namespace_keys = true
"##;

fn project(token_file: &str) -> (tempfile::TempDir, DesignSpec) {
    let dir = tempfile::tempdir().expect("tempdir");
    let tokens = dir.path().join("design/tokens");
    std::fs::create_dir_all(&tokens).unwrap();
    std::fs::write(tokens.join("brand.toml"), token_file).unwrap();
    let spec = parse_spec(SPEC, Path::new("crunk.toml"), dir.path()).expect("spec");
    (dir, spec)
}

fn content(spec: &DesignSpec, target: Target) -> String {
    render_managed(spec)
        .expect("renders")
        .into_iter()
        .find(|r| r.target == target)
        .unwrap_or_else(|| panic!("{target} not configured"))
        .content
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.from_spec_with_authored
// frob:tests crates/crunk-tokens/src/dialect.rs::read_authored
#[test]
fn an_authored_token_reaches_the_css_and_json_exports() {
    let (_dir, spec) = project("[brand]\nink = \"#123456\"\n");
    assert!(content(&spec, Target::Css).contains("--brand-ink: #123456;"));
    assert!(content(&spec, Target::Json).contains("\"brand-ink\""));
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.from_spec_with_authored
#[test]
fn an_authored_name_clashing_with_the_spec_refuses_naming_both() {
    let (_dir, spec) = project("[color]\nink = \"#123456\"\n");
    let err = TokenSet::from_spec_with_authored(&spec).expect_err("collision");
    let msg = err.to_string();
    assert!(
        msg.contains("--color-ink") && msg.contains("palette") && msg.contains("brand.toml"),
        "{msg}"
    );
    assert!(render_managed(&spec).is_err());
}

// frob:tests crates/crunk-tokens/src/model.rs::TokenSet.from_spec_with_authored
#[test]
fn a_file_that_does_not_compile_is_skipped_not_fatal() {
    let (_dir, spec) = project("[brand]\nink = \"not a color\"\n");
    assert!(content(&spec, Target::Css).contains("--color-ink"));
    assert!(!content(&spec, Target::Css).contains("--brand-ink"));
}

// frob:tests crates/crunk-tokens/src/export/mod.rs::render_target
#[test]
fn render_target_includes_authored_tokens() {
    let (_dir, spec) = project("[brand]\nink = \"#123456\"\n");
    let css = render_target(&spec, Target::Css).expect("renders");
    assert!(css.contains("--brand-ink: #123456;"), "{css}");
}

//! Port of the Python naming tests: sanitizing, step formatting and every token name.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use crunk_spec::model::TokensConfig;
use crunk_spec::naming::{
    color_token, font_family_stack_token, font_family_token, font_size_token, format_step,
    layer_token, radius_token, sanitize_ident, size_token, space_token, token_namespaces,
};

fn with(f: impl FnOnce(&mut TokensConfig)) -> TokensConfig {
    let mut cfg = TokensConfig::default();
    f(&mut cfg);
    cfg
}

// frob:tests crates/crunk-spec/src/naming.rs::color_token
#[test]
fn empty_color_prefix_drops_the_prefix_segment() {
    assert_eq!(
        color_token(&with(|c| c.color.clear()), "bg-primary"),
        "--bg-primary"
    );
    assert_eq!(
        color_token(&TokensConfig::default(), "bg-primary"),
        "--color-bg-primary"
    );
}

// frob:tests crates/crunk-spec/src/naming.rs::sanitize_ident
// frob:tests crates/crunk-spec/src/naming.rs::format_step
// frob:tests crates/crunk-spec/src/naming.rs::space_token
// frob:tests crates/crunk-spec/src/naming.rs::font_size_token
// frob:tests crates/crunk-spec/src/naming.rs::radius_token
// frob:tests crates/crunk-spec/src/naming.rs::layer_token
// frob:tests crates/crunk-spec/src/naming.rs::font_family_token
#[test]
fn naming_scheme_edge_cases() {
    let cfg = TokensConfig::default();
    assert_eq!(sanitize_ident("deep sky"), "deep-sky");
    assert_eq!(sanitize_ident("A.B  C_d-e"), "a-b-c_d-e");
    assert_eq!(sanitize_ident("caf\u{e9}"), "caf-");
    assert_eq!(format_step(6.5), "6_5");
    assert_eq!(format_step(4.0), "4");
    assert_eq!(format_step(-0.0), "0");
    assert_eq!(format_step(0.25), "0_25");
    assert_eq!(space_token(&cfg, 6.5), "--space-6_5");
    assert_eq!(font_size_token(&cfg, 16.0), "--font-size-16");
    assert_eq!(radius_token(&cfg, 4.0), "--radius-4");
    assert_eq!(layer_token(&cfg, "deep sky"), "--layer-deep-sky");
    assert_eq!(font_family_token(&cfg), "--font-family-base");
}

// frob:tests crates/crunk-spec/src/naming.rs::size_token
#[test]
fn size_tokens_honor_the_configured_prefix() {
    assert_eq!(size_token(&TokensConfig::default(), 44.0), "--size-44");
    assert_eq!(size_token(&TokensConfig::default(), 6.5), "--size-6_5");
    assert_eq!(
        size_token(&with(|c| c.size = "box".into()), 128.0),
        "--box-128"
    );
}

// frob:tests crates/crunk-spec/src/naming.rs::font_family_stack_token
#[test]
fn stack_tokens_honor_the_prefix() {
    assert_eq!(
        font_family_stack_token(&TokensConfig::default(), "Display Serif"),
        "--font-family-display-serif"
    );
    assert_eq!(
        font_family_stack_token(&with(|c| c.font_family.clear()), "body"),
        "--body"
    );
}

// frob:tests crates/crunk-spec/src/naming.rs::token_namespaces
#[test]
fn namespaces_default_and_collapse() {
    assert_eq!(
        token_namespaces(&TokensConfig::default()),
        [
            "--color-",
            "--space-",
            "--font-size-",
            "--radius-",
            "--layer-",
            "--font-family-"
        ]
    );
    assert_eq!(token_namespaces(&with(|c| c.color.clear())), ["--"]);
    assert_eq!(token_namespaces(&with(|c| c.layer.clear())), ["--"]);
}

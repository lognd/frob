//! `crunk extract-token` for px/rem lengths and the refused non-colour literals.

// frob:ticket 01M5H3RXZHDEDM508R6K4DBBVJ

use std::path::Path;

use gob_cli::run_for_test;

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111111"
"ink-bg" = "#eeeeee"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[jsx]
globs = ["src/**/*.tsx"]
"##;

const CSS: &str = concat!(
    ".a { padding: 16px; margin: 1rem 1.0rem; gap: 16PX; top: -16px; left: a-16px; }\n",
    ".b { width: calc(100% - 16px); background: url(x16px.png) url(16px.png); content: \"16px\"; }\n",
    ".c { margin: 160px 116px 16.5px 16pxx; }\n",
    "@media (min-width: 16px) { .d { padding: 16px; } }\n",
    "/* 16px in a comment */\n",
);
const TSX: &str = "export const A = () => <div style={{ padding: '16px' }}>16px</div>;\n";

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    std::fs::write(p.join("crunk.toml"), SPEC).unwrap();
    std::fs::create_dir_all(p.join("styles/base")).unwrap();
    std::fs::write(p.join("styles/base/a.css"), CSS).unwrap();
    std::fs::create_dir_all(p.join("src")).unwrap();
    std::fs::write(p.join("src/A.tsx"), TSX).unwrap();
    let (code, out, err) = crunk(p, &["tokens"]);
    assert_eq!(code, 0, "{out} {err}");
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn read(dir: &Path, rel: &str) -> String {
    std::fs::read_to_string(dir.join(rel)).unwrap()
}

fn refused(dir: &Path, args: &[&str], code: &str) {
    let (exit, out, err) = crunk(dir, args);
    assert_ne!(exit, 0, "{out} {err}");
    assert!(
        out.contains(code) || err.contains(code),
        "{code} not in {out} {err}"
    );
}

// frob:tests crates/crunk/src/extract.rs::ExtractToken
// frob:tests crates/crunk/src/extract.rs::LengthMatcher.new
// frob:tests crates/crunk/src/extract.rs::LengthMatcher.at
// frob:tests crates/crunk/src/extract.rs::parse_dimension
#[test]
fn extract_token_promotes_a_length_and_rewrites_its_uses() {
    let dir = project();
    let p = dir.path();
    let (code, out, err) = crunk(p, &["extract-token", "16px"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(read(p, "crunk.toml").contains("spacing = [0, 8, 16]"));
    assert!(read(p, "styles/tokens.css").contains("--space-16:"));

    let css = read(p, "styles/base/a.css");
    assert!(css.contains("padding: var(--space-16);"), "{css}");
    assert!(css.contains("gap: var(--space-16);"), "{css}");
    assert!(
        css.contains("margin: var(--space-16) var(--space-16);")
            || css.contains("margin: 1rem 1.0rem;"),
        "{css}"
    );
    assert!(css.contains("top: -16px;"), "negative kept: {css}");
    assert!(css.contains("left: a-16px;"), "ident kept: {css}");
    assert!(css.contains("calc(100% - var(--space-16))"), "{css}");
    assert!(
        css.contains("url(x16px.png) url(16px.png)"),
        "url kept: {css}"
    );
    assert!(css.contains("content: \"16px\""), "string kept: {css}");
    assert!(
        css.contains("margin: 160px 116px 16.5px 16pxx;"),
        "near misses kept: {css}"
    );
    assert!(
        css.contains("@media (min-width: 16px) { .d { padding: var(--space-16); } }"),
        "prelude kept: {css}"
    );
    assert!(css.contains("/* 16px in a comment */"), "{css}");
    assert!(read(p, "src/A.tsx").contains("'16px'"), "strings kept");
    let (code, out, err) = crunk(p, &["tokens", "--check"]);
    assert_eq!(code, 0, "{out} {err}");
}

// frob:tests crates/crunk/src/extract.rs::ExtractToken
#[test]
fn extract_token_converts_rem_and_honours_scale_and_dry_run() {
    let dir = project();
    let p = dir.path();
    let before = read(p, "crunk.toml");
    let (code, out, err) = crunk(p, &["extract-token", "1rem", "--dry-run"]);
    assert_eq!(code, 0, "{out} {err}");
    assert_eq!(read(p, "crunk.toml"), before, "dry run writes nothing");
    let (code, out, err) = crunk(p, &["extract-token", "1rem"]);
    assert_eq!(code, 0, "{out} {err}");
    let css = read(p, "styles/base/a.css");
    assert!(
        css.contains("margin: var(--space-16) var(--space-16);"),
        "{css}"
    );
    assert!(css.contains("padding: 16px;"), "same-unit only: {css}");
    let (code, out, err) = crunk(p, &["extract-token", "4px", "--scale", "radii"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(read(p, "crunk.toml").contains("radii = [0, 4]"));
    refused(p, &["extract-token", "0.5rem"], "E-EXTRACT-EXISTS");
    refused(
        p,
        &["extract-token", "20px", "--name", "x"],
        "E-EXTRACT-NAME",
    );
    refused(
        p,
        &["extract-token", "#abcdef", "--scale", "radii"],
        "E-EXTRACT-SCALE",
    );
}

// frob:tests crates/crunk/src/extract.rs::ExtractToken
#[test]
fn extract_token_refuses_durations_and_unsupported_lengths() {
    let dir = project();
    let p = dir.path();
    refused(p, &["extract-token", "150ms"], "E-EXTRACT-DURATION");
    refused(p, &["extract-token", "0.2s"], "E-EXTRACT-DURATION");
    refused(p, &["extract-token", "50%"], "E-EXTRACT-UNIT");
    refused(p, &["extract-token", "1em"], "E-EXTRACT-UNIT");
    refused(p, &["extract-token", "0px"], "E-EXTRACT-ZERO");
    refused(p, &["extract-token", "-4px"], "E-EXTRACT-NEGATIVE");
}

// frob:tests crates/crunk/src/extract.rs::ExtractToken
#[test]
fn extract_token_keeps_crlf_and_multiline_lists() {
    let dir = project();
    let p = dir.path();
    let crlf = read(p, "crunk.toml").replace('\n', "\r\n");
    std::fs::write(p.join("crunk.toml"), crlf).unwrap();
    let (code, out, err) = crunk(p, &["extract-token", "#abcdef"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(read(p, "crunk.toml").contains("cabcdef = \"#abcdef\"\r\n"));
    let multi =
        read(p, "crunk.toml").replace("spacing = [0, 8]", "spacing = [\r\n    0,\r\n    8,\r\n]");
    std::fs::write(p.join("crunk.toml"), multi).unwrap();
    let (code, out, err) = crunk(p, &["extract-token", "4px"]);
    assert_eq!(code, 0, "{out} {err}");
    let toml = read(p, "crunk.toml");
    assert!(toml.contains("    4,"), "{toml}");
    let (code, out, err) = crunk(p, &["tokens", "--check"]);
    assert_eq!(code, 0, "{out} {err}");
}

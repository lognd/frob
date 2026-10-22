//! `crunk rename` and `crunk extract-token` end to end over CSS, TSX and component specs.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT
// frob:ticket 01M5H3RXWHYH6MRJX6B2M35H0F

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

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

const CSS: &str = "/* --color-ink stays in comments */\n.a { color: var(--color-ink); background: var(--color-ink-bg); border-color: var(--color-ink) var(--color-ink); content: \"--color-ink\"; }\n";
const TSX: &str = "export const A = () => <div style={{ color: 'var(--color-ink)' }} className=\"x\">{'--color-ink-bg'}</div>;\n// --color-ink in a comment\n";
const COMPONENT: &str = "[[bindings]]\ntoken = \"--color-ink\"\n";

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    std::fs::write(p.join("crunk.toml"), SPEC).unwrap();
    std::fs::create_dir_all(p.join("styles/base")).unwrap();
    std::fs::write(p.join("styles/base/a.css"), CSS).unwrap();
    std::fs::create_dir_all(p.join("src")).unwrap();
    std::fs::write(p.join("src/A.tsx"), TSX).unwrap();
    std::fs::create_dir_all(p.join("design/components")).unwrap();
    std::fs::write(p.join("design/components/a.component.toml"), COMPONENT).unwrap();
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

fn json(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not json ({e}): {out}"))
}

fn refused(dir: &Path, args: &[&str], code: &str) {
    let (exit, out, err) = crunk(dir, args);
    assert_ne!(exit, 0, "{out} {err}");
    assert!(
        out.contains(code) || err.contains(code),
        "{code} not in {out} {err}"
    );
}

// frob:tests crates/crunk/src/rewrite.rs::header_of
// frob:tests crates/crunk/src/rewrite.rs::RewriteData.new
// frob:tests crates/crunk/src/rewrite.rs::RewriteData.lines
// frob:tests crates/crunk/src/rewrite.rs::commit_atomic
// frob:tests crates/crunk/src/rewrite.rs::source_files
// frob:tests crates/crunk/src/rewrite.rs::generated_changes
// frob:tests crates/crunk/src/rewrite.rs::reference_changes
// frob:tests crates/crunk/src/rename.rs::PlanError.code
// frob:tests crates/crunk/src/rename.rs::Rename
#[test]
fn rename_rewrites_css_tsx_and_specs_and_stays_clean() {
    let dir = project();
    let p = dir.path();
    let (code, out, err) = crunk(p, &["rename", "--color-ink", "--color-text", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(
        json(&out)["data"]["replacements"].as_u64().unwrap() >= 5,
        "{out}"
    );

    let css = read(p, "styles/base/a.css");
    assert!(css.contains("color: var(--color-text);"), "{css}");
    assert!(css.contains("var(--color-text) var(--color-text)"), "{css}");
    assert!(
        css.contains("var(--color-ink-bg)"),
        "prefix overlap kept: {css}"
    );
    assert!(css.contains("/* --color-ink stays in comments */"), "{css}");
    assert!(css.contains("content: \"--color-ink\""), "{css}");
    let tsx = read(p, "src/A.tsx");
    assert!(
        tsx.contains("var(--color-text)") && tsx.contains("'--color-ink-bg'"),
        "{tsx}"
    );
    assert!(tsx.contains("// --color-ink in a comment"), "{tsx}");
    assert!(read(p, "design/components/a.component.toml").contains("--color-text"));
    assert!(read(p, "crunk.toml").contains("text = \"#111111\""));
    assert!(read(p, "styles/tokens.css").contains("--color-text:"));

    let (code, out, err) = crunk(p, &["tokens", "--check"]);
    assert_eq!(code, 0, "tokens --check: {out} {err}");
    let (code, out, err) = crunk(p, &["check"]);
    assert_eq!(code, 0, "check: {out} {err}");
}

// frob:tests crates/crunk/src/rename.rs::Rename
#[test]
fn rename_refuses_collision_same_missing_and_invalid_names() {
    let dir = project();
    let p = dir.path();
    refused(
        p,
        &["rename", "--color-ink", "--color-ink-bg"],
        "E-RENAME-EXISTS",
    );
    refused(
        p,
        &["rename", "--color-ink", "--color-ink"],
        "E-RENAME-SAME",
    );
    refused(
        p,
        &["rename", "--color-nope", "--color-x"],
        "E-RENAME-MISSING",
    );
    refused(p, &["rename", "--color-ink", "color-x"], "E-RENAME-NAME");
    refused(p, &["rename", "--color-ink", "--1bad"], "E-RENAME-NAME");
    assert_eq!(read(p, "styles/base/a.css"), CSS);
}

// frob:tests crates/crunk/src/rename.rs::Rename
#[test]
fn rename_dry_run_writes_nothing() {
    let dir = project();
    let p = dir.path();
    let before = read(p, "crunk.toml");
    let (code, out, err) = crunk(
        p,
        &[
            "rename",
            "--color-ink",
            "--color-text",
            "--dry-run",
            "--json",
        ],
    );
    assert_eq!(code, 0, "{out} {err}");
    assert_eq!(json(&out)["data"]["dry_run"], true);
    assert_eq!(read(p, "styles/base/a.css"), CSS);
    assert_eq!(read(p, "crunk.toml"), before);
}

// frob:tests crates/crunk/src/rewrite.rs::commit
// frob:tests crates/crunk/src/rename.rs::Rename
#[cfg(unix)]
#[test]
fn rename_write_failure_leaves_every_file_untouched() {
    use std::os::unix::fs::PermissionsExt;
    let dir = project();
    let p = dir.path();
    let css = p.join("styles/base");
    std::fs::set_permissions(&css, std::fs::Permissions::from_mode(0o555)).unwrap();
    if std::fs::write(css.join("probe"), "").is_ok() {
        return; // running as root: permissions are not enforced
    }
    let before = read(p, "crunk.toml");
    let (code, out, err) = crunk(p, &["rename", "--color-ink", "--color-text"]);
    std::fs::set_permissions(&css, std::fs::Permissions::from_mode(0o755)).unwrap();
    assert_ne!(code, 0, "{out} {err}");
    assert_eq!(read(p, "crunk.toml"), before);
    assert_eq!(read(p, "src/A.tsx"), TSX);
    assert_eq!(read(p, "styles/base/a.css"), CSS);
}

// frob:tests crates/crunk/src/extract.rs::ExtractToken
#[test]
fn extract_token_promotes_a_literal_and_rewrites_uses() {
    let dir = project();
    let p = dir.path();
    std::fs::write(p.join("styles/base/b.css"), ".b { color: #ABCDEF; border: 1px solid #abcdef; fill: url(#abcdef); content: \"#abcdef\"; }\n").unwrap();
    std::fs::write(
        p.join("src/B.tsx"),
        "export const B = () => <p style={{ color: '#abcdef' }} />;\n",
    )
    .unwrap();
    let (code, out, err) = crunk(
        p,
        &["extract-token", "#abcdef", "--name", "accent", "--json"],
    );
    assert_eq!(code, 0, "{out} {err}");
    let css = read(p, "styles/base/b.css");
    assert_eq!(css.matches("var(--color-accent)").count(), 2, "{css}");
    assert!(
        css.contains("url(#abcdef)") && css.contains("\"#abcdef\""),
        "{css}"
    );
    assert!(read(p, "crunk.toml").contains("accent = \"#abcdef\""));
    assert!(read(p, "styles/tokens.css").contains("--color-accent:"));
    let (code, out, err) = crunk(p, &["tokens", "--check"]);
    assert_eq!(code, 0, "{out} {err}");
    let (code, out, err) = crunk(p, &["check"]);
    assert_eq!(code, 0, "{out} {err}");
}

// frob:tests crates/crunk/src/extract.rs::ExtractToken
#[test]
fn extract_token_refuses_non_hex_and_existing_names() {
    let dir = project();
    let p = dir.path();
    refused(p, &["extract-token", "12px"], "E-EXTRACT-LITERAL");
    refused(
        p,
        &["extract-token", "#abcdef", "--name", "ink"],
        "E-EXTRACT-EXISTS",
    );
}

const BRAND: &str = "[brand]\r\nink = \"#222222\"\r\n\"ink-bg\" = \"#fafafa\"\r\n\r\n[brand.accent]\r\nvalue = \"{brand.ink}\"\r\ndescription = \"see {brand.ink}\"\r\n\r\n[brand.hover]\r\nvalue = \"{brand-ink}\"\r\nmodes = { dark = \"{brand.ink}\" }\r\n";
const SCENE: &str = "<!-- --brand-ink in a comment -->\n<div style=\"color: var(--brand-ink); background: var( --brand-ink-bg)\">--brand-ink-bgx</div>\n";
const BRAND_CSS: &str = ".c { color: var(--brand-ink); border-color: var(--brand-ink-bg); }\n";

/// A project with a custom token file, a scene, a stylesheet and a component that use it.
fn custom_project() -> tempfile::TempDir {
    let dir = project();
    let p = dir.path();
    std::fs::create_dir_all(p.join("design/tokens")).unwrap();
    std::fs::write(p.join("design/tokens/brand.toml"), BRAND).unwrap();
    std::fs::create_dir_all(p.join("design/scenes")).unwrap();
    std::fs::write(p.join("design/scenes/home.scene.html"), SCENE).unwrap();
    std::fs::write(p.join("styles/base/brand.css"), BRAND_CSS).unwrap();
    std::fs::write(
        p.join("design/components/b.component.toml"),
        "[[bindings]]\ntoken = \"--brand-ink\"\n",
    )
    .unwrap();
    let (code, out, err) = crunk(p, &["tokens"]);
    assert_eq!(code, 0, "{out} {err}");
    dir
}

// frob:tests crates/crunk/src/rename.rs::plan
// frob:tests crates/crunk/src/rename.rs::Rename
#[test]
fn custom_token_rename_rewrites_definition_aliases_and_every_reference() {
    let dir = custom_project();
    let p = dir.path();
    let (code, out, err) = crunk(p, &["rename", "--brand-ink", "--brand-text", "--json"]);
    assert_eq!(code, 0, "{out} {err}");

    let brand = read(p, "design/tokens/brand.toml");
    assert!(brand.contains("\r\ntext = \"#222222\"\r\n"), "{brand:?}");
    assert!(
        brand.contains("\"ink-bg\" = "),
        "partial word kept: {brand:?}"
    );
    assert!(brand.contains("value = \"{brand.text}\""), "{brand:?}");
    assert!(brand.contains("value = \"{brand-text}\""), "{brand:?}");
    assert!(brand.contains("dark = \"{brand.text}\""), "{brand:?}");
    assert!(
        brand.contains("description = \"see {brand.ink}\""),
        "prose kept: {brand:?}"
    );
    assert_eq!(
        brand.matches("\r\n").count(),
        brand.matches('\n').count(),
        "CRLF kept"
    );

    let css = read(p, "styles/base/brand.css");
    assert!(
        css.contains("var(--brand-text)") && css.contains("var(--brand-ink-bg)"),
        "{css}"
    );
    let scene = read(p, "design/scenes/home.scene.html");
    assert!(scene.contains("var(--brand-text)"), "{scene}");
    assert!(
        scene.contains("var( --brand-ink-bg)") && scene.contains("--brand-ink-bgx"),
        "{scene}"
    );
    assert!(
        scene.contains("<!-- --brand-ink in a comment -->"),
        "{scene}"
    );
    assert!(read(p, "design/components/b.component.toml").contains("--brand-text"));

    let (code, out, err) = crunk(p, &["tokens", "--check"]);
    assert_eq!(code, 0, "tokens --check: {out} {err}");
}

// frob:tests crates/crunk/src/rename.rs::plan
#[test]
fn custom_token_rename_refuses_collisions_and_leaving_the_group() {
    let dir = custom_project();
    let p = dir.path();
    refused(
        p,
        &["rename", "--brand-ink", "--brand-ink-bg"],
        "E-RENAME-EXISTS",
    );
    refused(
        p,
        &["rename", "--brand-ink", "--color-ink"],
        "E-RENAME-EXISTS",
    );
    refused(
        p,
        &["rename", "--brand-ink", "--other-ink"],
        "E-RENAME-KIND",
    );
    refused(p, &["rename", "--brand-ink", "--brand-"], "E-RENAME-KIND");
    assert_eq!(read(p, "design/tokens/brand.toml"), BRAND);
    assert_eq!(read(p, "design/scenes/home.scene.html"), SCENE);
}

// frob:tests crates/crunk/src/rename.rs::plan
#[test]
fn custom_token_rename_dry_run_writes_nothing() {
    let dir = custom_project();
    let p = dir.path();
    let (code, out, err) = crunk(
        p,
        &[
            "rename",
            "--brand-ink",
            "--brand-text",
            "--dry-run",
            "--json",
        ],
    );
    assert_eq!(code, 0, "{out} {err}");
    assert_eq!(json(&out)["data"]["dry_run"], true);
    assert_eq!(read(p, "design/tokens/brand.toml"), BRAND);
    assert_eq!(read(p, "design/scenes/home.scene.html"), SCENE);
    assert_eq!(read(p, "styles/base/brand.css"), BRAND_CSS);
}

// frob:tests crates/crunk/src/rename.rs::plan
#[test]
fn custom_token_rename_handles_dotted_keys() {
    let dir = project();
    let p = dir.path();
    std::fs::create_dir_all(p.join("design/tokens")).unwrap();
    std::fs::write(
        p.join("design/tokens/dots.toml"),
        "brand.ink = \"#222222\"\nbrand.edge = \"{brand.ink}\"\n",
    )
    .unwrap();
    let (code, out, err) = crunk(p, &["rename", "--brand-ink", "--brand-text"]);
    assert_eq!(code, 0, "{out} {err}");
    assert_eq!(
        read(p, "design/tokens/dots.toml"),
        "brand.text = \"#222222\"\nbrand.edge = \"{brand.text}\"\n"
    );
}

// frob:tests crates/crunk/src/rename.rs::plan
// frob:tests crates/crunk/src/rename.rs::PlanError.code
#[test]
fn derived_tokens_are_refused_with_a_specific_reason() {
    let dir = project();
    let p = dir.path();
    let spec = SPEC.replace("[org]", "[tailwind]\nalpha_channels = true\n\n[org]");
    std::fs::write(p.join("crunk.toml"), &spec).unwrap();
    let (code, out, err) = crunk(p, &["tokens"]);
    assert_eq!(code, 0, "tokens: {out} {err}");
    refused(p, &["rename", "--space-8", "--space-9"], "E-RENAME-DERIVED");
    refused(
        p,
        &["rename", "--font-size-16", "--font-size-17"],
        "E-RENAME-DERIVED",
    );
    refused(
        p,
        &["rename", "--font-family-base", "--font-family-body"],
        "E-RENAME-DERIVED",
    );
    refused(
        p,
        &["rename", "--color-ink-rgb", "--color-text-rgb"],
        "E-RENAME-DERIVED",
    );
    assert_eq!(read(p, "styles/base/a.css"), CSS);
    assert_eq!(read(p, "crunk.toml"), spec);
}

// frob:tests crates/crunk/src/rename.rs::plan
#[test]
fn font_stack_tokens_are_renamed_through_typography_stacks() {
    let dir = project();
    let p = dir.path();
    let spec = format!("{SPEC}\n[typography.stacks]\nmono = [\"Inter\"]\n");
    std::fs::write(p.join("crunk.toml"), spec).unwrap();
    std::fs::write(
        p.join("styles/base/m.css"),
        ".m { font-family: var(--font-family-mono); }\n",
    )
    .unwrap();
    let (code, out, err) = crunk(p, &["tokens"]);
    assert_eq!(code, 0, "{out} {err}");
    let (code, out, err) = crunk(p, &["rename", "--font-family-mono", "--font-family-code"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(read(p, "crunk.toml").contains("code = [\"Inter\"]"));
    assert!(read(p, "styles/base/m.css").contains("var(--font-family-code)"));
    assert!(read(p, "styles/tokens.css").contains("--font-family-code:"));
    let (code, out, err) = crunk(p, &["check"]);
    assert_eq!(code, 0, "check: {out} {err}");
}

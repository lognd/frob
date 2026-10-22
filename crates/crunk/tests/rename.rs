//! `crunk rename` and `crunk extract-token` end to end over CSS, TSX and component specs.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT

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

//! `crunk rename` and `crunk extract-token` end to end over CSS, TSX and component specs.

// frob:ticket 01M4CXRB2DX0B0BW7YJPAN1YXT
// frob:ticket 01M5H3RXWHYH6MRJX6B2M35H0F

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

use crate::common;

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
const SCREEN: &str = "id = \"home\"\nentry = \"/\"\n[[states]]\nid = \"default\"\n[[states]]\nid = \"hover\"\n[[states]]\nid = \"active\"\n[[states]]\nid = \"disabled\"\n[[states]]\nid = \"focus\"\n[[states]]\nid = \"loading\"\n[[states]]\nid = \"error\"\n[[states]]\nid = \"empty\"\n";
const COMPONENT: &str = "name = \"a\"\n[[states]]\nid = \"default\"\n[[states]]\nid = \"hover\"\n[[states]]\nid = \"active\"\n[[states]]\nid = \"disabled\"\n[[states]]\nid = \"focus\"\n[[states]]\nid = \"loading\"\n[[states]]\nid = \"error\"\n[[states]]\nid = \"empty\"\n[anatomy]\nnodes = [\"root\"]\n[[bindings]]\nnode = \"root\"\nproperty = \"color\"\ntoken = \"--color-ink\"\n";

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    std::fs::write(p.join("crunk.toml"), SPEC).unwrap();
    std::fs::create_dir_all(p.join("styles/base")).unwrap();
    std::fs::write(p.join("styles/base/a.css"), CSS).unwrap();
    common::append_states(&p.join("styles/base/states.css"));
    common::satisfy_roles(p);
    std::fs::create_dir_all(p.join("src")).unwrap();
    std::fs::write(p.join("src/A.tsx"), TSX).unwrap();
    std::fs::create_dir_all(p.join("design/components")).unwrap();
    std::fs::write(p.join("design/components/a.component.toml"), COMPONENT).unwrap();
    std::fs::create_dir_all(p.join("design/screens")).unwrap();
    std::fs::write(p.join("design/screens/home.screen.toml"), SCREEN).unwrap();
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

/// What to lock so the write of `styles/base/a.css` fails: a read-only directory refuses the atomic
/// temp file on Unix; a read-only file refuses the rename over it on Windows.
fn lock_target(p: &Path) -> std::path::PathBuf {
    if cfg!(unix) {
        p.join("styles/base")
    } else {
        p.join("styles/base/a.css")
    }
}

/// Lock or unlock `target` (see [`lock_target`]).
fn set_locked(target: &Path, locked: bool) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = if locked { 0o555 } else { 0o755 };
        std::fs::set_permissions(target, std::fs::Permissions::from_mode(mode)).unwrap();
    }
    #[cfg(not(unix))]
    {
        let mut perms = std::fs::metadata(target).unwrap().permissions();
        #[allow(clippy::permissions_set_readonly_false)]
        perms.set_readonly(locked);
        std::fs::set_permissions(target, perms).unwrap();
    }
}

/// Whether the lock on `target` is enforced (it is not under root on Unix).
fn lock_enforced(target: &Path) -> bool {
    !cfg!(unix) || std::fs::write(target.join("probe"), "").is_err()
}

// frob:tests crates/crunk/src/rewrite.rs::commit
// frob:tests crates/crunk/src/rename.rs::Rename
#[test]
fn rename_write_failure_leaves_every_file_untouched() {
    let dir = project();
    let p = dir.path();
    let before = read(p, "crunk.toml");
    let target = lock_target(p);
    set_locked(&target, true);
    if !lock_enforced(&target) {
        set_locked(&target, false);
        // The environment cannot refuse a write (root); say so instead of passing silently.
        eprintln!(
            "SKIPPED rename_write_failure_leaves_every_file_untouched: file permissions are not enforced here (running as root)"
        );
        return;
    }
    let (code, out, err) = crunk(p, &["rename", "--color-ink", "--color-text"]);
    set_locked(&target, false);
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
    // CRAFT012 wants 90 percent token coverage; the literals left in `b.css` need this to be outweighed.
    std::fs::write(
        p.join("styles/base/covered.css"),
        ".c { color: var(--color-ink); }\n".repeat(30),
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
    refused(p, &["extract-token", "banana"], "E-EXTRACT-LITERAL");
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
        "name = \"b\"\n[[states]]\nid = \"default\"\n[[states]]\nid = \"hover\"\n[[states]]\nid = \"active\"\n[[states]]\nid = \"disabled\"\n[[states]]\nid = \"focus\"\n[[states]]\nid = \"loading\"\n[[states]]\nid = \"error\"\n[[states]]\nid = \"empty\"\n[anatomy]\nnodes = [\"root\"]\n[[bindings]]\nnode = \"root\"\nproperty = \"color\"\ntoken = \"--brand-ink\"\n",
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
    common::satisfy_roles(p);
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

//! `crunk export css|tailwind|uss|csharp` end to end: print, `--out`, and the unknown target.

// frob:ticket 01M5XCVMQBQWARH7HT8RYHA0KY

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]
"##;

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), SPEC).expect("write spec");
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

// frob:tests crates/crunk/src/export.rs::ExportUss
#[test]
fn export_uss_prints_the_sheet_and_exits_zero() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["export", "uss", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let env: Value = serde_json::from_str(&out).unwrap();
    assert_eq!(env["data"]["target"], "uss");
    assert!(env["data"]["content"].as_str().unwrap().contains(":root"));
    let (_, via_tokens, _) = crunk(dir.path(), &["tokens", "--target", "uss", "--json"]);
    let via: Value = serde_json::from_str(&via_tokens).unwrap();
    assert_eq!(via["data"]["content"], env["data"]["content"]);
}

// frob:tests crates/crunk/src/export.rs::ExportCss
// frob:tests crates/crunk/src/export.rs::ExportTailwind
// frob:tests crates/crunk/src/export.rs::ExportCsharp
#[test]
fn every_target_verb_renders_and_out_writes_the_file() {
    let dir = project();
    for target in ["css", "tailwind", "csharp"] {
        let (code, out, err) = crunk(dir.path(), &["export", target, "--json"]);
        assert_eq!(code, 0, "{target}: {out} {err}");
    }
    let (code, out, _) = crunk(dir.path(), &["export", "uss", "--out", "t.uss", "--json"]);
    assert_eq!(code, 0, "{out}");
    assert!(dir.path().join("t.uss").is_file());
}

// frob:tests crates/crunk/src/export.rs::ExportUss
#[test]
fn an_unknown_target_exits_two_naming_the_valid_targets() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["export", "bogus"]);
    assert_eq!(code, 2, "{out} {err}");
    let text = format!("{out}{err}");
    for t in ["css", "tailwind", "uss", "csharp", "dtcg"] {
        assert!(text.contains(t), "missing {t}: {text}");
    }
}

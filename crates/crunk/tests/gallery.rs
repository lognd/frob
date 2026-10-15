//! `crunk gallery check`: refuses with a remedy in the default build, runs the rules with `gallery`.

// frob:ticket 01M43ATDG0RG5DP9PVFAKETJJH

use std::path::Path;

use gob_cli::run_for_test;
#[cfg(feature = "gallery")]
use serde_json::Value;

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

#[cfg(not(feature = "gallery"))]
// frob:tests crates/crunk/src/gallery.rs::GalleryCheck
#[test]
fn default_build_says_the_gallery_is_not_built_in_and_how_to_get_it() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), "").expect("empty config");
    let (code, out, err) = crunk(dir.path(), &["gallery", "check", "--json"]);
    assert_ne!(code, 0, "{out} {err}");
    let text = format!("{out}{err}");
    assert!(text.contains("E-GALLERY-NOT-BUILT"), "{text}");
    assert!(text.contains("--features gallery"), "{text}");
}

#[cfg(feature = "gallery")]
// frob:tests crates/crunk/src/gallery.rs::GalleryCheck
#[test]
fn feature_build_reports_unrendered_cells_as_errors() {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = include_str!("../../crunk-spec/tests/fixtures/valid/gallery005_routes.toml");
    let platform = "\n[[platform]]\nid = \"chromium-desktop\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 1280, height = 800 }\n";
    std::fs::write(dir.path().join("crunk.toml"), format!("{spec}{platform}")).expect("spec");
    std::fs::create_dir_all(dir.path().join("gallery")).expect("dir");
    std::fs::write(
        dir.path().join("gallery/manifest.json"),
        r#"{"version":3,"cells":[]}"#,
    )
    .expect("manifest");
    let (code, out, err) = crunk(dir.path(), &["gallery", "check", "--json"]);
    assert_eq!(code, 1, "{out} {err}");
    let env: Value = serde_json::from_str(&out).expect("json");
    assert!(env["data"]["errors"].as_u64().unwrap() > 0);
}

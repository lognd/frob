//! `crunk render --engine browser`: the not-built and Playwright-absent refusals (exit 2, with
//! the remedy, nothing written), the pure id and URL logic, and, where a browser exists, a real
//! run whose PNG is hashed and whose boxes share the solve output's node ids. The real run skips
//! with a logged reason when Playwright is absent (and fails instead when
//! `CRUNK_REQUIRE_PLAYWRIGHT` is set, as in CI).

// frob:ticket 01M5XCXVAR2WSR1H6X5X7ETR1R

use std::path::Path;

use crunk::render_browser::{file_url, solved_ids, unshared_ids};
use gob_cli::run_for_test;

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

/// One-screen project with a scene: a web platform and `landing.scene.html`.
fn project_in(dir: &Path) {
    let spec = include_str!("../../../crunk-spec/tests/fixtures/valid/gallery005_routes.toml");
    let platform = "\n[[platform]]\nid = \"chromium-desktop\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 1280, height = 800 }\n";
    std::fs::write(dir.join("crunk.toml"), format!("{spec}{platform}")).expect("spec");
    let scenes = dir.join("design/scenes");
    std::fs::create_dir_all(&scenes).expect("scenes dir");
    let scene = r#"<div data-id="root" style="width:400px;padding:8px"><p data-id="title" style="font-size:20px">Hello</p><button data-id="go" style="width:100px;height:40px">Go</button></div>"#;
    std::fs::write(scenes.join("landing.scene.html"), scene).expect("scene");
}

// frob:tests crates/crunk/src/render_browser.rs::solved_ids
#[test]
fn solved_ids_are_read_in_document_order_and_bad_documents_refused() {
    let json = r#"{"version":1,"nodes":[{"id":"root"},{"id":"title"},{"id":"go"}]}"#;
    assert_eq!(solved_ids(json).expect("ids"), ["root", "title", "go"]);
    assert!(solved_ids("not json").is_err());
    assert!(solved_ids(r#"{"version":1}"#).is_err());
    assert!(solved_ids(r#"{"nodes":[{"kind":"box"}]}"#).is_err());
}

// frob:tests crates/crunk/src/render_browser.rs::unshared_ids
#[test]
fn ids_the_browser_did_not_measure_are_named_in_solve_order() {
    let solved = ["root", "title", "go"].map(str::to_owned);
    let measured = ["go", "root"].map(str::to_owned);
    assert_eq!(unshared_ids(&solved, &measured), ["title"]);
    assert!(unshared_ids(&solved, &solved).is_empty());
}

// frob:tests crates/crunk/src/render_browser.rs::file_url
#[test]
fn file_urls_use_forward_slashes_and_a_third_slash_for_drive_letters() {
    let url = file_url(Path::new(r"C:\proj\design\a.scene.html"));
    assert_eq!(url, "file:///C:/proj/design/a.scene.html");
    assert!(file_url(Path::new("/proj/a.html")).starts_with("file:///proj"));
}

#[cfg(not(feature = "gallery"))]
// frob:tests crates/crunk/src/render_browser.rs::not_built
#[test]
fn browser_engine_without_gallery_exits_2_with_the_remedy_and_writes_nothing() {
    let dir = tempfile::tempdir().expect("tempdir");
    project_in(dir.path());
    let (code, out, err) = crunk(dir.path(), &["render", "--engine", "browser", "--json"]);
    assert_eq!(code, 2, "{out} {err}");
    let text = format!("{out}{err}");
    assert!(text.contains("E-GALLERY-NOT-BUILT"), "{text}");
    assert!(text.contains("--features gallery"), "{text}");
    assert!(!dir.path().join(".crunk").exists(), "nothing written");
}

/// Every file the run created under `root` (the project's own inputs excluded).
#[cfg(feature = "gallery")]
fn files_under(root: &Path) -> Vec<std::path::PathBuf> {
    let mut found = Vec::new();
    let mut todo = vec![root.join(".crunk")];
    while let Some(dir) = todo.pop() {
        for entry in std::fs::read_dir(&dir).into_iter().flatten().flatten() {
            let path = entry.path();
            if path.is_dir() {
                todo.push(path);
            } else {
                found.push(path);
            }
        }
    }
    found
}

#[cfg(feature = "gallery")]
fn init_logging() {
    let _ = tracing_subscriber::fmt()
        .with_test_writer()
        .with_max_level(tracing::Level::DEBUG)
        .try_init();
}

#[cfg(feature = "gallery")]
// frob:tests crates/crunk/src/render_browser.rs::playwright_missing
#[test]
fn browser_engine_without_playwright_exits_2_and_never_fakes_a_pass() {
    init_logging();
    // Inside the workspace so Node resolves `playwright` the way CI installs it.
    let target = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../target");
    std::fs::create_dir_all(&target).expect("target");
    let dir = tempfile::tempdir_in(&target).expect("tempdir");
    project_in(dir.path());
    let (code, out, err) = crunk(
        dir.path(),
        &[
            "render", "--engine", "browser", "--screen", "landing", "--json",
        ],
    );
    let text = format!("{out}{err}");
    if text.contains("E-PLAYWRIGHT-MISSING") {
        assert!(
            std::env::var_os("CRUNK_REQUIRE_PLAYWRIGHT").is_none(),
            "playwright required but missing: {text}"
        );
        assert_eq!(code, 2, "{text}");
        assert!(text.contains("npx playwright install"), "{text}");
        assert!(files_under(dir.path()).is_empty(), "no fake output");
        tracing::warn!("browser run skipped: playwright not available");
        return;
    }
    assert_eq!(code, 0, "{text}");
    let env: serde_json::Value = serde_json::from_str(&out).expect("json");
    let cells = env["data"]["cells"].as_array().expect("cells");
    assert!(!cells.is_empty(), "{text}");
    for c in cells {
        let read = |key: &str| std::fs::read(dir.path().join(c[key].as_str().expect(key)));
        let png = read("png").expect("png");
        assert!(png.starts_with(&[0x89, b'P', b'N', b'G']));
        assert_eq!(c["sha256"].as_str().expect("sha").len(), 64);
        let layout = String::from_utf8(read("path").expect("layout")).expect("utf8");
        let boxes: serde_json::Value =
            serde_json::from_slice(&read("boxes").expect("boxes")).expect("boxes json");
        let browser_ids: Vec<String> = boxes["nodes"]
            .as_array()
            .expect("nodes")
            .iter()
            .map(|n| n["id"].as_str().expect("id").to_owned())
            .collect();
        assert_eq!(solved_ids(&layout).expect("ids"), browser_ids);
    }
}

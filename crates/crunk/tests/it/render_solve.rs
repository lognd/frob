//! `crunk render --engine solve` and `crunk snapshot [--update]` over a scene corpus.

// frob:ticket 01M5XCWYMSEMEQPNZ7EFHHY9Z7

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const SCREENS: [&str; 4] = [
    "landing",
    "portal-dashboard",
    "portal-invoices-empty",
    "login-page",
];

fn scene(width: u32) -> String {
    format!(
        r#"<div data-id="root" style="width:{width}px;padding:8px"><p data-id="title" style="font-size:20px">Hello</p><button data-id="go" style="width:100px;height:40px">Go</button></div>"#
    )
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

/// A project with four screens on one web platform and a scene for each screen but `skip`.
fn project(skip: Option<&str>) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = include_str!("../../../crunk-spec/tests/fixtures/valid/gallery005_routes.toml");
    let platform = "\n[[platform]]\nid = \"chromium-desktop\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 1280, height = 800 }\n";
    std::fs::write(dir.path().join("crunk.toml"), format!("{spec}{platform}")).expect("spec");
    let scenes = dir.path().join("design/scenes");
    std::fs::create_dir_all(&scenes).expect("scenes dir");
    for screen in SCREENS.iter().filter(|s| Some(**s) != skip) {
        std::fs::write(scenes.join(format!("{screen}.scene.html")), scene(400)).expect("scene");
    }
    dir
}

fn data(out: &str) -> Value {
    let env: Value = serde_json::from_str(out).expect("json envelope");
    env["data"].clone()
}

fn baseline(dir: &Path, screen: &str, state: &str) -> std::path::PathBuf {
    dir.join(format!(
        "design/baselines/{screen}/{state}/chromium-desktop.layout.json"
    ))
}

// frob:tests crates/crunk/src/render.rs::Render
#[test]
fn render_solve_writes_one_json_per_cell() {
    let dir = project(None);
    let (code, out, err) = crunk(dir.path(), &["render", "--engine", "solve", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let cells = data(&out)["cells"].as_array().expect("cells").clone();
    assert_eq!(cells.len(), 4, "{out}");
    for c in &cells {
        let rel = c["path"].as_str().expect("path");
        let text = std::fs::read_to_string(dir.path().join(rel)).expect("written file");
        let doc: Value = serde_json::from_str(&text).expect("layout json");
        assert_eq!(doc["version"], 1);
        assert!(doc["nodes"].as_array().is_some_and(|n| n.len() >= 3));
    }
    assert!(
        dir.path()
            .join(".crunk/render/landing/default/chromium-desktop.layout.json")
            .is_file()
    );
}

// frob:tests crates/crunk/src/render.rs::Render
#[test]
fn render_screen_without_scene_exits_2_naming_it() {
    let dir = project(Some("login-page"));
    let (code, out, err) = crunk(dir.path(), &["render", "--json"]);
    assert_eq!(code, 2, "{out} {err}");
    assert!(format!("{out}{err}").contains("login-page"), "{out} {err}");
    assert!(
        !dir.path().join(".crunk/render").exists(),
        "nothing written"
    );
}

#[cfg(not(feature = "gallery"))]
// frob:tests crates/crunk/src/render.rs::Render
#[test]
fn render_browser_engine_without_gallery_says_not_built_with_remedy() {
    let dir = project(None);
    let (code, out, err) = crunk(dir.path(), &["render", "--engine", "browser", "--json"]);
    assert_ne!(code, 0, "{out} {err}");
    let text = format!("{out}{err}");
    assert!(text.contains("E-GALLERY-NOT-BUILT"), "{text}");
    assert!(text.contains("--features gallery"), "{text}");
}

// frob:tests crates/crunk/src/render.rs::Render
#[test]
fn render_output_is_identical_across_jobs() {
    let dir = project(None);
    let (c1, out1, e1) = crunk(dir.path(), &["render", "--jobs", "1", "--json"]);
    assert_eq!(c1, 0, "{out1} {e1}");
    let first = std::fs::read_to_string(
        dir.path()
            .join(".crunk/render/portal-dashboard/default/chromium-desktop.layout.json"),
    )
    .expect("file");
    let (c4, out4, e4) = crunk(dir.path(), &["render", "--jobs", "4", "--json"]);
    assert_eq!(c4, 0, "{out4} {e4}");
    assert_eq!(data(&out1), data(&out4));
    let again = std::fs::read_to_string(
        dir.path()
            .join(".crunk/render/portal-dashboard/default/chromium-desktop.layout.json"),
    )
    .expect("file");
    assert_eq!(first, again);
}

// frob:tests crates/crunk/src/snapshot.rs::Snapshot
#[test]
fn snapshot_without_update_fails_on_missing_baseline_naming_the_path() {
    let dir = project(None);
    let (code, out, err) = crunk(dir.path(), &["snapshot", "--json"]);
    assert_eq!(code, 1, "{out} {err}");
    // The reported path uses the platform separator; compare it separator-insensitively.
    let text = format!("{out}{err}")
        .replace("\\\\", "/")
        .replace('\\', "/");
    assert!(
        text.contains("design/baselines/landing/default/chromium-desktop.layout.json"),
        "{text}"
    );
    assert!(
        !dir.path().join("design/baselines").exists(),
        "nothing written"
    );
}

// frob:tests crates/crunk/src/snapshot.rs::Snapshot
#[test]
fn snapshot_update_rewrites_only_changed_baselines() {
    let dir = project(None);
    let (code, out, err) = crunk(dir.path(), &["snapshot", "--update", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(baseline(dir.path(), "landing", "default").is_file());
    let (code, out, err) = crunk(dir.path(), &["snapshot", "--json"]);
    assert_eq!(code, 0, "clean compare passes: {out} {err}");

    std::fs::write(
        dir.path().join("design/scenes/landing.scene.html"),
        scene(500),
    )
    .expect("edit scene");
    let (code, out, err) = crunk(dir.path(), &["snapshot", "--update", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let statuses: Vec<(String, String)> = data(&out)["cells"]
        .as_array()
        .expect("cells")
        .iter()
        .map(|c| {
            (
                c["screen"].as_str().unwrap().to_owned(),
                c["status"].as_str().unwrap().to_owned(),
            )
        })
        .collect();
    for (screen, status) in &statuses {
        let want = if screen == "landing" {
            "updated"
        } else {
            "match"
        };
        assert_eq!(status, want, "{screen}: {statuses:?}");
    }
}

// frob:tests crates/crunk/src/snapshot.rs::Snapshot
#[test]
fn snapshot_diff_lists_the_changed_node_and_its_delta() {
    let dir = project(None);
    let (code, out, err) = crunk(dir.path(), &["snapshot", "--update", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    std::fs::write(
        dir.path().join("design/scenes/landing.scene.html"),
        scene(500),
    )
    .expect("edit scene");
    let (code, out, err) = crunk(dir.path(), &["snapshot", "--json"]);
    assert_eq!(code, 1, "{out} {err}");
    let env: Value = serde_json::from_str(&out).expect("json");
    let cells = env["data"]["cells"].as_array().expect("cells");
    let landing = cells
        .iter()
        .find(|c| c["screen"] == "landing")
        .expect("landing");
    assert_eq!(landing["status"], "changed");
    let root = landing["diff"]
        .as_array()
        .expect("diff")
        .iter()
        .find(|d| d["id"] == "root")
        .expect("root node differs");
    let width = root["fields"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["field"] == "width")
        .expect("width delta");
    assert_eq!(width["delta"].as_f64(), Some(100.0));
}

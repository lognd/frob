//! Solver-browser parity tests: pure comparison, plus a real-browser run that skips when no
//! Playwright is installed (and fails instead when `CRUNK_REQUIRE_PLAYWRIGHT` is set, as in CI).

// frob:ticket 01M4CXRWBYR6P0WFRW5GBBJGEY

use std::path::{Path, PathBuf};

use crunk_gallery::boxes::{BoxesError, BrowserBoxes, capture_boxes};
use crunk_gallery::cells::enumerate;
use crunk_gallery::parity::{DEFAULT_TOLERANCE_PX, Mismatch, compare, parse_solver};
use crunk_gallery::render::{RenderError, RenderOptions};
use crunk_spec::parse_spec;

const SOLVER: &str = r#"{"version":1,"viewport_width":400,"viewport_height":300,"nodes":[
{"id":"root","parent":null,"kind":"box","x":0,"y":0,"width":400,"height":300},
{"id":"card","parent":"root","kind":"box","x":20,"y":30,"width":200,"height":100}]}"#;

fn browser(card_width: f64) -> BrowserBoxes {
    let doc = format!(
        r#"{{"version":1,"viewport_width":400,"viewport_height":300,"nodes":[
{{"id":"root","parent":null,"kind":"box","x":0,"y":0,"width":400,"height":300}},
{{"id":"card","parent":"root","kind":"box","x":20,"y":30,"width":{card_width},"height":100}}],
"focus_order":[],"missing":[]}}"#
    );
    serde_json::from_str(&doc).expect("browser doc")
}

// frob:tests crates/crunk-gallery/src/parity.rs::compare
#[test]
fn boxes_within_tolerance_are_clean() {
    let solver = parse_solver(SOLVER).expect("solver");
    let report = compare(&solver, &browser(200.75), DEFAULT_TOLERANCE_PX);
    assert!(report.is_clean(), "{}", report.summary());
    assert!(compare(&solver, &browser(201.0), DEFAULT_TOLERANCE_PX).is_clean());
}

// frob:tests crates/crunk-gallery/src/parity.rs::compare
// frob:tests crates/crunk-gallery/src/parity.rs::ParityReport.summary
#[test]
fn box_beyond_tolerance_fails_naming_the_node() {
    let solver = parse_solver(SOLVER).expect("solver");
    let report = compare(&solver, &browser(230.0), DEFAULT_TOLERANCE_PX);
    assert!(!report.is_clean());
    assert!(matches!(&report.mismatches[0], Mismatch::Differs { id, .. } if id == "card"));
    assert!(
        report.summary().contains("node `card`"),
        "{}",
        report.summary()
    );
}

// frob:tests crates/crunk-gallery/src/parity.rs::compare
#[test]
fn nodes_on_one_side_only_are_mismatches() {
    let solver = parse_solver(SOLVER).expect("solver");
    let mut b = browser(200.0);
    b.nodes.remove(1);
    let report = compare(&solver, &b, DEFAULT_TOLERANCE_PX);
    assert_eq!(
        report.mismatches,
        [Mismatch::MissingInBrowser { id: "card".into() }]
    );

    let mut b = browser(200.0);
    let mut extra = b.nodes[1].clone();
    extra.id = "stray".into();
    b.nodes.push(extra);
    let report = compare(&solver, &b, DEFAULT_TOLERANCE_PX);
    assert_eq!(
        report.mismatches,
        [Mismatch::MissingInSolver { id: "stray".into() }]
    );
}

// frob:tests crates/crunk-gallery/src/parity.rs::parse_solver
#[test]
fn unreadable_solver_document_is_an_error() {
    assert!(parse_solver("not json").is_err());
}

/// The workspace root, where `npm install playwright` puts the package in CI.
fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

// frob:tests crates/crunk-gallery/src/parity.rs::compare
#[test]
fn solver_and_real_browser_agree_on_an_absolute_page() {
    let dir = tempfile::tempdir().expect("dir");
    let page = dir.path().join("page.html");
    std::fs::write(
        &page,
        r#"<!doctype html><html><body style="margin:0">
<div data-id="root" style="position:absolute;left:0;top:0;width:400px;height:300px">
<div data-id="card" style="position:absolute;left:20px;top:30px;width:200px;height:100px"></div>
</div></body></html>"#,
    )
    .expect("page");
    let entry = format!("file://{}", gob_path::Shown::of(&page));
    let text = format!(
        "[project]\ncss_root = \".\"\ntokens_file = \"t.css\"\nroot_font_size = 10\n\n\
         [palette]\na = \"white\"\n\n[scales]\nspacing = [1]\nfont_sizes = [10]\n\n\
         [typography]\nfamilies = [\"x\"]\nweights = [400]\n\n[org]\nbuckets = [\"b\"]\n\n\
         [[platform]]\nid = \"desk\"\nrenderer = \"web\"\nengine = \"chromium\"\n\
         viewport = {{ width = 400, height = 300 }}\n\n\
         [[screen]]\nid = \"home\"\nentry = \"{entry}\"\n\n[[screen.states]]\nid = \"default\"\n",
    );
    let root = workspace_root();
    let spec = parse_spec(&text, &root.join("design.toml"), &root).expect("spec");
    let opts = RenderOptions::new(dir.path().join("art"));
    let ids = ["root", "card"].map(str::to_owned);
    let boxes = match capture_boxes(&spec, &enumerate(&spec)[0], &ids, &opts) {
        Ok(b) => b,
        Err(BoxesError::Render(RenderError::PlaywrightMissing { reason, remedy })) => {
            assert!(
                std::env::var_os("CRUNK_REQUIRE_PLAYWRIGHT").is_none(),
                "playwright required but missing: {reason}; {remedy}"
            );
            eprintln!("skipping browser parity: playwright not available ({reason})");
            return;
        }
        Err(e) => panic!("capture failed: {e}"),
    };
    let solver = parse_solver(SOLVER).expect("solver");
    let report = compare(&solver, &boxes, DEFAULT_TOLERANCE_PX);
    assert!(report.is_clean(), "{}", report.summary());
}

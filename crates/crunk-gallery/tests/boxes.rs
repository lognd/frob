//! Browser boxes tests: the capture is driven by fake Node programs (no real browser).

// frob:ticket 01M5XCXV74XZTCK4N56B46PAY4

#![cfg(unix)]

use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::time::Duration;

use crunk_gallery::boxes::{BoxesError, RUNS, capture_boxes, parse_boxes};
use crunk_gallery::cells::enumerate;
use crunk_gallery::render::{RenderError, RenderOptions};
use crunk_spec::{DesignSpec, parse_spec};
use gob_exec::Program;

const WEB: &str = "[[platform]]\nid = \"desk\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 800, height = 600 }\nbase_url = \"http://localhost:1\"\n";
const CMD: &str = "[[platform]]\nid = \"shot\"\nrenderer = \"command\"\ncommand = \"true\"\n";

const DOC: &str = r#"{"version":1,"viewport_width":800,"viewport_height":600,"nodes":[{"id":"a","parent":null,"kind":"box","x":0,"y":0,"width":800,"height":40},{"id":"b","parent":"a","kind":"text","x":0,"y":0,"width":0,"height":0,"hidden":true}],"focus_order":["a"],"missing":["c"]}"#;

fn spec(dir: &Path, platform: &str) -> DesignSpec {
    let text = format!(
        "[project]\ncss_root = \".\"\ntokens_file = \"t.css\"\nroot_font_size = 10\n\n\
         [palette]\na = \"white\"\n\n[scales]\nspacing = [1]\nfont_sizes = [10]\n\n\
         [typography]\nfamilies = [\"x\"]\nweights = [400]\n\n[org]\nbuckets = [\"b\"]\n\n\
         {platform}\n\n[[screen]]\nid = \"home\"\nentry = \"/\"\n\n\
         [[screen.states]]\nid = \"default\"\n"
    );
    parse_spec(&text, &dir.join("design.toml"), dir).expect("spec parses")
}

/// A fake `node`: probe succeeds, a capture runs `body` (shell) with `$OUT` the results path.
fn fake_node(dir: &Path, body: &str) -> Program {
    let fake = dir.join("fake-node");
    let out = dir.join("art/home__default__desk.boxes.json");
    std::fs::write(
        &fake,
        format!(
            "#!/bin/sh\nif [ \"$1\" = \"-e\" ]; then exit 0; fi\nOUT='{}'\n{body}\n",
            out.display()
        ),
    )
    .expect("script");
    std::fs::set_permissions(&fake, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    Program::Hook { path: fake }
}

fn run(body: &str, ids: &[&str], timeout: Duration) -> Result<(), BoxesError> {
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), WEB);
    let mut opts = RenderOptions::new(dir.path().join("art"));
    opts.node = fake_node(dir.path(), body);
    opts.timeout = timeout;
    let ids: Vec<String> = ids.iter().map(|s| (*s).to_owned()).collect();
    capture_boxes(&d, &enumerate(&d)[0], &ids, &opts).map(|_| ())
}

fn write_doc() -> String {
    format!("cat > \"$OUT\" <<'EOF'\n{DOC}\nEOF")
}

// frob:tests crates/crunk-gallery/src/boxes.rs::capture_boxes
#[test]
fn stable_capture_returns_solver_shaped_boxes_with_hidden_and_missing() {
    if !gob_exec::require_sh("stable_capture") {
        return;
    }
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), WEB);
    let mut opts = RenderOptions::new(dir.path().join("art"));
    opts.node = fake_node(dir.path(), &write_doc());
    let ids = ["a", "b", "c"].map(str::to_owned);
    let b = capture_boxes(&d, &enumerate(&d)[0], &ids, &opts).expect("capture");
    assert_eq!(b.nodes.len(), 2);
    assert!(b.nodes[1].hidden);
    assert_eq!(b.missing, ["c"]);
    assert_eq!(b.focus_order, ["a"]);
}

// frob:tests crates/crunk-gallery/src/boxes.rs::capture_boxes
#[test]
fn runs_differing_are_unstable() {
    if !gob_exec::require_sh("runs_differing") {
        return;
    }
    // Each run appends to a counter file and writes a different width.
    let body = "echo x >> \"$OUT.n\"; N=$(wc -l < \"$OUT.n\"); \
         printf '{\"version\":1,\"viewport_width\":%s,\"viewport_height\":1,\"nodes\":[],\"focus_order\":[],\"missing\":[]}' \"$N\" > \"$OUT\"";
    let err = run(body, &[], Duration::from_secs(20)).expect_err("unstable");
    assert!(matches!(err, BoxesError::Unstable { run: 2 }), "{err}");
    assert_eq!(RUNS, 3);
}

// frob:tests crates/crunk-gallery/src/boxes.rs::capture_boxes
#[test]
fn unsettled_page_is_refused() {
    if !gob_exec::require_sh("unsettled_page") {
        return;
    }
    let err = run(
        "echo 'unsettled: fonts are not ready' >&2; exit 1",
        &[],
        Duration::from_secs(20),
    )
    .expect_err("refused");
    assert!(matches!(err, BoxesError::Unsettled(_)), "{err}");
}

// frob:tests crates/crunk-gallery/src/boxes.rs::capture_boxes
#[test]
fn page_that_never_settles_is_killed_at_the_timeout() {
    if !gob_exec::require_sh("never_settles") {
        return;
    }
    let started = std::time::Instant::now();
    let err = run("sleep 30", &[], Duration::from_millis(300)).expect_err("timeout");
    assert!(started.elapsed() < Duration::from_secs(20));
    assert!(
        matches!(err, BoxesError::Render(RenderError::TimedOut(_))),
        "{err}"
    );
}

// frob:tests crates/crunk-gallery/src/boxes.rs::capture_boxes
#[test]
fn missing_playwright_is_typed_with_remedy_and_exit_2() {
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), WEB);
    let mut opts = RenderOptions::new(dir.path().join("art"));
    opts.node = Program::Tool {
        name: "crunk-no-such-node".to_owned(),
    };
    let err = capture_boxes(&d, &enumerate(&d)[0], &[], &opts).expect_err("missing");
    assert_eq!(err.exit_code(), 2);
    assert!(err.to_string().contains("playwright install"), "{err}");
}

// frob:tests crates/crunk-gallery/src/boxes.rs::capture_boxes
#[test]
fn command_platform_is_not_a_browser() {
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), CMD);
    let opts = RenderOptions::new(dir.path().join("art"));
    let err = capture_boxes(&d, &enumerate(&d)[0], &[], &opts).expect_err("not web");
    assert!(matches!(err, BoxesError::NotWeb { .. }), "{err}");
    assert_eq!(err.exit_code(), 1);
}

// frob:tests crates/crunk-gallery/src/boxes.rs::parse_boxes
#[test]
fn unaccounted_requested_id_is_a_bad_report() {
    let wanted = ["a", "zzz"].map(str::to_owned);
    let err = parse_boxes(DOC, &wanted).expect_err("lost id");
    assert!(matches!(err, BoxesError::BadReport(m) if m.contains("zzz")));
    assert!(parse_boxes(DOC, &["a", "c"].map(str::to_owned)).is_ok());
    assert!(parse_boxes("nope", &[]).is_err());
    assert!(parse_boxes(&DOC.replace("\"version\":1", "\"version\":2"), &[]).is_err());
}

//! Golden pins for the gallery: manifest v1-v3 normalized shapes and cell enumeration order.
//!
//! The Python crunk gallery source was unavailable, so these pin the current (reconstructed)
//! behaviour; they catch drift but do not prove parity with Python.

use std::path::Path;

use crunk_gallery::cells::{Cell, enumerate};
use crunk_gallery::manifest::{Entry, Manifest, Render, Status, Verdict, parse};
use crunk_spec::parse_spec;

const ZERO: &str = "0000000000000000000000000000000000000000000000000000000000000000";

/// Pull the golden cell list for `name` as `screen/state/platform` strings.
fn order(name: &str) -> Vec<String> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../crunk-spec/tests/fixtures/valid")
        .join(name);
    let text = std::fs::read_to_string(&path).expect("fixture");
    let spec = parse_spec(&text, &path, path.parent().expect("dir")).expect("parses");
    tracing::debug!(fixture = name, "golden enumeration");
    enumerate(&spec)
        .into_iter()
        .map(
            |Cell {
                 screen,
                 state,
                 platform,
             }| format!("{screen}/{state}/{platform}"),
        )
        .collect()
}

// frob:tests parse
#[test]
fn v1_normalizes_to_stateless_entry_with_verdict_only() {
    let doc = r#"{"version":1,"entries":[{"screen":"landing","platform":"chromium-desktop","image":"a.png","status":"approved"}]}"#;
    let got = parse(doc).expect("v1");
    let want = Manifest {
        version: 1,
        entries: vec![Entry {
            screen: "landing".into(),
            state: None,
            platform: "chromium-desktop".into(),
            render: Some(Render {
                path: "a.png".into(),
                sha256: None,
            }),
            verdict: Some(Verdict {
                status: Status::Approved,
                reviewer: None,
                reviewed_at: None,
                expires_at: None,
            }),
        }],
    };
    assert_eq!(got, want);
}

// frob:tests parse
#[test]
fn v2_normalizes_with_hash_and_status_verdict() {
    let doc = format!(
        r#"{{"version":2,"cells":[{{"screen":"s","state":"default","platform":"p","image":"a.png","sha256":"{ZERO}","status":"rejected"}}]}}"#
    );
    let got = parse(&doc).expect("v2");
    let e = &got.entries[0];
    assert_eq!(got.version, 2);
    assert_eq!(e.state.as_deref(), Some("default"));
    assert_eq!(
        e.render,
        Some(Render {
            path: "a.png".into(),
            sha256: Some(ZERO.into())
        })
    );
    assert_eq!(e.verdict.as_ref().map(|v| v.status), Some(Status::Rejected));
}

// frob:tests parse
#[test]
fn v3_normalizes_attributed_verdict() {
    let doc = format!(
        r#"{{"version":3,"cells":[{{"screen":"s","state":"x","platform":"p","render":{{"path":"a.png","sha256":"{ZERO}"}},"verdict":{{"status":"approved","reviewer":"ana","reviewed_at":"2026-10-01","expires_at":"2026-10-10"}}}}]}}"#
    );
    let got = parse(&doc).expect("v3");
    let v = got.entries[0].verdict.as_ref().expect("verdict");
    assert_eq!(v.reviewer.as_deref(), Some("ana"));
    assert_eq!(v.reviewed_at.as_deref(), Some("2026-10-01"));
    assert_eq!(v.expires_at.as_deref(), Some("2026-10-10"));
}

// frob:tests enumerate
#[test]
fn cell_order_is_golden_for_screens_fixture() {
    let got = order("screens_v1_1.toml");
    let want: Vec<String> = include_str!("../golden/screens_v1_1.cells.txt")
        .lines()
        .map(str::to_owned)
        .collect();
    assert_eq!(got, want);
}

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

#[cfg(feature = "gallery")]
fn gallery_project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = include_str!("../../crunk-spec/tests/fixtures/valid/gallery005_routes.toml");
    let platform = "\n[[platform]]\nid = \"chromium-desktop\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 1280, height = 800 }\n";
    std::fs::write(dir.path().join("crunk.toml"), format!("{spec}{platform}")).expect("spec");
    std::fs::create_dir_all(dir.path().join("gallery/renders")).expect("dir");
    dir
}

#[cfg(feature = "gallery")]
fn first_cell(dir: &Path) -> (String, String, String) {
    let (code, out, err) = crunk(dir, &["gallery", "enumerate", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let env: Value = serde_json::from_str(&out).expect("json");
    let c = &env["data"]["cells"][0];
    let s = |k: &str| c[k].as_str().expect("field").to_owned();
    (s("screen"), s("state"), s("platform"))
}

#[cfg(feature = "gallery")]
// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ
// frob:tests crates/crunk/src/gallery.rs::GalleryEnumerate
#[test]
fn enumerate_lists_the_cells_and_honours_filters() {
    let dir = gallery_project();
    let (screen, _, _) = first_cell(dir.path());
    let (code, out, _) = crunk(
        dir.path(),
        &["gallery", "enumerate", "--json", "--screen", &screen],
    );
    assert_eq!(code, 0, "{out}");
    let env: Value = serde_json::from_str(&out).expect("json");
    assert!(
        env["data"]["cells"]
            .as_array()
            .unwrap()
            .iter()
            .all(|c| c["screen"] == screen.as_str())
    );
}

#[cfg(feature = "gallery")]
// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ
// frob:tests crates/crunk/src/gallery.rs::GalleryCheck
#[test]
fn expired_approval_is_gallery003_and_the_report_matches_the_schema() {
    let dir = gallery_project();
    let (screen, state, platform) = first_cell(dir.path());
    let manifest = serde_json::json!({"version": 3, "cells": [{
        "screen": screen, "state": state, "platform": platform,
        "render": {"path": "x.png", "sha256": "a".repeat(64)},
        "verdict": {"status": "approved", "reviewer": "ada", "reviewed_at": "2020-01-01", "expires_at": "2020-02-01"}
    }]});
    std::fs::write(
        dir.path().join("gallery/manifest.json"),
        manifest.to_string(),
    )
    .expect("manifest");
    let (code, out, err) = crunk(dir.path(), &["gallery", "check", "--json"]);
    assert_eq!(code, 1, "{out} {err}");
    let env: Value = serde_json::from_str(&out).expect("json");
    let findings = env["data"]["findings"].as_array().expect("findings");
    assert!(
        findings.iter().any(|f| f["rule"] == "GALLERY003"),
        "{findings:?}"
    );
    let mut report = env["data"].clone();
    report["version"] = Value::from(1);
    let problems = crunk_gallery::schema::validate(crunk_gallery::schema::CHECK_V1, &report);
    assert!(problems.is_empty(), "{problems:?}");
}

#[cfg(feature = "gallery")]
fn http(port: u16, method: &str, target: &str, token: Option<&str>, body: &str) -> Option<String> {
    use std::io::{Read, Write};
    let mut s = std::net::TcpStream::connect(("127.0.0.1", port)).ok()?;
    let tok = token.map_or(String::new(), |t| format!("X-Triage-Token: {t}\r\n"));
    write!(s, "{method} {target} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{tok}Content-Length: {}\r\n\r\n{body}", body.len()).ok()?;
    let mut out = Vec::new();
    s.read_to_end(&mut out).ok()?;
    Some(String::from_utf8_lossy(&out).into_owned())
}

#[cfg(feature = "gallery")]
// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ
// frob:tests crates/crunk/src/gallery.rs::GalleryTriage
#[test]
fn triage_serves_a_contact_sheet_and_saves_verdicts_to_the_manifest() {
    let dir = gallery_project();
    let (screen, state, platform) = first_cell(dir.path());
    let png = format!("{screen}__{state}__{platform}.png");
    std::fs::write(dir.path().join("gallery/renders").join(&png), b"\x89PNG").expect("png");
    let manifest = serde_json::json!({"version": 3, "cells": [{
        "screen": screen, "state": state, "platform": platform,
        "render": {"path": png, "sha256": "a".repeat(64)}
    }]});
    std::fs::write(
        dir.path().join("gallery/manifest.json"),
        manifest.to_string(),
    )
    .expect("manifest");
    let port = {
        let l = std::net::TcpListener::bind(("127.0.0.1", 0)).expect("probe");
        l.local_addr().expect("addr").port()
    };
    let path = dir.path().to_path_buf();
    let p = port.to_string();
    let server = std::thread::spawn(move || {
        crunk(
            &path,
            &[
                "gallery",
                "triage",
                "--json",
                "--port",
                &p,
                "--reviewer",
                "ada",
            ],
        )
    });
    let mut page = None;
    for _ in 0..100 {
        page = http(port, "GET", "/", None, "");
        if page.is_some() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    let page = page.expect("server came up");
    let token = page
        .split("const T=\"")
        .nth(1)
        .and_then(|r| r.split('"').next())
        .expect("token")
        .to_owned();
    let v = http(
        port,
        "POST",
        "/verdict",
        Some(&token),
        r#"{"index":0,"status":"approved"}"#,
    )
    .expect("verdict");
    assert!(v.contains("200 OK"), "{v}");
    http(port, "POST", "/done", Some(&token), "").expect("done");
    let (code, out, err) = server.join().expect("join");
    assert_eq!(code, 0, "{out} {err}");
    let saved: Value = serde_json::from_str(
        &std::fs::read_to_string(dir.path().join("gallery/manifest.json")).expect("read"),
    )
    .expect("json");
    assert_eq!(saved["cells"][0]["verdict"]["status"], "approved");
    assert_eq!(saved["cells"][0]["verdict"]["reviewer"], "ada");
}

#[cfg(not(feature = "gallery"))]
// frob:ticket 01M43ATE06MNRNVJJ314KW24RJ
// frob:tests crates/crunk/src/gallery.rs::GalleryTriage
#[test]
fn default_build_refuses_triage_and_render_and_enumerate() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), "").expect("empty config");
    for verb in ["enumerate", "render", "triage"] {
        let (code, out, err) = crunk(dir.path(), &["gallery", verb, "--json"]);
        assert_ne!(code, 0, "{out} {err}");
        assert!(
            format!("{out}{err}").contains("E-GALLERY-NOT-BUILT"),
            "{verb}"
        );
    }
}

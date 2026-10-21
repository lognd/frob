//! Render tests: command and Playwright renderers, driven by fake programs (no real browser).

// frob:ticket 01M43ATDR7DWY5RZPB3QB3GE3K

#![cfg(unix)]

use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::time::Duration;

use crunk_gallery::cells::enumerate;
use crunk_gallery::render::{RenderError, RenderOptions, render};
use crunk_spec::{DesignSpec, parse_spec};
use gob_exec::Program;
use sha2::{Digest, Sha256};

const PNG_PRINTF: &str = r#"printf '\211PNG\r\n\032\nbody' > "$CRUNK_OUTPUT""#;

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

fn command_platform(cmd: &str) -> String {
    format!("[[platform]]\nid = \"shot\"\nrenderer = \"command\"\ncommand = '''{cmd}'''\n")
}

const WEB_PLATFORM: &str = "[[platform]]\nid = \"desk\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 800, height = 600 }\nbase_url = \"http://localhost:1\"\n";

// frob:tests render
#[test]
fn command_renderer_writes_hashed_png() {
    if !gob_exec::require_sh("command_renderer_writes_hashed_png") {
        return;
    }
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), &command_platform(PNG_PRINTF));
    let out = dir.path().join("art");
    let report = render(&d, &enumerate(&d), &RenderOptions::new(&out)).expect("render");
    assert_eq!(report.failed(), 0);
    let r = report.results[0].outcome.as_ref().expect("rendered");
    let bytes = std::fs::read(out.join(&r.path)).expect("png");
    assert_eq!(r.path, "home__default__shot.png");
    assert_eq!(r.sha256.len(), 64);
    let want = Sha256::digest(&bytes)
        .iter()
        .fold(String::new(), |acc, b| acc + &format!("{b:02x}"));
    assert_eq!(r.sha256, want);
    assert!(report.notice.is_none());
}

// frob:tests render
#[test]
fn hanging_command_is_killed_and_cell_fails() {
    if !gob_exec::require_sh("hanging_command_is_killed_and_cell_fails") {
        return;
    }
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), &command_platform("sleep 30"));
    let mut opts = RenderOptions::new(dir.path().join("art"));
    opts.timeout = Duration::from_millis(300);
    let started = std::time::Instant::now();
    let report = render(&d, &enumerate(&d), &opts).expect("render");
    assert!(started.elapsed() < Duration::from_secs(20));
    assert_eq!(report.failed(), 1);
    assert!(matches!(
        report.results[0].outcome,
        Err(RenderError::TimedOut(_))
    ));
}

// frob:tests render
#[test]
fn missing_playwright_names_install_command_and_exits_2() {
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), WEB_PLATFORM);
    let mut opts = RenderOptions::new(dir.path().join("art"));
    opts.node = Program::Tool {
        name: "crunk-no-such-node".to_owned(),
    };
    let err = render(&d, &enumerate(&d), &opts).expect_err("must fail");
    assert_eq!(err.exit_code(), 2);
    assert!(err.to_string().contains("npx playwright install"), "{err}");
}

// frob:tests render
#[test]
fn installed_playwright_writes_hashed_png() {
    if !gob_exec::require_sh("installed_playwright_writes_hashed_png") {
        return;
    }
    let dir = tempfile::tempdir().expect("dir");
    let fake = dir.path().join("fake-node");
    std::fs::write(
        &fake,
        format!("#!/bin/sh\nif [ \"$1\" = \"-e\" ]; then exit 0; fi\n{PNG_PRINTF}\n"),
    )
    .expect("script");
    std::fs::set_permissions(&fake, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    let d = spec(dir.path(), WEB_PLATFORM);
    let out = dir.path().join("art");
    let mut opts = RenderOptions::new(&out);
    opts.node = Program::Hook { path: fake };
    let report = render(&d, &enumerate(&d), &opts).expect("render");
    assert_eq!(report.failed(), 0, "{:?}", report.results[0].outcome);
    let r = report.results[0].outcome.as_ref().expect("rendered");
    assert!(out.join(&r.path).is_file());
    assert_eq!(r.sha256.len(), 64);
    assert!(report.notice.is_some());
}

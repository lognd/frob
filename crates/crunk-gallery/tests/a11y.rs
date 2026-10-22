//! T3 axe: findings from recorded axe JSON, and the Playwright scanner driven by a fake node.

// frob:ticket 01M4CXRZAE5N45BP0RJPT56WSN

use std::path::Path;

use crunk_gallery::a11y::{A11yError, AxeScanner, PlaywrightAxe, check_a11y, parse_axe};
use crunk_gallery::cells::{Cell, enumerate};
use crunk_gallery::render::RenderOptions;
use crunk_spec::{DesignSpec, Severity, parse_spec};

/// Recorded axe-core output for a page with a contrast violation on two nodes.
const RECORDED: &str = r##"{"violations":[{"id":"color-contrast","impact":"serious","help":"Elements must meet minimum color contrast","helpUrl":"https://dequeuniversity.com/rules/axe/4.10/color-contrast","nodes":[{"target":["#hero > h1"],"html":"<h1 id=\"t\">Hi</h1>"},{"target":[["iframe.ad","a.cta"]],"html":"<a class=\"cta\">Buy</a>"}]},{"id":"image-alt","impact":null,"help":"Images must have alternate text","nodes":[]}],"passes":[],"incomplete":[{"id":"aria-valid-attr-value","nodes":[]}]}"##;

fn web_platform() -> &'static str {
    "[[platform]]\nid = \"desk\"\nrenderer = \"web\"\nengine = \"chromium\"\nviewport = { width = 800, height = 600 }\nbase_url = \"http://localhost:1\"\n"
}

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

fn cell() -> Cell {
    Cell {
        screen: "home".to_owned(),
        state: "default".to_owned(),
        platform: "desk".to_owned(),
    }
}

/// A scanner that returns canned text, standing in for the browser.
struct Canned(&'static str);

impl AxeScanner for Canned {
    fn scan(&self, _spec: &DesignSpec, _cell: &Cell) -> Result<String, A11yError> {
        Ok(self.0.to_owned())
    }
}

// frob:tests check_a11y
#[test]
fn axe_violation_finding_carries_the_rule_id_and_node() {
    let dir = tempfile::tempdir().expect("dir");
    let d = spec(dir.path(), web_platform());
    let found = check_a11y(&d, &cell(), &Canned(RECORDED)).expect("scan");
    let first = &found[0];
    assert_eq!(first.rule, "color-contrast");
    assert_eq!(first.node.as_deref(), Some("#hero > h1"));
    assert_eq!(first.severity, Severity::Error);
    assert!(
        first.message.contains("color-contrast"),
        "{}",
        first.message
    );
    assert_eq!(first.screen, "home");
    assert_eq!(first.platform, "desk");
}

// frob:tests parse_axe
#[test]
fn nested_targets_join_and_nodeless_violations_survive_as_warnings() {
    let found = parse_axe(RECORDED, &cell()).expect("parse");
    assert_eq!(found.len(), 3);
    assert_eq!(found[1].node.as_deref(), Some("iframe.ad >> a.cta"));
    assert_eq!(found[2].rule, "image-alt");
    assert!(found[2].node.is_none());
    assert_eq!(found[2].severity, Severity::Warn);
}

// frob:tests parse_axe
#[test]
fn clean_report_is_empty_and_unreadable_reports_are_errors() {
    assert!(
        parse_axe(r#"{"violations":[]}"#, &cell())
            .expect("clean")
            .is_empty()
    );
    for bad in ["", "not json", "{}", r#"{"violations":[{"id":" "}]}"#] {
        assert!(
            matches!(parse_axe(bad, &cell()), Err(A11yError::BadReport(_))),
            "{bad:?}"
        );
    }
}

// frob:tests PlaywrightAxe.scan
#[test]
fn non_web_platform_cannot_be_scanned() {
    let dir = tempfile::tempdir().expect("dir");
    let platform = "[[platform]]\nid = \"desk\"\nrenderer = \"command\"\ncommand = \"true\"\n";
    let d = spec(dir.path(), platform);
    let scanner = PlaywrightAxe::new(RenderOptions::new(dir.path().join("art")));
    let err = check_a11y(&d, &cell(), &scanner).expect_err("not web");
    assert!(matches!(err, A11yError::NotWeb { .. }), "{err}");
}

#[cfg(unix)]
mod fake_node {
    use super::*;
    use gob_exec::Program;
    use std::os::unix::fs::PermissionsExt;

    /// A fake `node`: the probe (`-e`) passes; a run writes `body` to `$CRUNK_AXE_OUTPUT`.
    fn scanner(dir: &Path, body: &str, exit: i32) -> PlaywrightAxe {
        let fake = dir.join("fake-node");
        std::fs::write(
            &fake,
            format!(
                "#!/bin/sh\nif [ \"$1\" = \"-e\" ]; then exit 0; fi\ncat > \"$CRUNK_AXE_OUTPUT\" <<'EOF'\n{body}\nEOF\nexit {exit}\n"
            ),
        )
        .expect("script");
        std::fs::set_permissions(&fake, std::fs::Permissions::from_mode(0o755)).expect("chmod");
        let mut opts = RenderOptions::new(dir.join("art"));
        opts.node = Program::Hook { path: fake };
        PlaywrightAxe::new(opts)
    }

    // frob:tests PlaywrightAxe.scan
    #[test]
    fn playwright_scanner_reads_the_results_the_script_wrote() {
        if !gob_exec::require_sh("playwright_scanner_reads_the_results_the_script_wrote") {
            return;
        }
        let dir = tempfile::tempdir().expect("dir");
        let d = spec(dir.path(), web_platform());
        let s = scanner(dir.path(), RECORDED, 0);
        let found = check_a11y(&d, &enumerate(&d)[0], &s).expect("scan");
        assert_eq!(found[0].rule, "color-contrast");
        assert_eq!(found[0].node.as_deref(), Some("#hero > h1"));
        let req = std::fs::read_to_string(
            dir.path()
                .join("art/.crunk/home__default__desk.axe-request.json"),
        )
        .expect("request");
        assert!(req.contains("\"axe_output\""), "{req}");
        assert!(req.contains("\"output\":null"), "{req}");
    }

    // frob:tests PlaywrightAxe.scan
    #[test]
    fn failing_script_is_an_error_not_a_clean_scan() {
        if !gob_exec::require_sh("failing_script_is_an_error_not_a_clean_scan") {
            return;
        }
        let dir = tempfile::tempdir().expect("dir");
        let d = spec(dir.path(), web_platform());
        let s = scanner(dir.path(), "{\"violations\":[]}", 3);
        let err = check_a11y(&d, &cell(), &s).expect_err("must fail");
        assert!(matches!(err, A11yError::Render(_)), "{err}");
    }
}

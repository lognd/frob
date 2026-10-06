//! The three products over one shared TSX/CSS/HTML fixture repository (language-engines.md
//! section 5, code-model.md section 3, D96, D101): `frob check`, `grimble check` and `crunk check`
//! each run end to end, and each asserts what it computes from the shared web capabilities.

mod common;

use std::path::{Path, PathBuf};

use gob_cli::run_for_test;
use serde_json::Value;

/// The shared fixture repository, owned by the gob-symbols conformance corpus.
fn fixture() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../gob-symbols/tests/corpus/web/repo")
}

fn copy_tree(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).expect("mkdir");
    for e in std::fs::read_dir(from).expect("read_dir").flatten() {
        let dest = to.join(e.file_name());
        if e.path().is_dir() {
            copy_tree(&e.path(), &dest);
        } else {
            std::fs::copy(e.path(), dest).expect("copy");
        }
    }
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The fixture copied into a fresh git repository; `siblings` adds crunk's and grimble's config and the model.
fn repo(siblings: Option<&str>) -> tempfile::TempDir {
    let dir = common::git_repo();
    copy_tree(&fixture(), dir.path());
    write(dir.path(), "frob.toml", "");
    if let Some(model) = siblings {
        write(dir.path(), "crunk.toml", "");
        write(
            dir.path(),
            "grimble.toml",
            "[grimble]\nmodels = [\"design/web.grmb\"]\n",
        );
        write(dir.path(), "design/web.grmb", model);
    }
    dir
}

/// Two component nodes: `ui` owns the TSX components, `api` the TypeScript client; the CSS and HTML stay unowned.
const NODES: &str = "grimble = \"2\";\nmodule web;\n\nnode ui : trusted {\n  kind component;\n  owns \"src/components/**\";\n}\nnode api : trusted {\n  kind component;\n  owns \"src/api/**\";\n}\n";

fn json_of(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not JSON ({e}): {out}"))
}

fn product(cli: &gob_cli::Cli, dir: &Path) -> Value {
    let (code, out, err) = run_for_test(cli, &["check", "--json", "--fail-on", "none"], dir);
    assert_eq!(code, 0, "{out}\n{err}");
    let env = json_of(&out);
    assert_eq!(env["ok"], true, "{env}");
    env["data"].clone()
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn frob_check_reads_typescript_through_cov001_and_leaves_css_and_html_to_the_text_rules() {
    let dir = repo(None);
    let out = common::frob_command()
        .current_dir(dir.path())
        .args(["check", "--json", "--fail-on", "none"])
        .output()
        .expect("run frob");
    let text = String::from_utf8_lossy(&out.stdout).into_owned();
    let env = json_of(&text);
    assert_eq!(env["ok"], true, "{text}");
    // COV001 examines the public TS and TSX functions (F2): the call graph and import graph feed it.
    // `fetchUser` is called from `test("..")` in client.test.ts, a test unit (~97A7SXX), so it is reached.
    // frob:ticket 01M4828JB2S4JZY2QRB97A7SXX
    assert!(
        !text.contains("COV001 public function `src/api/client.ts::fetchUser`"),
        "fetchUser is called from a test unit and must be reached: {text}"
    );
    for symref in [
        "src/api/client.ts::label",
        "src/components/App.tsx::App",
        "src/components/Button.tsx::Button",
    ] {
        assert!(
            text.contains(&format!("COV001 public function `{symref}`")),
            "COV001 does not examine {symref}: {text}"
        );
    }
    // Every web file parsed completely: no PARSE finding, and neither CSS nor HTML is a COV001 subject.
    assert!(!text.contains("PARSE00"), "{text}");
    assert!(
        !text.contains("COV001 public function `src/styles"),
        "{text}"
    );
    assert!(!text.contains("COV001 public function `public/"), "{text}");
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn grimble_check_binds_the_tsx_components_and_reports_the_web_languages_it_read() {
    let dir = repo(Some(NODES));
    let doc = product(&grimble::cli(), dir.path());
    assert_eq!(doc["product"], "grimble");
    let bound = |identity: &str, entity: &str| {
        doc["bindings"]
            .as_array()
            .expect("bindings")
            .iter()
            .any(|b| b["identity"] == identity && b["entity"] == entity && b["status"] == "must")
    };
    assert!(bound("src/components/App.tsx::App", "node/ui"));
    assert!(bound("src/components/Button.tsx::Button", "node/ui"));
    assert!(bound("src/api/client.ts::fetchUser", "node/api"));
    let levels: Vec<(String, String)> = doc["fidelity"]
        .as_array()
        .expect("fidelity")
        .iter()
        .map(|f| {
            (
                f["language"].as_str().expect("language").to_owned(),
                f["level"].as_str().expect("level").to_owned(),
            )
        })
        .collect();
    for lang in ["typescript", "css", "html"] {
        assert!(
            levels.contains(&(lang.to_owned(), "F2".to_owned())),
            "{lang} missing from {levels:?}"
        );
    }
    // The CSS, HTML and manifest files no node owns are the SYS001 findings; no web rule exists yet.
    let unowned: Vec<&str> = doc["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "SYS001")
        .filter_map(|f| f["message"].as_str())
        .collect();
    assert!(
        unowned.iter().any(|m| m.contains("src/styles/app.css")),
        "{unowned:?}"
    );
    assert!(
        unowned.iter().any(|m| m.contains("public/index.html")),
        "{unowned:?}"
    );
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn crunk_check_runs_over_the_fixture_with_no_web_rule_yet() {
    let dir = repo(Some(NODES));
    let doc = product(&crunk::cli(), dir.path());
    assert_eq!(doc["product"], "crunk");
    assert_eq!(doc["schema_version"], "gob.sibling/1");
    assert_eq!(doc["findings"].as_array().expect("findings").len(), 0);
    assert_eq!(
        doc["rules"].as_array().expect("rules").len(),
        0,
        "crunk has no web rule yet; the first one replaces this assertion"
    );
}

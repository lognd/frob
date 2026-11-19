//! `crunk stamp` end to end: the recorded hash satisfies STATE007 until the screen or a token changes.

// frob:ticket 01M5EF4AEM3BG06QWEX6081JS9

use std::path::Path;

use gob_cli::run_for_test;

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111111"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[jsx]
globs = ["src/**/*.tsx"]
"##;

const SCREEN: &str =
    "# keep me\nid = \"home\"\nentry = \"/\"\nstatus = \"ready\"\n\n[[states]]\nid = \"default\"\n";
const SCREEN_PATH: &str = "design/screens/home.screen.toml";

fn project(screen: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), SPEC).unwrap();
    std::fs::create_dir_all(dir.path().join("design/screens")).unwrap();
    std::fs::write(dir.path().join(SCREEN_PATH), screen).unwrap();
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

/// Whether `crunk check` reports STATE007 for the project.
fn state007(dir: &Path) -> bool {
    let (_, out, _) = crunk(dir, &["check", "--json"]);
    let v: serde_json::Value = serde_json::from_str(&out).expect("check emits JSON");
    v["data"]["findings"]
        .as_array()
        .expect("findings array")
        .iter()
        .any(|f| f["rule"] == "STATE007")
}

// frob:tests crates/crunk/src/stamp.rs::Stamp.run
#[test]
fn a_stamped_screen_is_clean_until_its_content_changes() {
    let dir = project(SCREEN);
    assert!(state007(dir.path()), "an unstamped locked screen fires");
    let (code, out, err) = crunk(dir.path(), &["stamp"]);
    assert_eq!(code, 0, "{out}{err}");
    let text = std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap();
    assert!(text.starts_with("# keep me\n"), "{text}");
    assert!(text.contains("content_hash = \""), "{text}");
    assert!(!state007(dir.path()), "stamped screen is clean");
    let edited = text.replace("[[states]]", "headings = [\"Hi\"]\n\n[[states]]");
    std::fs::write(dir.path().join(SCREEN_PATH), edited).unwrap();
    assert!(state007(dir.path()), "an edited screen goes stale");
    assert_eq!(crunk(dir.path(), &["stamp"]).0, 0);
    assert!(!state007(dir.path()), "restamped screen is clean");
}

// frob:tests crates/crunk/src/stamp.rs::Stamp.run
#[test]
fn a_token_change_stales_the_stamp() {
    let dir = project(SCREEN);
    assert_eq!(crunk(dir.path(), &["stamp"]).0, 0);
    assert!(!state007(dir.path()));
    std::fs::write(
        dir.path().join("crunk.toml"),
        SPEC.replace("#111111", "#222222"),
    )
    .unwrap();
    assert!(state007(dir.path()), "a token value change goes stale");
}

// frob:tests crates/crunk/src/stamp.rs::Stamp.run
#[test]
fn dry_run_and_draft_screens_write_nothing() {
    let draft = SCREEN.replace("ready", "draft");
    let dir = project(&draft);
    let (code, out, _) = crunk(dir.path(), &["stamp"]);
    assert_eq!(code, 0, "{out}");
    assert_eq!(
        std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap(),
        draft
    );
}

// frob:tests crates/crunk/src/stamp.rs::Stamp.run
#[test]
fn dry_run_writes_nothing() {
    let dir = project(SCREEN);
    let (code, _, _) = crunk(dir.path(), &["stamp", "--dry-run"]);
    assert_eq!(code, 0);
    assert_eq!(
        std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap(),
        SCREEN
    );
}

// frob:tests crates/crunk/src/stamp.rs::Stamp.run
#[test]
fn an_unknown_id_is_refused_and_nothing_is_written() {
    let dir = project(SCREEN);
    let (code, out, err) = crunk(dir.path(), &["stamp", "nope"]);
    assert_eq!(code, 2, "{out}{err}");
    assert_eq!(
        std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap(),
        SCREEN
    );
}

// frob:tests crates/crunk/src/stamp.rs::set_content_hash
#[test]
fn set_content_hash_keeps_comments_and_crlf_and_replaces_in_place() {
    let out = crunk::stamp::set_content_hash(
        "# c\r\nid = \"a\"\r\ncontent_hash = \"old\" # why\r\n",
        "new",
    )
    .unwrap();
    assert_eq!(out, "# c\r\nid = \"a\"\r\ncontent_hash = \"new\" # why\r\n");
    assert!(crunk::stamp::set_content_hash("= =", "x").is_err());
}

// frob:tests crates/crunk/src/stamp.rs::StampError.code
#[test]
fn stamp_errors_carry_their_stable_refusal_codes() {
    use crunk::stamp::StampError;
    assert_eq!(StampError::Load("x".into()).code(), "E-STAMP-LOAD");
    assert_eq!(StampError::Unknown("x".into()).code(), "E-STAMP-UNKNOWN");
    assert_eq!(
        StampError::Edit("f".into(), "x".into()).code(),
        "E-STAMP-EDIT"
    );
    assert_eq!(
        StampError::Write("f".into(), "x".into()).code(),
        "E-STAMP-WRITE"
    );
}

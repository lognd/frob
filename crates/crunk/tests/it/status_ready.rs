//! `crunk status ID ready` end to end: the handoff gate refuses with every reason and records nothing, or records the hash.

// frob:ticket 01M5XCZ18GTA7MKKF4Z0MD95W3
// frob:ticket 01M7TCKMBT95HKXRACWVH5VVDY

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

const SCREEN: &str = "id = \"home\"\nentry = \"/\"\nstatus = \"draft\"\nsources = [\"src/Home.tsx\"]\n\n[[states]]\nid = \"default\"\n";
const SCREEN_PATH: &str = "design/screens/home.screen.toml";
const BLOCKING: &str = "[[comment]]\nid = \"c1\"\nscreen = \"home\"\nanchor = \"default\"\nbody = \"fix spacing\"\nblocking = true\n";

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

/// A project with exported tokens, a source file and a draft screen.
fn project(screen: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    std::fs::write(p.join("crunk.toml"), SPEC).unwrap();
    std::fs::create_dir_all(p.join("design/screens")).unwrap();
    std::fs::create_dir_all(p.join("src")).unwrap();
    std::fs::write(p.join("src/Home.tsx"), "export const Home = () => null;\n").unwrap();
    std::fs::write(p.join(SCREEN_PATH), screen).unwrap();
    let (code, out, err) = crunk(p, &["tokens"]);
    assert_eq!(code, 0, "{out}{err}");
    dir
}

fn lock(dir: &Path) -> String {
    std::fs::read_to_string(dir.join("crunk.lock")).unwrap_or_default()
}

fn comment(dir: &Path, text: &str) {
    std::fs::create_dir_all(dir.join("design/review")).unwrap();
    std::fs::write(dir.join("design/review/home.toml"), text).unwrap();
}

fn ready(dir: &Path) -> (i32, String) {
    let (code, out, err) = crunk(dir, &["status", "home", "ready"]);
    (code, format!("{out}{err}"))
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn an_open_blocking_comment_refuses_and_records_nothing() {
    let dir = project(SCREEN);
    comment(dir.path(), BLOCKING);
    let (code, text) = ready(dir.path());
    assert_eq!(code, 3, "{text}");
    assert!(text.contains("c1"), "{text}");
    assert!(!lock(dir.path()).contains("[[ready]]"));
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn a_stale_export_refuses() {
    let dir = project(SCREEN);
    std::fs::write(
        dir.path().join("crunk.toml"),
        SPEC.replace("#111111", "#222222"),
    )
    .unwrap();
    let (code, text) = ready(dir.path());
    assert_eq!(code, 3, "{text}");
    assert!(text.contains("tokens.css"), "{text}");
    assert!(!lock(dir.path()).contains("[[ready]]"));
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn a_missing_code_mapping_refuses() {
    let dir = project(&SCREEN.replace("sources = [\"src/Home.tsx\"]\n", ""));
    let (code, text) = ready(dir.path());
    assert_eq!(code, 3, "{text}");
    assert!(text.contains("code"), "{text}");
    assert!(!lock(dir.path()).contains("[[ready]]"));
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn an_unknown_id_exits_two() {
    let dir = project(SCREEN);
    let (code, out, err) = crunk(dir.path(), &["status", "nope", "ready"]);
    assert_eq!(code, 2, "{out}{err}");
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn green_records_the_hash_and_a_later_change_marks_it_changed() {
    let dir = project(SCREEN);
    let (code, text) = ready(dir.path());
    assert_eq!(code, 0, "{text}");
    assert!(
        lock(dir.path()).contains("[[ready]]"),
        "{}",
        lock(dir.path())
    );
    let file = std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap();
    assert!(file.contains("status = \"ready\""), "{file}");
    let edited = file.replace("[[states]]", "headings = [\"Hi\"]\n\n[[states]]");
    std::fs::write(dir.path().join(SCREEN_PATH), edited).unwrap();
    let (code, out, err) = crunk(dir.path(), &["status", "home"]);
    assert_eq!(code, 0, "{out}{err}");
    assert!(out.contains("changed"), "{out}");
    let file = std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap();
    assert!(file.contains("status = \"changed\""), "{file}");
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn running_ready_twice_is_idempotent_and_writes_no_review() {
    let dir = project(SCREEN);
    assert_eq!(ready(dir.path()).0, 0);
    let (lock1, file1) = (
        lock(dir.path()),
        std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap(),
    );
    assert_eq!(ready(dir.path()).0, 0);
    assert_eq!(lock(dir.path()), lock1);
    assert_eq!(
        std::fs::read_to_string(dir.path().join(SCREEN_PATH)).unwrap(),
        file1
    );
    assert!(!lock1.contains("[[review]]"), "{lock1}");
}

// frob:tests crates/crunk/src/status.rs::Status.run
#[test]
fn a_comment_on_a_deleted_state_is_orphaned_and_does_not_block() {
    let dir = project(SCREEN);
    comment(dir.path(), &BLOCKING.replace("\"default\"", "\"gone\""));
    let (code, text) = ready(dir.path());
    assert_eq!(code, 0, "{text}");
    assert!(text.contains("c1"), "orphan reported: {text}");
}

// frob:tests crates/crunk/src/status.rs::StatusError.code
#[test]
fn status_errors_carry_their_stable_refusal_codes() {
    use crunk::status::StatusError;
    assert_eq!(StatusError::Load("x".into()).code(), "E-STATUS-LOAD");
    assert_eq!(StatusError::Unknown("x".into()).code(), "E-STATUS-UNKNOWN");
    assert_eq!(
        StatusError::NotReady {
            id: "home".into(),
            reasons: vec!["x".into()]
        }
        .code(),
        "E-STATUS-NOT-READY"
    );
    assert_eq!(
        StatusError::Write("f".into(), "x".into()).code(),
        "E-STATUS-WRITE"
    );
}

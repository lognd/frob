//! `crunk new` end to end: skeleton scaffolding, refusal on collision, and bad input writes nothing.

// frob:ticket 01M5H8MMN5PXGJG2XGS76STB57

use std::path::{Path, PathBuf};

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

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), SPEC).unwrap();
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn design(dir: &Path, sub: &str, file: &str) -> PathBuf {
    dir.join("design").join(sub).join(file)
}

/// Every file under `dir`, sorted, to compare before and after a refusal.
fn tree(dir: &Path) -> Vec<String> {
    fn walk(d: &Path, out: &mut Vec<String>) {
        for e in std::fs::read_dir(d).unwrap() {
            let p = e.unwrap().path();
            out.push(gob_path::Shown::of(&p).as_str().to_owned());
            if p.is_dir() {
                walk(&p, out);
            }
        }
    }
    let mut out = Vec::new();
    walk(dir, &mut out);
    out.sort();
    out
}

// frob:tests crates/crunk/src/new.rs::New.run
// frob:tests crates/crunk/src/new.rs::NewData.lines
#[test]
fn scaffolds_each_kind_and_screen_and_component_validate() {
    let dir = project();
    for (kind, sub, file) in [
        ("component", "components", "card.component.toml"),
        ("screen", "screens", "home.screen.toml"),
        ("flow", "flows", "signup.flow.toml"),
        ("token", "tokens", "brand.toml"),
    ] {
        let name = file.split('.').next().unwrap();
        let (exit, out, err) = crunk(dir.path(), &["new", kind, name]);
        assert_eq!(exit, 0, "{kind}: {out} {err}");
        let path = design(dir.path(), sub, file);
        let text = std::fs::read_to_string(&path).expect("file written");
        assert!(text.contains(name), "{kind}: {text}");
        text.parse::<toml_edit::DocumentMut>().expect("valid toml");
    }
    let text = std::fs::read_to_string(design(dir.path(), "screens", "home.screen.toml")).unwrap();
    crunk_spec::parse_screen_file(&text).expect("screen skeleton validates");
    let text =
        std::fs::read_to_string(design(dir.path(), "components", "card.component.toml")).unwrap();
    crunk_spec::parse_component_file(&text).expect("component skeleton validates");
    let (_, out, err) = crunk(dir.path(), &["check"]);
    let v: serde_json::Value = serde_json::from_str(&out).unwrap();
    let mine = v["data"]["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| {
            f["severity"] == "error" && f["file"].as_str().is_some_and(|p| p.starts_with("design"))
        });
    assert_eq!(mine.count(), 0, "{out} {err}");
}

// frob:tests crates/crunk/src/new.rs::New.run
#[test]
fn refuses_to_overwrite_an_existing_target() {
    let dir = project();
    let path = design(dir.path(), "screens", "home.screen.toml");
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(&path, "keep me\n").unwrap();
    let before = tree(dir.path());
    let (exit, out, err) = crunk(dir.path(), &["new", "screen", "home"]);
    assert_ne!(exit, 0);
    assert!(
        out.contains("E-NEW-EXISTS") || err.contains("E-NEW-EXISTS"),
        "{out} {err}"
    );
    assert_eq!(std::fs::read_to_string(&path).unwrap(), "keep me\n");
    assert_eq!(tree(dir.path()), before);
}

// frob:tests crates/crunk/src/new.rs::New.run
// frob:tests crates/crunk/src/new.rs::NewError.code
#[test]
fn invalid_name_or_missing_from_writes_nothing() {
    let dir = project();
    let before = tree(dir.path());
    for name in ["../evil", "Upper", "a/b", "9lives", "a.b", ""] {
        let (exit, out, err) = crunk(dir.path(), &["new", "screen", name]);
        assert_ne!(exit, 0, "{name:?}");
        assert!(
            out.contains("E-NEW-NAME") || err.contains("E-NEW-NAME"),
            "{name:?}: {out} {err}"
        );
    }
    let (exit, out, err) = crunk(
        dir.path(),
        &["new", "component", "card", "--from", "nope.toml"],
    );
    assert_ne!(exit, 0);
    assert!(
        out.contains("E-NEW-FROM") || err.contains("E-NEW-FROM"),
        "{out} {err}"
    );
    assert_eq!(tree(dir.path()), before);
}

// frob:tests crates/crunk/src/new.rs::New.run
#[test]
fn from_copies_renames_and_drops_review_state() {
    let dir = project();
    let src = dir.path().join("src.screen.toml");
    std::fs::write(
        &src,
        "# keep\r\nid = \"old\"\r\nentry = \"x\"\r\nstatus = \"ready\"\r\ncontent_hash = \"abc\"\r\n\r\n[[states]]\r\nid = \"default\"\r\n",
    )
    .unwrap();
    let (exit, out, err) = crunk(
        dir.path(),
        &["new", "screen", "fresh", "--from", "src.screen.toml"],
    );
    assert_eq!(exit, 0, "{out} {err}");
    let text = std::fs::read_to_string(design(dir.path(), "screens", "fresh.screen.toml")).unwrap();
    assert!(
        text.contains("id = \"fresh\"") && text.contains("# keep"),
        "{text}"
    );
    assert!(
        !text.contains("status") && !text.contains("content_hash"),
        "{text}"
    );
    assert!(
        text.contains("\r\n") && !text.replace("\r\n", "").contains('\n'),
        "{text:?}"
    );
    crunk_spec::parse_screen_file(&text).unwrap();
}

// frob:tests crates/crunk/src/new.rs::New.run
#[test]
fn dry_run_writes_nothing() {
    let dir = project();
    let before = tree(dir.path());
    let (exit, out, err) = crunk(dir.path(), &["new", "flow", "signup", "--dry-run"]);
    assert_eq!(exit, 0, "{out} {err}");
    assert_eq!(tree(dir.path()), before);
}

// frob:ticket 01M5JHRGCES4BCHCNBCB7WWZ9F
// frob:tests crates/crunk/src/new.rs::New.run
#[test]
fn new_flow_output_passes_the_flow_validator() {
    let dir = project();
    let (exit, out, err) = crunk(dir.path(), &["new", "flow", "signup"]);
    assert_eq!(exit, 0, "{out} {err}");
    let text = std::fs::read_to_string(design(dir.path(), "flows", "signup.flow.toml")).unwrap();
    let flow = crunk_spec::parse_flow_file(&text).expect("skeleton validates");
    assert_eq!(flow.name, "signup");
}

// frob:ticket 01M5JHRGCES4BCHCNBCB7WWZ9F
// frob:tests crates/crunk/src/new.rs::New.run
#[test]
fn from_a_flow_with_a_dangling_edge_is_refused_with_code_and_location() {
    let dir = project();
    let src = dir.path().join("bad.flow.toml");
    std::fs::write(
        &src,
        "name = \"old\"\nnodes = [\"a:x\"]\n[[edges]]\nfrom = \"a:x\"\nto = \"b:y\"\ntrigger = \"click\"\n",
    )
    .unwrap();
    let before = tree(dir.path());
    let (exit, out, err) = crunk(
        dir.path(),
        &["new", "flow", "fresh", "--from", "bad.flow.toml"],
    );
    assert_ne!(exit, 0, "{out} {err}");
    let all = format!("{out}{err}");
    assert!(
        all.contains("E-FLOW-DANGLING") && all.contains("edges[0].to"),
        "{all}"
    );
    assert_eq!(tree(dir.path()), before);
}

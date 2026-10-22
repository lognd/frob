//! Library-level integration scenarios INT-01..12, re-expressed against the Rust crunk.
//!
//! The Python originals (`tests/integration/test_int_NN_*.py`) are not in this repository; only the
//! file names survive in the parity index, and the fixtures were inline in the Python bodies. Each
//! test here is therefore a fresh check of the behaviour the Python file name describes, NOT a
//! line-by-line port. INT-04 is the exception: its golden `tokens.css` was captured verbatim.
//! INT-09 (result cache) is dropped in the mapping table because the Rust crunk has no cache.

// frob:ticket 01M43AVKZWSTQRGWR6YPXH7THX

use std::path::{Path, PathBuf};

use gob_cli::run_for_test;
use serde_json::Value;

fn parity_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/crunk-parity")
}

/// Run crunk in `cwd`; returns `(exit, stdout)`.
fn crunk(cwd: &Path, args: &[&str]) -> (i32, String) {
    let (code, out, _err) = run_for_test(&crunk::cli(), args, cwd);
    (code, out)
}

/// A scaffolded project in a fresh temp dir.
fn scaffold() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    assert_eq!(crunk(dir.path(), &["init"]).0, 0, "init must succeed");
    dir
}

fn copy_tree(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).expect("mkdir");
    for entry in std::fs::read_dir(from).expect("read_dir").flatten() {
        let (src, dst) = (entry.path(), to.join(entry.file_name()));
        if src.is_dir() {
            copy_tree(&src, &dst);
        } else {
            std::fs::copy(&src, &dst).expect("copy");
        }
    }
}

/// The captured `int04_default` project in a fresh temp dir.
fn int04_project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    copy_tree(
        &parity_root().join("fixtures/static/int04_default"),
        dir.path(),
    );
    dir
}

fn envelope(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("stdout is not an envelope: {e}"))
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_01_spec_toml() {
    let dir = int04_project();
    let (code, out) = crunk(dir.path(), &["doctor", "--json"]);
    assert_eq!(code, 0, "a valid crunk.toml loads: {out}");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_02_ingest_fs() {
    let dir = scaffold();
    let css = dir
        .path()
        .join("styles")
        .join("components")
        .join("planted.css");
    std::fs::write(&css, ".planted { color: #123456; }\n").expect("write css");
    let (code, out) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 1, "the planted off-palette colour fails the gate");
    assert!(
        out.contains("planted.css"),
        "the finding names the ingested file: {out}"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_03_rules_full_catalog() {
    let dir = int04_project();
    let (_, out) = crunk(dir.path(), &["check", "--json"]);
    let doc = envelope(&out);
    let ran: Vec<&str> = doc["data"]["rules"]
        .as_array()
        .expect("rules")
        .iter()
        .filter_map(|r| r["rule"].as_str())
        .collect();
    for id in [
        "COLOR001", "SPACE001", "TYPE001", "LAYER001", "ORG001", "TW001",
    ] {
        assert!(
            ran.contains(&id),
            "{id} is part of the evaluated catalog: {ran:?}"
        );
    }
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_04_tokens_spec() {
    let dir = int04_project();
    let (code, out) = crunk(dir.path(), &["tokens", "--target", "css"]);
    assert_eq!(code, 0, "tokens preview succeeds: {out}");
    let golden = std::fs::read_to_string(parity_root().join("expected/int-04-golden/tokens.css"))
        .expect("golden");
    let want = golden.trim().lines().map(str::trim).collect::<Vec<_>>();
    for line in want.iter().filter(|l| l.starts_with("--")) {
        assert!(
            out.contains(line),
            "golden declaration missing from tokens output: {line}"
        );
    }
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_05_fixes_pipeline() {
    let dir = scaffold();
    let (dry, _) = crunk(dir.path(), &["fix", "--dry-run", "--json"]);
    let (fix, _) = crunk(dir.path(), &["fix", "--json"]);
    let (check, out) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(
        (dry, fix),
        (0, 0),
        "fix on a clean scaffold has nothing to do"
    );
    assert_eq!(check, 0, "and the tree still passes: {out}");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_06_report() {
    let dir = scaffold();
    let (_, out) = crunk(dir.path(), &["check", "--json"]);
    let doc = envelope(&out);
    assert!(
        doc.get("verb").is_some() || doc.get("data").is_some(),
        "envelope shape: {out}"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_07_shell_wiring() {
    let dir = scaffold();
    let (code, out) = crunk(dir.path(), &["doctor", "--json"]);
    assert_eq!(code, 0, "doctor reports on a scaffolded project: {out}");
    let (bad, _) = crunk(dir.path(), &["no-such-verb"]);
    assert_eq!(bad, 2, "an unknown verb is a usage error");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_08_scaffold() {
    let dir = scaffold();
    assert!(
        dir.path().join("crunk.toml").is_file(),
        "init writes crunk.toml"
    );
    assert!(
        dir.path().join("styles").is_dir(),
        "init writes the css root"
    );
    assert_ne!(
        crunk(dir.path(), &["init"]).0,
        0,
        "re-init without force is refused"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_10_query() {
    let dir = scaffold();
    let (code, out) = crunk(dir.path(), &["query", "unused", "--json"]);
    assert_eq!(code, 0, "query unused answers on a scaffold: {out}");
    envelope(&out);
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_11_jsx() {
    let dir = scaffold();
    let toml = dir.path().join("crunk.toml");
    let mut spec = std::fs::read_to_string(&toml).expect("read spec");
    spec.push_str("\n[jsx]\nglobs = [\"frontend/**/*.tsx\"]\n");
    std::fs::write(&toml, spec).expect("write spec");
    let src = dir.path().join("frontend");
    std::fs::create_dir_all(&src).expect("mkdir");
    std::fs::write(
        src.join("Card.tsx"),
        "export const Card = () => <div style={{ color: '#123456' }} />;\n",
    )
    .expect("write tsx");
    let (code, out) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(
        code, 1,
        "a literal colour in a JSX style prop fails the gate: {out}"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn int_12_report() {
    let dir = int04_project();
    let (code, out) = crunk(dir.path(), &["query", "violations", "--json"]);
    assert_eq!(code, 0, "query violations answers: {out}");
    envelope(&out);
}

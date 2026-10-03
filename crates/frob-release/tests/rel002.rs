//! `REL002` unit tests: mismatch, equality, inheritance, unresolved manifests and this repository.
// frob:ticket 01M4069WNGJ8YR9DTTM9K9K8V5

use std::fs;
use std::path::Path;

use frob_release::rel002::evaluate;
use gob_rules::Severity;

fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    fs::create_dir_all(p.parent().unwrap()).unwrap();
    fs::write(p, text).unwrap();
}

fn workspace(root: &Path, version: &str) {
    write(
        root,
        "Cargo.toml",
        &format!(
            "[workspace]\nmembers = [\"crates/*\"]\n[workspace.package]\nversion = \"{version}\"\n"
        ),
    );
}

fn krate(root: &Path, name: &str, version_line: &str) {
    write(
        root,
        &format!("crates/{name}/Cargo.toml"),
        &format!("[package]\nname = \"{name}\"\n{version_line}\n"),
    );
}

#[test]
fn one_crate_with_a_different_version_fires_naming_it() {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    workspace(d.path(), "0.532.0");
    krate(d.path(), "a", "version = \"0.532.0\"");
    krate(d.path(), "b", "version = \"0.531.0\"");
    let e = evaluate(d.path());
    assert_eq!(e.subjects, 2);
    assert_eq!(e.findings.len(), 1, "{:?}", e.findings);
    let f = &e.findings[0];
    assert_eq!(f.severity, Severity::Error);
    for want in ["`b`", "0.531.0", "0.532.0", "frob release cut"] {
        assert!(f.message.contains(want), "{want} in {}", f.message);
    }
}

#[test]
fn all_equal_is_silent() {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    workspace(d.path(), "0.532.0");
    krate(d.path(), "a", "version = \"0.532.0\"");
    krate(d.path(), "b", "version = \"0.532.0\"");
    assert!(evaluate(d.path()).findings.is_empty());
}

#[test]
fn inherited_versions_count_as_equal() {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    workspace(d.path(), "0.532.0");
    krate(d.path(), "a", "version.workspace = true");
    krate(d.path(), "b", "version = { workspace = true }");
    assert!(evaluate(d.path()).findings.is_empty());
}

#[test]
fn an_unparseable_member_manifest_is_unresolved_with_the_reason() {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    workspace(d.path(), "0.532.0");
    krate(d.path(), "a", "version = \"0.532.0\"");
    write(d.path(), "crates/broken/Cargo.toml", "[package\nname = ");
    let e = evaluate(d.path());
    assert_eq!(e.findings.len(), 1, "{:?}", e.findings);
    assert_eq!(e.findings[0].severity, Severity::Unresolved);
    assert!(e.findings[0].message.contains("crates/broken/Cargo.toml"));
    assert!(e.findings[0].message.contains("not valid TOML"));
}

#[test]
fn wheel_metadata_absent_is_fine_and_present_is_compared() {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    workspace(d.path(), "0.532.0");
    krate(d.path(), "a", "version.workspace = true");
    assert!(evaluate(d.path()).findings.is_empty());
    write(
        d.path(),
        "pyproject.toml",
        "[project]\nname = \"frob\"\nversion = \"0.531.0\"\n",
    );
    let e = evaluate(d.path());
    assert_eq!(e.findings.len(), 1);
    assert!(e.findings[0].message.contains("wheel"));
    write(
        d.path(),
        "pyproject.toml",
        "[build-system]\nbuild-backend = \"maturin\"\n[project]\nname = \"frob\"\ndynamic = [\"version\"]\n",
    );
    assert!(evaluate(d.path()).findings.is_empty());
}

#[test]
fn this_repository_is_clean() {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let e = evaluate(&root);
    assert!(e.subjects > 30, "examined {}", e.subjects);
    assert!(e.findings.is_empty(), "{:?}", e.findings);
}

fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/frob-release/src/rel002.rs::evaluate
    let d = tempfile::tempdir().unwrap();
    for line in case.text.lines().filter(|l| !l.trim().is_empty()) {
        let w: Vec<&str> = line.split_whitespace().collect();
        match w[0] {
            "workspace" if w[1] == "-" => write(
                d.path(),
                "Cargo.toml",
                "[workspace]\nmembers = [\"crates/*\"]\n",
            ),
            "workspace" => workspace(d.path(), w[1]),
            "crate" if w[2] == "inherit" => krate(d.path(), w[1], "version.workspace = true"),
            "crate" => krate(d.path(), w[1], &format!("version = \"{}\"", w[2])),
            "wheel" if w[1] == "dynamic" => write(
                d.path(),
                "pyproject.toml",
                "[build-system]\nbuild-backend = \"maturin\"\n[project]\nname = \"frob\"\ndynamic = [\"version\"]\n",
            ),
            "wheel" => write(
                d.path(),
                "pyproject.toml",
                &format!("[project]\nname = \"frob\"\nversion = \"{}\"\n", w[1]),
            ),
            other => unreachable!("unknown DSL verb {other}"),
        }
    }
    evaluate(d.path()).findings
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

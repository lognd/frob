//! A vmodel `test` names its runnables by runner id or is manual, and TS and Rust test
//! selectors derive from the runner ids (grmb-spec 4.5.2 and 4.5.3).

// frob:ticket 01M4FGZ4KY03QKSWXACP7APFVH

use std::path::Path;

use grimble_bind::{BindInput, Binding, Role, Status};
use grimble_model::ModelFiles;

const PY: &str = "def test_one():\n    pass\n\n\ndef test_two():\n    pass\n";
const VITEST: &str = "import { describe, it } from 'vitest';\n\ndescribe('gate', () => {\n  it('shows exit state', () => {});\n  it('hides nothing', () => {});\n});\n";
const RUST_IT: &str = "#[test]\nfn error_finding() {}\n\n#[test]\nfn other_case() {}\n";
const RUST_SRC: &str =
    "pub fn run() {}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn it_works() {}\n}\n";

fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    std::fs::create_dir_all(p.parent().expect("a file has a parent")).expect("mkdir");
    std::fs::write(p, text).expect("write");
}

/// Bind a repository holding the code `files` and one vmodel `t` whose body is `body`.
fn bind_test(files: &[(&str, &str)], body: &str) -> Binding {
    let dir = tempfile::tempdir().expect("tempdir");
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let model = format!(
        "grimble = \"2\";\nmodule m;\nvmodel t {{\n  kind test;\n  level unit;\n{body}}}\n"
    );
    write(dir.path(), "design/m.grmb", &model);
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).expect("walk");
    let files = ModelFiles::new().with_file("design/m.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn bound(b: &Binding) -> Vec<String> {
    b.rows
        .iter()
        .filter(|r| r.role == Role::Runnable && r.status == Status::Must)
        .filter_map(|r| r.identity.clone())
        .collect()
}

fn fired<'a>(b: &'a Binding, rule: &str) -> Vec<&'a str> {
    b.findings
        .iter()
        .filter(|f| f.rule == rule)
        .map(|f| f.message.as_str())
        .collect()
}

#[test]
// frob:tests crates/grimble-bind/src/eval.rs::sys003
fn several_runnable_ids_each_bind_without_sys003() {
    let b = bind_test(
        &[("tests/test_a.py", PY)],
        "  runnable \"tests/test_a.py::test_one\";\n  runnable \"tests/test_a.py::test_two\";\n",
    );
    assert_eq!(
        bound(&b),
        vec![
            "tests/test_a.py::test_one".to_owned(),
            "tests/test_a.py::test_two".to_owned()
        ]
    );
    assert!(fired(&b, "SYS003").is_empty(), "{:?}", b.findings);
    assert!(fired(&b, "SYS011").is_empty(), "{:?}", b.findings);
}

#[test]
// frob:tests crates/grimble-bind/src/eval.rs::sys003
fn one_clause_naming_two_tests_is_still_ambiguous() {
    let b = bind_test(
        &[("tests/test_a.py", PY)],
        "  runnable \"tests/test_a.py::test_*\";\n",
    );
    assert_eq!(fired(&b, "SYS003").len(), 1, "{:?}", b.findings);
}

#[test]
// frob:tests crates/grimble-bind/src/model.rs::Model.manual_tests
fn a_manual_test_is_listed_and_raises_no_binding_finding() {
    let b = bind_test(
        &[("tests/test_a.py", PY)],
        "  manual because=\"needs a physical rig\";\n",
    );
    assert_eq!(
        b.manual_tests.get("vmodel/t").map(String::as_str),
        Some("needs a physical rig")
    );
    assert!(bound(&b).is_empty());
    assert!(fired(&b, "SYS011").is_empty(), "{:?}", b.findings);
    assert!(fired(&b, "SYS003").is_empty(), "{:?}", b.findings);
}

#[test]
// frob:tests crates/grimble-bind/src/relation.rs::selector_clause
fn a_vitest_selector_and_cargo_selectors_bind() {
    let b = bind_test(
        &[
            ("web/e2e/gate.test.ts", VITEST),
            ("crates/frob/tests/check_verb.rs", RUST_IT),
            ("crates/frob-check/src/lib.rs", RUST_SRC),
        ],
        "  runnable \"web/e2e/gate.test.ts::[gate > shows exit state]\";\n  runnable \"crates/frob/tests/check_verb.rs::error_finding\";\n  runnable \"crates/frob-check/src/lib.rs::tests.it_works\";\n",
    );
    assert_eq!(bound(&b).len(), 3, "{:?} {:?}", bound(&b), b.findings);
    assert!(fired(&b, "SYS011").is_empty(), "{:?}", b.findings);
    assert!(fired(&b, "SYS003").is_empty(), "{:?}", b.findings);
}

#[test]
// frob:tests crates/grimble-bind/src/eval.rs::sys011
fn a_wrong_id_in_an_existing_file_names_the_nearest_real_id() {
    let b = bind_test(
        &[("web/e2e/gate.test.ts", VITEST)],
        "  runnable \"web/e2e/gate.test.ts::[gate > shows exit stat]\";\n",
    );
    let msgs = fired(&b, "SYS011");
    assert_eq!(msgs.len(), 1, "{:?}", b.findings);
    assert!(msgs[0].contains("shows exit state"), "{}", msgs[0]);
}

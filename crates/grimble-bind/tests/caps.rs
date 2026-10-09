//! CAP001 and CAP002 (binding.md 7.2): an ungranted observed use is undeclared, a granted atom
//! never observed is declared-unused. Repros 09 and 11 of the logand adoption run.

// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const PY: &str = "import socket\nimport subprocess\n\ndef go():\n    with open(\"/etc/hosts\") as f:\n        f.read()\n    subprocess.run([\"ls\"])\n    s = socket.socket()\n    s.listen()\n";

fn model(body: &str) -> String {
    format!("grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n{body}}}\n")
}

fn bind_py(py: &str, body: &str) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::write(dir.path().join("src/x.py"), py).unwrap();
    let text = model(body);
    std::fs::write(dir.path().join("design/model.grmb"), &text).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", text.into_bytes());
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

fn of<'a>(b: &'a Binding, rule: &str) -> Vec<&'a grimble_bind::BindFinding> {
    b.findings.iter().filter(|f| f.rule == rule).collect()
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn ungranted_open_exec_and_listen_are_cap001_errors() {
    let b = bind_py(PY, "");
    let f = of(&b, "CAP001");
    let anchors: Vec<_> = f.iter().map(|f| f.anchor.as_str()).collect();
    assert_eq!(
        anchors,
        [
            "cap/node/a/fs.read",
            "cap/node/a/net.listen",
            "cap/node/a/process.spawn"
        ],
        "{f:?}"
    );
    assert!(f.iter().all(|f| f.reason.is_none()));
    assert!(
        f.iter()
            .all(|f| f.file.as_deref() == Some("design/model.grmb"))
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_grant_or_a_parent_grant_silences_cap001() {
    let b = bind_py(PY, "  may fs.read;\n  may exec;\n  may net.listen;\n");
    assert!(of(&b, "CAP001").is_empty(), "{:?}", b.findings);
    assert!(of(&b, "CAP002").is_empty(), "{:?}", b.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_method_name_is_a_use_only_beside_its_companion_call() {
    let b = bind_py("def go(server):\n    server.listen()\n", "");
    assert!(of(&b, "CAP001").is_empty(), "{:?}", b.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_granted_atom_never_observed_is_a_cap002_warning() {
    let b = bind_py(
        PY,
        "  may fs.read;\n  may exec;\n  may net.listen;\n  may fs.write;\n",
    );
    let f = of(&b, "CAP002");
    assert_eq!(f.len(), 1, "{:?}", b.findings);
    assert_eq!(f[0].severity, gob_rules::Severity::Warn);
    assert_eq!(f[0].anchor, "cap/node/a/fs.write");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_node_with_neither_use_nor_grant_is_a_clean_subject_of_both() {
    let b = bind_py("def go():\n    pass\n", "");
    assert!(of(&b, "CAP001").is_empty() && of(&b, "CAP002").is_empty());
    assert!(b.subjects.get("CAP001").copied().unwrap_or(0) > 0);
    assert!(b.subjects.get("CAP002").copied().unwrap_or(0) > 0);
    assert!(!b.not_applicable.contains_key("CAP002"));
}

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_parent_grant_and_an_alias_grant_cover_their_children_and_canonical_atom() {
    let py = "import subprocess\nimport os\n\ndef go():\n    open(\"x\")\n    subprocess.run([\"ls\"])\n    os.getenv(\"HOME\")\n";
    let b = bind_py(py, "  may fs;\n  may exec;\n  may process.env;\n");
    assert!(of(&b, "CAP001").is_empty(), "{:?}", b.findings);
    assert!(of(&b, "CAP002").is_empty(), "{:?}", b.findings);
    let b = bind_py(py, "  may fs;\n  may process.spawn;\n");
    let f = of(&b, "CAP001");
    assert_eq!(f.len(), 1, "{f:?}");
    assert_eq!(f[0].anchor, "cap/node/a/process.env");
}

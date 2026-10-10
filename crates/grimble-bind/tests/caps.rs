//! CAP001 and CAP002 (binding.md 7.2): an ungranted observed use is undeclared, a granted atom
//! never observed is declared-unused. Repros 09 and 11 of the logand adoption run.

// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:ticket 01M4HW9Y1TXZCN4Y5RF2T7C4A9
// frob:ticket 01M4K3BPQ72DVFEMK8EXQSD03K

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const PY: &str = "import socket\nimport subprocess\n\ndef go():\n    with open(\"/etc/hosts\") as f:\n        f.read()\n    subprocess.run([\"ls\"])\n    s = socket.socket()\n    s.listen()\n";

fn model(body: &str) -> String {
    format!("grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n{body}}}\n")
}

fn bind_py(py: &str, body: &str) -> Binding {
    bind_file("src/x.py", py, body)
}

fn bind_file(rel: &str, text: &str, body: &str) -> Binding {
    let py = text;
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::write(dir.path().join(rel), py).unwrap();
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

/// The repro shape: logand `auth/passwords.py`, a module-level `Path` constant read in a function.
const PASSWORDS: &str = "from pathlib import Path\n\n_PATH = Path(__file__).resolve().parent / \"data\" / \"x.txt\"\n\n\ndef load():\n    return _PATH.read_text(encoding=\"utf-8\")\n";

fn atoms(b: &Binding) -> Vec<String> {
    of(b, "CAP001").iter().map(|f| f.anchor.clone()).collect()
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn read_text_on_a_module_level_path_constant_is_a_must_fs_read() {
    let b = bind_py(PASSWORDS, "");
    let f = of(&b, "CAP001");
    assert_eq!(atoms(&b), ["cap/node/a/fs.read"], "{f:?}");
    assert!(f[0].reason.is_none(), "must be a resolved Error: {f:?}");
    assert!(f[0].message.contains("src/x.py:7"), "{}", f[0].message);
    let b = bind_py(PASSWORDS, "  may fs.read;\n");
    assert!(of(&b, "CAP001").is_empty(), "{:?}", b.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn inline_path_chains_annotated_parameters_and_locals_are_path_receivers() {
    for body in [
        "return Path(\"/etc/hostname\").read_text()",
        "return Path.home().joinpath(\"a\").read_bytes()",
        "return (Path(\".\") / \"a\").read_text()",
        "p = Path(\"x\")\n    return p.read_bytes()",
    ] {
        let py = format!("from pathlib import Path\n\n\ndef go():\n    {body}\n");
        let b = bind_py(&py, "");
        assert_eq!(
            atoms(&b),
            ["cap/node/a/fs.read"],
            "{body}: {:?}",
            b.findings
        );
        assert!(of(&b, "CAP001")[0].reason.is_none(), "{body}");
    }
    let py = "from pathlib import Path\n\n\ndef go(p: Path):\n    return p.open()\n";
    assert_eq!(atoms(&bind_py(py, "")), ["cap/node/a/fs.read"]);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn path_writes_are_fs_write_and_a_read_grant_does_not_cover_them() {
    let py = "from pathlib import Path\n\n_P = Path(\"o\")\n\n\ndef go():\n    _P.write_text(\"a\")\n    _P.write_bytes(b\"a\")\n";
    let b = bind_py(py, "  may fs.read;\n");
    assert_eq!(atoms(&b), ["cap/node/a/fs.write"], "{:?}", b.findings);
    assert!(of(&b, "CAP001")[0].reason.is_none());
    assert!(of(&bind_py(py, "  may fs.write;\n"), "CAP001").is_empty());
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_vocabulary_method_on_an_unresolved_receiver_is_a_may_use_never_clean() {
    for call in [
        "p.read_text()",
        "p.read_bytes()",
        "p.open()",
        "p.write_text(\"a\")",
        "p.write_bytes(b\"a\")",
    ] {
        let py = format!("def go(p):\n    return {call}\n");
        let b = bind_py(&py, "");
        let f = of(&b, "CAP001");
        assert_eq!(f.len(), 1, "{call}: {:?}", b.findings);
        assert!(
            f[0].reason.is_some(),
            "{call}: must be Unresolved, not an Error: {f:?}"
        );
        assert!(
            f[0].message.contains("src/x.py:2"),
            "{call}: {}",
            f[0].message
        );
        assert!(f[0].anchor.ends_with("/receiver"), "{}", f[0].anchor);
    }
    // a constant assigned something that is not a Path does not resolve either
    let py = "from pathlib import Path\n\n_P = make()\n\n\ndef go():\n    return _P.read_text()\n";
    let f = of(&bind_py(py, ""), "CAP001").len();
    assert_eq!(f, 1);
    // a grant silences the May use too
    let b = bind_py("def go(p):\n    return p.read_text()\n", "  may fs.read;\n");
    assert!(of(&b, "CAP001").is_empty(), "{:?}", b.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn common_python_file_apis_are_fs_uses() {
    for (call, atom) in [
        ("os.walk(\".\")", "fs.read"),
        ("shutil.rmtree(\"d\")", "fs.write"),
        ("os.remove(\"d\")", "fs.write"),
        ("tempfile.mkdtemp()", "fs.write"),
        ("glob.glob(\"*\")", "fs.read"),
    ] {
        let py = format!("import os, shutil, tempfile, glob\n\n\ndef go():\n    {call}\n");
        let b = bind_py(&py, "");
        assert!(
            atoms(&b).contains(&format!("cap/node/a/{atom}")),
            "{call}: {:?}",
            b.findings
        );
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_fs_paths_read_and_write_including_qualified_forms() {
    let rs = "fn go() {\n    let _ = std::fs::read_to_string(\"a\");\n    let _ = tokio::fs::write(\"a\", b\"\");\n    let _ = fs::remove_file(\"a\");\n}\n";
    let b = bind_file("src/x.rs", rs, "");
    assert_eq!(
        atoms(&b),
        ["cap/node/a/fs.read", "cap/node/a/fs.write"],
        "{:?}",
        b.findings
    );
    assert!(of(&b, "CAP001").iter().all(|f| f.reason.is_none()));
}

// frob:ticket 01M4K3BPQ72DVFEMK8EXQSD03K
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn a_clap_command_is_not_a_process_spawn_but_std_process_command_is() {
    let clap = "fn cli() {\n    let _ = clap::Command::new(\"x\");\n}\n";
    let b = bind_file("src/x.rs", clap, "");
    assert!(of(&b, "CAP001").is_empty(), "{:?}", b.findings);
    let std = "fn go() {\n    let _ = std::process::Command::new(\"ls\");\n}\n";
    let b = bind_file("src/x.rs", std, "");
    assert_eq!(atoms(&b), ["cap/node/a/process.spawn"], "{:?}", b.findings);
}

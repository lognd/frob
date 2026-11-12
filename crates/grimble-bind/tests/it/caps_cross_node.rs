//! CAP001 for a capability reached through a call into another node (ticket
//! 01M642304NQ5XQP3WWD0T8Z2BM, audit case q07): the caller's node inherits the uses of the
//! function it calls, resolved through the call graph; unproven hops are Unresolved.

// frob:ticket 01M642304NQ5XQP3WWD0T8Z2BM

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n}\nnode b : trusted {\n  owns \"src/b/**\";\n  may process.spawn;\n  may fs.read;\n  may net.connect;\n}\nnode c : trusted {\n  owns \"src/c/**\";\n  may process.spawn;\n}\n";

fn bind_files(files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    std::fs::write(dir.path().join("design/model.grmb"), MODEL).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", MODEL.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// (atom, certain) of every CAP001 finding against `node`.
fn cap001(node: &str, files: &[(&str, &str)]) -> Vec<(String, bool)> {
    let prefix = format!("cap/node/{node}/");
    let mut v: Vec<_> = bind_files(files)
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001" && f.anchor.starts_with(&prefix))
        .map(|f| {
            (
                f.anchor.trim_start_matches(&prefix).to_owned(),
                f.reason.is_none(),
            )
        })
        .collect();
    v.sort();
    v.dedup();
    v
}

fn has(found: &[(String, bool)], atom: &str, certain: bool) -> bool {
    found.iter().any(|(a, c)| a == atom && *c == certain)
}

const HELPER_PY: &str = "import os\n\n\ndef run(c):\n    os.system(c)\n";

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_python_from_import_call_carries_the_callee_use() {
    for caller in [
        "from b.helper import run\n\n\ndef go(c):\n    run(c)\n",
        "from b.helper import run as r\n\n\ndef go(c):\n    r(c)\n",
        "import b.helper as h\n\n\ndef go(c):\n    h.run(c)\n",
    ] {
        let f = cap001(
            "a",
            &[
                ("src/b/helper.py", HELPER_PY),
                ("src/b/__init__.py", ""),
                ("src/a/x.py", caller),
            ],
        );
        assert!(has(&f, "process.spawn", true), "{caller}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_python_transitive_chain_and_reexport_reach_the_caller() {
    let f = cap001(
        "a",
        &[
            ("src/c/deep.py", HELPER_PY),
            ("src/c/__init__.py", ""),
            (
                "src/b/mid.py",
                "from c.deep import run\n\n\ndef relay(c):\n    run(c)\n",
            ),
            ("src/b/__init__.py", "from b.mid import relay\n"),
            (
                "src/a/x.py",
                "from b import relay\n\n\ndef go(c):\n    relay(c)\n",
            ),
        ],
    );
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_recursion_and_cycles_terminate() {
    let f = cap001(
        "a",
        &[
            (
                "src/b/h.py",
                "import os\nfrom a.x import go\n\n\ndef run(c, n):\n    if n:\n        run(c, n - 1)\n        go(c)\n    os.system(c)\n",
            ),
            ("src/b/__init__.py", ""),
            ("src/a/__init__.py", ""),
            (
                "src/a/x.py",
                "from b.h import run\n\n\ndef go(c):\n    run(c, 1)\n",
            ),
        ],
    );
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_same_node_call_adds_nothing_and_unrelated_call_is_clean() {
    let f = cap001(
        "a",
        &[
            ("src/b/helper.py", HELPER_PY),
            ("src/b/__init__.py", ""),
            (
                "src/a/x.py",
                "def pure(c):\n    return c\n\n\ndef go(c):\n    pure(c)\n",
            ),
        ],
    );
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_a_granted_caller_is_not_flagged() {
    let f = cap001(
        "b",
        &[
            ("src/c/helper.py", HELPER_PY),
            ("src/c/__init__.py", ""),
            (
                "src/b/x.py",
                "from c.helper import run\n\n\ndef go(c):\n    run(c)\n",
            ),
        ],
    );
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_a_method_name_guess_is_unresolved_never_clean() {
    let f = cap001(
        "a",
        &[
            (
                "src/b/svc.py",
                "import os\n\n\nclass Svc:\n    def fire(self, c):\n        os.system(c)\n",
            ),
            ("src/a/x.py", "def go(thing, c):\n    thing.fire(c)\n"),
        ],
    );
    assert!(!has(&f, "process.spawn", true), "{f:?}");
    assert!(has(&f, "process.spawn/receiver", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_typescript_import_call_carries_the_callee_use() {
    let f = cap001(
        "a",
        &[
            (
                "src/b/helper.ts",
                "import { exec } from \"child_process\";\nexport function run(x: string) { exec(x); }\n",
            ),
            (
                "src/a/x.ts",
                "import { run } from \"../b/helper\";\nexport function go(x: string) { run(x); }\n",
            ),
        ],
    );
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_rust_path_call_carries_the_callee_use() {
    let f = cap001(
        "a",
        &[
            (
                "src/b/helper.rs",
                "pub fn run(c: &str) {\n    let _ = std::process::Command::new(c).spawn();\n}\n",
            ),
            (
                "src/a/x.rs",
                "use crate::b::helper::run;\n\npub fn go(c: &str) {\n    run(c);\n}\n",
            ),
        ],
    );
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn q07_cap_csharp_static_call_carries_the_callee_use() {
    let f = cap001(
        "a",
        &[
            (
                "src/b/Helper.cs",
                "namespace B { public static class Helper { public static void Run(string c) { System.Diagnostics.Process.Start(c); } } }\n",
            ),
            (
                "src/a/X.cs",
                "using B;\nnamespace A { public class X { public void Go(string c) { Helper.Run(c); } } }\n",
            ),
        ],
    );
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

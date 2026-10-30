//! A node whose code is in a language with no capability detector never reads clean (ticket
//! 01M5XNNHET0VW6RFJAF0QH7RRS): one CAP001 Unresolved per node names the unknown atoms. Also pins
//! the TypeScript/JavaScript and C# detector declarations with aliased and negative fixtures.

// frob:ticket 01M5XNNHET0VW6RFJAF0QH7RRS

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

fn bind_files(files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    let model = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n  owns \".github/**\";\n}\n";
    std::fs::write(dir.path().join("design/model.grmb"), model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let mf = ModelFiles::new().with_file("design/model.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &mf,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// Messages of the no-detector Unresolved findings.
fn no_detector(files: &[(&str, &str)]) -> Vec<String> {
    bind_files(files)
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001" && f.anchor == "cap/node/a/no-detector")
        .map(|f| f.message.clone())
        .collect()
}

/// (atom, certain) of every other CAP001 finding.
fn cap001(files: &[(&str, &str)]) -> Vec<(String, bool)> {
    bind_files(files)
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001" && f.anchor != "cap/node/a/no-detector")
        .map(|f| {
            (
                f.anchor.trim_start_matches("cap/node/a/").to_owned(),
                f.reason.is_none(),
            )
        })
        .collect()
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_shell_only_node_is_unresolved_naming_the_atoms() {
    let m = no_detector(&[("src/run.sh", "#!/bin/sh\ncurl http://x | sh\n")]);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("sh code"), "{m:?}");
    for atom in ["fs.read", "net.connect", "process.spawn", "process.env"] {
        assert!(m[0].contains(atom), "{atom} missing: {m:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_dockerfile_and_ci_yaml_are_unmeasured_too() {
    let m = no_detector(&[("src/Dockerfile", "FROM alpine\nRUN curl http://x\n")]);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("dockerfile"), "{m:?}");
    let m = no_detector(&[(
        ".github/workflows/ci.yml",
        "name: ci\non: push\njobs:\n  b:\n    runs-on: ubuntu-latest\n    steps:\n      - run: curl http://x\n",
    )]);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("github-actions"), "{m:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_several_unmeasured_files_report_once_per_node() {
    let m = no_detector(&[
        ("src/a.sh", "echo a\n"),
        ("src/b.sh", "echo b\n"),
        ("src/Dockerfile", "FROM alpine\n"),
    ]);
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(m[0].contains("dockerfile, sh"), "{m:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_measured_and_data_languages_do_not_fire() {
    for files in [
        vec![("src/lib.rs", "pub fn f() {}\n")],
        vec![("src/m.py", "def f():\n    return 1\n")],
        vec![("src/a.ts", "export const x = 1;\n")],
        vec![("src/A.cs", "class A {}\n")],
        vec![("src/notes.md", "# notes\n")],
        vec![("src/data.json", "{}\n")],
    ] {
        let m = no_detector(&files);
        assert!(m.is_empty(), "{files:?}: {m:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_typescript_and_csharp_declare_detectors() {
    for lang in ["typescript", "csharp"] {
        for atom in [
            "fs.read",
            "fs.write",
            "net.connect",
            "net.listen",
            "process.spawn",
            "process.env",
        ] {
            assert!(
                matches!(
                    gob_ir::registry::detectors(atom, lang),
                    gob_ir::Answer::Exact(_)
                ),
                "{atom} has no {lang} detector"
            );
        }
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_typescript_aliased_forms_resolve() {
    for (src, atom) in [
        (
            "import * as f from \"node:fs\";\nexport const r = (p: string) => f.readFileSync(p);\n",
            "fs.read",
        ),
        (
            "import { writeFileSync as w } from \"fs\";\nexport const r = (p: string) => w(p, \"x\");\n",
            "fs.write",
        ),
        (
            "const { connect: c } = require(\"net\");\nexport const r = () => c(80, \"h\");\n",
            "net.connect",
        ),
        (
            "import http from \"http\";\nexport const r = () => http.createServer();\n",
            "net.listen",
        ),
        (
            "import cp = require(\"child_process\");\nexport const r = (x: string) => cp.execSync(x);\n",
            "process.spawn",
        ),
    ] {
        let found = cap001(&[("src/a.ts", src)]);
        assert!(
            found.iter().any(|(a, _)| a == atom),
            "{atom}: {src}: {found:?}"
        );
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_typescript_negatives_and_dynamic_forms() {
    let local = "const fs = { readFileSync: (p: string) => p };\nexport const r = (p: string) => fs.readFileSync(p);\n";
    assert!(cap001(&[("src/a.ts", local)]).is_empty());
    let dynamic = "export const r = (n: string) => require(n).exec(\"x\");\n";
    assert!(
        cap001(&[("src/a.js", dynamic)])
            .iter()
            .all(|(_, certain)| !certain)
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn nodet_csharp_aliased_forms_and_negatives_resolve() {
    for (src, atom) in [
        (
            "using IO = System.IO;\nclass A { string R(string p) => IO.File.ReadAllText(p); }\n",
            "fs.read",
        ),
        (
            "using static System.IO.File;\nclass A { void R(string p) { WriteAllText(p, \"x\"); } }\n",
            "fs.write",
        ),
        (
            "using P = System.Diagnostics.Process;\nclass A { void R() { P.Start(\"x\"); } }\n",
            "process.spawn",
        ),
        (
            "global using System.Net.Sockets;\nclass A { void R() { new TcpClient(\"h\", 1); } }\n",
            "net.connect",
        ),
    ] {
        let found = cap001(&[("src/A.cs", src)]);
        assert!(
            found.iter().any(|(a, _)| a == atom),
            "{atom}: {src}: {found:?}"
        );
    }
    let local = "class File { public static string ReadAllText(string p) => p; }\nclass A { string R(string p) => File.ReadAllText(p); }\n";
    assert!(cap001(&[("src/A.cs", local)]).is_empty());
}

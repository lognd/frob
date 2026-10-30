//! LOG001 and LOG002: symbolic direct-output detection per language, with aliased, re-exported
//! and negative (shadowed, string, comment) fixtures.

// frob:ticket 01M5XMR67K19SFAWNTDJKKJPTT

#![allow(unused_crate_dependencies)]

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

/// The `rule` findings of a repo made of `files` (a `grimble.toml` is added).
fn findings(rule: &str, files: &[(&str, &str)]) -> Vec<serde_json::Value> {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("grimble.toml"), "[check]\n").unwrap();
    for (rel, text) in files {
        let path = dir.path().join(rel);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, text).unwrap();
    }
    let r = run(Path::new(dir.path()), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == rule)
        .cloned()
        .collect()
}

/// Run only the LOG pass over `files` (bypasses the shared pipeline, whose C# symbol graph
/// overflows the stack on `using static`).
fn direct(files: &[(&str, &str)]) -> Vec<grimble_lints::pass::PathFinding> {
    use grimble_check::config::{default_log_exempt, default_log_modules};
    use grimble_check::log::pass::{LogOptions, analyze};
    let files: Vec<_> = files
        .iter()
        .map(|(path, text)| grimble_lints::pass::PathFile {
            path,
            language: gob_languages::Language::detect(path).unwrap(),
            text,
        })
        .collect();
    let opts = LogOptions {
        modules: default_log_modules(),
        exempt: default_log_exempt(),
        extra_crates: vec![],
    };
    analyze(&files, &opts)
        .findings
        .into_iter()
        .filter(|f| f.rule == "LOG001")
        .collect()
}

/// Assert LOG001 finds `n` hits in a single file `name`.
fn hits(name: &str, text: &str, n: usize) {
    let found = findings("LOG001", &[(name, text)]);
    assert_eq!(found.len(), n, "{name}: {text}\n{found:#?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn python_direct_output_atoms_fire() {
    let cases = [
        "print('x')\n",
        "import sys as s\ns.stdout.write('x')\n",
        "from sys import stdout as o\no.write('x')\n",
        "p = print\np('x')\n",
        "import sys\ngetattr(sys, 'stdout').write('x')\n",
        "import builtins\nbuiltins.print('x')\n",
        "import os\nos.write(1, b'x')\n",
        "import os\nos.fdopen(1, 'w')\n",
        "open('/dev/stdout', 'w')\n",
        "import subprocess\nsubprocess.run(['ls'])\n",
        "import traceback\ntraceback.print_exc()\n",
        "import pprint\npprint.pprint({})\n",
        "import warnings\nwarnings.warn('x')\n",
        "import logging\nh = logging.StreamHandler()\n",
        "import logging\nh = logging.FileHandler('a.log')\n",
        "import contextlib, io\nwith contextlib.redirect_stdout(io.StringIO()):\n    pass\n",
        "import sys\nsys.__stderr__.write('x')\n",
        "import sys\nsys.stderr.writelines(['x'])\n",
        "import sys\nsys.stdout.flush()\n",
    ];
    for c in cases {
        let found = findings("LOG001", &[("app.py", c)]);
        assert!(!found.is_empty(), "expected a hit for: {c}");
    }
}

// frob:tests crates/grimble-check/src/log/lang_python.rs::scan
#[test]
fn python_negatives_are_clean() {
    hits("app.py", "def f(print):\n    return print('x')\n", 0);
    hits("app.py", "s = \"print('x')\"\n", 0);
    hits("app.py", "# print('x')\nx = 1\n", 0);
    hits("app.py", "import sys\nprint = len\nx = print('abc')\n", 0);
    hits("app.py", "x = open('data.txt')\n", 0);
}

// frob:tests crates/grimble-check/src/log/engine.rs::Project
#[test]
fn python_reexported_wrapper_is_followed() {
    let found = findings(
        "LOG001",
        &[
            ("util.py", "say = print\n"),
            ("app.py", "from util import say\nsay('x')\n"),
        ],
    );
    assert!(found.iter().any(|f| f["file"] == "app.py"), "{found:#?}");
}

// frob:tests crates/grimble-check/src/log/lang_rust.rs::scan
#[test]
fn rust_atoms_fire_and_negatives_are_clean() {
    hits("src/a.rs", "fn f() { println!(\"x\"); }\n", 1);
    hits("src/a.rs", "fn f() { eprintln!(\"x\"); dbg!(1); }\n", 2);
    hits(
        "src/a.rs",
        "use std::io::stdout as out;\nfn f() { let _ = out(); }\n",
        1,
    );
    hits(
        "src/a.rs",
        "macro_rules! m { () => {} }\nfn f() { let s = \"println!(1)\"; }\n",
        0,
    );
    hits("src/a.rs", "// println!(\"x\")\nfn f() {}\n", 0);
    hits(
        "src/a.rs",
        "fn f() { let println = 1; let _ = println; }\n",
        0,
    );
}

// frob:tests crates/grimble-check/src/log/lang_rust.rs::scan
#[test]
fn rust_reexported_alias_is_followed() {
    let found = findings(
        "LOG001",
        &[
            ("src/lib.rs", "pub mod util;\npub mod app;\n"),
            ("src/util.rs", "pub use std::io::stdout as out;\n"),
            (
                "src/app.rs",
                "use crate::util::out;\nfn f() { let _ = out(); }\n",
            ),
        ],
    );
    assert!(
        found.iter().any(|f| f["file"] == "src/app.rs"),
        "{found:#?}"
    );
}

// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn javascript_family_fires_and_negatives_are_clean() {
    for name in ["a.js", "a.ts", "a.jsx", "a.tsx"] {
        hits(name, "console.log('x');\n", 1);
        hits(name, "const log = console.log;\nlog('x');\n", 1);
        hits(name, "const { error } = console;\nerror('x');\n", 1);
        hits(name, "globalThis.console.warn('x');\n", 1);
        hits(name, "process.stdout.write('x');\n", 1);
        hits(name, "function f(console) { console.log('x'); }\n", 0);
        hits(name, "const s = \"console.log('x')\";\n", 0);
        hits(name, "// console.log('x')\nconst a = 1;\n", 0);
    }
}

// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn javascript_reexported_wrapper_is_followed() {
    let found = findings(
        "LOG001",
        &[
            ("util.js", "export const log = console.log;\n"),
            ("app.js", "import { log } from './util';\nlog('x');\n"),
        ],
    );
    assert!(found.iter().any(|f| f["file"] == "app.js"), "{found:#?}");
}

// frob:tests crates/grimble-check/src/log/lang_csharp.rs::scan
#[test]
fn csharp_atoms_fire_and_negatives_are_clean() {
    hits(
        "A.cs",
        "class A { void F() { System.Console.WriteLine(\"x\"); } }\n",
        1,
    );
    hits(
        "A.cs",
        "using System;\nclass A { void F() { Console.Write(\"x\"); } }\n",
        1,
    );
    hits(
        "A.cs",
        "using C = System.Console;\nclass A { void F() { C.WriteLine(\"x\"); } }\n",
        1,
    );
    let t = "using static System.Console;\nclass A { void F() { WriteLine(\"x\"); } }\n";
    assert_eq!(direct(&[("A.cs", t)]).len(), 1);
    hits(
        "A.cs",
        "class A { void F(int Console) { var s = \"Console.WriteLine\"; } }\n",
        0,
    );
    hits("A.cs", "// System.Console.WriteLine(1)\nclass A { }\n", 0);
}

// frob:tests crates/grimble-check/src/log/lang_csharp.rs::global_usings
#[test]
fn csharp_global_using_static_is_followed() {
    let found = direct(&[
        ("G.cs", "global using static System.Console;\n"),
        ("A.cs", "class A { void F() { WriteLine(\"x\"); } }\n"),
    ]);
    assert!(found.iter().any(|f| f.file == "A.cs"), "{found:#?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn log002_requires_a_logging_crate() {
    let without = findings("LOG002", &[("app.py", "print('x')\n")]);
    assert_eq!(without.len(), 1, "{without:#?}");
    let with = findings(
        "LOG002",
        &[
            ("app.py", "print('x')\n"),
            ("setup.py", "import logging\nlogging.basicConfig()\n"),
        ],
    );
    assert!(with.is_empty(), "{with:#?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn logging_module_and_tests_are_not_judged() {
    let found = findings(
        "LOG001",
        &[
            ("log/sink.py", "print('x')\n"),
            ("tests/test_a.py", "print('x')\n"),
            ("app.py", "x = 1\n"),
        ],
    );
    assert!(found.is_empty(), "{found:#?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn finding_message_tells_agents_and_humans() {
    let found = findings("LOG001", &[("app.py", "print('x')\n")]);
    let msg = found[0]["message"].as_str().unwrap();
    assert!(msg.contains("frob:waive LOG001"), "{msg}");
    assert!(msg.contains("Agents"), "{msg}");
}

// frob:ticket 01M6422ZYR690QV4JF17VYCFGM
// frob:tests crates/grimble-check/src/log/lang_python.rs::scan
#[test]
fn p04_python_nfkc_spellings_of_output_atoms_fire() {
    // Fullwidth `print`, fullwidth `sys`, and a fullwidth `import` alias all name the ASCII symbol.
    for c in [
        "\u{ff50}\u{ff52}\u{ff49}\u{ff4e}\u{ff54}('x')\n",
        "import \u{ff53}\u{ff59}\u{ff53}\n\u{ff53}\u{ff59}\u{ff53}.stdout.write('x')\n",
        "import sys\nsys.\u{ff53}tdout.write('x')\n",
        "p = \u{ff50}rint\np('x')\n",
    ] {
        let found = findings("LOG001", &[("app.py", c)]);
        assert!(!found.is_empty(), "expected a hit for: {c}");
    }
    // A string that merely contains the fullwidth spelling is not code.
    hits(
        "app.py",
        "s = \"\u{ff50}\u{ff52}\u{ff49}\u{ff4e}\u{ff54}('x')\"\n",
        0,
    );
}

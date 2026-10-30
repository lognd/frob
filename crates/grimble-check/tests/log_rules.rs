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

/// Split a single JS file's LOG001 results into (resolved hits, unresolved reports).
fn js_log(text: &str) -> (usize, usize) {
    let found = direct(&[("a.js", text)]);
    let unres = found
        .iter()
        .filter(|f| matches!(f.severity, gob_rules::Severity::Unresolved))
        .count();
    (found.len() - unres, unres)
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_computed_members_resolve_or_report() {
    assert_eq!(js_log("console['log']('x');\n"), (1, 0));
    assert_eq!(js_log("const k = 'log';\nconsole[k]('x');\n"), (1, 0));
    assert_eq!(js_log("console['lo' + 'g']('x');\n"), (1, 0));
    assert_eq!(js_log("function f(k) { console[k]('x'); }\n"), (0, 1));
    assert_eq!(js_log("const o = {};\no[k] = 1;\n"), (0, 0));
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_nested_and_computed_destructuring_resolve() {
    assert_eq!(js_log("const { log } = console;\nlog('x');\n"), (1, 0));
    assert_eq!(
        js_log("const { stdout: { write } } = process;\nwrite('x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("const { stdout: { write: w } } = globalThis.process;\nw('x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("const { log = noop } = console;\nlog('x');\n"),
        (1, 0)
    );
    assert_eq!(js_log("const { ['log']: l } = console;\nl('x');\n"), (1, 0));
    assert_eq!(
        js_log("function f(k) { const { [k]: l } = console; }\n"),
        (0, 1)
    );
    assert_eq!(
        js_log("const { stdout: { write } } = other;\nwrite('x');\n"),
        (0, 0)
    );
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_eval_and_function_constructor_are_reported() {
    assert_eq!(js_log("eval(code);\n"), (0, 1));
    assert_eq!(js_log("new Function('return 1')();\n"), (0, 1));
    assert_eq!(js_log("(0, eval)(code);\n"), (0, 1));
    assert_eq!(js_log("const e = eval;\ne(code);\n"), (0, 1));
    assert_eq!(js_log("setTimeout('console.log(1)', 0);\n"), (0, 1));
    assert_eq!(js_log("setTimeout(() => {}, 0);\n"), (0, 0));
    assert_eq!(js_log("function eval2(eval) { eval(1); }\n"), (0, 0));
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_dynamic_import_and_require_resolve_or_report() {
    assert_eq!(js_log("import('node:process').then(p => p);\n"), (0, 0));
    assert_eq!(js_log("const m = import(name);\n"), (0, 1));
    assert_eq!(js_log("const m = require(name);\n"), (0, 1));
    assert_eq!(
        js_log("const p = require('process');\np.stdout.write('x');\n"),
        (1, 0)
    );
    let shadow = "function f(require) { return require(name); }\n";
    assert_eq!(js_log(shadow), (0, 0));
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_process_internals_fire() {
    assert_eq!(js_log("process._rawDebug('x');\n"), (1, 0));
    assert_eq!(
        js_log("const { _rawDebug } = process;\n_rawDebug('x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("process.stderr._handle.writeUtf8String(r, 'x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("const o = { _rawDebug() {} };\no._rawDebug('x');\n"),
        (0, 0)
    );
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_require_through_a_variable_is_followed() {
    assert_eq!(
        js_log("const r = require;\nr('process').stdout.write('x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log(
            "const { createRequire } = require('module');\nconst require = createRequire(u);\nrequire('process').stdout.write('x');\n"
        ),
        (1, 0)
    );
    assert_eq!(
        js_log("const s = 'process';\nrequire(s).stdout.write('x');\n"),
        (1, 0)
    );
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_parameter_defaults_alias_output_symbols() {
    assert_eq!(
        js_log("function f(log = console.log) { log('x'); }\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("const f = (log = console.log) => log('x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("function f({ log } = console) { log('x'); }\n"),
        (1, 0)
    );
    assert_eq!(js_log("function f(log = noop) { log('x'); }\n"), (0, 0));
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_reflect_forms_resolve_or_report() {
    assert_eq!(js_log("Reflect.get(console, 'log')('x');\n"), (1, 0));
    assert_eq!(
        js_log("Reflect.apply(console.log, console, ['x']);\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("function f(k) { Reflect.get(console, k)('x'); }\n"),
        (0, 1)
    );
    assert_eq!(js_log("Reflect.get(obj, 'log')('x');\n"), (0, 0));
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_with_blocks_resolve_or_report() {
    assert_eq!(js_log("with (console) { log('x'); }\n"), (1, 0));
    assert_eq!(js_log("with (Math) { max(1, 2); }\n"), (0, 0));
    assert_eq!(js_log("function f(o) { with (o) { log('x'); } }\n"), (0, 1));
}

// frob:ticket 01M64230KYDRZ7V51SECS763EX
// frob:tests crates/grimble-check/src/log/lang_js.rs::scan
#[test]
fn js_log_fs_write_to_a_standard_fd() {
    assert_eq!(
        js_log("const fs = require('fs');\nfs.writeSync(1, 'x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("const fs = require('fs');\nconst FD = 2;\nfs.writeSync(FD, 'x');\n"),
        (1, 0)
    );
    assert_eq!(
        js_log("const fs = require('fs');\nfs.writeSync(3, 'x');\n"),
        (0, 0)
    );
    assert_eq!(
        js_log("const fs = require('fs');\nfunction f(fd) { fs.writeSync(fd, 'x'); }\n"),
        (0, 1)
    );
}

/// Split one C# file's LOG001 results into (resolved hits, unresolved reports).
fn cs_log(files: &[(&str, &str)]) -> (usize, usize) {
    let found = direct(files);
    let unres = found
        .iter()
        .filter(|f| matches!(f.severity, gob_rules::Severity::Unresolved))
        .count();
    (found.len() - unres, unres)
}

// frob:ticket 01M64230Q2FSG2WXTFT4ENDA4R
// frob:tests crates/grimble-check/src/log/lang_csharp.rs::scan
#[test]
fn cs_log_global_qualified_names_resolve() {
    let one = |t: &str| cs_log(&[("A.cs", t)]);
    assert_eq!(
        one("class A { void M() { global::System.Console.WriteLine(\"x\"); } }"),
        (1, 0)
    );
    assert_eq!(
        one(
            "global using static global::System.Console;\nclass A { void M() { WriteLine(\"x\"); } }"
        ),
        (1, 0)
    );
    assert_eq!(
        one("using C = global::System.Console;\nclass A { void M() { C.WriteLine(\"x\"); } }"),
        (1, 0)
    );
    assert_eq!(
        one("class A { void M() { var o = global::System.Console.Out; } }"),
        (1, 0)
    );
    assert_eq!(
        one("class A { void M() { global::Other.Console.WriteLine(\"x\"); } }"),
        (0, 0)
    );
}

// frob:ticket 01M64230Q2FSG2WXTFT4ENDA4R
// frob:tests crates/grimble-check/src/log/lang_csharp.rs::scan
#[test]
fn cs_log_reflection_resolves_or_reports() {
    let one = |t: &str| {
        cs_log(&[(
            "A.cs",
            &format!("using System;\nclass A {{ void M(string n, object o) {{ {t} }} }}"),
        )])
    };
    assert_eq!(
        one(
            "typeof(Console).GetMethod(\"WriteLine\", new[] { typeof(string) }).Invoke(null, new object[] { \"x\" });"
        ),
        (1, 0)
    );
    assert_eq!(
        one("var m = typeof(System.Console).GetMethod(\"WriteLine\");\nm.Invoke(null, null);"),
        (1, 0)
    );
    assert_eq!(
        one("Type.GetType(\"System.Console\").GetMethod(\"Write\").Invoke(null, null);"),
        (1, 0)
    );
    assert_eq!(
        one("typeof(Console).GetMethod(n).Invoke(null, null);"),
        (0, 1)
    );
    assert_eq!(
        one("Type.GetType(n).GetMethod(\"WriteLine\").Invoke(null, null);"),
        (0, 1)
    );
    assert_eq!(
        one("o.GetType().GetMethod(\"WriteLine\").Invoke(o, null);"),
        (0, 1)
    );
    assert_eq!(
        one("o.GetType().GetMethod(\"Frobnicate\").Invoke(o, null);"),
        (0, 0)
    );
    assert_eq!(
        one("typeof(Math).GetMethod(\"Abs\").Invoke(null, null);"),
        (0, 0)
    );
}

// frob:ticket 01M64230Q2FSG2WXTFT4ENDA4R
// frob:tests crates/grimble-check/src/log/lang_csharp.rs::scan
#[test]
fn cs_log_inherited_unity_print_resolves_or_reports() {
    let mono = |t: &str| cs_log(&[("A.cs", t)]);
    assert_eq!(
        mono("using UnityEngine;\nclass A : MonoBehaviour { void M() { print(\"x\"); } }"),
        (1, 0)
    );
    assert_eq!(
        mono(
            "class A : UnityEngine.MonoBehaviour { void M() { this.print(\"x\"); base.print(\"y\"); } }"
        ),
        (2, 0)
    );
    assert_eq!(
        mono("using U = UnityEngine;\nclass A : U.MonoBehaviour { void M() { print(\"x\"); } }"),
        (1, 0)
    );
    assert_eq!(
        mono(
            "using UnityEngine;\nclass A : global::UnityEngine.MonoBehaviour { void M() { print(\"x\"); } }"
        ),
        (1, 0)
    );
    // Indirect inheritance through project classes, across files.
    assert_eq!(
        cs_log(&[
            (
                "Base.cs",
                "using UnityEngine;\nclass Base : MonoBehaviour { }"
            ),
            ("Mid.cs", "class Mid : Base { }"),
            ("Leaf.cs", "class Leaf : Mid { void M() { print(\"x\"); } }"),
        ]),
        (1, 0)
    );
    // A same-named method of the class shadows the inherited helper.
    assert_eq!(
        mono(
            "using UnityEngine;\nclass A : MonoBehaviour { void print(string s) { } void M() { print(\"x\"); } }"
        ),
        (0, 0)
    );
    // Not a MonoBehaviour: a plain class with its own base.
    assert_eq!(
        mono("class A : IDisposable { void M() { print(\"x\"); } }"),
        (0, 0)
    );
    // A base the project cannot see may be a MonoBehaviour: undecidable, so reported.
    assert_eq!(
        mono("class A : NetworkBehaviour { void M() { print(\"x\"); } }"),
        (0, 1)
    );
}

// frob:ticket 01M64230Q2FSG2WXTFT4ENDA4R
// frob:tests crates/grimble-check/src/log/lang_csharp.rs::scan
#[test]
fn cs_log_native_import_output_functions_fire() {
    let one = |t: &str| cs_log(&[("A.cs", t)]);
    let pre = "using System.Runtime.InteropServices;\n";
    assert_eq!(
        one(&format!(
            "{pre}class N {{ [DllImport(\"libc\")] static extern int puts(string s); void M() {{ puts(\"x\"); }} }}"
        )),
        (1, 0)
    );
    assert_eq!(
        one(&format!(
            "{pre}class N {{ [DllImport(\"libc\", EntryPoint = \"write\")] static extern int sys_write(int fd, byte[] b, int n); void M() {{ sys_write(1, null, 0); }} }}"
        )),
        (1, 0)
    );
    assert_eq!(
        one(&format!(
            "{pre}class N {{ [DllImport(\"kernel32.dll\")] public static extern bool WriteConsole(int h); }}\nclass B {{ void M() {{ N.WriteConsole(1); }} }}"
        )),
        (1, 0)
    );
    assert_eq!(
        one(
            "class N { [System.Runtime.InteropServices.DllImport(\"libc\")] static extern int puts(string s); void M() { puts(\"x\"); } }"
        ),
        (1, 0)
    );
    // An unrelated native function is not output.
    assert_eq!(
        one(&format!(
            "{pre}class N {{ [DllImport(\"libc\")] static extern int getpid(); void M() {{ getpid(); }} }}"
        )),
        (0, 0)
    );
    // A computed EntryPoint cannot be resolved.
    assert_eq!(
        one(&format!(
            "{pre}class N {{ const string E = \"write\"; [DllImport(\"libc\", EntryPoint = E)] static extern int w(int fd); }}"
        )),
        (0, 1)
    );
}

/// Split a multi-file Python project's LOG001 results for `file` into (resolved, unresolved).
fn py_log(files: &[(&str, &str)], file: &str) -> (usize, usize) {
    let found: Vec<_> = direct(files)
        .into_iter()
        .filter(|f| f.file == file)
        .collect();
    let unres = found
        .iter()
        .filter(|f| matches!(f.severity, gob_rules::Severity::Unresolved))
        .count();
    (found.len() - unres, unres)
}

// frob:ticket 01M64230T88F77RTBYS9M3CY3C
// frob:tests crates/grimble-check/src/log/lang_python.rs::scan
#[test]
fn py_log_star_import_from_project_module_resolves() {
    let util = ("util.py", "say = print\n_hidden = print\n");
    assert_eq!(
        py_log(
            &[util, ("app.py", "from util import *\nsay('x')\n")],
            "app.py"
        ),
        (1, 0)
    );
    assert_eq!(
        py_log(
            &[util, ("pkg/app.py", "from util import *\n_hidden('x')\n")],
            "pkg/app.py"
        ),
        (0, 0)
    );
    // an explicit local definition after the star import shadows it
    assert_eq!(
        py_log(
            &[
                util,
                ("app.py", "from util import *\ndef say(x): pass\nsay('x')\n")
            ],
            "app.py"
        ),
        (0, 0)
    );
    // a star import of a project module that exports nothing hostile stays clean
    assert_eq!(
        py_log(
            &[
                ("util.py", "x = 1\n"),
                ("app.py", "from util import *\nsay('x')\n")
            ],
            "app.py"
        )
        .1,
        0
    );
    // a relative star import resolves through the package path
    assert_eq!(
        py_log(
            &[
                ("pkg/util.py", "say = print\n"),
                ("pkg/app.py", "from .util import *\nsay('x')\n"),
            ],
            "pkg/app.py"
        ),
        (1, 0)
    );
}

// frob:ticket 01M64230T88F77RTBYS9M3CY3C
// frob:tests crates/grimble-check/src/log/engine.rs::Project
#[test]
fn py_log_long_reexport_chain_resolves_to_origin() {
    let chain = [
        ("a.py", "say = print\n"),
        ("b.py", "from a import say\n"),
        ("c.py", "from b import say as talk\n"),
        ("d.py", "from c import talk as shout\n"),
        ("e.py", "from d import shout as yell\n"),
        ("app.py", "from e import yell\nyell('x')\n"),
    ];
    assert_eq!(py_log(&chain, "app.py"), (1, 0));
    let mut star = chain.to_vec();
    star[2] = ("c.py", "from b import *\n");
    star[3] = ("d.py", "from c import *\n");
    star[4] = ("e.py", "from d import *\n");
    star[5] = ("app.py", "import e\ne.say('x')\n");
    assert_eq!(py_log(&star, "app.py"), (1, 0));
}

// frob:ticket 01M64230T88F77RTBYS9M3CY3C
// frob:tests crates/grimble-check/src/log/lang_python.rs::scan
#[test]
fn py_log_exec_and_eval_of_constant_source_resolve() {
    let one = |t: &str| py_log(&[("a.py", t)], "a.py");
    assert_eq!(one("exec(\"print('x')\")\n"), (1, 0));
    assert_eq!(one("eval(\"print('x')\")\n"), (1, 0));
    assert_eq!(one("code = \"print('x')\"\nexec(code)\n"), (1, 0));
    assert_eq!(one("exec(\"pri\" \"nt('x')\")\n"), (1, 0));
    assert_eq!(
        one("exec(\"import sys\\nsys.stdout.write('x')\")\n"),
        (1, 0)
    );
    assert_eq!(one("exec(compile(\"print('x')\", 'f', 'exec'))\n"), (1, 0));
    assert_eq!(
        one("import builtins\nbuiltins.exec(\"print(1)\")\n"),
        (1, 0)
    );
    assert_eq!(one("exec(\"x = 1\")\n"), (0, 0));
    assert_eq!(one("exec(\"x = (\")\n"), (0, 1));
    // an unresolvable source is reported, never passed silently
    assert_eq!(one("exec(src)\n"), (0, 1));
    assert_eq!(one("def f(s):\n    eval(s)\n"), (0, 1));
    assert_eq!(one("exec(f\"print({1})\")\n"), (0, 1));
    assert_eq!(one("code = 'a'\ncode += 'b'\nexec(code)\n"), (0, 1));
    // a shadowing local named exec is not the builtin
    assert_eq!(one("def exec(s): pass\nexec(src)\n"), (0, 0));
}

//! Symbolic-resolution regression suite: every capability-detector case the adversarial audit
//! found CAUGHT is pinned here through the public checker API (`run` + `sibling_document`), per
//! language. Detection is symbolic (imports, aliases, receivers, re-exports), never lexical, so
//! each positive case is paired with a decoy that spells the name but is not the symbol.

// frob:ticket 01M63ZVCMA9J28JWXJEVNVD3Q1

#![allow(unused_crate_dependencies)]

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

/// What the checker said about one atom: certain use, or an unresolved (maybe) report.
#[derive(Debug, Default)]
struct Seen {
    certain: Vec<String>,
    unresolved: Vec<String>,
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// Check a repo with one trusted, grant-less node owning `src/**` and return the CAP001 atoms.
fn cap(files: &[(&str, &str)]) -> Seen {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n",
    );
    for (rel, text) in files {
        write(dir.path(), rel, text);
    }
    let r = run(dir.path(), &CheckOptions::default()).expect("run");
    let doc = sibling_document(&r);
    let mut seen = Seen::default();
    for f in doc["findings"].as_array().expect("findings") {
        if f["rule"] != "CAP001" {
            continue;
        }
        let msg = f["message"].as_str().expect("message");
        let atom = msg
            .split('`')
            .nth(if f["reason"].is_null() { 3 } else { 1 });
        let atom = atom.expect("atom in message").to_owned();
        if f["reason"].is_null() {
            seen.certain.push(atom);
        } else {
            seen.unresolved.push(atom);
        }
    }
    seen
}

fn one(rel: &str, text: &str) -> Seen {
    cap(&[(rel, text)])
}

/// Assert every `(label, source)` is a certain use of `atom`.
fn all_certain(rel: &str, atom: &str, cases: &[(&str, &str)]) {
    for (label, src) in cases {
        let s = one(rel, src);
        assert!(
            s.certain.iter().any(|a| a == atom),
            "{label}: expected certain {atom}, got {s:?}\n{src}"
        );
    }
}

/// Assert every `(label, source)` is reported (certain or unresolved), never silently clean.
fn all_reported(rel: &str, cases: &[(&str, &str)]) {
    for (label, src) in cases {
        let s = one(rel, src);
        assert!(
            !s.certain.is_empty() || !s.unresolved.is_empty(),
            "{label}: silently clean\n{src}"
        );
    }
}

/// Assert every `(label, source)` raises nothing (a decoy that only spells the name).
fn all_clean(rel: &str, cases: &[(&str, &str)]) {
    for (label, src) in cases {
        let s = one(rel, src);
        assert!(
            s.certain.is_empty() && s.unresolved.is_empty(),
            "{label}: decoy flagged {s:?}\n{src}"
        );
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn python_imports_aliases_and_renames_resolve_to_the_origin() {
    all_certain(
        "src/x.py",
        "process.spawn",
        &[
            (
                "plain",
                "import subprocess\ndef go(c):\n    subprocess.run(c)\n",
            ),
            (
                "as-alias",
                "import subprocess as s\ndef go(c):\n    s.run(c)\n",
            ),
            (
                "from-import",
                "from subprocess import run\ndef go(c):\n    run(c)\n",
            ),
            (
                "from-import rename",
                "from subprocess import run as r\ndef go(c):\n    r(c)\n",
            ),
            (
                "assignment alias of a function",
                "import subprocess\nr = subprocess.run\ndef go(c):\n    r(c)\n",
            ),
            (
                "alias chain",
                "import subprocess\na = subprocess.run\nb = a\ndef go(c):\n    b(c)\n",
            ),
            (
                "alias passed as a value",
                "from subprocess import run\ndef go(c):\n    return list(map(run, c))\n",
            ),
            (
                "wildcard import",
                "from subprocess import *\ndef go(c):\n    run(c)\n",
            ),
            (
                "os.system via wildcard",
                "from os import *\ndef go(c):\n    system(c)\n",
            ),
            ("os.popen", "import os\ndef go(c):\n    os.popen(c)\n"),
            (
                "__import__ literal",
                "def go(c):\n    __import__(\"subprocess\").run(c)\n",
            ),
            (
                "__import__ literal os",
                "def go(c):\n    __import__(\"os\").system(c)\n",
            ),
            (
                "getattr literal on module",
                "import subprocess\ndef go(c):\n    getattr(subprocess, \"run\")(c)\n",
            ),
            (
                "importlib literal",
                "import importlib\ndef go(c):\n    importlib.import_module(\"subprocess\").run(c)\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn python_builtin_aliases_and_nfkc_spellings_resolve() {
    all_certain(
        "src/x.py",
        "fs.read",
        &[
            ("local alias", "def go(p):\n    o = open\n    return o(p)\n"),
            ("module alias", "o = open\ndef go(p):\n    return o(p)\n"),
            (
                "builtins module",
                "import builtins\ndef go(p):\n    return builtins.open(p)\n",
            ),
            (
                "map over builtin",
                "def go(f):\n    return list(map(open, f))\n",
            ),
        ],
    );
    all_reported(
        "src/x.py",
        &[(
            "nfkc fullwidth subprocess call",
            "import subprocess\ndef go(c):\n    subprocess.\u{ff52}\u{ff55}\u{ff4e}(c)\n",
        )],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn python_computed_and_dynamic_forms_are_reported_never_clean() {
    all_reported(
        "src/x.py",
        &[
            ("eval", "def go(c):\n    eval(c)\n"),
            ("exec", "def go(c):\n    exec(c)\n"),
            (
                "computed getattr name",
                "import subprocess\ndef go(n, c):\n    getattr(subprocess, n)(c)\n",
            ),
            (
                "computed import name",
                "def go(n):\n    return __import__(n)\n",
            ),
            (
                "computed importlib name",
                "import importlib\ndef go(n):\n    return importlib.import_module(n)\n",
            ),
            ("aliased eval", "e = eval\ndef go(c):\n    e(c)\n"),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn python_decoys_that_only_spell_the_name_are_clean() {
    all_clean(
        "src/x.py",
        &[
            (
                "local function named run",
                "def run(c):\n    return c\ndef go(c):\n    run(c)\n",
            ),
            (
                "parameter shadows wildcard name",
                "from subprocess import *\ndef go(run):\n    run(1)\n",
            ),
            (
                "string and comment",
                "def go():\n    s = \"subprocess.run(x)\"  # os.system('x')\n    return s\n",
            ),
            (
                "local class method named run",
                "class T:\n    def run(self):\n        return 1\ndef go():\n    T().run()\n",
            ),
            (
                "repository open",
                "def open(p):\n    return p\ndef go(p):\n    return open(p)\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn python_receiver_types_from_constructors_resolve() {
    all_certain(
        "src/x.py",
        "net.connect",
        &[
            (
                "socket constructor receiver",
                "import socket\ndef go(h):\n    s = socket.socket()\n    s.connect((h, 80))\n",
            ),
            (
                "socket from-import receiver",
                "from socket import socket\ndef go(h):\n    s = socket()\n    s.connect((h, 80))\n",
            ),
            (
                "create_connection",
                "import socket\ndef go(h):\n    socket.create_connection((h, 80))\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn python_cross_module_reexports_resolve_to_the_origin() {
    let s = cap(&[
        ("src/helpers.py", "from subprocess import run as launch\n"),
        (
            "src/x.py",
            "from helpers import launch\ndef go(c):\n    launch(c)\n",
        ),
    ]);
    assert!(s.certain.iter().any(|a| a == "process.spawn"), "{s:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_paths_aliases_and_receivers_resolve() {
    all_certain(
        "src/x.rs",
        "process.spawn",
        &[
            (
                "full path",
                "pub fn go() { let _ = std::process::Command::new(\"ls\").spawn(); }\n",
            ),
            (
                "use import",
                "use std::process::Command;\npub fn go() { let _ = Command::new(\"ls\").spawn(); }\n",
            ),
            (
                "use rename",
                "use std::process::Command as C;\npub fn go() { let _ = C::new(\"ls\").spawn(); }\n",
            ),
            (
                "module alias",
                "use std::process as p;\npub fn go() { let _ = p::Command::new(\"ls\").output(); }\n",
            ),
            (
                "type alias",
                "type C = std::process::Command;\npub fn go() { let _ = C::new(\"ls\").status(); }\n",
            ),
            (
                "function-local use",
                "pub fn go() { use std::process::Command; let _ = Command::new(\"ls\").spawn(); }\n",
            ),
        ],
    );
    all_certain(
        "src/x.rs",
        "fs.write",
        &[
            (
                "std::fs::write",
                "pub fn go() { let _ = std::fs::write(\"a\", \"b\"); }\n",
            ),
            (
                "renamed fs",
                "use std::fs as f;\npub fn go() { let _ = f::write(\"a\", \"b\"); }\n",
            ),
            (
                "imported fn rename",
                "use std::fs::write as w;\npub fn go() { let _ = w(\"a\", \"b\"); }\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_cross_file_alias_and_reexport_resolve() {
    let s = cap(&[
        (
            "src/lib.rs",
            "pub mod io;\nmod fsx;\npub fn go() { io::put(); }\n",
        ),
        (
            "src/io.rs",
            "pub use std::fs::write as put_file;\npub fn put() { let _ = put_file(\"a\", \"b\"); }\n",
        ),
    ]);
    assert!(s.certain.iter().any(|a| a == "fs.write"), "{s:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_decoys_and_unresolved_receivers_behave() {
    all_clean(
        "src/x.rs",
        &[
            (
                "local type named Command",
                "struct Command;\nimpl Command { fn new(_s: &str) -> Command { Command } fn spawn(&self) {} }\npub fn go() { Command::new(\"ls\").spawn(); }\n",
            ),
            (
                "local module named fs",
                "mod fs { pub fn write(_a: &str, _b: &str) {} }\npub fn go() { fs::write(\"a\", \"b\"); }\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn javascript_and_typescript_imports_resolve() {
    all_certain(
        "src/x.ts",
        "process.spawn",
        &[
            (
                "namespace import",
                "import * as cp from \"child_process\";\nexport function go(x: string) { cp.exec(x); }\n",
            ),
            (
                "named import",
                "import { exec } from \"child_process\";\nexport function go(x: string) { exec(x); }\n",
            ),
            (
                "renamed import with node: prefix",
                "import { exec as run } from \"node:child_process\";\nexport function go(x: string) { run(x); }\n",
            ),
            (
                "default import",
                "import cp from \"node:child_process\";\nexport function go(x: string) { cp.spawn(x); }\n",
            ),
            (
                "import equals require",
                "import cp = require(\"child_process\");\nexport function go(x: string) { cp.execSync(x); }\n",
            ),
        ],
    );
    all_certain(
        "src/x.js",
        "process.spawn",
        &[
            (
                "require",
                "const cp = require('child_process');\nfunction go(x) { cp.exec(x); }\n",
            ),
            (
                "destructured require",
                "const { exec } = require('child_process');\nfunction go(x) { exec(x); }\n",
            ),
            (
                "renamed destructure",
                "const { exec: run } = require('child_process');\nfunction go(x) { run(x); }\n",
            ),
            (
                "require through a variable",
                "const cp = require('child_process');\nconst c = cp;\nfunction go(x) { c.exec(x); }\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn javascript_dynamic_forms_are_reported_and_decoys_are_clean() {
    all_reported(
        "src/x.js",
        &[
            (
                "computed require",
                "function go(n) { return require(n); }\n",
            ),
            ("eval", "function go(c) { eval(c); }\n"),
            (
                "Function constructor",
                "function go(c) { return new Function(c)(); }\n",
            ),
            (
                "aliased eval",
                "const e = eval;\nfunction go(c) { e(c); }\n",
            ),
            (
                "computed import",
                "async function go(n) { return import(n); }\n",
            ),
        ],
    );
    all_clean(
        "src/x.js",
        &[
            (
                "parameter named require",
                "function go(require) { return require('x'); }\n",
            ),
            (
                "parameter named eval",
                "function go(eval) { return eval('x'); }\n",
            ),
            (
                "local object with exec",
                "const o = { exec(x) { return x; } };\nfunction go(x) { o.exec(x); }\n",
            ),
        ],
    );
}

// frob:ticket 01M67HFSK2YWDBR37W8NTP5BXK
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn javascript_dynamic_import_then_callback_resolves_symbolically() {
    all_certain(
        "src/x.js",
        "process.spawn",
        &[
            (
                "top level arrow",
                "import('child_process').then(m => m.exec('x'));\n",
            ),
            (
                "inside a function",
                "function go(x) { return import('child_process').then(m => m.exec(x)); }\n",
            ),
            (
                "function expression and renamed parameter",
                "function go(x) { import('node:child_process').then(function (cp) { cp.spawn(x); }); }\n",
            ),
            (
                "destructured parameter",
                "function go(x) { import('child_process').then(({ exec }) => exec(x)); }\n",
            ),
            (
                "two imports sharing a parameter name",
                "function a() { import('os').then(m => m.cpus()); }\nfunction go(x) { import('child_process').then(m => m.exec(x)); }\n",
            ),
        ],
    );
    all_reported(
        "src/x.js",
        &[
            (
                "named callback at top level",
                "function h(m) { return m.exec('x'); }\nimport('child_process').then(h);\n",
            ),
            (
                "named callback inside a function",
                "function go(h) { return import('child_process').then(h); }\n",
            ),
        ],
    );
    all_clean(
        "src/x.js",
        &[
            (
                "then on a non-import promise",
                "function go(p, x) { return p.then(m => m.exec(x)); }\n",
            ),
            (
                "then on a call that is not an import",
                "function go(x) { return load('child_process').then(m => m.exec(x)); }\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn csharp_using_and_reflection_forms_resolve_or_report() {
    all_certain(
        "src/x.cs",
        "process.spawn",
        &[
            (
                "using namespace",
                "using System.Diagnostics;\nclass C { void Go(string x) { Process.Start(x); } }\n",
            ),
            (
                "fully qualified",
                "class C { void Go(string x) { System.Diagnostics.Process.Start(x); } }\n",
            ),
            (
                "using alias",
                "using P = System.Diagnostics.Process;\nclass C { void Go(string x) { P.Start(x); } }\n",
            ),
            (
                "global-qualified",
                "class C { void Go(string x) { global::System.Diagnostics.Process.Start(x); } }\n",
            ),
        ],
    );
    all_reported(
        "src/x.cs",
        &[
            (
                "dllimport native interop",
                "using System.Runtime.InteropServices;\nclass C { [DllImport(\"libc\")] static extern int system(string c); void Go(string c) { system(c); } }\n",
            ),
            (
                "assembly load from path",
                "using System.Reflection;\nclass C { void Go(string p) { Assembly.LoadFrom(p); } }\n",
            ),
        ],
    );
    all_clean(
        "src/x.cs",
        &[(
            "local class named Process",
            "class Process { public static void Start(string x) {} }\nclass C { void Go(string x) { Process.Start(x); } }\n",
        )],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_unsafe_and_native_interop_forms_are_reported() {
    all_reported(
        "src/x.rs",
        &[
            (
                "extern block call",
                "extern \"C\" { fn getpid() -> i32; }\npub fn go() -> i32 { unsafe { getpid() } }\n",
            ),
            (
                "transmute",
                "pub fn go() -> u32 { unsafe { std::mem::transmute::<f32, u32>(1.0) } }\n",
            ),
        ],
    );
}

/// Every miss class of the audit is a ticket under the grimble audit epic ~FZ3G6WK (milestone
/// 0.533.0); the caught classes are pinned by the tests above. This test documents the classification so a reader can map classes to tickets.
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn audit_miss_classes_are_tracked_as_tickets_under_the_epic() {
    // (miss class, ticket)
    let classes = [
        ("python wildcard import", "~G68NRS1"),
        ("python local alias of a builtin", "~8B9HSHH"),
        ("python computed attribute and import lookups", "~6CV37RW"),
        ("python dynamic code evaluation", "~T78E2WZ"),
        (
            "python re-export, definition order, conditional binding",
            "~7XKRQQ2",
        ),
        ("python constructor receiver types", "~BG4T2RC"),
        ("python registry entry points", "~R269X33"),
        ("python NFKC identifiers", "~7VYCFGM"),
        ("same-named method on unrelated class", "~313NY13"),
        ("capability reached through another node", "~0T8Z2BM"),
        ("ts js go java c csharp shell detection", "~PKW7X2J"),
        ("reflection, native interop, eval forms", "~S3EC85S"),
        ("rust alias, re-export, macro_rules, include!", "~D37NDVN"),
        ("rust receiver types", "~55XRPGG"),
        ("log javascript output forms", "~CS763EX"),
        ("log csharp output forms", "~4ENDA4R"),
        ("log python star import and chains", "~9M3CY3C"),
        ("js import('lit').then(cb) callback parameter", "~NTP5BXK"),
    ];
    assert!(
        classes
            .iter()
            .all(|(_, t)| t.starts_with('~') && t.len() == 8)
    );
}

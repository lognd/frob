//! Symbolic-resolution regression suite: every capability-detector case the adversarial audit
//! found CAUGHT is pinned here through the public checker API (`run` + `sibling_document`), per
//! language. Detection is symbolic (imports, aliases, receivers, re-exports), never lexical, so
//! each positive case is paired with a decoy that spells the name but is not the symbol.

// frob:ticket 01M63ZVCMA9J28JWXJEVNVD3Q1
// frob:ticket 01M64VBRCNYQ3WC895EYXR6GME

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

// frob:ticket 01M64VBRNZ32N2JR6EYVVKBEKG
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn csharp_dllimport_and_libraryimport_externs_are_ffi_uses() {
    all_certain(
        "src/x.cs",
        "ffi",
        &[
            (
                "dllimport via using",
                "using System.Runtime.InteropServices;\nclass C { [DllImport(\"libc\")] static extern int system(string c); }\n",
            ),
            (
                "dllimport attribute suffix",
                "using System.Runtime.InteropServices;\nclass C { [DllImportAttribute(\"libc\")] static extern int system(string c); }\n",
            ),
            (
                "dllimport fully qualified",
                "class C { [System.Runtime.InteropServices.DllImport(\"libc\")] static extern int system(string c); }\n",
            ),
            (
                "libraryimport partial",
                "using System.Runtime.InteropServices;\nclass C { [LibraryImport(\"libc\")] static partial int system(string c); }\n",
            ),
            (
                "dllimport via using alias",
                "using I = System.Runtime.InteropServices;\nclass C { [I.DllImport(\"libc\")] static extern int system(string c); }\n",
            ),
            (
                "dllimport in an attribute list with others",
                "using System.Runtime.InteropServices;\nclass C { [SuppressGCTransition, DllImport(\"libc\")] static extern int f(); }\n",
            ),
        ],
    );
    all_clean(
        "src/x.cs",
        &[
            (
                "local attribute named DllImport",
                "class DllImport : System.Attribute { public DllImport(string s) {} }\nclass C { [DllImport(\"x\")] static void f() {} }\n",
            ),
            (
                "extern without an import attribute is not an ffi spelling",
                "class C { static void f() {} }\n",
            ),
        ],
    );
}

// frob:ticket 01M64VBRNZ32N2JR6EYVVKBEKG
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn csharp_typed_parameter_and_field_receivers_resolve_or_report() {
    all_certain(
        "src/x.cs",
        "net.connect",
        &[
            (
                "typed parameter",
                "using System.Net.Http;\nclass C { async void Go(HttpClient c) { await c.GetAsync(\"u\"); } }\n",
            ),
            (
                "typed field",
                "using System.Net.Http;\nclass C { private readonly HttpClient _c = new HttpClient(); async void Go() { await _c.GetAsync(\"u\"); } }\n",
            ),
            (
                "typed field without initializer",
                "using System.Net.Http;\nclass C { HttpClient _c; async void Go() { await _c.GetStringAsync(\"u\"); } }\n",
            ),
            (
                "field accessed through this",
                "using System.Net.Http;\nclass C { HttpClient _c; async void Go() { await this._c.GetAsync(\"u\"); } }\n",
            ),
            (
                "typed auto property",
                "using System.Net.Http;\nclass C { HttpClient Http { get; } async void Go() { await Http.GetAsync(\"u\"); } }\n",
            ),
            (
                "constructor parameter",
                "using System.Net.Http;\nclass C { C(HttpClient c) { c.GetAsync(\"u\"); } }\n",
            ),
            (
                "lambda typed parameter",
                "using System.Net.Http;\nclass C { void Go() { System.Action<HttpClient> f = (HttpClient c) => c.GetAsync(\"u\"); } }\n",
            ),
        ],
    );
    all_reported(
        "src/x.cs",
        &[
            (
                "dynamic parameter receiver",
                "class C { void Go(dynamic c) { c.GetAsync(\"u\"); } }\n",
            ),
            (
                "dynamic local receiver",
                "class C { void Go() { dynamic c = Make(); c.GetAsync(\"u\"); } object Make() => null; }\n",
            ),
        ],
    );
    all_clean(
        "src/x.cs",
        &[
            (
                "local type named HttpClient",
                "class HttpClient { public void GetAsync(string u) {} }\nclass C { void Go(HttpClient c) { c.GetAsync(\"u\"); } }\n",
            ),
            (
                "typed parameter of an unrelated type",
                "class Repo { public void GetAsync(string u) {} }\nclass C { void Go(Repo r) { r.GetAsync(\"u\"); } }\n",
            ),
        ],
    );
}

// frob:ticket 01M64VBRNZ32N2JR6EYVVKBEKG
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn typescript_express_app_listen_is_a_net_listen_use() {
    all_certain(
        "src/x.ts",
        "net.listen",
        &[
            (
                "default import called",
                "import express from 'express';\nconst app = express();\napp.listen(3000);\n",
            ),
            (
                "renamed default import",
                "import ex from 'express';\nconst server = ex();\nserver.listen(3000);\n",
            ),
            (
                "namespace import",
                "import * as express from 'express';\nconst app = express();\napp.listen(3000);\n",
            ),
            (
                "require",
                "const express = require('express');\nconst app = express();\napp.listen(3000);\n",
            ),
            (
                "inside a function",
                "import express from 'express';\nexport function go() { const app = express(); app.listen(8080, () => {}); }\n",
            ),
            (
                "typed parameter",
                "import express, { Express } from 'express';\nexport function go(app: Express) { app.listen(8080); }\n",
            ),
            (
                "chained",
                "import express from 'express';\nexpress().listen(3000);\n",
            ),
        ],
    );
    all_clean(
        "src/x.ts",
        &[
            (
                "listen on an object that is not from express",
                "const app = { listen(_p: number) {} };\napp.listen(3000);\n",
            ),
            (
                "express imported but listen on a local class",
                "import express from 'express';\nclass Srv { listen(_p: number) {} }\nexport const s = new Srv();\ns.listen(1);\n",
            ),
        ],
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

// Go (audit g01, ticket 01M64VBRCNYQ3WC895EYXR6GME): uses resolve through the import path, so
// aliases and dot imports name the package and a local `exec` names nothing.
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn go_imports_aliases_and_dot_imports_resolve_to_the_package() {
    all_certain(
        "src/x.go",
        "process.spawn",
        &[
            (
                "g01 plain",
                "package m\nimport \"os/exec\"\nfunc Run(c string) { exec.Command(c).Run() }\n",
            ),
            (
                "aliased",
                "package m\nimport e \"os/exec\"\nfunc Run(c string) { e.Command(c).Run() }\n",
            ),
            (
                "dot import",
                "package m\nimport . \"os/exec\"\nfunc Run(c string) { Command(c).Run() }\n",
            ),
            (
                "grouped",
                "package m\nimport (\n\t\"fmt\"\n\t\"os/exec\"\n)\nfunc Run(c string) { fmt.Println(); exec.CommandContext(nil, c) }\n",
            ),
            (
                "function value",
                "package m\nimport \"os/exec\"\nfunc Run(c string) { run := exec.Command; run(c) }\n",
            ),
        ],
    );
    all_certain(
        "src/x.go",
        "env.read",
        &[
            (
                "os.Getenv",
                "package m\nimport \"os\"\nfunc K() string { return os.Getenv(\"K\") }\n",
            ),
            (
                "aliased os",
                "package m\nimport o \"os\"\nfunc K() string { return o.Getenv(\"K\") }\n",
            ),
        ],
    );
    all_certain(
        "src/x.go",
        "net.connect",
        &[
            (
                "net/http",
                "package m\nimport \"net/http\"\nfunc G() { http.Get(\"u\") }\n",
            ),
            (
                "aliased http",
                "package m\nimport h \"net/http\"\nfunc G() { h.Get(\"u\") }\n",
            ),
            (
                "net",
                "package m\nimport \"net\"\nfunc G() { net.Dial(\"tcp\", \"h:1\") }\n",
            ),
        ],
    );
    all_certain(
        "src/x.go",
        "net.listen",
        &[
            (
                "net.Listen",
                "package m\nimport \"net\"\nfunc G() { net.Listen(\"tcp\", \":1\") }\n",
            ),
            (
                "ListenAndServe",
                "package m\nimport \"net/http\"\nfunc G() { http.ListenAndServe(\":1\", nil) }\n",
            ),
        ],
    );
    all_certain(
        "src/x.go",
        "ffi",
        &[(
            "plugin.Open",
            "package m\nimport \"plugin\"\nfunc L(p string) { plugin.Open(p) }\n",
        )],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn go_decoys_that_only_spell_the_name_raise_nothing() {
    all_clean(
        "src/x.go",
        &[
            (
                "local variable named exec",
                "package m\nimport \"os/exec\"\ntype fake struct{}\nfunc (fake) Command(string) {}\nfunc Run() { exec := fake{}; exec.Command(\"ls\") }\n",
            ),
            (
                "parameter named os",
                "package m\nimport \"os\"\ntype env interface{ Getenv(string) string }\nfunc K(os env) string { return os.Getenv(\"K\") }\n",
            ),
            (
                "blank import",
                "package m\nimport _ \"os/exec\"\nfunc Run() { exec.Command(\"ls\") }\n",
            ),
            (
                "unimported package name",
                "package m\nfunc Run(exec interface{ Command(string) }) { exec.Command(\"ls\") }\n",
            ),
            (
                "comment and string",
                "package m\n// exec.Command(\"ls\") os.Getenv\nvar s = \"exec.Command plugin.Open\"\n",
            ),
            (
                "other package with the same last segment",
                "package m\nimport \"example.com/exec\"\nfunc Run() { exec.Command(\"ls\") }\n",
            ),
        ],
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn go_unresolvable_forms_are_reported_never_silent() {
    all_reported(
        "src/x.go",
        &[
            (
                "reassigned function value",
                "package m\nimport \"os/exec\"\nfunc Run(f func(string), c string) {\n\trun := exec.Command\n\trun = nil\n\trun(c)\n}\n",
            ),
            (
                "dot import of an unknown package beside a known one",
                "package m\nimport (\n\t. \"os/exec\"\n\t. \"example.com/helpers\"\n)\nfunc Run(c string) { Command(c) }\n",
            ),
        ],
    );
}

/// A Java class `A` with `imports` on top and `body` inside one method.
fn java(imports: &str, body: &str) -> String {
    format!("{imports}\nclass A {{\n  void f(String c) throws Exception {{\n    {body}\n  }}\n}}\n")
}

// Java (audit j01, ticket 01M64VBRFWT0EKCG800ANRZDTE): uses resolve through single-type,
// wildcard, static and fully qualified names, so a local `ProcessBuilder` names nothing.
// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn java_imports_wildcards_static_and_qualified_names_resolve() {
    let spawn: Vec<(&str, String)> = vec![
        ("j01 plain", java("", "Runtime.getRuntime().exec(c);")),
        ("ProcessBuilder", java("", "new ProcessBuilder(c).start();")),
        (
            "fully qualified",
            java("", "java.lang.Runtime.getRuntime().exec(c);"),
        ),
        (
            "typed local",
            java("", "Runtime rt = Runtime.getRuntime();\n    rt.exec(c);"),
        ),
        (
            "var alias",
            java("", "var rt = Runtime.getRuntime();\n    rt.exec(c);"),
        ),
    ];
    let spawn: Vec<(&str, &str)> = spawn.iter().map(|(l, s)| (*l, s.as_str())).collect();
    all_certain("src/A.java", "process.spawn", &spawn);
    let read: Vec<(&str, String)> = vec![
        (
            "single-type import",
            java("import java.nio.file.Files;", "Files.readAllBytes(null);"),
        ),
        (
            "wildcard import",
            java("import java.nio.file.*;", "Files.readString(null);"),
        ),
        (
            "java.io",
            java("import java.io.*;", "new FileInputStream(c);"),
        ),
        (
            "fully qualified type",
            java("", "java.io.FileReader r = new java.io.FileReader(c);"),
        ),
    ];
    let read: Vec<(&str, &str)> = read.iter().map(|(l, s)| (*l, s.as_str())).collect();
    all_certain("src/A.java", "fs.read", &read);
    all_certain(
        "src/A.java",
        "fs.write",
        &[(
            "Files.delete",
            &java("import java.nio.file.Files;", "Files.delete(null);"),
        )],
    );
    let net: Vec<(&str, String)> = vec![
        (
            "HttpClient",
            java(
                "import java.net.http.HttpClient;",
                "HttpClient.newHttpClient();",
            ),
        ),
        ("Socket", java("import java.net.*;", "new Socket(c, 1);")),
    ];
    let net: Vec<(&str, &str)> = net.iter().map(|(l, s)| (*l, s.as_str())).collect();
    all_certain("src/A.java", "net.connect", &net);
    all_certain(
        "src/A.java",
        "net.listen",
        &[(
            "ServerSocket",
            &java("import java.net.ServerSocket;", "new ServerSocket(1);"),
        )],
    );
    let env: Vec<(&str, String)> = vec![
        ("System.getenv", java("", "System.getenv(c);")),
        (
            "static import",
            java("import static java.lang.System.getenv;", "getenv(c);"),
        ),
        (
            "static wildcard",
            java("import static java.lang.System.*;", "getenv(c);"),
        ),
    ];
    let env: Vec<(&str, &str)> = env.iter().map(|(l, s)| (*l, s.as_str())).collect();
    all_certain("src/A.java", "env.read", &env);
    all_certain(
        "src/A.java",
        "ffi",
        &[(
            "System.loadLibrary",
            &java("", "System.loadLibrary(\"x\");"),
        )],
    );
}

// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn java_decoys_that_only_spell_the_name_raise_nothing() {
    let own = "class ProcessBuilder { void start() {} }\nclass A { void f() { new ProcessBuilder().start(); } }\n";
    let foreign = java(
        "import com.example.ProcessBuilder;",
        "new ProcessBuilder(c).start();",
    );
    let comment = java(
        "",
        "// Runtime.getRuntime().exec(c)\n    String s = \"System.getenv\";",
    );
    let unbound = java("", "Files.readAllBytes(null);");
    all_clean(
        "src/A.java",
        &[
            ("local class named ProcessBuilder", own),
            ("import of another package's ProcessBuilder", &foreign),
            ("comment and string", &comment),
            ("same-package name with no import", &unbound),
        ],
    );
}

// frob:ticket 01M64VBRFWT0EKCG800ANRZDTE
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn java_unresolvable_forms_are_reported_never_silent() {
    let moved = java(
        "",
        "var rt = Runtime.getRuntime();\n    rt = null;\n    rt.exec(c);",
    );
    let unknown = java("import com.example.*;", "Files.readAllBytes(null);");
    let reflect = java("", "Class.forName(c);");
    let loader = java("", "ClassLoader.getSystemClassLoader().loadClass(c);");
    all_reported(
        "src/A.java",
        &[
            ("reassigned alias", &moved),
            ("wildcard of an unknown package", &unknown),
            ("computed Class.forName", &reflect),
            ("ClassLoader", &loader),
        ],
    );
}

/// A C file with `includes` on top and `body` inside one function.
fn c(includes: &str, body: &str) -> String {
    format!("{includes}\nvoid f(const char *c) {{\n  {body}\n}}\n")
}

// C and C++ (audit cc01, ticket 01M64VBRHX20P2EJGQ2S1VG0FG): uses resolve through the `#include`
// that supplies the function and the local scope, so a locally defined `system` names nothing.
// frob:ticket 01M64VBRHX20P2EJGQ2S1VG0FG
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c_and_cpp_calls_resolve_through_their_includes() {
    let atoms: Vec<(&str, &str, String)> = vec![
        (
            "process.spawn",
            "cc01 system",
            c("#include <stdlib.h>", "system(c);"),
        ),
        (
            "process.spawn",
            "popen",
            c("#include <stdio.h>", "popen(c, \"r\");"),
        ),
        (
            "process.spawn",
            "execv",
            c("#include <unistd.h>", "execv(c, 0);"),
        ),
        (
            "fs.read",
            "fopen",
            c("#include <stdio.h>", "fopen(c, \"r\");"),
        ),
        ("fs.write", "open", c("#include <fcntl.h>", "open(c, 1);")),
        (
            "net.connect",
            "socket",
            c("#include <sys/socket.h>", "socket(2, 1, 0);"),
        ),
        (
            "net.connect",
            "connect",
            c("#include <sys/socket.h>", "connect(3, 0, 0);"),
        ),
        (
            "net.listen",
            "bind",
            c("#include <sys/socket.h>", "bind(3, 0, 0);"),
        ),
        ("env.read", "getenv", c("#include <stdlib.h>", "getenv(c);")),
        ("ffi", "dlopen", c("#include <dlfcn.h>", "dlopen(c, 1);")),
        (
            "process.spawn",
            "alias then call",
            c(
                "#include <stdlib.h>",
                "int (*r)(const char *) = system;\n  r(c);",
            ),
        ),
    ];
    for (atom, label, src) in &atoms {
        all_certain("src/a.c", atom, &[(label, src)]);
    }
    let cpp: Vec<(&str, &str, String)> = vec![
        (
            "process.spawn",
            "std::system",
            c("#include <cstdlib>", "std::system(c);"),
        ),
        (
            "env.read",
            "global ::getenv",
            c("#include <cstdlib>", "::getenv(c);"),
        ),
        (
            "process.spawn",
            "plain system",
            c("#include <stdlib.h>", "system(c);"),
        ),
    ];
    for (atom, label, src) in &cpp {
        all_certain("src/a.cpp", atom, &[(label, src)]);
    }
}

// frob:ticket 01M64VBRHX20P2EJGQ2S1VG0FG
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c_decoys_that_only_spell_the_name_raise_nothing() {
    let own = "#include <stdlib.h>\nint system(const char *c) { return 0; }\nvoid f() { system(\"x\"); }\n";
    let local = c("#include <stdlib.h>", "int getenv = 1; (void)getenv;");
    let text =
        "#include <stdlib.h>\n// system(x)\nconst char *s = \"system(x)\";\n/* getenv(y) */\n";
    let other = c("#include <stdlib.h>", "mysystem(c);");
    let cpp_other = c("#include <cstdlib>", "other::system(c);");
    all_clean(
        "src/a.c",
        &[
            ("local definition named system", own),
            ("local variable named getenv", &local),
            ("comment and string", text),
            ("unrelated name", &other),
        ],
    );
    all_clean("src/a.cpp", &[("foreign namespace", &cpp_other)]);
}

// frob:ticket 01M64VBRHX20P2EJGQ2S1VG0FG
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c_unresolvable_forms_are_reported_never_silent() {
    let field = "#include <stdlib.h>\nstruct S { int (*run)(const char *); };\nvoid f(struct S *s) { s->run(\"x\"); }\n";
    let ptr = "#include <stdlib.h>\nvoid f(int (*fp)(const char *)) { fp(\"x\"); }\n";
    let table = "#include <stdlib.h>\nint (*tbl[1])(const char *);\nvoid f() { tbl[0](\"x\"); }\n";
    let mac = "#include <stdlib.h>\n#define RUN system\nvoid f() { RUN(\"x\"); }\n";
    let fnmac = "#define RUN(c) system(c)\nvoid f() { RUN(\"x\"); }\n";
    let implicit = "void f() { system(\"x\"); }\n";
    all_reported(
        "src/a.c",
        &[
            ("function pointer field", field),
            ("function pointer parameter", ptr),
            ("function pointer table", table),
            ("object-like macro", mac),
            ("function-like macro", fnmac),
            ("no header supplies the name", implicit),
        ],
    );
}

// ---------------------------------------------------------------------------------------------
// Aliasing / shadowing / computed-name probes (ticket 01M67VHPGMWP2ZSN378AH9XAGZ): one of each per
// supported language. Aliases and literal-folded names resolve to the origin (certain); a local
// that shadows an import names nothing; a name the checker cannot fold is Unresolved, never clean.
// Cases the checker silently passes today are `#[ignore]`d with their follow-up ticket.
// ---------------------------------------------------------------------------------------------

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_python_alias_shadow_and_computed_name() {
    all_certain(
        "src/x.py",
        "process.spawn",
        &[
            ("alias", "import os as o\ndef go(c):\n    o.system(c)\n"),
            (
                "literal __import__",
                "def go(c):\n    __import__(\"os\").system(c)\n",
            ),
            (
                "folded __import__ concatenation",
                "def go(c):\n    __import__(\"o\" + \"s\").system(c)\n",
            ),
            (
                "literal getattr",
                "import os\ndef go(c):\n    getattr(os, \"system\")(c)\n",
            ),
            (
                "folded getattr concatenation",
                "import os\ndef go(c):\n    getattr(os, \"sys\" + \"tem\")(c)\n",
            ),
        ],
    );
    // A local rebinding or parameter named like the import is over-approximated as the import
    // (a false positive, the safe direction): it must at least be reported.
    all_reported(
        "src/x.py",
        &[
            (
                "local rebinding of the import name",
                "import subprocess\ndef go(c):\n    subprocess = Fake()\n    subprocess.run(c)\n",
            ),
            (
                "parameter named like the import",
                "import subprocess\ndef go(subprocess, c):\n    subprocess.run(c)\n",
            ),
        ],
    );
    all_reported(
        "src/x.py",
        &[(
            "runtime-computed import name",
            "def go(n, c):\n    __import__(n).system(c)\n",
        )],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_rust_alias_shadow_and_computed_name() {
    all_certain(
        "src/x.rs",
        "process.spawn",
        &[
            (
                "use-as alias",
                "use std::process::Command as C;\npub fn go(c: &str) { C::new(c); }\n",
            ),
            (
                "folded concat! argument is irrelevant to the path",
                "pub fn go(c: &str) { std::process::Command::new(concat!(\"s\", \"h\")); }\n",
            ),
        ],
    );
    all_clean(
        "src/x.rs",
        &[
            (
                "local module shadows the name",
                "mod Command { pub fn new(_c: &str) {} }\npub fn go(c: &str) { Command::new(c); }\n",
            ),
            (
                "let binding shadows the import",
                "use std::process::Command;\npub fn go(c: &str) { let Command = Fake; Command.new(c); }\n",
            ),
        ],
    );
    all_certain(
        "src/x.rs",
        "ffi",
        &[(
            "computed library name",
            "pub fn go(n: &str) { libloading::Library::new(n); }\n",
        )],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_javascript_alias_shadow_and_computed_name() {
    all_certain(
        "src/x.js",
        "process.spawn",
        &[
            (
                "import-as alias",
                "import { exec as e } from 'child_process';\nexport function go(c){ e(c); }\n",
            ),
            (
                "destructured rename of a require",
                "const cp = require('child_process');\nconst { exec: e } = cp;\nfunction go(c){ e(c); }\n",
            ),
            (
                "folded module name",
                "const m = 'child_' + 'process';\nconst cp = require(m);\nfunction go(c){ cp.exec(c); }\n",
            ),
            (
                "folded member name",
                "const cp = require('child_process');\nfunction go(c){ cp['ex'+'ec'](c); }\n",
            ),
            (
                "literal bracket member",
                "function go(c){ require('child_process')['exec'](c); }\n",
            ),
        ],
    );
    all_clean(
        "src/x.js",
        &[(
            "parameter shadows the import",
            "import { exec } from 'child_process';\nexport function go(exec, c){ exec(c); }\n",
        )],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_typescript_alias_shadow_and_computed_name() {
    all_certain(
        "src/x.ts",
        "process.spawn",
        &[(
            "import-as alias",
            "import { exec as e } from 'child_process';\nexport function go(c: string){ e(c); }\n",
        )],
    );
    all_clean(
        "src/x.ts",
        &[(
            "typed parameter shadows the import",
            "import { exec } from 'child_process';\nexport function go(exec: (c: string) => void, c: string){ exec(c); }\n",
        )],
    );
    let s = one(
        "src/x.ts",
        "import * as cp from 'child_process';\nexport function go(n: string, c: string){ (cp as any)[n](c); }\n",
    );
    assert!(
        s.unresolved.iter().any(|a| a == "process.spawn"),
        "runtime-computed member: expected unresolved process.spawn, got {s:?}"
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_csharp_alias_shadow_and_computed_name() {
    all_certain(
        "src/X.cs",
        "process.spawn",
        &[
            (
                "using alias",
                "using P = System.Diagnostics.Process;\nclass A { void Go(string c) { P.Start(c); } }\n",
            ),
            (
                "literal reflection type name",
                "class A { void Go(string c) { System.Type.GetType(\"System.Diagnostics.Process\").GetMethod(\"Start\").Invoke(null, null); } }\n",
            ),
        ],
    );
    all_clean(
        "src/X.cs",
        &[(
            "local class shadows the imported one",
            "using System.Diagnostics;\nclass Process { public static void Start(string c) {} }\nclass A { void Go(string c) { Process.Start(c); } }\n",
        )],
    );
    all_reported(
        "src/X.cs",
        &[(
            "runtime-computed type name",
            "class A { void Go(string n, string c) { System.Type.GetType(n).GetMethod(\"Start\").Invoke(null, null); } }\n",
        )],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_go_alias_shadow_and_computed_name() {
    all_certain(
        "src/x.go",
        "process.spawn",
        &[(
            "import alias",
            "package m\nimport e \"os/exec\"\nfunc Run(c string) { e.Command(c) }\n",
        )],
    );
    all_clean(
        "src/x.go",
        &[
            (
                "local variable shadows the package",
                "package m\nimport \"os/exec\"\nfunc Run(c string) { exec := fake{}; exec.Command(c) }\n",
            ),
            (
                "parameter shadows the package",
                "package m\nimport \"os/exec\"\nfunc Run(exec fake, c string) { exec.Command(c) }\n",
            ),
        ],
    );
    all_certain(
        "src/x.go",
        "ffi",
        &[(
            "computed plugin path",
            "package m\nimport \"plugin\"\nfunc Run(n string) { plugin.Open(n) }\n",
        )],
    );
}

// frob:ticket 01M68811YBPN99TW7VD4RA3JAJ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_go_reflect_method_by_name_is_reported() {
    all_reported(
        "src/x.go",
        &[
            (
                "reflect MethodByName with a computed name",
                "package m\nimport \"reflect\"\nfunc Run(v any, n string) { reflect.ValueOf(v).MethodByName(n).Call(nil) }\n",
            ),
            (
                "method value kept in a local then called",
                "package m\nimport \"reflect\"\nfunc Run(v any, n string) { m := reflect.ValueOf(v).MethodByName(n); m.Call(nil) }\n",
            ),
            (
                "aliased reflect import",
                "package m\nimport r \"reflect\"\nfunc Run(v any, n string) { r.Indirect(r.ValueOf(v)).MethodByName(n).Call(nil) }\n",
            ),
        ],
    );
    // positive control: the dispatch is reported Unresolved code.eval, never certain and never clean
    let src = "package m\nimport \"reflect\"\nfunc Run(v any, n string) { reflect.ValueOf(v).MethodByName(n).Call(nil) }\n";
    let s = one("src/x.go", src);
    assert!(
        s.unresolved.iter().any(|a| a == "code.eval"),
        "expected unresolved code.eval, got {s:?}"
    );
    all_clean(
        "src/x.go",
        &[
            (
                "reflect used only to read a kind",
                "package m\nimport \"reflect\"\nfunc Run(v any) bool { return reflect.ValueOf(v).Kind() == reflect.Ptr }\n",
            ),
            (
                "local reflect shadows the package",
                "package m\nimport \"reflect\"\nfunc Run(v any, n string) { reflect := fake{}; reflect.ValueOf(v).MethodByName(n).Call(nil) }\n",
            ),
        ],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_java_alias_shadow_and_computed_name() {
    all_certain(
        "src/A.java",
        "process.spawn",
        &[(
            "local variable alias of the runtime",
            "import java.lang.Runtime;\nclass A { void go(String c) throws Exception { Runtime r = Runtime.getRuntime(); Runtime x = r; x.exec(c); } }\n",
        )],
    );
    all_clean(
        "src/A.java",
        &[(
            "nested class shadows the import",
            "import java.lang.ProcessBuilder;\nclass A { static class ProcessBuilder { ProcessBuilder(String c){} } void go(String c) { new ProcessBuilder(c); } }\n",
        )],
    );
    all_reported(
        "src/A.java",
        &[(
            "folded-concatenation class name is still reflection",
            "class A { void go(String c) throws Exception { Class.forName(\"java.lang.\" + \"Runtime\"); } }\n",
        )],
    );
}

// frob:ticket 01M68B54QSJ9VSZ6S1SZYJNFX1
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_java_class_literal_reflection_is_reported() {
    all_reported(
        "src/A.java",
        &[
            (
                "Runtime.class getMethod invoke",
                "class A { void go(Object o) throws Exception { Runtime.class.getMethod(\"exec\", String.class).invoke(o, \"x\"); } }\n",
            ),
            (
                "getDeclaredMethod",
                "class A { void go(Object o) throws Exception { Runtime.class.getDeclaredMethod(\"exec\", String.class).invoke(o, \"x\"); } }\n",
            ),
            (
                "fully qualified literal",
                "class A { void go(Object o) throws Exception { java.lang.Runtime.class.getMethod(\"exec\", String.class).invoke(o, \"x\"); } }\n",
            ),
            (
                "literal held in a Class local",
                "class A { void go(Object o) throws Exception { Class<?> c = Runtime.class; c.getMethod(\"exec\", String.class).invoke(o, \"x\"); } }\n",
            ),
            (
                "ProcessBuilder literal",
                "class A { void go() throws Exception { Class<?> c = ProcessBuilder.class; c.getConstructors(); } }\n",
            ),
        ],
    );
    all_clean(
        "src/A.java",
        &[
            (
                "a local Runtime type shadows java.lang.Runtime",
                "class A { static class Runtime { void exec(String s) {} } void go() throws Exception { Runtime.class.getMethod(\"exec\", String.class); } }\n",
            ),
            (
                "a harmless class literal",
                "class A { void go() throws Exception { String.class.getMethod(\"trim\"); } }\n",
            ),
        ],
    );
}

// frob:ticket 01M68B54TJ3MNW1AHNQEV1AJCV
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_java_method_handle_lookup_is_reported() {
    let imp = "import java.lang.invoke.MethodHandles;\n";
    let body = |b: &str| {
        format!("{imp}class A {{ void go(Object o, String c) throws Throwable {{ {b} }} }}\n")
    };
    let cases: Vec<(&str, String)> = vec![
        ("findVirtual", body("MethodHandles.lookup().findVirtual(Runtime.class, \"exec\", null);")),
        ("findStatic", body("MethodHandles.lookup().findStatic(Runtime.class, \"getRuntime\", null);")),
        ("findConstructor", body("MethodHandles.lookup().findConstructor(ProcessBuilder.class, null);")),
        ("findSpecial", body("MethodHandles.lookup().findSpecial(Runtime.class, \"exec\", null, A.class);")),
        ("unreflect", body("MethodHandles.lookup().unreflect(null);")),
        ("publicLookup", body("MethodHandles.publicLookup().findVirtual(Runtime.class, \"exec\", null);")),
        ("privateLookupIn", body("MethodHandles.privateLookupIn(A.class, MethodHandles.lookup()).findVirtual(Runtime.class, \"exec\", null);")),
        ("lookup in", body("MethodHandles.lookup().in(A.class).findVirtual(Runtime.class, \"exec\", null);")),
        ("Lookup local", body("MethodHandles.Lookup l = MethodHandles.lookup(); l.findVirtual(Runtime.class, \"exec\", null);")),
        ("var local", body("var l = MethodHandles.lookup(); l.findVirtual(Runtime.class, \"exec\", null);")),
        ("computed class", body("MethodHandles.lookup().findVirtual(Class.forName(c), \"exec\", null);")),
        ("class from a parameter", format!("{imp}class A {{ void go(Class<?> k) throws Throwable {{ MethodHandles.lookup().findVirtual(k, \"exec\", null); }} }}\n")),
        ("static import", "import static java.lang.invoke.MethodHandles.lookup;\nclass A { void go() throws Throwable { lookup().findVirtual(Runtime.class, \"exec\", null); } }\n".to_owned()),
        ("wildcard import", "import java.lang.invoke.*;\nclass A { void go() throws Throwable { MethodHandles.lookup().findStatic(Runtime.class, \"getRuntime\", null); } }\n".to_owned()),
        ("qualified", "class A { void go() throws Throwable { java.lang.invoke.MethodHandles.lookup().findVirtual(Runtime.class, \"exec\", null); } }\n".to_owned()),
        ("qualified Lookup type", "class A { void go() throws Throwable { java.lang.invoke.MethodHandles.Lookup l = java.lang.invoke.MethodHandles.lookup(); l.findVirtual(Runtime.class, \"exec\", null); } }\n".to_owned()),
    ];
    let refs: Vec<(&str, &str)> = cases.iter().map(|(n, s)| (*n, s.as_str())).collect();
    all_reported("src/A.java", &refs);
    all_clean(
        "src/A.java",
        &[
            (
                "a local MethodHandles type shadows java.lang.invoke",
                "class A { static class MethodHandles { static MethodHandles lookup() { return null; } Object findVirtual(Object c, String n) { return null; } } void go() { MethodHandles.lookup().findVirtual(null, \"exec\"); } }\n",
            ),
            (
                "an unrelated lookup",
                "class A { Object lookup() { return null; } void go() { lookup().toString(); } }\n",
            ),
            (
                "an import of another MethodHandles",
                "import com.example.MethodHandles;\nclass A { void go() { MethodHandles.lookup().findVirtual(null, \"exec\"); } }\n",
            ),
        ],
    );
}

// frob:ticket 01M688121YPN90V6GKDTFZAPQN
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_java_literal_class_forname_get_method_is_reported() {
    all_reported(
        "src/A.java",
        &[
            (
                "literal Class.forName then getMethod",
                "class A { void go(String c) throws Exception { Class.forName(\"java.lang.Runtime\").getMethod(\"exec\", String.class); } }\n",
            ),
            (
                "literal Class.forName of a harmless class then a chained call",
                "class A { void go() throws Exception { Class.forName(\"java.lang.String\").getName(); } }\n",
            ),
            (
                "computed Class.forName then getMethod",
                "class A { void go(String c) throws Exception { Class.forName(c).getMethod(\"exec\", String.class); } }\n",
            ),
        ],
    );
    all_clean(
        "src/A.java",
        &[
            (
                "a local Class type shadows java.lang.Class",
                "class A { static class Class { static Class forName(String s) { return null; } Class getMethod(String n) { return this; } } void go() { Class.forName(\"java.lang.Runtime\").getMethod(\"exec\"); } }\n",
            ),
            (
                "a chain on an unrelated call",
                "class A { void go(String s) { s.trim().length(); } }\n",
            ),
        ],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_c_alias_shadow_and_computed_name() {
    all_reported(
        "src/a.c",
        &[
            (
                "function pointer aliasing the libc function",
                "#include <stdlib.h>\nvoid f() { int (*s)(const char*) = system; s(\"x\"); }\n",
            ),
            (
                "token pasting builds the name",
                "#include <stdlib.h>\n#define CAT(a,b) a##b\nvoid f() { CAT(sys,tem)(\"x\"); }\n",
            ),
        ],
    );
    all_clean(
        "src/a.c",
        &[
            (
                "file-local definition shadows libc",
                "#include <stdlib.h>\nstatic int system(const char *c) { return 0; }\nvoid f() { system(\"x\"); }\n",
            ),
            (
                "parameter named like libc",
                "#include <stdlib.h>\nvoid f(int system) { system = 1; }\n",
            ),
        ],
    );
    all_certain(
        "src/a.c",
        "ffi",
        &[(
            "dlsym with a pasted literal name",
            "#include <dlfcn.h>\nvoid f(void *h) { dlsym(h, \"sys\" \"tem\"); }\n",
        )],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_cpp_alias_shadow_and_computed_name() {
    all_certain(
        "src/a.cpp",
        "process.spawn",
        &[(
            "using-declaration alias",
            "#include <cstdlib>\nusing std::system;\nvoid f() { system(\"x\"); }\n",
        )],
    );
    all_clean(
        "src/a.cpp",
        &[(
            "user namespace shadows the libc name",
            "#include <cstdlib>\nnamespace n { int system(const char*); }\nvoid f() { n::system(\"x\"); }\n",
        )],
    );
    all_certain(
        "src/a.cpp",
        "ffi",
        &[(
            "dlsym with a runtime name",
            "#include <dlfcn.h>\nvoid f(void *h, const char *n) { dlsym(h, n); }\n",
        )],
    );
}

// frob:ticket 01M688124N09MGJXMHXHVSKPQW
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_cpp_namespace_alias_is_reported() {
    all_reported(
        "src/a.cpp",
        &[(
            "namespace alias of std",
            "#include <cstdlib>\nnamespace s = std;\nvoid f() { s::system(\"x\"); }\n",
        )],
    );
    all_certain(
        "src/a.cpp",
        "process.spawn",
        &[
            (
                "positive control: plain std",
                "#include <cstdlib>\nvoid f() { std::system(\"x\"); }\n",
            ),
            (
                "namespace alias of std",
                "#include <cstdlib>\nnamespace s = std;\nvoid f() { s::system(\"x\"); }\n",
            ),
            (
                "chained alias",
                "#include <cstdlib>\nnamespace a = std;\nnamespace b = a;\nvoid f() { b::system(\"x\"); }\n",
            ),
            (
                "alias declared in a function body",
                "#include <cstdlib>\nvoid f() { namespace s = std; s::system(\"x\"); }\n",
            ),
            (
                "alias declared in a nested namespace",
                "#include <cstdlib>\nnamespace o { namespace s = ::std; void f() { s::system(\"x\"); } }\n",
            ),
        ],
    );
    all_clean(
        "src/a.cpp",
        &[
            (
                "alias of a user namespace",
                "#include <cstdlib>\nnamespace n { int system(const char*); }\nnamespace s = n;\nvoid f() { s::system(\"x\"); }\n",
            ),
            (
                "inner alias shadows the outer std alias",
                "#include <cstdlib>\nnamespace n { int system(const char*); }\nnamespace s = std;\nvoid f() { namespace s = n; s::system(\"x\"); }\n",
            ),
            (
                "alias out of scope at the use",
                "#include <cstdlib>\nnamespace n { int system(const char*); }\nnamespace s = n;\nvoid g() { namespace s = std; }\nvoid f() { s::system(\"x\"); }\n",
            ),
        ],
    );
}

// frob:ticket 01M67VHPGMWP2ZSN378AH9XAGZ
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_shell_alias_shadow_and_computed_name_are_unresolved() {
    // Shell has no capability detector: a node owning it gets one Unresolved, never a clean pass.
    for (label, src) in [
        ("alias", "alias r=rm\nr -rf /\n"),
        (
            "function shadowing a command",
            "rm() { echo hi; }\nrm -rf x\n",
        ),
        ("computed command name", "c=r; $c\"m\" -rf x\n"),
        ("eval of a parameter", "eval \"$1\"\n"),
    ] {
        let s = one("src/a.sh", src);
        assert!(
            s.certain.is_empty() && s.unresolved == ["node/a"],
            "{label}: expected one node-level unresolved, got {s:?}"
        );
    }
}

const GO_REFLECT_DECLARED: &[(&str, &str)] = &[
    (
        "tuple return (reflect.Value, error)",
        "package m\nimport \"reflect\"\nfunc get() (reflect.Value, error) { return reflect.Value{}, nil }\nfunc Run() { x, _ := get(); x.Call(nil) }\n",
    ),
    (
        "range over []reflect.Value",
        "package m\nimport \"reflect\"\nfunc Run(vs []reflect.Value) { for _, v := range vs { v.Call(nil) } }\n",
    ),
    (
        "index into []reflect.Value",
        "package m\nimport \"reflect\"\nfunc Run(vs []reflect.Value) { vs[0].Call(nil) }\n",
    ),
    (
        "map[string]reflect.Value element",
        "package m\nimport \"reflect\"\nfunc Run(m map[string]reflect.Value) { m[\"a\"].Call(nil) }\n",
    ),
    (
        "parameter declared reflect.Value",
        "package m\nimport \"reflect\"\nfunc Run(m reflect.Value) { m.Call(nil) }\n",
    ),
    (
        "pointer parameter",
        "package m\nimport \"reflect\"\nfunc Run(m *reflect.Value) { m.Call(nil) }\n",
    ),
    (
        "aliased import in the parameter type",
        "package m\nimport r \"reflect\"\nfunc Run(m r.Value) { m.Call(nil) }\n",
    ),
    (
        "struct field called through a parameter",
        "package m\nimport \"reflect\"\ntype S struct{ m reflect.Value }\nfunc Run(s S) { s.m.Call(nil) }\n",
    ),
    (
        "struct field called through a receiver",
        "package m\nimport \"reflect\"\ntype S struct{ m reflect.Value }\nfunc (s *S) Run() { s.m.Call(nil) }\n",
    ),
    (
        "returned reflect.Value called",
        "package m\nimport \"reflect\"\nfunc get() reflect.Value { return reflect.Value{} }\nfunc Run() { get().Call(nil) }\n",
    ),
    (
        "var declared reflect.Value",
        "package m\nimport \"reflect\"\nfunc Run() { var m reflect.Value; m.Call(nil) }\n",
    ),
    (
        "local alias of reflect.Value",
        "package m\nimport \"reflect\"\ntype V = reflect.Value\nfunc Run(m V) { m.Call(nil) }\n",
    ),
    (
        "method value held in a parameter",
        "package m\nimport \"reflect\"\nfunc Run(m reflect.Value, n string) { m.MethodByName(n) }\n",
    ),
    (
        "local initialised from ValueOf then called",
        "package m\nimport \"reflect\"\nfunc Run(fn any) { f := reflect.ValueOf(fn); f.Call(nil) }\n",
    ),
    (
        "local initialised from a function returning reflect.Value",
        "package m\nimport \"reflect\"\nfunc get() reflect.Value { return reflect.Value{} }\nfunc Run() { x := get(); x.Call(nil) }\n",
    ),
    (
        "local copy of a reflect.Value field",
        "package m\nimport \"reflect\"\ntype S struct{ m reflect.Value }\nfunc Run(s S) { x := s.m; x.Call(nil) }\n",
    ),
    (
        "multi-value lookup then Func.Call",
        "package m\nimport \"reflect\"\nfunc Run(v any, n string) { m, _ := reflect.TypeOf(v).MethodByName(n); m.Func.Call(nil) }\n",
    ),
];

// frob:ticket 01M68A4X3WSCGTN070S8H1QZPX
// frob:ticket 01M68ERE6YM5671NGNK7EP55G9
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_go_reflect_value_declared_type_is_reported() {
    all_reported("src/x.go", GO_REFLECT_DECLARED);
    for (label, src) in GO_REFLECT_DECLARED {
        let s = one("src/x.go", src);
        assert!(
            s.unresolved.iter().any(|a| a == "code.eval"),
            "{label}: expected unresolved code.eval, got {s:?}"
        );
    }
}

// frob:ticket 01M68A4X3WSCGTN070S8H1QZPX
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_go_local_value_type_stays_clean() {
    all_clean(
        "src/x.go",
        &[
            (
                "parameter of a locally declared Value",
                "package m\nimport \"reflect\"\ntype Value struct{}\nfunc (Value) Call(a any) {}\nfunc Run(m Value) { m.Call(nil) }\n",
            ),
            (
                "field of a locally declared Value",
                "package m\nimport \"reflect\"\ntype Value struct{}\ntype S struct{ m Value }\nfunc Run(s S) { s.m.Call(nil) }\n",
            ),
            (
                "local reflect shadows the import in a type",
                "package m\nimport \"reflect\"\nfunc Run(reflect pkg, m reflect.Value) { m.Call(nil) }\n",
            ),
            (
                "tuple return of a local type",
                "package m\nimport \"reflect\"\ntype Value struct{}\nfunc (Value) Call(a any) {}\nfunc get() (Value, error) { return Value{}, nil }\nfunc Run() { x, _ := get(); x.Call(nil); _ = reflect.Ptr }\n",
            ),
            (
                "range over a slice of a local type",
                "package m\nimport \"reflect\"\ntype Value struct{}\nfunc (Value) Call(a any) {}\nfunc Run(vs []Value) { for _, v := range vs { v.Call(nil) }; _ = reflect.Ptr }\n",
            ),
            (
                "index and map element of a local type",
                "package m\nimport \"reflect\"\ntype Value struct{}\nfunc (Value) Call(a any) {}\nfunc Run(vs []Value, m map[string]Value) { vs[0].Call(nil); m[\"a\"].Call(nil); _ = reflect.Ptr }\n",
            ),
            (
                "local initialised from an unrelated call",
                "package m\nimport \"reflect\"\nfunc other() T { return T{} }\nfunc Run() { x := other(); x.Call(nil); _ = reflect.Ptr }\n",
            ),
            (
                "reflect imported but parameter is another package type",
                "package m\nimport \"reflect\"\nimport \"time\"\nfunc Run(m time.Time) { m.Unix(); _ = reflect.Ptr }\n",
            ),
        ],
    );
}

// frob:ticket 01M68CKMCEMGZ5V79E8ZCE2A5G
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn probe_cpp_namespace_alias_siblings_resolve_like_file_scope() {
    all_certain(
        "src/a.cpp",
        "process.spawn",
        &[
            (
                "positive control: file-scope alias",
                "#include <cstdlib>\nnamespace s = std;\nvoid f() { s::system(\"x\"); }\n",
            ),
            (
                "using namespace of an alias, bare call",
                "#include <cstdlib>\nnamespace s = std;\nusing namespace s;\nvoid f() { system(\"x\"); }\n",
            ),
            (
                "alias in a reopened namespace",
                "#include <cstdlib>\nnamespace o { namespace s = std; }\nnamespace o { void f() { s::system(\"x\"); } }\n",
            ),
            (
                "alias in an inline namespace used from the parent",
                "#include <cstdlib>\nnamespace o { inline namespace v { namespace s = std; } }\nvoid g() { o::s::system(\"x\"); }\nnamespace o { void f() { s::system(\"x\"); } }\n",
            ),
            (
                "alias in an inline namespace used unqualified in the parent",
                "#include <cstdlib>\nnamespace o { inline namespace v { namespace s = std; } void f() { s::system(\"x\"); } }\n",
            ),
            (
                "user namespace std with other names does not hide the library",
                "#include <cstdlib>\nnamespace std { void other(); }\nvoid f() { std::system(\"x\"); }\n",
            ),
            (
                "using namespace of the namespace holding the alias",
                "#include <cstdlib>\nnamespace o { namespace s = std; }\nusing namespace o;\nvoid f() { s::system(\"x\"); }\n",
            ),
            (
                "alias in a class body",
                "#include <cstdlib>\nstruct C { namespace s = std; void f() { s::system(\"x\"); } };\n",
            ),
            (
                "alias in a class body used in an out-of-line method",
                "#include <cstdlib>\nstruct C { namespace s = std; void f(); };\nvoid C::f() { s::system(\"x\"); }\n",
            ),
        ],
    );
    all_clean(
        "src/a.cpp",
        &[
            (
                "alias of a user namespace, reopened",
                "#include <cstdlib>\nnamespace n { int system(const char*); }\nnamespace o { namespace s = n; }\nnamespace o { void f() { s::system(\"x\"); } }\n",
            ),
            (
                "alias in a sibling non-inline namespace is not visible",
                "#include <cstdlib>\nnamespace n { int system(const char*); }\nnamespace p { namespace s = std; }\nnamespace s = n;\nnamespace o { void f() { s::system(\"x\"); } }\n",
            ),
            (
                "user-defined std::system without the library header",
                "namespace std { int system(const char*) { return 0; } }\nvoid f() { std::system(\"x\"); }\n",
            ),
        ],
    );
}

//! CAP001 for the TypeScript family and C# (ticket PKW7X2J): process, filesystem, network,
//! environment and code-evaluation capabilities resolved through each language's import system.
//! Pins the audit cases t01, t02, m02 and c01; unresolved forms are reported, never clean.

// frob:ticket PKW7X2J

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

fn bind_src(rel: &str, text: &str, body: &str) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("src")).unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    std::fs::write(dir.path().join(rel), text).unwrap();
    let model =
        format!("grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n{body}}}\n");
    std::fs::write(dir.path().join("design/model.grmb"), &model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/model.grmb", model.into_bytes());
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

/// (atom, certain) of every CAP001 finding of `text` in file `rel`, ungranted.
fn cap001(rel: &str, text: &str) -> Vec<(String, bool)> {
    let b = bind_src(rel, text, "");
    let mut v: Vec<_> = b
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001")
        .map(|f| {
            (
                f.anchor.trim_start_matches("cap/node/a/").to_owned(),
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

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t01_typescript_imports_resolve_to_a_process_spawn() {
    for src in [
        "import * as cp from \"child_process\";\nexport function go(x: string) { cp.exec(x); }\n",
        "import { exec } from \"child_process\";\nexport function go(x: string) { exec(x); }\n",
        "import { exec as run } from \"node:child_process\";\nexport function go(x: string) { run(x); }\n",
        "import cp from \"node:child_process\";\nexport function go(x: string) { cp.spawn(x); }\n",
        "import cp = require(\"child_process\");\nexport function go(x: string) { cp.execSync(x); }\n",
    ] {
        let f = cap001("src/x.ts", src);
        assert!(has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_require_resolves_through_variables_and_destructuring() {
    for src in [
        "const cp = require('child_process');\nfunction go(x) { cp.exec(x); }\n",
        "const { exec } = require('child_process');\nfunction go(x) { exec(x); }\n",
        "const { spawn: sp } = require('node:child_process');\nfunction go(x) { sp(x); }\n",
        "var a = require('child_process');\nvar b = a;\nfunction go(x) { b.execFile(x); }\n",
    ] {
        let f = cap001("src/x.js", src);
        assert!(has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn typescript_filesystem_network_environment_and_globals() {
    let f = cap001(
        "src/x.ts",
        "import * as fs from \"fs\";\nexport const a = (p: string) => fs.readFileSync(p);\n",
    );
    assert!(has(&f, "fs.read", true), "{f:?}");
    let f = cap001(
        "src/x.ts",
        "import { writeFile } from \"node:fs/promises\";\nexport const a = (p: string) => writeFile(p, \"\");\n",
    );
    assert!(has(&f, "fs.write", true), "{f:?}");
    let f = cap001("src/x.ts", "export const a = (u: string) => fetch(u);\n");
    assert!(has(&f, "net.connect", true), "{f:?}");
    let f = cap001(
        "src/x.ts",
        "export const a = (u: string) => globalThis.fetch(u);\n",
    );
    assert!(has(&f, "net.connect", true), "{f:?}");
    let f = cap001(
        "src/x.ts",
        "import http from \"http\";\nexport const a = () => http.createServer();\n",
    );
    assert!(has(&f, "net.listen", true), "{f:?}");
    let f = cap001(
        "src/x.ts",
        "export const a = () => process.env.HOME;\nexport const b = (k: string) => process.env[k];\n",
    );
    assert!(has(&f, "process.env", true), "{f:?}");
    let f = cap001(
        "src/x.ts",
        "export const a = (u: string) => new WebSocket(u);\n",
    );
    assert!(has(&f, "net.connect", true), "{f:?}");
    let f = cap001(
        "src/x.ts",
        "export const a = () => Deno.readTextFile('x');\n",
    );
    assert!(has(&f, "fs.read", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn typescript_decoys_and_shadowing_are_not_capabilities() {
    for src in [
        "const fs = { readFile(p: string) { return p; } };\nexport const a = (p: string) => fs.readFile(p);\n",
        "export function a(fs: { readFile(p: string): string }, p: string) { return fs.readFile(p); }\n",
        "function exec(x: string) { return x; }\nexport const a = (x: string) => exec(x);\n",
        "function fetch(u: string) { return u; }\nexport const a = (u: string) => fetch(u);\n",
        "import { exec } from \"./local\";\nexport const a = (x: string) => exec(x);\n",
        "const cp = { exec(x: string) { return x; } };\nexport const a = (x: string) => cp.exec(x);\n",
    ] {
        let f = cap001("src/x.ts", src);
        assert!(f.is_empty(), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn typescript_unresolvable_forms_are_unresolved_never_clean() {
    for src in [
        "export function a(n: string) { return require(n); }\n",
        "const fs = require('fs');\nexport function a(k: string) { return fs[k]('x'); }\n",
        "export function a(s: string) { return eval(s); }\n",
        "export function a(s: string) { return new Function(s); }\n",
        "export function a(k: string) { return process.env[k]; }\n",
    ] {
        let f = cap001("src/x.ts", src);
        assert!(!f.is_empty(), "{src}: nothing reported");
        if !src.contains("process.env") {
            assert!(
                f.iter().all(|(_, c)| !c),
                "{src}: must be Unresolved: {f:?}"
            );
        }
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn m02_a_typescript_grant_covers_the_resolved_use() {
    let src =
        "import * as cp from \"child_process\";\nexport function go(x: string) { cp.exec(x); }\n";
    let b = bind_src("src/x.ts", src, "  may process.spawn;\n");
    assert!(
        !b.findings.iter().any(|f| f.rule == "CAP001"),
        "{:?}",
        b.findings
    );
    let b = bind_src("src/x.ts", src, "  may fs.read;\n");
    assert!(
        b.findings.iter().any(|f| f.rule == "CAP001"),
        "{:?}",
        b.findings
    );
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c01_csharp_using_resolves_to_a_process_spawn() {
    for src in [
        "using System.Diagnostics;\nclass C { void M(string x) { Process.Start(x); } }\n",
        "class C { void M(string x) { System.Diagnostics.Process.Start(x); } }\n",
        "using P = System.Diagnostics.Process;\nclass C { void M(string x) { P.Start(x); } }\n",
        "using static System.Diagnostics.Process;\nclass C { void M(string x) { Start(x); } }\n",
        "using SD = System.Diagnostics;\nclass C { void M(string x) { SD.Process.Start(x); } }\n",
        "class C { void M(string x) { global::System.Diagnostics.Process.Start(x); } }\n",
        "using System.Diagnostics;\nclass C { void M(string x) { var p = new Process(); p.Start(); } }\n",
    ] {
        let f = cap001("src/x.cs", src);
        assert!(has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn csharp_filesystem_network_and_environment() {
    let f = cap001(
        "src/x.cs",
        "using System.IO;\nclass C { string M(string p) { return File.ReadAllText(p); } }\n",
    );
    assert!(has(&f, "fs.read", true), "{f:?}");
    let f = cap001(
        "src/x.cs",
        "class C { void M(string p) { System.IO.File.WriteAllText(p, \"\"); } }\n",
    );
    assert!(has(&f, "fs.write", true), "{f:?}");
    let f = cap001(
        "src/x.cs",
        "using System.Net.Http;\nclass C { object M() { return new HttpClient(); } }\n",
    );
    assert!(has(&f, "net.connect", true), "{f:?}");
    let f = cap001(
        "src/x.cs",
        "using System;\nclass C { string M() { return Environment.GetEnvironmentVariable(\"A\"); } }\n",
    );
    assert!(has(&f, "process.env", true), "{f:?}");
    let f = cap001(
        "src/x.cs",
        "using System.Net.Sockets;\nclass C { object M() { return new TcpListener(null, 1); } }\n",
    );
    assert!(has(&f, "net.listen", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn csharp_decoys_and_unresolved_forms() {
    let f = cap001(
        "src/x.cs",
        "class File { public static string ReadAllText(string p) { return p; } }\nclass C { string M(string p) { return File.ReadAllText(p); } }\n",
    );
    assert!(f.is_empty(), "{f:?}");
    let f = cap001(
        "src/x.cs",
        "class C { string M(string p, Process Process) { return Process.Start(p); } }\n",
    );
    assert!(f.is_empty(), "{f:?}");
    let f = cap001(
        "src/x.cs",
        "using System;\nclass C { object M(string n) { return Type.GetType(n); } }\n",
    );
    assert!(!f.is_empty() && f.iter().all(|(_, c)| !c), "{f:?}");
}

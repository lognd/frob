//! CAP001 for reflection, native interop and eval forms (ticket S3EC85S): C# reflection and
//! `DllImport`, Rust `extern` blocks, `libc` calls, `transmute`, inline assembly, and JavaScript
//! `require` / `eval` / `Function`. Every form is resolved through the language's import system;
//! a spelled lookalike that is a local binding names nothing, and a form whose target cannot be
//! resolved is reported as an uncertain use, never passed silently.

// frob:ticket 01M64230AR8DHJZY9QQS3EC85S

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

/// True when `atom` is reported certain, or (for `certain == false`) as an unresolved receiver.
fn has(found: &[(String, bool)], atom: &str, certain: bool) -> bool {
    let anchor = if certain {
        atom.to_owned()
    } else {
        format!("{atom}/receiver")
    };
    found.iter().any(|(a, c)| *a == anchor && *c == certain)
}

fn lacks(found: &[(String, bool)], atom: &str) -> bool {
    !found
        .iter()
        .any(|(a, _)| a == atom || *a == format!("{atom}/receiver"))
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c01_csharp_literal_reflection_chain_resolves_to_the_target() {
    let found = cap001(
        "src/x.cs",
        "using System;\nclass A { void Go(){ Type.GetType(\"System.Diagnostics.Process\").GetMethod(\"Start\").Invoke(null, null); } }\n",
    );
    assert!(has(&found, "process.spawn", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c01_csharp_computed_method_name_is_unresolved() {
    let found = cap001(
        "src/x.cs",
        "using System;\nclass A { void Go(string n){ Type.GetType(\"System.Diagnostics.Process\").GetMethod(n).Invoke(null, null); } }\n",
    );
    assert!(has(&found, "process.spawn", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_computed_type_name_is_unresolved() {
    let found = cap001(
        "src/x.cs",
        "using System;\nclass A { void Go(string n){ Activator.CreateInstance(Type.GetType(n)); } }\n",
    );
    assert!(has(&found, "ffi", false), "{found:?}");
    assert!(has(&found, "process.spawn", false), "{found:?}");
    assert!(has(&found, "code.eval", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_dllimport_is_native_interop() {
    let found = cap001(
        "src/x.cs",
        "using System.Runtime.InteropServices;\nclass A { [DllImport(\"libc\")] static extern int system(string c); }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_qualified_dllimport_is_native_interop() {
    let found = cap001(
        "src/x.cs",
        "class A { [System.Runtime.InteropServices.DllImport(\"libc\")] static extern int system(string c); }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_function_pointer_marshalling_is_native_interop() {
    let found = cap001(
        "src/x.cs",
        "using System.Runtime.InteropServices;\nclass A { void Go(System.IntPtr p){ Marshal.GetDelegateForFunctionPointer(p, typeof(int)); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_native_library_load_is_native_interop() {
    let found = cap001(
        "src/x.cs",
        "using System.Runtime.InteropServices;\nclass A { void Go(){ NativeLibrary.Load(\"x\"); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_assembly_load_from_a_path_is_unresolved_eval() {
    let found = cap001(
        "src/x.cs",
        "using System.Reflection;\nclass A { void Go(string p){ Assembly.LoadFrom(p); } }\n",
    );
    assert!(has(&found, "code.eval", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn c02_csharp_local_marshal_class_names_nothing() {
    let found = cap001(
        "src/x.cs",
        "class Marshal { public static void GetDelegateForFunctionPointer(int a){} }\nclass A { void Go(){ Marshal.GetDelegateForFunctionPointer(1); } }\n",
    );
    assert!(lacks(&found, "ffi"), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r07_rust_extern_block_and_call_are_native_interop() {
    let found = cap001(
        "src/x.rs",
        "extern \"C\" { fn system(c: *const i8) -> i32; }\npub fn go(c: *const i8) { unsafe { system(c); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r07_rust_unsafe_extern_block_is_native_interop() {
    let found = cap001(
        "src/x.rs",
        "unsafe extern \"C\" { pub safe fn getpid() -> i32; }\npub fn go() -> i32 { getpid() }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r07_rust_libc_call_is_native_interop() {
    let found = cap001(
        "src/x.rs",
        "pub fn go(c: *const i8) { unsafe { libc::system(c); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r08_rust_aliased_libc_call_is_native_interop() {
    let found = cap001(
        "src/x.rs",
        "use libc as l;\npub fn go(c: *const i8) { unsafe { l::system(c); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r08_rust_imported_libc_function_is_native_interop() {
    let found = cap001(
        "src/x.rs",
        "use libc::system;\npub fn go(c: *const i8) { unsafe { system(c); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r08_rust_libc_glob_import_is_unresolved() {
    let found = cap001(
        "src/x.rs",
        "use libc::*;\npub fn go(c: *const i8) { unsafe { system(c); } }\n",
    );
    assert!(has(&found, "ffi", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r08_rust_dynamic_library_load_is_native_interop() {
    let found = cap001(
        "src/x.rs",
        "pub fn go() { unsafe { let _ = libloading::Library::new(\"x\"); } }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r11_rust_transmute_is_an_unsafe_escape() {
    let found = cap001(
        "src/x.rs",
        "pub fn go(p: *const ()) { let f: fn() = unsafe { std::mem::transmute(p) }; f(); }\n",
    );
    assert!(has(&found, "unsafe", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r11_rust_imported_transmute_is_an_unsafe_escape() {
    let found = cap001(
        "src/x.rs",
        "use std::mem::transmute;\npub fn go(p: *const ()) { let f: fn() = unsafe { transmute(p) }; f(); }\n",
    );
    assert!(has(&found, "unsafe", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r22_rust_inline_asm_is_an_unsafe_escape() {
    let found = cap001(
        "src/x.rs",
        "pub fn go() { unsafe { core::arch::asm!(\"nop\"); } }\n",
    );
    assert!(has(&found, "unsafe", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r22_rust_imported_asm_is_an_unsafe_escape() {
    let found = cap001(
        "src/x.rs",
        "use std::arch::asm;\npub fn go() { unsafe { asm!(\"nop\"); } }\n",
    );
    assert!(has(&found, "unsafe", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r22_rust_arch_glob_import_is_unresolved() {
    let found = cap001(
        "src/x.rs",
        "use std::arch::*;\npub fn go() { unsafe { asm!(\"nop\"); } }\n",
    );
    assert!(has(&found, "unsafe", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r22_rust_local_libc_module_names_nothing() {
    let found = cap001(
        "src/x.rs",
        "mod libc { pub fn system(_c: i32) {} }\npub fn go() { libc::system(1); }\n",
    );
    assert!(lacks(&found, "ffi"), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn r22_rust_local_function_named_like_libc_names_nothing() {
    let found = cap001(
        "src/x.rs",
        "fn system(_c: i32) {}\npub fn go() { system(1); }\n",
    );
    assert!(lacks(&found, "ffi"), "{found:?}");
    assert!(lacks(&found, "process.spawn"), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_computed_require_is_unresolved() {
    let found = cap001("src/x.js", "function go(n){ return require(n); }\n");
    assert!(has(&found, "code.eval", false), "{found:?}");
    assert!(has(&found, "process.spawn", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_computed_import_is_unresolved() {
    let found = cap001("src/x.js", "async function go(n){ return import(n); }\n");
    assert!(has(&found, "code.eval", false), "{found:?}");
    assert!(has(&found, "process.spawn", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_eval_is_unresolved_eval() {
    let found = cap001("src/x.js", "function go(s){ return eval(s); }\n");
    assert!(has(&found, "code.eval", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_function_constructor_is_unresolved_eval() {
    let found = cap001("src/x.js", "function go(s){ return new Function(s)(); }\n");
    assert!(has(&found, "code.eval", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_aliased_eval_is_unresolved_eval() {
    let found = cap001(
        "src/x.js",
        "const e = eval;\nfunction go(s){ return e(s); }\n",
    );
    assert!(has(&found, "code.eval", false), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_literal_require_resolves_to_the_module() {
    let found = cap001(
        "src/x.js",
        "const cp = require(\"child_process\");\nfunction go(c){ return cp.exec(c); }\n",
    );
    assert!(has(&found, "process.spawn", true), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_parameter_named_require_names_nothing() {
    let found = cap001(
        "src/x.js",
        "function go(require, n){ return require(n); }\n",
    );
    assert!(lacks(&found, "code.eval"), "{found:?}");
    assert!(lacks(&found, "process.spawn"), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_parameter_named_eval_names_nothing() {
    let found = cap001("src/x.js", "function go(eval, n){ return eval(n); }\n");
    assert!(lacks(&found, "code.eval"), "{found:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn t02_javascript_process_dlopen_is_native_interop() {
    let found = cap001(
        "src/x.js",
        "function go(m, f){ return process.dlopen(m, f); }\n",
    );
    assert!(has(&found, "ffi", true), "{found:?}");
}

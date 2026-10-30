//! CAP001 through Rust receiver types (ticket 01M64230GWHHTH9R7CZ55XRPGG, audit cases q01, q03,
//! q04, r10): types flow through fn return types and builder chains, an inner `let` does not hide
//! the outer binding outside its block, and generic or trait-bound receivers are Unresolved.

// frob:ticket 01M64230GWHHTH9R7CZ55XRPGG

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n}\n";

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

/// (atom, certain) of every CAP001 finding against node `a`.
fn cap001(files: &[(&str, &str)]) -> Vec<(String, bool)> {
    let mut v: Vec<_> = bind_files(files)
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001" && f.anchor.starts_with("cap/node/a/"))
        .map(|f| {
            (
                f.anchor
                    .trim_start_matches("cap/node/a/")
                    .split('/')
                    .next()
                    .unwrap_or_default()
                    .to_owned(),
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
fn rust_receiver_cap_fn_return_flows() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nfn make() -> Agent { Agent::new_with_defaults() }\npub fn go() {\n    let a = make();\n    a.get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_result_return_with_question_mark() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nfn make() -> Result<Agent, ()> { Ok(Agent::new_with_defaults()) }\npub fn go() -> Result<(), ()> {\n    let a = make()?;\n    a.get(\"x\");\n    Ok(())\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_unwrap_chain() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nfn make() -> Option<Agent> { None }\npub fn go() {\n    make().unwrap().get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_method_return_builder_chain() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nstruct B { a: Agent }\nimpl B {\n    fn new() -> Self { B { a: Agent::new_with_defaults() } }\n    fn agent(&self) -> &Agent { &self.a }\n}\npub fn go() {\n    B::new().agent().get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_local_builder_self_chain() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nstruct B { a: Agent }\nimpl B {\n    fn new() -> Self { B { a: Agent::new_with_defaults() } }\n    fn tune(self) -> Self { self }\n}\npub fn go() {\n    let b = B::new().tune().tune();\n    b.a.get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_outer_binding_survives_inner_shadow() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go(a: &Agent) {\n    {\n        let a = 3u8;\n        let _ = a;\n    }\n    a.get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_outer_binding_survives_inner_block_of_other_type() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go() {\n    let a = Agent::new_with_defaults();\n    if true {\n        let a = other();\n        a.get(\"inner\");\n    }\n    a.get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_inner_shadow_hides_outer_inside_its_block() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go(a: &Agent) {\n    let a = mystery();\n    a.get(\"x\");\n}\n",
    )]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_closure_param_shadow_does_not_leak() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go(a: &Agent) {\n    let f = |a: u8| a;\n    f(1);\n    a.get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_generic_bound_receiver_is_unresolved() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\ntrait Client { fn get(&self, u: &str); }\npub fn go<T: Client>(c: &T) {\n    c.get(\"x\");\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_impl_trait_receiver_is_unresolved() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\ntrait Client { fn get(&self, u: &str); }\npub fn go(c: impl Client) {\n    c.get(\"x\");\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_dyn_trait_receiver_is_unresolved() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\ntrait Client { fn get(&self, u: &str); }\npub fn go(c: &Box<dyn Client>) {\n    c.get(\"x\");\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_generic_struct_field_is_unresolved() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nstruct W<T> { inner: T }\nimpl<T> W<T> {\n    fn go(&self) {\n        self.inner.get(\"x\");\n    }\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_unrelated_method_on_generic_is_silent() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go<T: Clone>(c: &T) {\n    c.frobnicate();\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_unknown_concrete_type_is_silent() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go(a: &Other) {\n    a.get(\"x\");\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_local_type_named_agent_is_silent() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nstruct Local;\nimpl Local { fn get(&self) {} }\nfn make() -> Local { Local }\npub fn go() {\n    make().get();\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_type_alias_return() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\ntype C = Agent;\nfn make() -> C { Agent::new_with_defaults() }\npub fn go() {\n    make().get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_function_local_use_alias() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "fn go() {\n    use ureq::Agent as A;\n    let a: A = make();\n    a.get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_arc_box_wrappers() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nuse std::sync::Arc;\nfn make() -> Arc<Box<Agent>> { todo!() }\npub fn go() {\n    make().get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_mutex_guard() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nuse std::sync::{Arc, Mutex};\nfn go(m: Arc<Mutex<Agent>>) {\n    m.lock().unwrap().get(\"x\");\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_if_let_some() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nfn make() -> Option<Agent> { None }\npub fn go() {\n    if let Some(a) = make() {\n        a.get(\"x\");\n    }\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_match_ok_arm() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\nfn make() -> Result<Agent, ()> { Err(()) }\npub fn go() {\n    match make() {\n        Ok(a) => { a.get(\"x\"); }\n        Err(_) => {}\n    }\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_closure_captures_outer() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go(a: &Agent) {\n    let f = || a.get(\"x\");\n    f();\n}\n",
    )]);
    assert!(has(&f, "net.connect", true), "{f:?}");
    assert!(!has(&f, "net.connect", false), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_question_mark_on_unknown_is_silent() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use ureq::Agent;\npub fn go() -> Result<(), ()> {\n    let a = mystery()?;\n    a.get(\"x\");\n    Ok(())\n}\nfn _u(_: Agent) {}\n",
    )]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_r10_file_options_and_symlink() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use std::fs::File;\npub fn go() {\n    let _ = File::options().read(true).write(true).open(\"x\");\n    let _ = std::os::unix::fs::symlink(\"a\", \"b\");\n}\n",
    )]);
    assert!(has(&f, "fs.write", true), "{f:?}");
    assert!(has(&f, "fs.read", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_fs_symlink_alone_is_fs_write() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "use std::fs;\npub fn go() {\n    let _ = fs::soft_link(\"a\", \"b\");\n}\n",
    )]);
    assert!(has(&f, "fs.write", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_receiver_cap_cross_file_alias_and_reexport() {
    let f = cap001(&[
        ("src/a/lib.rs", "mod http;\npub use http::Client;\n"),
        ("src/a/http.rs", "pub type Client = ureq::Agent;\n"),
        (
            "src/a/use_it.rs",
            "use crate::Client;\npub fn go(c: &Client) {\n    c.get(\"x\");\n}\n",
        ),
    ]);
    assert!(
        has(&f, "net.connect", true) || has(&f, "net.connect", false),
        "{f:?}"
    );
}

//! CAP001 through Rust names (ticket 01M64230DV9KGPE0JH2D37NDVN, audit cases r02 to r06): type
//! aliases, `pub use` chains across modules and files, `macro_rules!` bodies and `include!`
//! targets resolve to the origin path, symbolically; what cannot be resolved is Unresolved.

// frob:ticket 01M64230DV9KGPE0JH2D37NDVN

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
fn rust_resolve_cap_baseline_direct_spawn() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "pub fn go() { std::process::Command::new(\"sh\"); }\n",
    )]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r02_type_alias_chain() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "type B = std::process::Command;\ntype C = B;\npub fn go() { C::new(\"sh\"); }\n",
    )]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r02_generic_alias() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "type C<T> = std::process::Command;\npub fn go() { C::<u8>::new(\"sh\"); }\n",
    )]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r02_alias_cycle_terminates() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "type A = B;\ntype B = A;\npub fn go() { A::new(\"sh\"); }\n",
    )]);
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r03_inline_module_reexport_under_alias() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "mod w { pub use std::process::Command as Cmd; }\nuse w::Cmd;\npub fn go() { Cmd::new(\"sh\"); }\n",
    )]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r03_pub_crate_and_nested_reexport() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "mod x { pub mod y { pub(crate) use std::process::Command; } }\nuse x::y::Command;\npub fn go() { Command::new(\"sh\"); }\n",
    )]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r03_repository_item_is_not_a_capability() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "mod w { pub struct Command; impl Command { pub fn new(_: &str) -> Self { Self } } }\nuse w::Command;\npub fn go() { Command::new(\"sh\"); }\n",
    )]);
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_file_reexport_via_use() {
    let f = cap001(&[
        (
            "src/a/lib.rs",
            "mod w;\nuse w::Cmd;\npub fn go() { Cmd::new(\"sh\"); }\n",
        ),
        ("src/a/w.rs", "pub use std::process::Command as Cmd;\n"),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_file_reexport_via_crate_path() {
    let f = cap001(&[
        (
            "src/a/lib.rs",
            "mod w;\nuse crate::w::Cmd;\npub fn go() { Cmd::new(\"sh\"); }\n",
        ),
        ("src/a/w.rs", "pub use std::process::Command as Cmd;\n"),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_file_reexport_via_qualified_call() {
    let f = cap001(&[
        (
            "src/a/lib.rs",
            "mod w;\npub fn go() { w::Cmd::new(\"sh\"); }\n",
        ),
        ("src/a/w.rs", "pub use std::process::Command as Cmd;\n"),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_file_reexport_via_super() {
    let f = cap001(&[
        ("src/a/lib.rs", "mod w;\nmod v;\n"),
        ("src/a/w.rs", "pub use std::process::Command as Cmd;\n"),
        (
            "src/a/v.rs",
            "use super::w::Cmd;\npub fn go() { Cmd::new(\"sh\"); }\n",
        ),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_path_attribute() {
    let f = cap001(&[
        (
            "src/a/lib.rs",
            "#[path = \"impl/real.rs\"]\nmod w;\nuse w::Cmd;\npub fn go() { Cmd::new(\"sh\"); }\n",
        ),
        (
            "src/a/impl/real.rs",
            "pub use std::process::Command as Cmd;\n",
        ),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_glob_reexport_is_unproven() {
    let f = cap001(&[
        (
            "src/a/lib.rs",
            "mod w;\nuse w::Command as C;\npub fn go() { C::new(\"sh\"); }\n",
        ),
        ("src/a/w.rs", "pub use std::process::*;\n"),
    ]);
    assert!(has(&f, "process.spawn/receiver", false), "{f:?}");
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r04_missing_module_file_is_never_certain() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "mod w;\nuse w::Cmd;\npub fn go() { Cmd::new(\"sh\"); }\n",
    )]);
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r05_macro_rules_literal_body() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "macro_rules! sp { () => { std::process::Command::new(\"sh\") }; }\npub fn go() { sp!(); }\n",
    )]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r05_macro_rules_fragment_path_is_unresolved() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "macro_rules! sp { ($x:expr) => { $x::new(\"sh\") }; }\npub fn go() { sp!(std::process::Command); }\n",
    )]);
    assert!(
        !f.is_empty(),
        "an unexpandable macro body must be reported: {f:?}"
    );
    assert!(f.iter().all(|(_, certain)| !certain), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r06_include_target_outside_the_node() {
    let f = cap001(&[
        ("src/a/lib.rs", "include!(\"../b/gen.rs\");\n"),
        (
            "src/b/gen.rs",
            "pub fn go() { std::process::Command::new(\"sh\"); }\n",
        ),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r06_computed_include_is_unresolved() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "include!(concat!(env!(\"OUT_DIR\"), \"/gen.rs\"));\n",
    )]);
    assert!(!f.is_empty(), "a computed include must be reported: {f:?}");
    assert!(f.iter().all(|(_, certain)| !certain), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r06_missing_include_target_is_unresolved() {
    let f = cap001(&[("src/a/lib.rs", "include!(\"nope.rs\");\n")]);
    assert!(
        !f.is_empty(),
        "an unreadable include must be reported: {f:?}"
    );
    assert!(f.iter().all(|(_, certain)| !certain), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn rust_resolve_cap_r06_include_str_and_env_are_not_code() {
    let f = cap001(&[(
        "src/a/lib.rs",
        "pub fn go() { let _ = include_str!(\"x.txt\"); let _ = env!(\"HOME\"); }\n",
    )]);
    assert!(f.is_empty(), "{f:?}");
}

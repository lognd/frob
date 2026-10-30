//! CAP001 through transitive effect summaries (ticket 01M5XNNJ994RN6Y24AT6ZD117V): wrappers,
//! closures, function values and dispatch cannot launder a capability across nodes.

// frob:ticket 01M5XNNJ994RN6Y24AT6ZD117V

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/a/**\";\n}\nnode b : trusted {\n  owns \"src/b/**\";\n  may fs.write;\n}\n";

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

fn any(found: &[(String, bool)]) -> bool {
    found.iter().any(|(a, _)| a.starts_with("fs.write"))
}

const STORE: (&str, &str) = (
    "src/b/store.rs",
    "pub fn write_any(p: &str, d: &str) {\n    let _ = std::fs::write(p, d);\n}\n\npub fn wrap(p: &str) {\n    write_any(p, \"x\");\n}\n",
);

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn wrapper_call_makes_the_caller_need_fs_write() {
    let f = cap001(&[
        STORE,
        (
            "src/a/x.rs",
            "use crate::b::store::wrap;\n\npub fn go() {\n    wrap(\"p\");\n}\n",
        ),
    ]);
    assert!(f.iter().any(|(a, c)| a == "fs.write" && *c), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn function_value_and_closure_calls_are_never_silent() {
    let mut missed = Vec::new();
    for body in &[
        "use crate::b::store::write_any;\n\npub fn go() {\n    let f = write_any;\n    f(\"p\", \"d\");\n}\n",
        "use crate::b::store::write_any;\n\npub fn go() {\n    let f = |p: &str| write_any(p, \"d\");\n    f(\"p\");\n}\n",
        "use crate::b::store::write_any;\n\npub fn go() {\n    [\"p\"].iter().for_each(|p| write_any(p, \"d\"));\n}\n",
        "use crate::b::store::write_any;\n\npub fn go() {\n    [\"p\"].iter().for_each(|p| write_any(p, \"d\"));\n}\n",
        "use crate::b::store::write_any;\n\npub fn go(v: Vec<&str>) {\n    v.into_iter().for_each(|p| write_any(p, \"d\"));\n}\n",
    ] {
        let f = cap001(&[STORE, ("src/a/x.rs", body)]);
        if !any(&f) {
            missed.push(*body);
        }
    }
    assert!(missed.is_empty(), "silent: {missed:#?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn dispatch_through_a_trait_object_is_unresolved() {
    let f = cap001(&[
        (
            "src/b/store.rs",
            "pub trait Sink {\n    fn put(&self, p: &str);\n}\npub struct Disk;\nimpl Sink for Disk {\n    fn put(&self, p: &str) {\n        let _ = std::fs::write(p, \"x\");\n    }\n}\n",
        ),
        (
            "src/a/x.rs",
            "use crate::b::store::Sink;\n\npub fn go(s: &dyn Sink) {\n    s.put(\"p\");\n}\n",
        ),
    ]);
    assert!(
        f.iter().any(|(a, c)| a.starts_with("fs.write") && !*c),
        "{f:?}"
    );
}

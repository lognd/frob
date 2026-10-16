//! Call edges from the source models: `super::` paths, std-macro arguments, parameter callees.

use gob_ir::Truth;
use gob_ir::eval::Ctx;
use gob_symbols::model_of_source_at;

/// The `Yes` call pairs and the unknown-callee frontier size for `text` folded at `path`.
fn calls(path: &str, text: &str) -> (usize, usize) {
    let model = model_of_source_at(path, text).expect("model folds");
    let rel = Ctx::new(&model).rel_calls();
    let yes = rel.iter().filter(|(_, _, t)| *t == Truth::Yes).count();
    (yes, rel.unknown_out().count())
}

// frob:ticket 01M53BEYPGE27A1202G8KS9TG8
// frob:tests crates/gob-symbols/src/rust.rs::bind_super_paths
#[test]
fn rust_super_path_call_resolves() {
    let src = "pub fn double(x: i32) -> i32 { x * 2 }\n\
               #[cfg(test)] mod tests { #[test] fn d() { super::double(2); } }\n";
    let (yes, _) = calls("lib.rs", src);
    assert_eq!(yes, 1, "super::double is a resolved call edge");
}

// frob:ticket 01M53BEYPGE27A1202G8KS9TG8
// frob:tests crates/gob-symbols/src/rust.rs::macro_arg_terms
#[test]
fn rust_macro_argument_calls_become_edges() {
    let src = "fn a() -> i32 { 1 }\nfn b() { assert_eq!(a(), 1); }\n";
    let (yes, _) = calls("lib.rs", src);
    assert_eq!(yes, 1, "a() inside assert_eq! is a call edge from b");
}

// frob:ticket 01M53BEYPGE27A1202G8KS9TG8
// frob:tests crates/gob-ir/src/eval/ctx.rs::rel_calls
#[test]
fn python_parameter_callee_is_unknown() {
    let (yes, unknown) = calls("m.py", "def helper(cb):\n    cb()\n");
    assert_eq!(yes, 0);
    assert!(unknown >= 1, "a call through a parameter is unresolved");
}

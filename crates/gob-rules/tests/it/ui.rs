//! Compile-fail test: a `Fix` cannot be built without stating its applicability.
// frob:ticket 01M3ZX7E968R74N08V8DW4RJVG

#[test]
fn fix_without_applicability_does_not_compile() {
    let ui_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/ui");
    assert!(ui_dir.is_dir(), "compile_fail needs the ui case directory");
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}

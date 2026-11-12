//! Compile-fail test: a `Fix` cannot be built without stating its applicability.
// frob:ticket 01M3ZX7E968R74N08V8DW4RJVG

#[test]
fn fix_without_applicability_does_not_compile() {
    let cases = std::fs::read_dir(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/ui"))
        .expect("the ui case directory exists")
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().is_some_and(|x| x == "rs"))
        .count();
    assert!(cases > 0, "compile_fail needs at least one ui case");
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}

//! Compile-fail tests for `#[derive(Rule)]` diagnostics.

#[test]
fn ui() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}

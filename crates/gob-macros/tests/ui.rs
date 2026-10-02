//! Compile-fail tests for the `Rule`, `ConfigTable` and `Command` derive diagnostics.

#[test]
fn ui() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}

//! Compile-fail tests for the `Rule`, `ConfigTable`, `Command` and `Directive` derive diagnostics.

#[test]
fn ui() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}

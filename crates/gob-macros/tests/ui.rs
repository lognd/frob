//! Compile-fail tests for the `Rule`, `ConfigTable`, `Command` and `Directive` derive diagnostics.

// frob:tests crates/gob-macros/src/lib.rs::derive_ticket_schema
// frob:tests crates/gob-macros/src/lib.rs::derive_rule
// frob:tests crates/gob-macros/src/lib.rs::derive_config_table
// frob:tests crates/gob-macros/src/lib.rs::derive_command
// frob:tests crates/gob-macros/src/lib.rs::derive_directive
#[test]
fn ui() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}

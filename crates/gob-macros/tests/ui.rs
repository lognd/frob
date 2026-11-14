//! Compile-fail tests for the `Rule`, `ConfigTable`, `Command` and `Directive` derive diagnostics.

// frob:tests crates/gob-macros/src/lib.rs::derive_ticket_schema
// frob:tests crates/gob-macros/src/lib.rs::derive_rule
// frob:tests crates/gob-macros/src/lib.rs::derive_config_table
// frob:tests crates/gob-macros/src/lib.rs::derive_command
// frob:tests crates/gob-macros/src/lib.rs::derive_directive
#[test]
fn ui() {
    let run = std::panic::catch_unwind(|| {
        let t = trybuild::TestCases::new();
        t.compile_fail("tests/ui/*.rs");
    });
    assert!(run.is_ok(), "a ui case did not fail to compile as expected");
}

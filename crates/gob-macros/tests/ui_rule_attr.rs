//! Compile tests for the `#[rule]` attribute (~N88H9SY, spiked in ~9R52NCF): one pass case and one fail case
//! per mistake. Each case dir holds `todo001.rs` plus its own `todo001.md` (the page is read
//! relative to the declaring file).

#[test]
fn ui_rule_attr() {
    let t = trybuild::TestCases::new();
    t.pass("tests/ui_rule/pass/*/todo001.rs");
    t.compile_fail("tests/ui_rule/fail/*/todo001.rs");
}

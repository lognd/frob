//! Compile-fail cases for `product_rules!` uniqueness (~PBJ6GPZ): each duplicate is a build error
//! that names both declarations.

#[test]
fn ui_product() {
    let run = std::panic::catch_unwind(|| {
        let t = trybuild::TestCases::new();
        t.compile_fail("tests/ui_product/*.rs");
    });
    assert!(
        run.is_ok(),
        "a ui_product case did not fail to compile as expected"
    );
}

//! TYPE002 and TYPE003 beyond the rule pages: stack matching, named stacks and weight keywords.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

mod support;

use crunk_rules::rules::{type002::Type002, type003::Type003};
use crunk_rules::typography::{Weight, effective_stacks, split_family_stack, weight_of};
use gob_rules::Severity;

fn css(text: &str) -> support::Project {
    support::project("styles/app.css", text, None)
}

// frob:tests crates/crunk-rules/src/typography/mod.rs::split_family_stack
#[test]
fn a_stack_is_split_lowercased_and_unquoted() {
    assert_eq!(
        split_family_stack("\"Inter\", 'System-UI' ,, sans-serif"),
        ["inter", "system-ui", "sans-serif"]
    );
}

// frob:tests crates/crunk-rules/src/typography/mod.rs::weight_of
#[test]
fn weights_resolve_keywords_and_exempt_relative_ones() {
    assert_eq!(weight_of("bold"), Weight::Numeric(700));
    assert_eq!(weight_of(" NORMAL "), Weight::Numeric(400));
    assert_eq!(weight_of("600"), Weight::Numeric(600));
    assert_eq!(weight_of("bolder"), Weight::Exempt);
    assert_eq!(weight_of("inherit"), Weight::Exempt);
    assert_eq!(weight_of("var(--w)"), Weight::Unparseable);
}

// frob:tests crates/crunk-rules/src/typography/mod.rs::effective_stacks
#[test]
fn without_named_stacks_the_families_are_the_one_implicit_stack() {
    let host = css("");
    let stacks = effective_stacks(&host.spec);
    assert_eq!(stacks.len(), 1);
    assert_eq!(stacks["<families>"], ["inter", "system-ui", "sans-serif"]);
}

// frob:tests crates/crunk-rules/src/rules/type002.rs::Type002
#[test]
fn a_named_stack_replaces_the_implicit_one() {
    let spec = support::DEFAULT_SPEC.replace(
        "[typography]",
        "[typography.stacks]\nmono = [\"Inter\", \"sans-serif\"]\n\n[typography]",
    );
    let host = support::project_with_spec(
        &spec,
        "styles/app.css",
        "a { font-family: Inter, sans-serif; }\nb { font-family: Inter, system-ui; }\n",
    );
    let found = support::run::<Type002>(&host);
    assert_eq!(
        found.len(),
        1,
        "only the stack that is a prefix of nothing fires: {found:?}"
    );
    assert!(
        found[0].message.contains("[\"inter\", \"system-ui\"]"),
        "{}",
        found[0].message
    );
    assert!(found[0].message.contains("mono"), "{}", found[0].message);
}

// frob:tests crates/crunk-rules/src/rules/type002.rs::Type002
#[test]
fn a_var_anywhere_in_the_value_exempts_the_whole_stack() {
    let host = css("a { font-family: var(--font-family-base), papyrus; }\n");
    assert!(support::run::<Type002>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/type003.rs::Type003
#[test]
fn type003_names_the_weight_and_the_declared_ones_and_is_a_warning() {
    let found = support::run::<Type003>(&css("h1 { font-weight: 600; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "font-weight 600 is outside declared weights [400, 500, 700]"
    );
    assert_eq!(found[0].severity, Severity::Warn);
    assert!(support::run::<Type003>(&css("h1 { font-weight: var(--w); }\n")).is_empty());
}

//! CRAFT008 beyond its rule page: each missing semantic role is reported once, a partial set
//! reports only what is missing, aliases and case count, and a complete set is clean.

// frob:ticket 01M5HM3W18AJZET52BZBEJFYD4

mod support;

use crunk_rules::rules::craft008::Craft008;
use crunk_spec::model::RolePair;
use gob_rules::{RepoRule, Severity};

fn css() -> support::Project {
    support::project("styles/app.css", ".a { color: #111111; }\n", None)
}

fn declare(host: &mut support::Project, names: &[&str]) {
    for name in names {
        host.spec.roles.insert(
            (*name).to_owned(),
            RolePair {
                foreground: "ink".to_owned(),
                background: "paper".to_owned(),
                floor: 4.5,
            },
        );
    }
}

fn messages(host: &support::Project) -> Vec<String> {
    support::run::<Craft008>(host)
        .into_iter()
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
#[test]
fn a_palette_with_no_semantic_role_reports_each_one() {
    let host = css();
    let found = support::run::<Craft008>(&host);
    assert_eq!(found.len(), 3, "{found:?}");
    for (finding, role) in found.iter().zip(["danger", "warning", "success"]) {
        assert!(
            finding.message.starts_with(&format!("no `{role}` role")),
            "{}",
            finding.message
        );
        assert_eq!(finding.severity, Severity::Advisory);
    }
}

// frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
#[test]
fn a_palette_declaring_all_three_roles_is_clean() {
    let mut host = css();
    declare(&mut host, &["danger", "warning", "success"]);
    assert!(messages(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
#[test]
fn a_partial_set_reports_only_the_missing_roles() {
    let mut host = css();
    declare(&mut host, &["danger"]);
    let found = messages(&host);
    assert_eq!(found.len(), 2, "{found:?}");
    assert!(found[0].starts_with("no `warning` role"), "{}", found[0]);
    assert!(found[1].starts_with("no `success` role"), "{}", found[1]);

    let mut only_success = css();
    declare(&mut only_success, &["success"]);
    assert_eq!(messages(&only_success).len(), 2);
}

// frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
#[test]
fn aliases_and_case_count_for_the_role() {
    let mut host = css();
    declare(&mut host, &["Error", "CAUTION", "positive"]);
    assert!(messages(&host).is_empty(), "{:?}", messages(&host));

    let mut destructive = css();
    declare(&mut destructive, &["destructive", "Warning", "Success"]);
    assert!(messages(&destructive).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
#[test]
fn unrelated_role_names_do_not_stand_in_for_a_semantic_role() {
    let mut host = css();
    declare(
        &mut host,
        &["dangerous", "warn", "successful", "info", "body"],
    );
    assert_eq!(messages(&host).len(), 3);
}

// frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
#[test]
fn the_rule_applies_to_a_project_with_a_spec_and_styles() {
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Craft008, &css()),
        None
    );
}

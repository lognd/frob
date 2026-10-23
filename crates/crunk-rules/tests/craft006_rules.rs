//! CRAFT006 beyond its rule page: each missing scale is reported once, names the rule it leaves
//! with nothing to judge, and a project declaring all three is clean.

// frob:ticket 01M5HM3VTW5FAZQ3TXM8XH739S

mod support;

use crunk_rules::rules::craft006::Craft006;
use gob_rules::{RepoRule, Severity};

fn css(config: Option<&str>) -> support::Project {
    support::project("styles/app.css", ".a { color: #111111; }\n", config)
}

fn messages(host: &support::Project) -> Vec<String> {
    support::run::<Craft006>(host)
        .into_iter()
        .map(|f| f.message)
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
#[test]
fn every_missing_scale_is_reported_with_its_paired_rule() {
    let mut host = css(None);
    host.spec.scales.font_sizes.clear();
    host.spec.scales.spacing.clear();
    host.spec.scales.radii.clear();
    let found = support::run::<Craft006>(&host);
    assert_eq!(found.len(), 3, "{found:?}");
    assert!(
        found[0].message.starts_with("no type scale") && found[0].message.contains("TYPE001"),
        "{}",
        found[0].message
    );
    assert!(
        found[1].message.starts_with("no spacing scale") && found[1].message.contains("SPACE001"),
        "{}",
        found[1].message
    );
    assert!(
        found[2].message.starts_with("no radius policy") && found[2].message.contains("SLOP022"),
        "{}",
        found[2].message
    );
    assert!(found.iter().all(|f| f.severity == Severity::Advisory));
}

// frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
#[test]
fn a_project_declaring_all_three_scales_is_clean() {
    let host = css(None);
    assert!(messages(&host).is_empty());
    let mut one_step = css(None);
    one_step.spec.scales.font_sizes = vec![16.0];
    one_step.spec.scales.spacing = vec![8.0];
    one_step.spec.scales.radii = vec![0.0];
    assert!(
        messages(&one_step).is_empty(),
        "a one-step scale is still a scale"
    );
}

// frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
#[test]
fn a_partial_set_reports_only_the_missing_scale() {
    let mut host = css(None);
    host.spec.scales.spacing.clear();
    let found = messages(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("SPACE001"), "{}", found[0]);

    let radii_missing = css(Some("no-radii"));
    let found = messages(&radii_missing);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("RADIUS001"), "{}", found[0]);
}

// frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
#[test]
fn a_radius_decision_stands_in_for_the_radii_scale() {
    let host = css(Some("no-radii-decided"));
    assert!(host.spec.scales.radii.is_empty());
    assert!(messages(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
#[test]
fn radii_declared_but_unused_are_still_a_policy() {
    let host = css(None);
    assert!(!host.spec.scales.radii.is_empty());
    assert!(messages(&host).is_empty(), "no border-radius is written");
}

// frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
#[test]
fn the_rule_applies_to_a_project_with_a_spec_and_styles() {
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Craft006, &css(None)),
        None
    );
}

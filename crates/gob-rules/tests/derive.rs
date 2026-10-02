//! End-to-end proof of `#[derive(Rule)]`, the registry and the reason checker.

use gob_rules::{
    FixKind, Polarity, ReasonPolicy, ReasonRejected, Registry, RegistryError, Rule, RuleMeta,
    Scope, Severity, Tier, check_reason,
};

/// Every public item needs a doc comment.
///
/// Longer markdown explanation of the rule.
#[derive(Rule)]
#[rule(
    id = "DEM001", slug = "demo-rule", family = "DEM", product = "frob",
    severity = Error, tier = Lang, scope = File, fix = Manual, version = 1, since = "2.0.0"
)]
struct DemoRule;

/// Second rule used for lookups.
#[derive(Rule)]
#[rule(id = "DEM002", slug = "demo-two", family = "DEM", severity = Warn,
    tier = Universal, scope = Repo, fix = FixIt, version = 3)]
struct DemoTwo;

/// Declares polarity and `must_measure` explicitly.
#[derive(Rule)]
#[rule(id = "DEM003", slug = "demo-three", family = "DEM", severity = Warn,
    tier = Universal, scope = Repo, fix = Manual, polarity = Pminus, must_measure = true, version = 1)]
struct DemoThree;

#[test]
fn polarity_defaults_to_pplus_and_must_measure_to_false() {
    assert_eq!(DemoRule.meta().polarity, Polarity::Pplus);
    assert!(!DemoRule.meta().must_measure);
    assert_eq!(DemoThree.meta().polarity, Polarity::Pminus);
    assert!(DemoThree.meta().must_measure);
    assert_eq!(Polarity::Pminus.symbol(), "P-");
}

#[test]
fn registry_lists_derived_rules_by_id_and_slug() {
    let reg = Registry::global();
    let m = reg.by_id("DEM001").expect("registered");
    assert_eq!(m.slug, "demo-rule");
    assert_eq!(m.summary, "Every public item needs a doc comment.");
    assert_eq!(
        m.explanation,
        "Every public item needs a doc comment.\n\nLonger markdown explanation of the rule."
    );
    assert_eq!(
        (m.severity, m.tier, m.scope, m.fix),
        (Severity::Error, Tier::Lang, Scope::File, FixKind::Manual)
    );
    assert!(m.module.starts_with("derive"));
    assert_eq!(reg.by_slug("demo-two").map(|m| m.id), Some("DEM002"));
    assert_eq!(DemoTwo.meta().version, 3);
    assert_eq!(DemoRule.meta().rule_id().unwrap().family(), "DEM");
    let ids: Vec<_> = reg.iter().map(|m| m.id).collect();
    assert!(ids.windows(2).all(|w| w[0] <= w[1]));
    assert!(reg.verify_unique().is_ok());
}

#[test]
fn duplicate_ids_are_reported_with_both_modules() {
    static A: RuleMeta = DemoRule::META;
    static B: RuleMeta = RuleMeta {
        module: "other_crate::rules",
        slug: "other",
        ..DemoRule::META
    };
    let reg = Registry::from_metas([&A, &B]);
    let err = reg.verify_unique().unwrap_err();
    assert!(matches!(err, RegistryError::DuplicateId { .. }));
    let text = err.to_string();
    assert!(
        text.contains("DEM001") && text.contains("derive") && text.contains("other_crate::rules"),
        "{text}"
    );
}

#[test]
fn reasons_are_vetted() {
    let p = ReasonPolicy::default();
    assert!(check_reason("generated code, see ADR-0007", &p).is_ok());
    assert!(matches!(
        check_reason("short", &p),
        Err(ReasonRejected::TooShort { .. })
    ));
    assert_eq!(
        check_reason("this is temporary until later", &p),
        Err(ReasonRejected::Banned {
            pattern: "temporary".into()
        })
    );
    assert_eq!(
        check_reason("we will fix later maybe", &p),
        Err(ReasonRejected::Banned {
            pattern: "fix-later".into()
        })
    );
    assert!(matches!(
        check_reason("COV006 does not apply", &p),
        Err(ReasonRejected::RestatesRule { .. })
    ));
    assert!(matches!(
        check_reason("really really needed here", &p),
        Err(ReasonRejected::RepeatedWord { .. })
    ));
    let strict = ReasonPolicy {
        min_len: 40,
        ..ReasonPolicy::default()
    };
    assert!(check_reason("generated code, see ADR-0007", &strict).is_err());
}

#[test]
fn fingerprint_ignores_numbers_and_whitespace_but_not_anchor() {
    use gob_rules::{Finding, RuleId};
    let r: RuleId = "DEM001".parse().unwrap();
    let a = Finding::new(
        r.clone(),
        Severity::Warn,
        None,
        "line 3:  too   long (120)",
        "a.rs",
    );
    let b = Finding::new(
        r.clone(),
        Severity::Warn,
        None,
        "line 40: too long (9)",
        "a.rs",
    );
    let c = Finding::new(r, Severity::Warn, None, "line 3: too long (120)", "b.rs");
    assert_eq!(a.fingerprint, b.fingerprint);
    assert_ne!(a.fingerprint, c.fingerprint);
    assert_eq!(a.fingerprint.to_hex().len(), 64);
}

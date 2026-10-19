// frob:ticket 01M3ZX7XBY8S4DXNFVYWVF8884
//! Policy snapshot and delta tests (security.md 2.7).
use gob_trust::policy::{PolicyChange, PolicySnapshot};

const BASE: &str = r#"
name = "x"
fail_on = "error"
[rules.SEC001]
severity = "error"
[exclude]
paths = ["target/**"]
[display]
color = true
"#;

const HEAD: &str = r#"
name = "renamed"
fail_on = "error"
[rules.SEC001]
severity = "error"
disabled = true
[exclude]
paths = ["target/**", "src/**"]
[display]
color = false
"#;

// frob:tests crates/gob-trust/src/policy/mod.rs::PolicySnapshot.diff
#[test]
fn disabled_rule_and_widened_exclude_appear_with_old_and_new() {
    let base = PolicySnapshot::from_toml(BASE).unwrap();
    let head = PolicySnapshot::from_toml(HEAD).unwrap();
    let delta = base.diff(&head);
    assert_eq!(
        delta.changes,
        vec![
            PolicyChange {
                key: "exclude.paths".into(),
                old: Some(r#"["target/**"]"#.into()),
                new: Some(r#"["target/**", "src/**"]"#.into()),
            },
            PolicyChange {
                key: "rules.SEC001.disabled".into(),
                old: None,
                new: Some("true".into()),
            },
        ]
    );
}

// frob:tests crates/gob-trust/src/policy/mod.rs::PolicySnapshot.diff
#[test]
fn identical_policy_has_empty_delta() {
    let a = PolicySnapshot::from_toml(BASE).unwrap();
    let b = PolicySnapshot::from_toml(BASE)
        .unwrap()
        .with_declaration("x", "y");
    assert!(a.diff(&a.clone()).is_empty());
    assert!(!a.diff(&b).is_empty());
}

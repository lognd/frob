//! Effect class inference and may-alias write placement (cohesion.md 5).
// frob:ticket 01M4CXT1GFPWZAMV0BCBH3WC4G
use std::collections::BTreeSet;

use gob_ir::Answer;
use gob_ir::effect_class::{
    Callee, EffectClass, EffectCollector, EffectFacts, WriteTarget, classify,
};

fn set(names: &[&str]) -> BTreeSet<String> {
    names.iter().map(|s| (*s).to_owned()).collect()
}

// frob:tests crates/gob-ir/src/effect_class.rs::classify
#[test]
fn classes_follow_lo_and_hi() {
    let none = EffectFacts::default();
    let clock = EffectFacts {
        ambient: set(&["clock"]),
        ..EffectFacts::default()
    };
    let open = EffectFacts {
        open: true,
        ..EffectFacts::default()
    };
    assert_eq!(classify(&Answer::Exact(none.clone())), EffectClass::Pure);
    assert_eq!(classify(&Answer::Unknown), EffectClass::Unknown);
    assert_eq!(classify(&Answer::NotApplicable), EffectClass::Unknown);
    assert_eq!(
        classify(&Answer::Bounds {
            lo: clock.clone(),
            hi: open.clone()
        }),
        EffectClass::Impure
    );
    assert_eq!(
        classify(&Answer::Bounds {
            lo: none.clone(),
            hi: open
        }),
        EffectClass::Unknown
    );
    assert_eq!(
        classify(&Answer::Bounds {
            lo: none,
            hi: clock
        }),
        EffectClass::Unknown
    );
}

// frob:tests crates/gob-ir/src/effect_class.rs::EffectCollector.call
// frob:tests crates/gob-ir/src/effect_class.rs::EffectCollector.finish
#[test]
fn callee_param_writes_land_on_argument_targets() {
    let mut w = EffectCollector::new();
    w.write(WriteTarget::Param);
    let writer = w.finish().effects;
    // Passing the caller's own parameter keeps the caller honest.
    let mut c = EffectCollector::new();
    c.call("s", Callee::Resolved(&writer), &[WriteTarget::Param]);
    assert_eq!(c.finish().class(), EffectClass::Honest);
    // Passing a fresh local is no effect on the outside world.
    let mut c = EffectCollector::new();
    c.call("s", Callee::Resolved(&writer), &[WriteTarget::Local]);
    assert_eq!(c.finish().class(), EffectClass::Pure);
    // Passing a global may write it: not proven, so Unknown.
    let mut c = EffectCollector::new();
    c.call("s", Callee::Resolved(&writer), &[WriteTarget::Global]);
    assert_eq!(c.finish().class(), EffectClass::Unknown);
    // No argument to land on: unresolvable.
    let mut c = EffectCollector::new();
    c.call("s", Callee::Resolved(&writer), &[]);
    assert_eq!(c.finish().class(), EffectClass::Unknown);
    // An Unknown callee answer widens.
    let mut c = EffectCollector::new();
    c.call("s", Callee::Resolved(&Answer::Unknown), &[]);
    assert_eq!(c.finish().class(), EffectClass::Unknown);
}

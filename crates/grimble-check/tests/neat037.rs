//! NEAT037 effect-row-widening and the conditional answers of claimed boundaries (cohesion.md 5).

// frob:ticket 01M4CXT1GFPWZAMV0BCBH3WC4G

#![allow(unused_crate_dependencies)]

use gob_ir::Answer;
use gob_ir::effect_class::{
    Callee, ClaimStatus, EffectClaim, EffectClass, EffectCollector, EffectFacts, Inferred,
    WriteTarget, claim_status,
};
use grimble_check::neat037::{Neat037, neat011_applies, neat037};

/// A helper with no annotation: reads the clock when `reads_clock`, otherwise only arithmetic.
fn helper(reads_clock: bool) -> Inferred {
    let mut c = EffectCollector::new();
    if reads_clock {
        c.ambient("clock");
    }
    c.finish()
}

fn ffi_claim() -> EffectClaim {
    EffectClaim {
        label: "ffi.c:3 grimble:effects none".to_owned(),
        allows: EffectFacts::default(),
    }
}

// frob:tests crates/grimble-check/src/neat037.rs::neat037
// frob:tests crates/gob-ir/src/effect_class.rs::Inferred.class
#[test]
fn pure_helper_that_reads_the_clock_fires_without_annotation() {
    let base = helper(false);
    assert_eq!(base.class(), EffectClass::Pure);
    let head = helper(true);
    let v = neat037(Some(&base), &head);
    assert_eq!(
        v,
        Neat037::Fire {
            from: EffectClass::Pure,
            to: EffectClass::Impure,
            witnesses: vec![],
            assumed: vec![],
        }
    );
}

// frob:tests crates/grimble-check/src/neat037.rs::neat037
#[test]
fn unchanged_better_and_new_units_do_not_fire() {
    let pure = helper(false);
    let impure = helper(true);
    assert_eq!(neat037(Some(&pure), &pure), Neat037::Clean);
    assert_eq!(neat037(Some(&impure), &pure), Neat037::Clean);
    assert_eq!(neat037(Some(&impure), &impure), Neat037::Clean);
    assert_eq!(neat037(None, &impure), Neat037::NoBase);
}

// frob:tests crates/grimble-check/src/neat037.rs::neat037
// frob:tests crates/gob-ir/src/effect_class.rs::EffectCollector.widen
#[test]
fn losing_the_proof_is_a_widening_with_the_call_site_as_witness() {
    let base = helper(false);
    let mut c = EffectCollector::new();
    c.call("f.py:9 mystery()", Callee::Opaque, &[]);
    let head = c.finish();
    assert_eq!(head.class(), EffectClass::Unknown);
    let Neat037::Fire { to, witnesses, .. } = neat037(Some(&base), &head) else {
        panic!("expected Fire")
    };
    assert_eq!(to, EffectClass::Unknown);
    assert_eq!(witnesses, vec!["f.py:9 mystery()".to_owned()]);
}

// frob:tests crates/grimble-check/src/neat037.rs::neat037
// frob:tests crates/gob-ir/src/effect_class.rs::EffectCollector.write
#[test]
fn honest_to_may_alias_global_write_widens_but_param_write_does_not() {
    let mut c = EffectCollector::new();
    c.write(WriteTarget::Param);
    let honest = c.finish();
    assert_eq!(honest.class(), EffectClass::Honest);
    let mut c = EffectCollector::new();
    c.write(WriteTarget::Param);
    c.write(WriteTarget::Local);
    assert_eq!(neat037(Some(&honest), &c.finish()), Neat037::Clean);
    let mut c = EffectCollector::new();
    c.write(WriteTarget::MayAlias);
    let aliased = c.finish();
    assert_eq!(aliased.class(), EffectClass::Unknown);
    assert!(matches!(
        neat037(Some(&honest), &aliased),
        Neat037::Fire { .. }
    ));
}

// frob:tests crates/gob-ir/src/effect_class.rs::EffectCollector.call
// frob:tests crates/gob-ir/src/effect_class.rs::claim_status
// frob:tests crates/gob-ir/src/effect_class.rs::EffectFacts.within
// frob:tests crates/gob-ir/src/effect_class.rs::Inferred.reasons
#[test]
fn ffi_boundary_claim_resolves_callers_conditionally_and_stays_unverified() {
    let claim = ffi_claim();
    let mut c = EffectCollector::new();
    c.call("lib.rs:5 ffi_add()", Callee::Claimed(&claim), &[]);
    let caller = c.finish();
    assert_eq!(caller.class(), EffectClass::Pure);
    assert!(caller.is_conditional());
    assert_eq!(
        caller.reasons(),
        vec!["assumed:ffi.c:3 grimble:effects none".to_owned()]
    );
    assert!(caller.witnesses.is_empty());
    // The same caller without the claim is Unknown: the claim is what resolves it.
    let mut c = EffectCollector::new();
    c.call("lib.rs:5 ffi_add()", Callee::Opaque, &[]);
    assert_eq!(c.finish().class(), EffectClass::Unknown);
    // The claim itself is never verified while the body is unreachable.
    assert_eq!(
        claim_status(&claim, &Answer::Unknown),
        ClaimStatus::Unverified
    );
    assert_eq!(
        claim_status(&claim, &Answer::NotApplicable),
        ClaimStatus::Unverified
    );
}

// frob:tests crates/gob-ir/src/effect_class.rs::claim_status
// frob:tests crates/gob-ir/src/effect_class.rs::EffectFacts.within
#[test]
fn claim_against_an_analysable_body_is_verified_or_contradicted() {
    let claim = ffi_claim();
    let pure = Answer::Exact(EffectFacts::default());
    assert_eq!(claim_status(&claim, &pure), ClaimStatus::Verified);
    let clock = helper(true).effects;
    assert_eq!(claim_status(&claim, &clock), ClaimStatus::Contradicted);
    let open = Answer::Bounds {
        lo: EffectFacts::default(),
        hi: EffectFacts {
            open: true,
            ..EffectFacts::default()
        },
    };
    assert_eq!(claim_status(&claim, &open), ClaimStatus::Unverified);
}

// frob:tests crates/grimble-check/src/neat037.rs::neat011_applies
#[test]
fn neat011_asks_only_public_units_of_unknown_class() {
    assert!(neat011_applies(true, EffectClass::Unknown));
    assert!(!neat011_applies(false, EffectClass::Unknown));
    for c in [EffectClass::Pure, EffectClass::Honest, EffectClass::Impure] {
        assert!(!neat011_applies(true, c));
    }
}

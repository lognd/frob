//! Type precision of type-dependent answers (`cohesion.md` 2.1, 2.3).
// frob:ticket 01M4CXSVQQCP2ZJK37Y5GNWGYG
use gob_ir::{SiteFacts, Status, TypePrecision, TypeProvenance, TypeTrust, resolve_site};
use gob_rules::{UnknownClass, UnresolvedReason};

// frob:tests crates/gob-ir/src/precision.rs::resolve_site
#[test]
fn any_receiver_dispatch_is_unknown_dynamic_site_with_remedy() {
    let a = resolve_site(SiteFacts::default());
    assert_eq!(a.status, Status::Unknown);
    assert_eq!(a.precision, TypePrecision::Dynamic);
    assert_eq!(
        a.reason.as_ref().map(UnresolvedReason::code),
        Some("dynamic-site")
    );
    assert_eq!(a.class(), Some(UnknownClass::DynamicSite));
    assert!(a.remedy().is_some_and(|r| r.contains("annotate")));
}

// frob:tests crates/gob-ir/src/precision.rs::resolve_site
#[test]
fn the_policy_table_maps_provenance_to_status() {
    let base = SiteFacts {
        provenance: TypeProvenance::CHECKER,
        closed: true,
        checker_ran: true,
        concrete: true,
        ..SiteFacts::default()
    };
    assert_eq!(resolve_site(base).status, Status::Must);
    assert_eq!(resolve_site(base).precision, TypePrecision::Exact);
    assert_eq!(
        resolve_site(SiteFacts {
            concrete: false,
            ..base
        })
        .status,
        Status::May
    );

    let inf = SiteFacts {
        provenance: TypeProvenance::LOCAL_INFERENCE,
        ..SiteFacts::default()
    };
    assert_eq!(resolve_site(inf).status, Status::Must);
    assert_eq!(
        resolve_site(SiteFacts {
            class_mutated: true,
            ..inf
        })
        .status,
        Status::May
    );
    assert_eq!(
        resolve_site(SiteFacts {
            opaque_eval: true,
            ..inf
        })
        .status,
        Status::Unknown
    );

    let ann = SiteFacts {
        provenance: TypeProvenance::ANNOTATION,
        ..SiteFacts::default()
    };
    let r = resolve_site(ann);
    assert_eq!(
        (r.status, r.class()),
        (Status::Unknown, Some(UnknownClass::NotRun))
    );
    let r = resolve_site(SiteFacts {
        checker_ran: true,
        ..ann
    });
    assert_eq!(r.class(), Some(UnknownClass::UntrustedType));
    let r = resolve_site(SiteFacts {
        trust: TypeTrust::Annotated,
        ..ann
    });
    assert_eq!(
        (r.status, r.precision),
        (Status::May, TypePrecision::Claimed)
    );

    let both = SiteFacts {
        provenance: TypeProvenance::ANNOTATION.union(TypeProvenance::LOCAL_INFERENCE),
        conflict: true,
        ..SiteFacts::default()
    };
    let r = resolve_site(both);
    assert_eq!(
        r.reason.as_ref().map(UnresolvedReason::code),
        Some("conflict:annotation-vs-inference")
    );
}

// frob:tests crates/gob-ir/src/precision.rs::TypeAnswer.compose
#[test]
fn composition_meets_status_unions_provenance_and_keeps_the_unknown_reason() {
    let must = resolve_site(SiteFacts {
        provenance: TypeProvenance::LOCAL_INFERENCE,
        ..SiteFacts::default()
    });
    let dynamic = resolve_site(SiteFacts::default());
    let c = must.compose(&dynamic);
    assert_eq!(c.status, Status::Unknown);
    assert_eq!(c.precision, TypePrecision::Dynamic);
    assert_eq!(
        c.reason.as_ref().map(UnresolvedReason::code),
        Some("dynamic-site")
    );
    assert!(c.provenance.contains(TypeProvenance::LOCAL_INFERENCE));
}

// frob:tests crates/gob-ir/src/precision.rs::TypePrecision.name
#[test]
fn precision_names_are_stable() {
    assert_eq!(TypePrecision::Exact.name(), "exact");
    assert_eq!(TypePrecision::Claimed.name(), "claimed");
    assert_eq!(TypePrecision::Inferred.name(), "inferred");
    assert_eq!(TypePrecision::Dynamic.name(), "dynamic");
}

//! Candidate parser and fragment tests (ported from crunk's Python parsing cases).

// frob:ticket 01M43ARVZPN52N6NMB7VRKZYGS

use crunk_tailwind::{
    Alpha, CandidateError, Segment, UtilityValue, parse_candidate, parse_class_list,
    parse_class_segments,
};

fn named(s: &str) -> UtilityValue {
    UtilityValue::Named(s.to_owned())
}

#[test]
fn full_class_splits_into_separate_fields() {
    let c = parse_candidate("md:hover:-mt-[13px]/50").unwrap();
    let variants: Vec<&str> = c.variants.iter().map(|v| v.text.as_str()).collect();
    assert_eq!(variants, ["md", "hover"]);
    assert!(c.negative);
    assert!(!c.important);
    assert_eq!(c.utility, "mt");
    assert_eq!(
        c.value,
        Some(UtilityValue::Arbitrary {
            hint: None,
            content: "13px".into()
        })
    );
    assert_eq!(c.alpha, Some(Alpha::Named("50".into())));
    assert_eq!(c.raw, "md:hover:-mt-[13px]/50");
}

#[test]
fn bare_and_named_utilities() {
    let c = parse_candidate("flex").unwrap();
    assert_eq!((c.utility.as_str(), c.value), ("flex", None));
    let c = parse_candidate("bg-red-500/50").unwrap();
    assert_eq!(
        (c.utility.as_str(), c.value, c.alpha),
        (
            "bg",
            Some(named("red-500")),
            Some(Alpha::Named("50".into()))
        )
    );
    let c = parse_candidate("min-w-4").unwrap();
    assert_eq!((c.utility.as_str(), c.value), ("min-w", Some(named("4"))));
    let c = parse_candidate("-translate-x-1").unwrap();
    assert!(c.negative);
    assert_eq!(
        (c.utility.as_str(), c.value),
        ("translate-x", Some(named("1")))
    );
}

#[test]
fn negative_z_index_arbitrary() {
    let c = parse_candidate("-z-[5]").unwrap();
    assert!(c.negative);
    assert_eq!(c.utility, "z");
}

#[test]
fn importance_both_spellings() {
    assert!(parse_candidate("!p-4").unwrap().important);
    assert!(parse_candidate("p-4!").unwrap().important);
    assert!(!parse_candidate("p-4").unwrap().important);
}

#[test]
fn arbitrary_variants_and_colons_inside_brackets() {
    let c = parse_candidate("[&>p:first-child]:hover:bg-[url(a:b)]").unwrap();
    assert_eq!(c.variants.len(), 2);
    assert!(c.variants[0].arbitrary);
    assert!(!c.variants[1].arbitrary);
    assert_eq!(
        c.value,
        Some(UtilityValue::Arbitrary {
            hint: None,
            content: "url(a:b)".into()
        })
    );
}

#[test]
fn type_hints_arbitrary_alpha_and_css_var() {
    let c = parse_candidate("text-[length:var(--x)]").unwrap();
    assert_eq!(
        c.value,
        Some(UtilityValue::Arbitrary {
            hint: Some("length".into()),
            content: "var(--x)".into()
        })
    );
    let c = parse_candidate("bg-[#ff0000]/[0.37]").unwrap();
    assert_eq!(c.alpha, Some(Alpha::Arbitrary("0.37".into())));
    let c = parse_candidate("bg-(--brand)").unwrap();
    assert_eq!(
        c.value,
        Some(UtilityValue::CssVar {
            hint: None,
            name: "--brand".into()
        })
    );
}

#[test]
fn arbitrary_property() {
    let c = parse_candidate("[mask-image:url(a/b)]").unwrap();
    assert_eq!(c.utility, "");
    assert_eq!(
        c.value,
        Some(UtilityValue::Property {
            property: "mask-image".into(),
            value: "url(a/b)".into()
        })
    );
    assert!(c.alpha.is_none());
}

#[test]
fn malformed_tokens_are_errors() {
    assert_eq!(parse_candidate(""), Err(CandidateError::Empty));
    assert!(matches!(
        parse_candidate("p-[13px"),
        Err(CandidateError::Unbalanced(_))
    ));
    assert!(matches!(
        parse_candidate(":p-4"),
        Err(CandidateError::EmptyVariant(_))
    ));
    assert!(matches!(
        parse_candidate("p-[]"),
        Err(CandidateError::EmptyValue(_))
    ));
    assert!(matches!(
        parse_candidate("p-4/"),
        Err(CandidateError::EmptyValue(_))
    ));
    assert!(matches!(
        parse_candidate("[nocolon]"),
        Err(CandidateError::BadProperty(_))
    ));
    assert!(matches!(
        parse_candidate("-"),
        Err(CandidateError::NoUtility(_))
    ));
}

#[test]
fn static_list_yields_candidates() {
    let r = parse_class_list("p-4  hover:flex\n[bad");
    assert_eq!(r.candidates.len(), 2);
    assert!(r.dynamic.is_empty());
    assert_eq!(r.invalid.len(), 1);
}

#[test]
fn computed_fragments_are_dynamic_not_guessed() {
    // `p-4 z-${n} ${on} flex`
    let r = parse_class_segments(&[
        Segment::Static("p-4 z-"),
        Segment::Dynamic,
        Segment::Static(" "),
        Segment::Dynamic,
        Segment::Static(" flex"),
    ]);
    let names: Vec<&str> = r.candidates.iter().map(|c| c.raw.as_str()).collect();
    assert_eq!(names, ["p-4", "flex"]);
    let partials: Vec<&str> = r.dynamic.iter().map(|d| d.partial.as_str()).collect();
    assert_eq!(partials, ["z-", ""]);
}

#[test]
fn dynamic_suffix_and_prefix_both_dropped() {
    let r = parse_class_segments(&[Segment::Dynamic, Segment::Static("-4 mt-2")]);
    assert_eq!(r.candidates.len(), 1);
    assert_eq!(r.dynamic[0].partial, "-4");
}

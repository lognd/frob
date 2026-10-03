//! Property tests of the glob text overlap test: a "disjoint" answer must be sound.

// frob:ticket 01M41FDWMMZTSHZETC48C6Y5DZ

use frob_lease::overlap::{globs_overlap, matcher};
use proptest::prelude::*;

/// Path segment alphabet for generated paths.
const PATH_SEGS: [&str; 6] = ["a", "b", "c", "ab", "ba", "x.rs"];

/// Every path of 1 to 4 segments over [`PATH_SEGS`].
fn all_paths() -> Vec<String> {
    let mut out = Vec::new();
    let mut layer: Vec<String> = vec![String::new()];
    for _ in 0..4 {
        layer = layer
            .iter()
            .flat_map(|p| {
                PATH_SEGS.iter().map(move |s| {
                    if p.is_empty() {
                        (*s).to_owned()
                    } else {
                        format!("{p}/{s}")
                    }
                })
            })
            .collect();
        out.extend(layer.iter().cloned());
    }
    out
}

fn wild_segment() -> impl Strategy<Value = &'static str> {
    prop::sample::select(vec!["a", "b", "c", "a*", "*", "**", "x.rs", "*.rs", "?"])
}

/// A glob of 1 to 3 segments with at least one wildcard segment.
fn wild_glob() -> impl Strategy<Value = String> {
    prop::collection::vec(wild_segment(), 1..=3)
        .prop_filter("needs a wildcard", |v| {
            v.iter().any(|s| s.contains(['*', '?']))
        })
        .prop_map(|v| v.join("/"))
}

fn literal_path() -> impl Strategy<Value = String> {
    prop::collection::vec(prop::sample::select(PATH_SEGS.to_vec()), 1..=3).prop_map(|v| v.join("/"))
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(512))]

    // A disjoint verdict on two wildcard globs means no path matches both.
    #[test]
    fn disjoint_wild_pairs_share_no_path(a in wild_glob(), b in wild_glob()) {
        if !globs_overlap(&a, &b).unwrap() {
            let (ma, mb) = (matcher(&a).unwrap(), matcher(&b).unwrap());
            for p in all_paths() {
                prop_assert!(!(ma.is_match(&p) && mb.is_match(&p)), "{a} vs {b} share {p}");
            }
        }
    }

    // Symmetry: the verdict does not depend on argument order.
    #[test]
    fn wild_overlap_is_symmetric(a in wild_glob(), b in wild_glob()) {
        prop_assert_eq!(globs_overlap(&a, &b).unwrap(), globs_overlap(&b, &a).unwrap());
    }

    // Literal vs literal: overlap iff equal or one names a directory holding the other.
    #[test]
    fn literal_vs_literal_unchanged(a in literal_path(), b in literal_path()) {
        let expect = a == b
            || b.strip_prefix(&a).is_some_and(|r| r.starts_with('/'))
            || a.strip_prefix(&b).is_some_and(|r| r.starts_with('/'));
        prop_assert_eq!(globs_overlap(&a, &b).unwrap(), expect);
    }

    // Literal vs wild: a wildcard that matches the literal always overlaps it, and one
    // whose literal prefix sits under the literal directory overlaps it.
    #[test]
    fn literal_vs_wild_unchanged(l in literal_path(), w in wild_glob()) {
        let m = matcher(&w).unwrap();
        let prefix_under = w
            .find(['*', '?'])
            .is_some_and(|i| w[..i].starts_with(&format!("{l}/")));
        prop_assert_eq!(globs_overlap(&l, &w).unwrap(), m.is_match(&l) || prefix_under);
    }
}

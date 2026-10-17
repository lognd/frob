//! What BP001-003 share: the px widths the `[breakpoints]` table allows in a media query, and the
//! reading of a responsive utility variant against its base family.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::DesignSpec;

/// The group key of the shared display family (`flex`, `grid`, `block`, `hidden`).
pub const DISPLAY_GROUP: &str = "display";

/// True when `px` equals a declared breakpoint, or the "just below it" spelling `bp - 0.02`.
pub fn matches_breakpoint(px: f64, spec: &DesignSpec) -> bool {
    spec.breakpoints.points.values().any(|bp| {
        let bp = f64::from(i32::try_from(*bp).unwrap_or(i32::MAX));
        (px - bp).abs() < 1e-6 || (px - (bp - 0.02)).abs() < 1e-6
    })
}

/// True when any variant is a declared breakpoint name or an arbitrary `min-[..]`.
pub fn has_responsive_variant(variants: &[String], spec: &DesignSpec) -> bool {
    variants.iter().any(|v| {
        spec.breakpoints.points.contains_key(v.as_str())
            || (v.starts_with("min-[") && v.ends_with(']') && v.len() > "min-[]".len())
    })
}

/// The `(family, group key)` a utility belongs to: an entry ending in `-` is a prefix family
/// (group key is the entry), any other entry must equal the name and joins the shared display group.
pub fn matched_family<'a>(name: &str, base_required: &'a [String]) -> Option<(&'a str, &'a str)> {
    base_required.iter().map(String::as_str).find_map(|entry| {
        if entry.ends_with('-') {
            name.starts_with(entry).then_some((entry, entry))
        } else {
            (name == entry).then_some((entry, DISPLAY_GROUP))
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec() -> DesignSpec {
        let preset = crunk_spec::presets::preset("default").expect("default preset");
        let text = &format!("{preset}\n[breakpoints]\nsm = 640\nmd = 768\n");
        crunk_spec::parse_spec(
            text,
            std::path::Path::new("crunk.toml"),
            std::path::Path::new("."),
        )
        .expect("spec parses")
    }

    // frob:tests crates/crunk-rules/src/breakpoints/mod.rs::matches_breakpoint
    #[test]
    fn a_width_matches_a_breakpoint_or_just_below_it() {
        let s = spec();
        assert!(matches_breakpoint(640.0, &s));
        assert!(matches_breakpoint(767.98, &s));
        assert!(!matches_breakpoint(767.0, &s));
        assert!(!matches_breakpoint(900.0, &s));
    }

    // frob:tests crates/crunk-rules/src/breakpoints/mod.rs::has_responsive_variant
    #[test]
    fn responsive_variants_are_declared_names_or_min_arbitrary() {
        let s = spec();
        let v = |x: &[&str]| x.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
        assert!(has_responsive_variant(&v(&["md"]), &s));
        assert!(has_responsive_variant(&v(&["hover", "min-[900px]"]), &s));
        assert!(!has_responsive_variant(&v(&["max-md"]), &s));
        assert!(!has_responsive_variant(&v(&["hover"]), &s));
    }

    // frob:tests crates/crunk-rules/src/breakpoints/mod.rs::matched_family
    #[test]
    fn families_match_by_prefix_or_exact_name() {
        let req: Vec<String> = ["flex", "hidden", "w-"]
            .iter()
            .map(|s| (*s).to_owned())
            .collect();
        assert_eq!(matched_family("flex", &req), Some(("flex", "display")));
        assert_eq!(matched_family("hidden", &req), Some(("hidden", "display")));
        assert_eq!(matched_family("flex-col", &req), None);
        assert_eq!(matched_family("w-1/2", &req), Some(("w-", "w-")));
        assert_eq!(matched_family("p-4", &req), None);
    }
}

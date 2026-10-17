//! What BP001-003 share: the px widths the `[breakpoints]` table allows in a media query, and the
//! reading of a responsive utility variant against its base family.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::DesignSpec;

/// Utility families that decide the same display property, so `hidden md:block` has a base.
const DISPLAY: &[&str] = &["flex", "grid", "block", "hidden"];

/// The declared breakpoint widths in px, in declaration order.
pub fn widths(spec: &DesignSpec) -> Vec<f64> {
    spec.breakpoints
        .points
        .values()
        .map(|v| f64::from(i32::try_from(*v).unwrap_or(i32::MAX)))
        .collect()
}

/// True when a `min-width` of `px` is a declared breakpoint.
pub fn min_allowed(px: f64, widths: &[f64]) -> bool {
    widths.iter().any(|w| (w - px).abs() < 1e-6)
}

/// True when a `max-width` of `px` is a declared breakpoint, or the usual "just below it" form
/// (`w - 1`, or `w - 0.02` for the fractional spelling).
pub fn max_allowed(px: f64, widths: &[f64]) -> bool {
    widths
        .iter()
        .any(|w| [0.0, 1.0, 0.02].iter().any(|d| (w - d - px).abs() < 1e-6))
}

/// The breakpoint name a utility variant (`md`, `max-md`, `min-lg`) responds to, if it is one.
pub fn responsive_variant<'a>(variants: &'a [String], spec: &DesignSpec) -> Option<&'a str> {
    variants.iter().map(String::as_str).find(|v| {
        let name = v
            .strip_prefix("max-")
            .or_else(|| v.strip_prefix("min-"))
            .unwrap_or(v);
        spec.breakpoints.points.contains_key(name)
    })
}

/// The `base_required` entry a utility name belongs to: an entry ending in `-` is a prefix
/// (`w-`), any other must equal the name or start the name before a `-` (`flex`, `flex-col`).
pub fn base_family<'a>(name: &str, base_required: &'a [String]) -> Option<&'a str> {
    let name = name.trim_start_matches(['!', '-']);
    base_required.iter().map(String::as_str).find(|entry| {
        if entry.ends_with('-') {
            name.starts_with(entry)
        } else {
            name == *entry || name.strip_prefix(entry).is_some_and(|r| r.starts_with('-'))
        }
    })
}

/// True when two `base_required` entries are the same family (the display group counts as one).
pub fn same_family(a: &str, b: &str) -> bool {
    a == b || (DISPLAY.contains(&a) && DISPLAY.contains(&b))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-rules/src/breakpoints/mod.rs::max_allowed
    #[test]
    fn max_width_may_sit_just_below_a_breakpoint() {
        let w = [768.0, 1024.0];
        assert!(min_allowed(768.0, &w));
        assert!(!min_allowed(767.0, &w));
        assert!(max_allowed(768.0, &w));
        assert!(max_allowed(767.0, &w));
        assert!(max_allowed(1023.98, &w));
        assert!(!max_allowed(850.0, &w));
    }

    // frob:tests crates/crunk-rules/src/breakpoints/mod.rs::base_family
    #[test]
    fn families_match_by_prefix_or_whole_word() {
        let req: Vec<String> = ["flex", "grid", "w-"]
            .iter()
            .map(|s| (*s).to_owned())
            .collect();
        assert_eq!(base_family("flex", &req), Some("flex"));
        assert_eq!(base_family("flex-col", &req), Some("flex"));
        assert_eq!(base_family("flexible", &req), None);
        assert_eq!(base_family("w-1/2", &req), Some("w-"));
        assert_eq!(base_family("p-4", &req), None);
        assert!(same_family("flex", "hidden"));
        assert!(!same_family("flex", "w-"));
    }
}

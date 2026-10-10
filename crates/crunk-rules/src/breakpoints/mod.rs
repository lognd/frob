//! What BP001-BP003 share (port of `crunk/rules/_breakpoints.py`): the declared-breakpoint match
//! with the `-0.02px` Tailwind idiom, the responsive-variant test, and the `base_required` family
//! grouping of BP002.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use indexmap::IndexMap;

/// The `-0.02px` Tailwind max-width idiom: a declared breakpoint is also accepted at bp - 0.02.
const DOT02_TOLERANCE: f64 = 0.02;

/// The group key every bare `base_required` entry shares: `flex`, `grid`, `block` and `hidden` are
/// mutually exclusive display values, so any one unprefixed establishes the display base for all.
const DISPLAY_FAMILY: &str = "display";

/// True when `px` equals a declared breakpoint or that breakpoint minus the `-0.02px` idiom.
#[allow(
    clippy::float_cmp,
    reason = "a breakpoint matches only on an exact written value, as in the Python rule"
)]
pub fn matches_breakpoint(px: f64, points: &IndexMap<String, i64>) -> bool {
    points.values().any(|&bp| {
        #[allow(clippy::cast_precision_loss, reason = "breakpoints are small integers")]
        let bp = bp as f64;
        px == bp || px == bp - DOT02_TOLERANCE
    })
}

/// True when a utility's variants include a declared breakpoint name or an arbitrary `min-[...]`.
pub fn has_responsive_variant(variants: &[String], points: &IndexMap<String, i64>) -> bool {
    variants.iter().any(|variant| {
        points.contains_key(variant)
            || (variant.len() > "min-[]".len()
                && variant.starts_with("min-[")
                && variant.ends_with(']'))
    })
}

/// `(display name, group key)` of the `base_required` family `name` belongs to: a prefix match for
/// entries ending in `-` (each its own group), an exact match otherwise (all sharing one group).
pub fn matched_family<'a>(name: &str, base_required: &'a [String]) -> Option<(&'a str, &'a str)> {
    base_required.iter().find_map(|family| {
        if family.ends_with('-') {
            name.starts_with(family.as_str())
                .then_some((family.as_str(), family.as_str()))
        } else {
            (name == family).then_some((family.as_str(), DISPLAY_FAMILY))
        }
    })
}

/// Why the BP rules cannot run on `host`: no spec or styles, or no `[breakpoints]` (the family is
/// off, as in the Python rules which returned nothing).
pub fn off_reason<H: crate::host::CrunkHost + ?Sized>(host: &H) -> Option<String> {
    if let Some(why) = crate::host::missing_inputs(host) {
        return Some(why);
    }
    host.spec()
        .is_some_and(|spec| spec.breakpoints.points.is_empty())
        .then(|| {
            "no [breakpoints] are declared and no [tailwind] config supplies defaults".to_owned()
        })
}

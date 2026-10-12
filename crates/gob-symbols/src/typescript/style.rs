//! Pure text helpers for lowering inline `style={{..}}` objects: property names and React's unit rules.
//!
//! The value tokens live in [`crate::css::tokens`], shared with the CSS adapter.

// frob:ticket 01M47QKSBYX7YFQHV3VVGKB025

/// Properties React leaves unitless when the value is a number.
const UNITLESS: [&str; 22] = [
    "animation-iteration-count",
    "aspect-ratio",
    "column-count",
    "flex",
    "flex-grow",
    "flex-shrink",
    "flex-order",
    "font-weight",
    "grid-area",
    "grid-column",
    "grid-row",
    "line-height",
    "opacity",
    "order",
    "orphans",
    "scale",
    "tab-size",
    "widows",
    "z-index",
    "zoom",
    "fill-opacity",
    "stroke-opacity",
];

/// The CSS property for a style-object key: `backgroundColor` is `background-color`, `WebkitX` is `-webkit-x`.
pub(super) fn css_property(key: &str) -> String {
    if key.starts_with("--") {
        return key.to_owned();
    }
    let mut out = String::with_capacity(key.len() + 4);
    if key.starts_with("ms") && key[2..].starts_with(|c: char| c.is_ascii_uppercase()) {
        out.push('-');
    }
    for c in key.chars() {
        if c.is_ascii_uppercase() {
            out.push('-');
            out.push(c.to_ascii_lowercase());
        } else {
            out.push(c);
        }
    }
    out
}

// frob:ticket 01M4DPJQ0TAE8FM53FEJZPBV6H
/// Whether React leaves a bare number on `property` (a CSS name) without a unit: the single unitless list, plus custom properties.
pub fn is_unitless(property: &str) -> bool {
    UNITLESS.contains(&property) || property.starts_with("--")
}

// frob:ticket 01M4DPJQ0TAE8FM53FEJZPBV6H
/// The raw CSS text of a numeric style value: React appends `px` unless the property is unitless or the value is 0.
pub fn numeric_raw(property: &str, number: &str) -> String {
    let zero = number.parse::<f64>().is_ok_and(|v| v == 0.0);
    if zero || is_unitless(property) {
        number.to_owned()
    } else {
        format!("{number}px")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-symbols/src/typescript/style.rs::css_property
    #[test]
    fn keys_become_css_properties() {
        assert_eq!(css_property("backgroundColor"), "background-color");
        assert_eq!(css_property("WebkitMask"), "-webkit-mask");
        assert_eq!(css_property("msTransform"), "-ms-transform");
        assert_eq!(css_property("--gap"), "--gap");
        assert_eq!(css_property("color"), "color");
    }

    // frob:ticket 01M4DPJQ0TAE8FM53FEJZPBV6H
    // frob:tests crates/gob-symbols/src/typescript/style.rs::is_unitless
    #[test]
    fn unitless_covers_the_list_and_custom_properties() {
        assert!(is_unitless("opacity"));
        assert!(is_unitless("--gap"));
        assert!(!is_unitless("margin-top"));
    }

    // frob:tests crates/gob-symbols/src/typescript/style.rs::numeric_raw
    #[test]
    fn numbers_get_px_unless_unitless() {
        assert_eq!(numeric_raw("margin-top", "16"), "16px");
        assert_eq!(numeric_raw("opacity", "0.5"), "0.5");
        assert_eq!(numeric_raw("margin", "0"), "0");
    }
}

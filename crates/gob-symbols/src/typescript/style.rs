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

/// The raw CSS text of a numeric style value: React appends `px` unless the property is unitless or the value is 0.
pub(super) fn numeric_raw(property: &str, number: &str) -> String {
    let zero = number.parse::<f64>().is_ok_and(|v| v == 0.0);
    if zero || UNITLESS.contains(&property) || property.starts_with("--") {
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

    // frob:tests crates/gob-symbols/src/typescript/style.rs::numeric_raw
    #[test]
    fn numbers_get_px_unless_unitless() {
        assert_eq!(numeric_raw("margin-top", "16"), "16px");
        assert_eq!(numeric_raw("opacity", "0.5"), "0.5");
        assert_eq!(numeric_raw("margin", "0"), "0");
    }
}

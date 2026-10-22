//! The dialect's allow-lists: the CSS properties the layout solver implements (plus the paint and
//! text properties that map to design tokens) and the HTML tags a scene may use.

// frob:ticket 01M4CXRDTCFVJ4VPZKAJ22BXS0

/// The CSS properties a scene may declare, lowercase and sorted.
///
/// Layout: `display`, block, flex (wrap in both directions) and grid (tracks, cells, spans),
/// absolute positioning, `gap`, padding and margin, min and max sizes and `aspect-ratio`. Paint and
/// text: the longhands that take a token (`color`, `background-color`, `border-*`, `font-*`).
/// Shorthands that can smuggle in an unsupported feature (`background`, `font`, `transition`,
/// `animation`, `filter`) are deliberately absent; their longhands are listed instead.
pub const SUPPORTED_PROPERTIES: &[&str] = &[
    "align-content",
    "align-items",
    "align-self",
    "aspect-ratio",
    "background-color",
    "border",
    "border-bottom",
    "border-bottom-color",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
    "border-bottom-width",
    "border-color",
    "border-left",
    "border-left-color",
    "border-left-width",
    "border-radius",
    "border-right",
    "border-right-color",
    "border-right-width",
    "border-style",
    "border-top",
    "border-top-color",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-top-width",
    "border-width",
    "bottom",
    "box-sizing",
    "color",
    "column-gap",
    "display",
    "flex",
    "flex-basis",
    "flex-direction",
    "flex-flow",
    "flex-grow",
    "flex-shrink",
    "flex-wrap",
    "font-family",
    "font-size",
    "font-style",
    "font-weight",
    "gap",
    "grid",
    "grid-area",
    "grid-auto-columns",
    "grid-auto-flow",
    "grid-auto-rows",
    "grid-column",
    "grid-column-end",
    "grid-column-start",
    "grid-row",
    "grid-row-end",
    "grid-row-start",
    "grid-template",
    "grid-template-areas",
    "grid-template-columns",
    "grid-template-rows",
    "height",
    "inset",
    "justify-content",
    "justify-items",
    "justify-self",
    "left",
    "letter-spacing",
    "line-height",
    "margin",
    "margin-bottom",
    "margin-left",
    "margin-right",
    "margin-top",
    "max-height",
    "max-width",
    "min-height",
    "min-width",
    "opacity",
    "order",
    "overflow",
    "overflow-x",
    "overflow-y",
    "padding",
    "padding-bottom",
    "padding-left",
    "padding-right",
    "padding-top",
    "place-content",
    "place-items",
    "place-self",
    "position",
    "right",
    "row-gap",
    "text-align",
    "top",
    "width",
    "z-index",
];

/// The lowercase HTML tags a scene may use; capitalised tags are component instances.
pub const KNOWN_TAGS: &[&str] = &[
    "a", "article", "aside", "body", "button", "div", "footer", "form", "h1", "h2", "h3", "h4",
    "h5", "h6", "head", "header", "html", "img", "input", "label", "li", "main", "nav", "ol", "p",
    "section", "span", "style", "svg", "textarea", "ul",
];

/// Whether `property` (any case, no surrounding whitespace) is in the dialect.
///
/// Custom properties (`--x`) are token definitions, not styling, and are always allowed. A vendor
/// prefix is never stripped, so `-webkit-box-shadow` is judged as itself and is unsupported.
pub fn is_supported_property(property: &str) -> bool {
    if property.starts_with("--") {
        return true;
    }
    let lower = property.to_ascii_lowercase();
    SUPPORTED_PROPERTIES.binary_search(&lower.as_str()).is_ok()
}

//! crunk's scene dialect (docs/design/crunk.md section 3): restricted HTML and CSS in which every
//! element carries a stable `data-id`, component instances are capitalised tags and the CSS is the
//! subset the layout solver implements. Parsing goes through the gob HTML adapter, which folds
//! `<style>` bodies and inline `style` attributes into the same term, so one pass reads the markup
//! and every declaration. [`unsupported_properties`] is the SCENE001 check.

// frob:ticket 01M4CXRDTCFVJ4VPZKAJ22BXS0

mod dialect;
mod doc;
mod scene001;

pub use dialect::{KNOWN_TAGS, SUPPORTED_PROPERTIES, is_supported_property};
pub use doc::{
    ElementKind, SceneDecl, SceneDoc, SceneElement, SceneError, parse_scene_bytes, parse_scene_html,
};
pub use scene001::{Scene001, unsupported_properties};

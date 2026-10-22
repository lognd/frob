//! SCENE001: a CSS property outside the scene dialect. An unsupported property is a finding, never
//! a silent approximation (docs/design/crunk.md section 3).

// frob:ticket 01M4CXRDTCFVJ4VPZKAJ22BXS0

use crate::dialect::is_supported_property;
use crate::doc::SceneDoc;

/// The rule id.
pub const SCENE001: &str = "SCENE001";

/// One SCENE001 finding: a property the dialect does not implement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Scene001 {
    /// The property as written.
    pub property: String,
    /// Byte offset of the declaration.
    pub offset: usize,
    /// 1-based line of the declaration.
    pub line: u32,
    /// The message, which names the property.
    pub message: String,
}

/// Every declaration of `doc` whose property is outside the dialect, in source order.
pub fn unsupported_properties(doc: &SceneDoc) -> Vec<Scene001> {
    doc.declarations
        .iter()
        .filter(|d| !is_supported_property(&d.property))
        .map(|d| {
            tracing::debug!(property = %d.property, line = d.line, "{SCENE001}: unsupported property");
            Scene001 {
                property: d.property.clone(),
                offset: d.offset,
                line: d.line,
                message: format!(
                    "'{}' is not a scene property; use a supported layout or token property",
                    d.property
                ),
            }
        })
        .collect()
}

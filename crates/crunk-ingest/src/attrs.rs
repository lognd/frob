//! The per-file attributes a crunk host stamps on the file root of a GRL input: the
//! css_root-relative bucket and component, and the outside-`css_root` flag ORG005 reads.

// frob:ticket 01M70RNZ00HMGWP284A0ZD14NZ

use crate::model::{Bucket, Stylesheet};

/// Attribute carrying the bucket name (empty when the file sits in no bucket).
pub const FILE_BUCKET_ATTR: &str = "file.bucket";
/// Attribute carrying the component name (empty when the file is not a component sheet).
pub const FILE_COMPONENT_ATTR: &str = "file.component";
/// Attribute that is `"true"` for a file outside `css_root`, `"false"` for one under it.
pub const OUTSIDE_CSS_ROOT_ATTR: &str = "file.outside_css_root";

/// The attributes stamped on a file root: `(name, value)` pairs.
pub type FileAttrs = Vec<(&'static str, String)>;

fn flag(outside: bool) -> String {
    outside.to_string()
}

/// The attributes of an ingested sheet (always under `css_root`): bucket, component, not outside.
pub fn sheet_attrs(sheet: &Stylesheet) -> FileAttrs {
    let bucket = sheet.bucket.map(Bucket::as_str).unwrap_or_default();
    tracing::debug!(path = %sheet.path.display(), bucket, "ingest: stamping sheet attributes");
    vec![
        (FILE_BUCKET_ATTR, bucket.to_owned()),
        (
            FILE_COMPONENT_ATTR,
            sheet.component.clone().unwrap_or_default(),
        ),
        (OUTSIDE_CSS_ROOT_ATTR, flag(false)),
    ]
}

/// The attributes of an ungoverned `.css` file outside `css_root`: no bucket, no component.
pub fn outside_attrs() -> FileAttrs {
    vec![
        (FILE_BUCKET_ATTR, String::new()),
        (FILE_COMPONENT_ATTR, String::new()),
        (OUTSIDE_CSS_ROOT_ATTR, flag(true)),
    ]
}

//! The per-file attributes the crunk host stamps on each file root of a GRL input
//! (`file.bucket`, `file.component`, `file.outside_css_root`), gathered from the ingested styles.

// frob:ticket 01M70VN3RSMK4QGY4XCNBAN5SY

use std::path::PathBuf;

use crunk_ingest::{FileAttrs, ProjectStyles, outside_attrs, sheet_attrs};

use crate::host::CrunkHost;

/// One file node of the GRL input: its path and the attributes stamped on its root.
#[derive(Debug, Clone, PartialEq)]
pub struct StampedFile {
    /// The file path as ingest saw it.
    pub path: PathBuf,
    /// The `(name, value)` attributes of the file root.
    pub attrs: FileAttrs,
}

/// Every file of `styles` with its stamped attributes: ingested sheets first, then ungoverned files.
pub fn stamp_styles(styles: &ProjectStyles) -> Vec<StampedFile> {
    let sheets = styles.sheets.iter().map(|sheet| StampedFile {
        path: sheet.path.clone(),
        attrs: sheet_attrs(sheet),
    });
    let outside = styles.ungoverned.iter().map(|path| StampedFile {
        path: path.clone(),
        attrs: outside_attrs(),
    });
    let files: Vec<StampedFile> = sheets.chain(outside).collect();
    tracing::debug!(files = files.len(), "host: stamped file attributes");
    files
}

/// The stamped file nodes `host` offers to GRL rules (empty when nothing was ingested).
pub fn host_stamped_files<H: CrunkHost + ?Sized>(host: &H) -> Vec<StampedFile> {
    host.styles().map(stamp_styles).unwrap_or_default()
}

//! Path-to-text bridges for this crate, built on `gob_path` (paths.md section 3).
// frob:ticket 01M41S1MDS78B52KFYDQVZS5DW

use std::ffi::OsStr;
use std::path::Path;

use gob_path::Shown;

/// `path` as text without `~` collapsing (lossy for a non-Unicode path).
pub(crate) fn text(path: &Path) -> String {
    Shown::with_home(path, None).to_string()
}

/// A file name as text (lossy for a non-Unicode name).
pub(crate) fn name_text(name: &OsStr) -> String {
    text(Path::new(name))
}

/// A path's extension as text, if it has one.
pub(crate) fn ext_text(path: &Path) -> Option<String> {
    path.extension().map(name_text)
}

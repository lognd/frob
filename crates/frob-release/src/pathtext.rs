//! Path-to-text bridges for this crate, built on `gob_path` (paths.md section 3).
// frob:ticket 01M41S1MDS78B52KFYDQVZS5DW

use std::ffi::OsStr;
use std::path::Path;

use gob_path::{RelPath, Shown};

/// `path` relative to `root` with `/` separators; the full display form when it is not under `root`.
pub(crate) fn rel_text(root: &Path, path: &Path) -> String {
    RelPath::from_host(root, path).map_or_else(
        |_| Shown::with_home(path, None).to_string(),
        |r| r.as_str().to_owned(),
    )
}

/// A directory entry's file name as text (lossy for a non-Unicode name, which cannot be a `RelPath`).
pub(crate) fn name_text(name: &OsStr) -> String {
    Shown::with_home(Path::new(name), None).to_string()
}

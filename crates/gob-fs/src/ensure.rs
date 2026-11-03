//! Idempotent filesystem steps (ensure a parent, remove if present, copy a tree) that callers
//! would otherwise guard with an `exists()` check, so no caller branches on data and then acts.

use std::fs;
use std::io;
use std::path::Path;

/// Create the parent directory of `path` (and its ancestors); a path with no parent needs none.
///
/// # Errors
/// The I/O error from creating the directory.
pub fn ensure_parent(path: &Path) -> io::Result<()> {
    path.parent().map_or(Ok(()), fs::create_dir_all)
}

/// Remove the file at `path`; a file that is already absent is success.
///
/// # Errors
/// Any I/O error other than the file not existing.
pub fn remove_file_if_present(path: &Path) -> io::Result<()> {
    absent_is_ok(fs::remove_file(path))
}

/// Remove the directory tree at `path`; a tree that is already absent is success.
///
/// # Errors
/// Any I/O error other than the directory not existing.
pub fn remove_dir_all_if_present(path: &Path) -> io::Result<()> {
    absent_is_ok(fs::remove_dir_all(path))
}

/// True when the file at `path` reads as UTF-8 text satisfying `pred`; unreadable counts as false.
pub fn text_matches(path: &Path, pred: impl FnOnce(&str) -> bool) -> bool {
    fs::read_to_string(path).is_ok_and(|text| pred(&text))
}

/// The UTF-8 text at `path`, or `None` when the file does not exist.
///
/// # Errors
/// Any I/O error other than "not found".
pub fn read_optional(path: &Path) -> io::Result<Option<String>> {
    match fs::read_to_string(path) {
        Ok(text) => Ok(Some(text)),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(e),
    }
}

/// Treat "not found" as success, pass every other outcome through.
fn absent_is_ok(done: io::Result<()>) -> io::Result<()> {
    match done {
        Err(e) if e.kind() != io::ErrorKind::NotFound => Err(e),
        _ => Ok(()),
    }
}

/// Recursively copy the directory `from` into `to`, creating `to` and every subdirectory.
///
/// # Errors
/// The first I/O error met while reading `from` or writing `to`.
pub fn copy_tree(from: &Path, to: &Path) -> io::Result<()> {
    fs::create_dir_all(to)?;
    for entry in fs::read_dir(from)? {
        let src = entry?.path();
        let dest = to.join(entry_name(&src));
        copier_for(&src)(&src, &dest)?;
    }
    Ok(())
}

/// The final component of `path`, or an empty path for a path that has none.
fn entry_name(path: &Path) -> &std::ffi::OsStr {
    path.file_name().unwrap_or_default()
}

/// The copy step for `src`: recurse into a directory, copy a file.
fn copier_for(src: &Path) -> fn(&Path, &Path) -> io::Result<()> {
    if src.is_dir() { copy_tree } else { copy_file }
}

/// Copy the single file `from` to `to`.
fn copy_file(from: &Path, to: &Path) -> io::Result<()> {
    fs::copy(from, to).map(drop)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn copy_tree_copies_nested_files() {
        let src = tempfile::tempdir().unwrap();
        let dst = tempfile::tempdir().unwrap();
        fs::create_dir_all(src.path().join("a/b")).unwrap();
        fs::write(src.path().join("a/b/f.txt"), "x").unwrap();
        copy_tree(src.path(), &dst.path().join("out")).unwrap();
        assert_eq!(
            fs::read_to_string(dst.path().join("out/a/b/f.txt")).unwrap(),
            "x"
        );
    }

    #[test]
    fn removals_tolerate_absence_and_ensure_parent_creates() {
        let dir = tempfile::tempdir().unwrap();
        remove_file_if_present(&dir.path().join("none")).unwrap();
        remove_dir_all_if_present(&dir.path().join("none")).unwrap();
        let file = dir.path().join("p/q/f");
        ensure_parent(&file).unwrap();
        assert!(dir.path().join("p/q").is_dir());
    }
}

//! The shared atomic file write: temp sibling, fsync, rename.

// frob:ticket 01M42MGPHZVTJWJHEGJWS4WZBD

use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

/// The sibling temp path a write of `path` stages into.
fn temp_sibling(path: &Path) -> PathBuf {
    let mut tmp = path.as_os_str().to_owned();
    tmp.push(format!(".frob-{}.tmp", std::process::id()));
    PathBuf::from(tmp)
}

/// Write `bytes` to `path` so the target is wholly old or wholly new, never truncated.
///
/// `put` performs the byte transfer into the staged file (tests inject a fault there).
pub(crate) fn write_atomic_with(
    path: &Path,
    bytes: &[u8],
    put: impl FnOnce(&mut File, &[u8]) -> io::Result<()>,
) -> io::Result<()> {
    let tmp = temp_sibling(path);
    let staged = (|| {
        let mut file = File::create(&tmp)?;
        if let Ok(meta) = fs::metadata(path) {
            file.set_permissions(meta.permissions())?;
        }
        put(&mut file, bytes)?;
        file.sync_all()
    })();
    let done = staged.and_then(|()| fs::rename(&tmp, path));
    if let Err(err) = &done {
        tracing::warn!(path = %path.display(), %err, "atomic write failed; target untouched");
        let _ = fs::remove_file(&tmp);
    } else {
        tracing::debug!(path = %path.display(), bytes = bytes.len(), "atomic write committed");
    }
    done
}

/// Write `bytes` to `path` atomically (temp sibling, fsync, rename).
pub(crate) fn write_atomic(path: &Path, bytes: &[u8]) -> io::Result<()> {
    write_atomic_with(path, bytes, |f, b| f.write_all(b))
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests gob-check::atomic::write_atomic_with
    #[test]
    fn killed_write_leaves_the_old_file_whole() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("f.txt");
        fs::write(&path, "old contents").unwrap();
        let err = write_atomic_with(&path, b"brand new contents", |f, b| {
            f.write_all(&b[..5])?;
            Err(io::Error::other("killed after 5 bytes"))
        });
        assert!(err.is_err());
        assert_eq!(fs::read_to_string(&path).unwrap(), "old contents");
        let leftovers = fs::read_dir(dir.path()).unwrap().count();
        assert_eq!(leftovers, 1, "temp file removed");
    }

    // frob:tests gob-check::atomic::write_atomic
    #[test]
    fn completed_write_is_wholly_new() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("f.txt");
        fs::write(&path, "old").unwrap();
        write_atomic(&path, b"new").unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), "new");
    }
}

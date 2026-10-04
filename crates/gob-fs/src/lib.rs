//! Filesystem primitives shared by every goblin: the one atomic file write.
//!
//! Every write that must leave the target wholly old or wholly new goes through
//! [`write_atomic`] (or [`write_atomic_private`] for owner-only files); the
//! inventory test in `tests/inventory.rs` fails on any hand-rolled temp-and-rename.

// frob:ticket 01M43JETBHW7FYNMR6SGVWFAEV

use std::fs::{self, File, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

/// Process-wide counter so concurrent writers of one target never share a temp name.
static SEQ: AtomicU64 = AtomicU64::new(0);

/// How the staged file is created.
#[derive(Clone, Copy)]
enum Perms {
    /// Inherit the target's permissions when it exists.
    Inherit,
    /// Owner read/write only (mode 0600 on Unix).
    Private,
}

/// The sibling temp path a write of `path` stages into.
fn temp_sibling(path: &Path) -> PathBuf {
    let mut tmp = path.as_os_str().to_owned();
    tmp.push(format!(
        ".frob-{}-{}.tmp",
        std::process::id(),
        SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    PathBuf::from(tmp)
}

/// Create the staged file exclusively with the requested permissions.
fn create_staged(tmp: &Path, target: &Path, perms: Perms) -> io::Result<File> {
    let mut opts = OpenOptions::new();
    opts.write(true).create_new(true);
    #[cfg(unix)]
    if matches!(perms, Perms::Private) {
        use std::os::unix::fs::OpenOptionsExt;
        opts.mode(0o600);
    }
    let file = opts.open(tmp)?;
    if matches!(perms, Perms::Inherit)
        && let Ok(meta) = fs::metadata(target)
    {
        file.set_permissions(meta.permissions())?;
    }
    Ok(file)
}

/// Flush the directory entry of a renamed file to disk (Unix; a no-op elsewhere).
fn sync_parent(path: &Path) -> io::Result<()> {
    #[cfg(unix)]
    {
        let dir = match path.parent() {
            Some(p) if !p.as_os_str().is_empty() => p,
            _ => Path::new("."),
        };
        File::open(dir)?.sync_all()?;
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
}

/// Shared body: stage, sync, rename, sync the parent, clean up on failure.
fn write_with(
    path: &Path,
    bytes: &[u8],
    perms: Perms,
    put: impl FnOnce(&mut File, &[u8]) -> io::Result<()>,
) -> io::Result<()> {
    let tmp = temp_sibling(path);
    let staged = (|| {
        let mut file = create_staged(&tmp, path, perms)?;
        put(&mut file, bytes)?;
        file.sync_all()
    })();
    let done = staged.and_then(|()| fs::rename(&tmp, path));
    if let Err(err) = &done {
        tracing::warn!(path = %path.display(), %err, "atomic write failed; target untouched");
        let _ = fs::remove_file(&tmp);
        return done;
    }
    // The rename is committed; a failed directory sync is reported but the content is in place.
    if let Err(err) = sync_parent(path) {
        tracing::warn!(path = %path.display(), %err, "parent directory sync failed after rename");
        return Err(err);
    }
    tracing::debug!(path = %path.display(), bytes = bytes.len(), "atomic write committed");
    Ok(())
}

/// Write `bytes` to `path` so the target is wholly old or wholly new, never truncated.
///
/// `put` performs the byte transfer into the staged file (tests inject a fault there).
///
/// # Errors
/// The I/O error from staging, syncing or renaming; the target is left untouched
/// and the temp file removed.
pub fn write_atomic_with(
    path: &Path,
    bytes: &[u8],
    put: impl FnOnce(&mut File, &[u8]) -> io::Result<()>,
) -> io::Result<()> {
    write_with(path, bytes, Perms::Inherit, put)
}

/// Write `bytes` to `path` atomically (temp sibling, fsync, rename, parent fsync).
///
/// An existing target keeps its permissions.
///
/// # Errors
/// The I/O error from staging, syncing or renaming; the target is left untouched.
pub fn write_atomic(path: &Path, bytes: &[u8]) -> io::Result<()> {
    write_with(path, bytes, Perms::Inherit, Write::write_all)
}

/// Write `bytes` to `path` atomically into an owner-only (0600 on Unix) file.
///
/// # Errors
/// The I/O error from staging, syncing or renaming; the target is left untouched.
pub fn write_atomic_private(path: &Path, bytes: &[u8]) -> io::Result<()> {
    write_with(path, bytes, Perms::Private, Write::write_all)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-fs/src/lib.rs::write_atomic_with
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

    // frob:tests crates/gob-fs/src/lib.rs::write_atomic
    #[test]
    fn completed_write_is_wholly_new() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("f.txt");
        fs::write(&path, "old").unwrap();
        write_atomic(&path, b"new").unwrap();
        assert_eq!(fs::read_to_string(&path).unwrap(), "new");
        assert_eq!(fs::read_dir(dir.path()).unwrap().count(), 1);
    }

    // frob:tests crates/gob-fs/src/lib.rs::write_atomic
    #[test]
    fn bare_relative_parent_syncs_the_current_dir() {
        assert!(sync_parent(Path::new("bare.txt")).is_ok());
    }

    // frob:tests crates/gob-fs/src/lib.rs::write_atomic_private
    #[cfg(unix)]
    #[test]
    fn private_write_is_owner_only() {
        use std::os::unix::fs::PermissionsExt;
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("k");
        write_atomic_private(&path, b"secret").unwrap();
        let mode = fs::metadata(&path).unwrap().permissions().mode() & 0o777;
        assert_eq!(mode, 0o600);
    }

    // frob:tests crates/gob-fs/src/lib.rs::write_atomic
    #[cfg(unix)]
    #[test]
    fn existing_permissions_are_kept() {
        use std::os::unix::fs::PermissionsExt;
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("x.sh");
        fs::write(&path, "a").unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).unwrap();
        write_atomic(&path, b"b").unwrap();
        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o755
        );
    }
}

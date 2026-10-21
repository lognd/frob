//! Pack tree digest: a blake3 Merkle hash over every byte of a pack
//! directory (security.md section 2.1, invariant I3).
//!
//! The digest binds each file's normalized relative path, file type,
//! executable bit and exact bytes (manifest, GRL, WASM, data and explain
//! text alike), plus the digests of included packs. Symlinks, hardlinks,
//! device files and paths escaping the root are refused as PACK005 and no
//! digest is produced.

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use tracing::{debug, warn};

use crate::PackError;

/// A 32-byte blake3 tree digest.
pub type Digest = [u8; 32];

/// Computes the tree digest of the pack at `root`, folding in the digests of
/// `included` packs (order-insensitive).
///
/// # Errors
/// PACK005 [`PackError::Malformed`] for a symlink, hardlink, device file,
/// non-UTF-8 or escaping path, or an unreadable entry; no digest is produced.
pub fn tree_digest(root: &Path, included: &[Digest]) -> Result<Digest, PackError> {
    let name = gob_path::Shown::with_home(root, None).to_string();
    let meta =
        fs::symlink_metadata(root).map_err(|e| bad(&name, &name, format!("unreadable: {e}")))?;
    if !meta.is_dir() {
        return Err(bad(&name, &name, "pack root is not a plain directory"));
    }
    let mut leaves: Vec<(String, Digest)> = Vec::new();
    walk(root, "", &name, &mut leaves)?;
    leaves.sort();
    let mut h = blake3::Hasher::new();
    h.update(b"gob-packs/tree/v1\0");
    h.update(&(leaves.len() as u64).to_le_bytes());
    for (_, d) in &leaves {
        h.update(d);
    }
    let mut inc: Vec<&Digest> = included.iter().collect();
    inc.sort();
    h.update(&(inc.len() as u64).to_le_bytes());
    for d in inc {
        h.update(d);
    }
    let out = *h.finalize().as_bytes();
    debug!(root = %name, files = leaves.len(), "pack tree digest computed");
    Ok(out)
}

/// Renders a digest as lowercase hex.
pub fn to_hex(d: &Digest) -> String {
    d.iter().fold(String::with_capacity(64), |mut s, b| {
        let _ = write!(s, "{b:02x}");
        s
    })
}

fn bad(file: &str, key: &str, reason: impl Into<String>) -> PackError {
    let e = PackError::malformed(file, key, reason);
    warn!(error = %e, "pack tree digest refused");
    e
}

fn walk(
    dir: &Path,
    rel: &str,
    file: &str,
    out: &mut Vec<(String, Digest)>,
) -> Result<(), PackError> {
    let rd = fs::read_dir(dir).map_err(|e| {
        bad(
            file,
            if rel.is_empty() { file } else { rel },
            format!("unreadable: {e}"),
        )
    })?;
    for entry in rd {
        let entry = entry.map_err(|e| bad(file, rel, format!("unreadable: {e}")))?;
        let os = entry.file_name();
        let Some(n) = gob_path::exact_text(&os) else {
            return Err(bad(file, rel, "non-UTF-8 path component"));
        };
        if n.is_empty() || n == "." || n == ".." || n.contains(['/', '\\']) {
            return Err(bad(
                file,
                rel,
                format!("path component `{n}` escapes the pack root"),
            ));
        }
        let rp = if rel.is_empty() {
            n.to_owned()
        } else {
            format!("{rel}/{n}")
        };
        let path = entry.path();
        let md =
            fs::symlink_metadata(&path).map_err(|e| bad(file, &rp, format!("unreadable: {e}")))?;
        let ft = md.file_type();
        if ft.is_symlink() {
            return Err(bad(file, &rp, "symlinks are not allowed in a pack"));
        } else if ft.is_dir() {
            walk(&path, &rp, file, out)?;
        } else if ft.is_file() {
            check_links(&md, file, &rp)?;
            let bytes = fs::read(&path).map_err(|e| bad(file, &rp, format!("unreadable: {e}")))?;
            let mut h = blake3::Hasher::new();
            h.update(&(rp.len() as u64).to_le_bytes());
            h.update(rp.as_bytes());
            h.update(&[b'f', u8::from(is_exec(&md))]);
            h.update(&(bytes.len() as u64).to_le_bytes());
            h.update(&bytes);
            out.push((rp, *h.finalize().as_bytes()));
        } else {
            return Err(bad(
                file,
                &rp,
                "device files and special files are not allowed in a pack",
            ));
        }
    }
    Ok(())
}

#[cfg(unix)]
fn check_links(md: &fs::Metadata, file: &str, rp: &str) -> Result<(), PackError> {
    use std::os::unix::fs::MetadataExt;
    if md.nlink() > 1 {
        return Err(bad(file, rp, "hardlinks are not allowed in a pack"));
    }
    Ok(())
}

#[cfg(not(unix))]
#[allow(clippy::unnecessary_wraps)]
fn check_links(_md: &fs::Metadata, _file: &str, _rp: &str) -> Result<(), PackError> {
    Ok(())
}

#[cfg(unix)]
fn is_exec(md: &fs::Metadata) -> bool {
    use std::os::unix::fs::PermissionsExt;
    md.permissions().mode() & 0o111 != 0
}

#[cfg(not(unix))]
fn is_exec(_md: &fs::Metadata) -> bool {
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pack() -> tempfile::TempDir {
        let d = tempfile::tempdir().unwrap();
        fs::write(d.path().join("pack.toml"), "x").unwrap();
        fs::create_dir(d.path().join("docs")).unwrap();
        fs::write(d.path().join("docs/README.md"), "hello").unwrap();
        d
    }

    #[test]
    fn doc_change_changes_digest() {
        let d = pack();
        let a = tree_digest(d.path(), &[]).unwrap();
        assert_eq!(a, tree_digest(d.path(), &[]).unwrap());
        fs::write(d.path().join("docs/README.md"), "hellp").unwrap();
        assert_ne!(a, tree_digest(d.path(), &[]).unwrap());
    }

    #[cfg(unix)]
    #[test]
    fn exec_bit_changes_digest() {
        use std::os::unix::fs::PermissionsExt;
        let d = pack();
        let a = tree_digest(d.path(), &[]).unwrap();
        let p = d.path().join("pack.toml");
        fs::set_permissions(&p, fs::Permissions::from_mode(0o755)).unwrap();
        assert_ne!(a, tree_digest(d.path(), &[]).unwrap());
    }

    #[test]
    fn included_digests_change_digest() {
        let d = pack();
        assert_ne!(
            tree_digest(d.path(), &[]).unwrap(),
            tree_digest(d.path(), &[[1; 32]]).unwrap()
        );
    }

    #[cfg(unix)]
    #[test]
    fn symlink_is_pack005() {
        let d = pack();
        std::os::unix::fs::symlink("/etc/passwd", d.path().join("l")).unwrap();
        let e = tree_digest(d.path(), &[]).unwrap_err();
        assert_eq!(e.code().as_str(), "PACK005");
    }

    #[cfg(unix)]
    #[test]
    fn hardlink_is_pack005() {
        let d = pack();
        fs::hard_link(d.path().join("pack.toml"), d.path().join("h")).unwrap();
        let e = tree_digest(d.path(), &[]).unwrap_err();
        assert_eq!(e.code().as_str(), "PACK005");
    }

    #[cfg(unix)]
    #[test]
    fn symlink_root_is_pack005() {
        let d = pack();
        let t = tempfile::tempdir().unwrap();
        let l = t.path().join("root");
        std::os::unix::fs::symlink(d.path(), &l).unwrap();
        assert!(tree_digest(&l, &[]).is_err());
    }

    #[test]
    fn hex_is_64_chars() {
        assert_eq!(to_hex(&[0xab; 32]).len(), 64);
    }
}

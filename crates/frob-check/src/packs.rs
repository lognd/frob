//! Live repository packs for `check --trust-from`: every `packs/<name>/` directory with its
//! tree digest, so the base-ref lock can vouch for (or refuse) each one (`security.md` 2.3).

// frob:ticket 01M5C7AWM806DSCHVT4531WB9C

use std::path::Path;

use gob_check::trust_from::LivePack;
use gob_packs::{to_hex, tree_digest};
use tracing::{debug, warn};

/// Repo-relative directory holding vendored repository packs.
pub(crate) const PACKS_DIR: &str = "packs";

#[allow(
    clippy::disallowed_methods,
    reason = "pack dirs are vendored content hashed whole, not walked sources"
)]
/// Enumerates the repository packs under `root/packs` with their `blake3:` tree digests.
///
/// Built-in packs (reserved name prefixes) are compiled in and never lock-gated, so they are
/// skipped. A directory whose manifest or digest cannot be read is skipped: the
/// pack loader reports it as PACK005, and an unlisted pack is never silently trusted because
/// only listed packs are checked against the lock. Packs are `required` so an untrusted one fails CI.
pub(crate) fn live_packs(root: &Path) -> Vec<LivePack> {
    let Ok(entries) = std::fs::read_dir(root.join(PACKS_DIR)) else {
        debug!(root = %root.display(), "no packs directory; no live packs");
        return Vec::new();
    };
    let mut dirs: Vec<_> = entries
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.join("pack.toml").is_file())
        .collect();
    dirs.sort();
    dirs.iter().filter_map(|dir| live_pack(dir)).collect()
}

/// One pack directory as a [`LivePack`], or `None` for a built-in or unreadable pack.
fn live_pack(dir: &Path) -> Option<LivePack> {
    let manifest_path = dir.join("pack.toml");
    // `load` refuses reserved (built-in) names, which are compiled in and not lock-gated.
    let manifest = gob_packs::load(&manifest_path)
        .map_err(|e| debug!(dir = %dir.display(), error = %e, "built-in or invalid pack; skipped"))
        .ok()?;
    let name = manifest.pack.name;
    let digest = tree_digest(dir, &[])
        .map_err(|e| warn!(pack = %name, error = %e, "pack tree digest failed; skipped"))
        .ok()?;
    Some(LivePack {
        name,
        tree: format!("blake3:{}", to_hex(&digest)),
        required: true,
    })
}

#[cfg(test)]
mod tests {
    use super::live_packs;

    fn write_pack(root: &std::path::Path, dir: &str, name: &str) {
        let d = root.join("packs").join(dir);
        std::fs::create_dir_all(&d).unwrap();
        std::fs::write(
            d.join("pack.toml"),
            format!("[pack]\nname = \"{name}\"\nversion = \"1.0.0\"\n"),
        )
        .unwrap();
    }

    // frob:tests crates/frob-check/src/packs.rs::live_packs
    #[test]
    fn live_packs_lists_repo_packs_with_digest_and_skips_builtin() {
        let t = tempfile::tempdir().unwrap();
        write_pack(t.path(), "py-safety", "py-safety");
        write_pack(t.path(), "std", "std");
        let packs = live_packs(t.path());
        assert_eq!(packs.len(), 1);
        assert_eq!(packs[0].name, "py-safety");
        assert!(packs[0].tree.starts_with("blake3:"));
        assert!(packs[0].required);
        std::fs::write(t.path().join("packs/py-safety/extra.grl"), "x").unwrap();
        assert_ne!(live_packs(t.path())[0].tree, packs[0].tree);
    }

    // frob:tests crates/frob-check/src/packs.rs::live_packs
    #[test]
    fn live_packs_empty_without_packs_dir() {
        let t = tempfile::tempdir().unwrap();
        assert!(live_packs(t.path()).is_empty());
    }
}

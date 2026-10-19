//! Process packs: a tool program resolved to an absolute path outside the work tree, with its
//! digest recorded so a different binary is untrusted (security.md section 2.4, I11).

// frob:ticket 01M3ZX7VPGRERTZNVS5VR437JY

use std::ffi::OsStr;
use std::path::{Path, PathBuf};

use tracing::{debug, warn};

use crate::ExecError;
use crate::program::bare_name;

/// Environment names a process pack may inherit besides the baseline; nothing secret-shaped.
pub const PACK_ENV: &[&str] = &["LANG", "LC_ALL", "TERM"];

/// A program resolved for trust: its absolute path and the digest of the binary there.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcessPack {
    /// The command name the stage declared.
    pub name: String,
    /// Absolute, canonical path outside the work tree.
    pub path: PathBuf,
    /// `blake3:` digest of the binary at `path`.
    pub digest: String,
}

impl ProcessPack {
    /// Re-hash the binary and fail unless it still matches the recorded digest.
    ///
    /// # Errors
    /// [`ExecError::DigestChanged`] when the bytes differ, [`ExecError::NotFound`] when unreadable.
    pub fn verify(&self) -> Result<(), ExecError> {
        let found = digest_file(&self.path).ok_or_else(|| ExecError::NotFound {
            program: self.name.clone(),
        })?;
        if found == self.digest {
            Ok(())
        } else {
            warn!(program = %self.name, recorded = %self.digest, %found, "process pack digest changed");
            Err(ExecError::DigestChanged {
                program: self.name.clone(),
                recorded: self.digest.clone(),
                found,
            })
        }
    }
}

/// The `blake3:` digest of the file at `path`; `None` when it cannot be read.
pub fn digest_file(path: &Path) -> Option<String> {
    let bytes = std::fs::read(path).ok()?;
    Some(format!("blake3:{}", blake3::hash(&bytes).to_hex()))
}

/// Resolve `name` against the `search` path list to a pack outside `root`.
///
/// The first executable match wins; if it canonicalizes to a path inside `root` the program is
/// refused (a `PATH` entry inside the work tree cannot be trusted).
///
/// # Errors
/// [`ExecError::NotAllowed`] for a path-like name, [`ExecError::NotFound`] when no entry has it,
/// [`ExecError::InsideWorkTree`] when the match lives inside `root`.
pub fn resolve_pack(name: &str, root: &Path, search: &OsStr) -> Result<ProcessPack, ExecError> {
    let name = bare_name(name)?;
    let root = std::fs::canonicalize(root).unwrap_or_else(|_| root.to_path_buf());
    let found = std::env::split_paths(search)
        .filter(|d| !d.as_os_str().is_empty())
        // A relative entry is relative to the work tree the stage runs in.
        .map(|d| if d.is_absolute() { d } else { root.join(d) })
        .map(|d| d.join(name))
        .find(|p| is_executable(p))
        .ok_or_else(|| ExecError::NotFound {
            program: name.to_owned(),
        })?;
    let path = std::fs::canonicalize(&found).map_err(|_| ExecError::NotFound {
        program: name.to_owned(),
    })?;
    if path.starts_with(&root) || found.starts_with(&root) {
        warn!(program = name, path = %path.display(), "pack resolves inside the work tree; refused");
        return Err(ExecError::InsideWorkTree {
            program: name.to_owned(),
            path: path.display().to_string(),
        });
    }
    let digest = digest_file(&path).ok_or_else(|| ExecError::NotFound {
        program: name.to_owned(),
    })?;
    debug!(program = name, path = %path.display(), %digest, "process pack resolved");
    Ok(ProcessPack {
        name: name.to_owned(),
        path,
        digest,
    })
}

/// True for a regular file with an execute bit (any file on non-Unix).
fn is_executable(path: &Path) -> bool {
    let Ok(meta) = std::fs::metadata(path) else {
        return false;
    };
    if !meta.is_file() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        meta.permissions().mode() & 0o111 != 0
    }
    #[cfg(not(unix))]
    {
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(unix)]
    fn tool(dir: &Path, name: &str, body: &str) -> PathBuf {
        use std::os::unix::fs::PermissionsExt;
        std::fs::create_dir_all(dir).expect("mkdir");
        let p = dir.join(name);
        std::fs::write(&p, body).expect("write");
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).expect("chmod");
        p
    }

    // frob:tests crates/gob-exec/src/pack.rs::resolve_pack
    #[cfg(unix)]
    #[test]
    fn a_path_entry_inside_the_work_tree_is_refused() {
        let root = tempfile::tempdir().expect("root");
        tool(&root.path().join("bin"), "tool", "#!/bin/sh\n");
        let err = resolve_pack("tool", root.path(), root.path().join("bin").as_os_str())
            .expect_err("refused");
        assert!(matches!(err, ExecError::InsideWorkTree { .. }), "{err}");
        let rel = resolve_pack("tool", root.path(), OsStr::new("./bin")).expect_err("relative");
        assert!(matches!(rel, ExecError::InsideWorkTree { .. }), "{rel}");
    }

    // frob:tests crates/gob-exec/src/pack.rs::resolve_pack
    #[cfg(unix)]
    #[test]
    fn a_program_outside_the_work_tree_resolves_with_its_digest() {
        let root = tempfile::tempdir().expect("root");
        let out = tempfile::tempdir().expect("out");
        let p = tool(out.path(), "tool", "#!/bin/sh\n");
        let pack = resolve_pack("tool", root.path(), out.path().as_os_str()).expect("resolves");
        assert_eq!(pack.path, std::fs::canonicalize(&p).expect("canon"));
        assert!(pack.digest.starts_with("blake3:"));
        assert!(pack.verify().is_ok());
    }

    // frob:tests crates/gob-exec/src/pack.rs::ProcessPack.verify
    #[cfg(unix)]
    #[test]
    fn a_changed_binary_fails_verification() {
        let root = tempfile::tempdir().expect("root");
        let out = tempfile::tempdir().expect("out");
        let p = tool(out.path(), "tool", "#!/bin/sh\n");
        let pack = resolve_pack("tool", root.path(), out.path().as_os_str()).expect("resolves");
        tool(out.path(), "tool", "#!/bin/sh\necho changed\n");
        assert!(matches!(
            pack.verify(),
            Err(ExecError::DigestChanged { .. })
        ));
        assert!(p.exists());
    }

    // frob:tests crates/gob-exec/src/pack.rs::resolve_pack
    #[test]
    fn a_path_like_name_is_not_allowed() {
        let root = tempfile::tempdir().expect("root");
        let err = resolve_pack("./tool", root.path(), OsStr::new("/usr/bin")).expect_err("no");
        assert!(matches!(err, ExecError::NotAllowed { .. }));
    }

    // frob:tests crates/gob-exec/src/runner.rs::Runner.run_pack
    #[cfg(unix)]
    #[test]
    fn a_pack_runs_with_a_scrubbed_environment_and_closed_stdin() {
        let root = tempfile::tempdir().expect("root");
        let out = tempfile::tempdir().expect("out");
        tool(
            out.path(),
            "envtool",
            "#!/bin/sh\nenv | sort\nif read x; then echo stdin-open; else echo stdin-closed; fi\n",
        );
        let pack = resolve_pack("envtool", root.path(), out.path().as_os_str()).expect("pack");
        let runner = crate::Runner::new(crate::Limits { jobs: 1 });
        let o = runner
            .run_pack(
                &pack,
                Vec::new(),
                Some(root.path().to_path_buf()),
                std::time::Duration::from_secs(10),
            )
            .expect("runs");
        assert!(o.stdout.contains("GIT_CONFIG_NOSYSTEM=1"), "{}", o.stdout);
        assert!(o.stdout.contains("stdin-closed"), "{}", o.stdout);
        assert!(!o.stdout.contains("CARGO_HOME"), "{}", o.stdout);
        assert!(!o.stdout.contains("USER="), "{}", o.stdout);
    }

    // frob:tests crates/gob-exec/src/runner.rs::Runner.run_pack
    #[cfg(unix)]
    #[test]
    fn a_swapped_binary_is_not_run() {
        let root = tempfile::tempdir().expect("root");
        let out = tempfile::tempdir().expect("out");
        tool(out.path(), "swap", "#!/bin/sh\n");
        let pack = resolve_pack("swap", root.path(), out.path().as_os_str()).expect("pack");
        tool(out.path(), "swap", "#!/bin/sh\necho evil\n");
        let runner = crate::Runner::new(crate::Limits { jobs: 1 });
        let err = runner
            .run_pack(&pack, Vec::new(), None, std::time::Duration::from_secs(10))
            .expect_err("refused");
        assert!(matches!(err, ExecError::DigestChanged { .. }), "{err}");
    }
}

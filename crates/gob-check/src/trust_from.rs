//! `check --trust-from REF`: base-ref trust in CI (`security.md` section 2.3, I1).
//!
//! The pack lock is read from git objects at `REF` (never the work tree) and
//! only the (tree digest, effects) pairs in it are trusted. A pack the change
//! adds or alters reports Unresolved `untrusted-in-change`, which is required
//! in CI, so the gate fails. No user trust store is read or written.

// frob:ticket 01M3ZX7V587K71E94E0AE4GWW8

use gob_git::{GitError, Repo};
use gob_rules::{PackFailure, RequiredReason};
use gob_trust::baseref::{BaseRefError, BaseRefTrust, BaseRefVerdict};
use tracing::{debug, info};

/// Why the base-ref lock could not be loaded.
#[derive(Debug, thiserror::Error)]
pub enum TrustFromError {
    /// `REF` did not resolve or the object read failed.
    #[error("E-TRUST-FROM-REF: {0}")]
    Git(#[from] GitError),
    /// The lock at `REF` is not a valid pack lock.
    #[error("{0}")]
    Lock(#[from] BaseRefError),
    /// The lock at `REF` is not UTF-8.
    #[error("E-TRUST-FROM-UTF8: pack lock at the base ref is not UTF-8")]
    NotUtf8,
}

/// The base-ref decision for one live pack.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PackTrust {
    /// The pack name.
    pub pack: String,
    /// Trusted with recorded effects, or untrusted-in-change.
    pub verdict: BaseRefVerdict,
    /// The required Unresolved reason, set only when untrusted and the pack is required.
    pub required: Option<RequiredReason>,
}

/// A live pack as the check sees it.
#[derive(Debug, Clone)]
pub struct LivePack {
    /// The pack name.
    pub name: String,
    /// The `blake3:` tree digest of the pack as it is in the work tree.
    pub tree: String,
    /// Whether the pack is `required = true`.
    pub required: bool,
}

/// Loads the trust set from `lock_path` (repo-relative) at `base_ref`; a missing lock trusts nothing.
///
/// # Errors
/// [`TrustFromError`] when the ref does not resolve or the lock is malformed.
pub fn load(repo: &Repo, base_ref: &str, lock_path: &str) -> Result<BaseRefTrust, TrustFromError> {
    let Some(bytes) = repo.read_blob_at(base_ref, lock_path)? else {
        info!(
            base_ref,
            lock_path, "no pack lock at base ref; trusting nothing"
        );
        return Ok(BaseRefTrust::empty());
    };
    let text = String::from_utf8(bytes).map_err(|_| TrustFromError::NotUtf8)?;
    Ok(BaseRefTrust::from_lock_toml(&text)?)
}

/// Decides every live pack against `trust`; an untrusted required pack carries its required reason.
#[must_use]
pub fn evaluate(trust: &BaseRefTrust, packs: &[LivePack]) -> Vec<PackTrust> {
    packs
        .iter()
        .map(|p| {
            let verdict = trust.decide(&p.name, &p.tree);
            let required = if verdict.is_trusted() {
                None
            } else {
                RequiredReason::for_pack(p.required, &p.name, PackFailure::UntrustedInChange)
            };
            debug!(pack = %p.name, trusted = verdict.is_trusted(), "base-ref pack decision");
            PackTrust {
                pack: p.name.clone(),
                verdict,
                required,
            }
        })
        .collect()
}

/// True when any pack carries a required Unresolved reason: the gate fails.
#[must_use]
pub fn gate_fails(decisions: &[PackTrust]) -> bool {
    decisions.iter().any(|d| d.required.is_some())
}

#[cfg(test)]
mod tests {
    use super::*;

    const LOCK: &str = r#"
lock_version = 1
digest_scheme = 1

[[pack]]
name = "a"
version = "1"
tree = "blake3:aaa"
[pack.effects]
fs = ["read:src/**"]
"#;

    fn live(tree: &str) -> Vec<LivePack> {
        vec![LivePack {
            name: "a".into(),
            tree: tree.into(),
            required: true,
        }]
    }

    // frob:tests crates/gob-check/src/trust_from.rs::evaluate
    // frob:tests crates/gob-check/src/trust_from.rs::gate_fails
    #[test]
    fn changed_pack_is_untrusted_in_change_and_fails_gate() {
        let trust = BaseRefTrust::from_lock_toml(LOCK).unwrap();
        let d = evaluate(&trust, &live("blake3:bbb"));
        assert_eq!(d[0].verdict, BaseRefVerdict::UntrustedInChange);
        assert_eq!(
            d[0].required.as_ref().map(ToString::to_string).as_deref(),
            Some("untrusted-in-change: a")
        );
        assert!(gate_fails(&d));
    }

    // frob:tests crates/gob-check/src/trust_from.rs::evaluate
    #[test]
    fn unchanged_pack_is_trusted_with_recorded_effects() {
        let trust = BaseRefTrust::from_lock_toml(LOCK).unwrap();
        let d = evaluate(&trust, &live("blake3:aaa"));
        let BaseRefVerdict::Trusted { effects } = &d[0].verdict else {
            panic!("expected trusted");
        };
        assert_eq!(effects["fs"], vec!["read:src/**".to_owned()]);
        assert!(!gate_fails(&d));
    }

    // frob:tests crates/gob-check/src/trust_from.rs::load
    #[test]
    fn load_reads_lock_from_git_objects_not_the_work_tree() {
        let dir = tempfile::tempdir().unwrap();
        let repo = Repo::init(dir.path()).unwrap();
        let path = gob_git::RelPath::new("grimble.packs.lock").unwrap();
        let opts = gob_git::CommitOptions {
            cas_retries: 5,
            author: Some(("Test".into(), "test@example.com".into())),
        };
        repo.commit_paths(
            "refs/heads/main",
            &[(path, Some(LOCK.as_bytes().to_vec()))],
            "base",
            &opts,
        )
        .unwrap();
        // The work tree disagrees with the committed lock.
        std::fs::write(dir.path().join("grimble.packs.lock"), "").unwrap();
        let trust = load(&repo, "refs/heads/main", "grimble.packs.lock").unwrap();
        assert!(trust.decide("a", "blake3:aaa").is_trusted());
        let none = load(&repo, "refs/heads/main", "absent.lock").unwrap();
        assert!(!none.decide("a", "blake3:aaa").is_trusted());
    }
}

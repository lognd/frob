//! `frob release adopt VERSION`: record tags made by hand as a release cut, touching nothing in git.
//!
//! Design: `releases.md` section 4. A release cut by plain `git tag` (and pushed, and
//! published) makes `REL001` report the tag as stray; deleting a published tag is destructive,
//! so adoption instead resolves the tags the configured `[release] tag` pattern and `products`
//! name for the version, checks that each exists and peels to a commit, and returns the
//! [`CutData`] that `frob release cut` would have recorded. The caller appends it (with an
//! `adopt` event, see [`frob_pm::event::AdoptData`]) and moves the milestone to released.
//! Nothing here writes a ref, a commit or the remote.

use std::path::Path;

use frob_pm::event::{CutData, TagRecord};
use gob_git::Repo;

use crate::{ProductTags, ReleaseError};

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
/// Why a version cannot be adopted.
#[derive(Debug, thiserror::Error)]
pub enum AdoptError {
    /// The version is not `MAJOR.MINOR.PATCH[-pre]`.
    #[error("E-ADOPT-VERSION: `{0}` is not a version (MAJOR.MINOR.PATCH[-pre])")]
    InvalidVersion(String),
    /// Some or all of the version's tags do not exist.
    #[error("E-ADOPT-NO-TAG: no tag {}; nothing to adopt for this version", .0.join(", "))]
    MissingTags(Vec<String>),
    /// A tag does not resolve to a commit.
    #[error("E-ADOPT-NOT-COMMIT: tag {tag} does not point at a commit: {why}")]
    NotCommit {
        /// The tag name.
        tag: String,
        /// What git said.
        why: String,
    },
    /// The release configuration could not be resolved.
    #[error("E-ADOPT-CONFIG: {0}")]
    Config(#[from] ReleaseError),
    /// Git could not be read.
    #[error("E-ADOPT-GIT: {0}")]
    Git(#[from] gob_git::GitError),
}

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
impl AdoptError {
    /// True for a refusal the caller can act on (exit 3); false for an internal failure.
    #[must_use]
    pub fn is_refusal(&self) -> bool {
        matches!(
            self,
            Self::InvalidVersion(_)
                | Self::MissingTags(_)
                | Self::NotCommit { .. }
                | Self::Config(_)
        )
    }

    /// The command or step that fixes the refusal.
    #[must_use]
    pub fn remedy(&self, version: &str) -> String {
        match self {
            Self::InvalidVersion(_) => {
                "pass the version without the tag prefix, for example 0.1.0".to_owned()
            }
            Self::MissingTags(_) => format!(
                "create the tags by hand, or run frob release cut {version} for a release that was never tagged; check [release] tag and products in frob.toml"
            ),
            Self::NotCommit { .. } => "re-create the tag on the release commit".to_owned(),
            Self::Config(_) => "fix the [release] table of frob.toml".to_owned(),
            Self::Git(_) => format!("rerun frob release adopt {version}"),
        }
    }
}

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
/// Resolve every tag a release of `version` names under the configured pattern and products into the cut they would have recorded.
///
/// The first tag's commit is the cut's `commit`; each [`TagRecord`] carries its own tag object
/// and commit, so tags hand-made at different commits are recorded as they are.
///
/// # Errors
/// [`AdoptError`] for a bad version, any missing tag (all named), a tag that is not a commit,
/// an unusable configuration, or a git read failure.
pub fn resolve(root: &Path, version: &str) -> Result<CutData, AdoptError> {
    if !crate::valid_version(version) {
        return Err(AdoptError::InvalidVersion(version.to_owned()));
    }
    let products = ProductTags::load(root)?;
    let repo = Repo::discover(root)?;
    let mut tags = Vec::new();
    let mut missing = Vec::new();
    for name in products.tag_names(version) {
        let Some(info) = repo.find_tag(&name)? else {
            missing.push(name);
            continue;
        };
        let commit = info.commit.to_string();
        repo.first_parent_subjects(&commit, 1)
            .map_err(|e| AdoptError::NotCommit {
                tag: name.clone(),
                why: e.to_string(),
            })?;
        tracing::debug!(tag = %name, %commit, annotated = info.annotated, "tag to adopt");
        tags.push(TagRecord {
            name,
            object: info.object.to_string(),
            commit,
        });
    }
    if !missing.is_empty() {
        tracing::warn!(?missing, version, "adopt refused: tags missing");
        return Err(AdoptError::MissingTags(missing));
    }
    let commit = tags.first().map(|t| t.commit.clone()).unwrap_or_default();
    tracing::info!(version, %commit, tags = tags.len(), "tags resolved for adoption");
    Ok(CutData {
        version: version.to_owned(),
        commit,
        tags,
    })
}

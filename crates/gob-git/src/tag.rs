//! Annotated tags and first-parent history, in process through gix (no `git` spawn).

use gix::bstr::ByteSlice;
use gix::refs::transaction::PreviousValue;
use tracing::{debug, info};

use crate::read::odb_err;
use crate::{GitError, Oid, Repo};

/// An existing tag: the ref's own object and the commit it ends at.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TagInfo {
    /// The object the tag ref points at (the tag object when annotated, else the commit).
    pub object: Oid,
    /// The commit the tag resolves to after peeling.
    pub commit: Oid,
    /// True when the ref points at a tag object rather than straight at a commit.
    pub annotated: bool,
}

impl Repo {
    /// Create the annotated tag `refs/tags/<name>` on `commit`; refuses an existing tag.
    ///
    /// The tagger is `author`, else git config `user.name` and `user.email`. Returns the tag object id.
    ///
    /// # Errors
    /// [`GitError::NoIdentity`] without a tagger, [`GitError::Ref`] when the tag exists
    /// or the ref cannot be written, [`GitError::Odb`] when the tag object cannot be written.
    pub fn create_annotated_tag(
        &self,
        name: &str,
        commit: Oid,
        message: &str,
        author: Option<(String, String)>,
    ) -> Result<Oid, GitError> {
        let (n, e) = author
            .or_else(|| self.config_user())
            .ok_or(GitError::NoIdentity)?;
        let sig = gix::actor::Signature {
            name: n.into(),
            email: e.into(),
            time: gix::date::Time::now_utc(),
        };
        let mut buf = gix::date::parse::TimeBuf::default();
        let reference = self
            .gix
            .tag(
                name,
                commit,
                gix::object::Kind::Commit,
                Some(sig.to_ref(&mut buf)),
                message,
                PreviousValue::MustNotExist,
            )
            .map_err(|e| GitError::Ref(format!("tag `{name}`: {e}")))?;
        let id = reference
            .target()
            .try_id()
            .map(gix::oid::to_owned)
            .ok_or_else(|| GitError::Ref(format!("tag `{name}` is not a direct ref")))?;
        info!(tag = name, %commit, object = %id, "annotated tag created");
        Ok(id)
    }

    /// Look up `refs/tags/<name>`; `None` when there is no such tag.
    ///
    /// # Errors
    /// [`GitError::Ref`] when the ref cannot be read or peeled.
    pub fn find_tag(&self, name: &str) -> Result<Option<TagInfo>, GitError> {
        let full = format!("refs/tags/{name}");
        let Some(mut r) = self
            .gix
            .try_find_reference(&full)
            .map_err(|e| GitError::Ref(e.to_string()))?
        else {
            return Ok(None);
        };
        let object = r
            .target()
            .try_id()
            .map(gix::oid::to_owned)
            .ok_or_else(|| GitError::Ref(format!("`{full}` is symbolic")))?;
        let commit = r
            .peel_to_id()
            .map_err(|e| GitError::Ref(e.to_string()))?
            .detach();
        debug!(tag = name, %object, %commit, "tag found");
        Ok(Some(TagInfo {
            object,
            commit,
            annotated: object != commit,
        }))
    }

    /// Up to `limit` commits from `rev` following first parents, newest first, with their subject lines.
    ///
    /// # Errors
    /// [`GitError::Rev`] when `rev` does not resolve, [`GitError::Odb`] on a read failure.
    pub fn first_parent_subjects(
        &self,
        rev: &str,
        limit: usize,
    ) -> Result<Vec<(Oid, String)>, GitError> {
        let tip = self.rev_parse(rev)?;
        let walk = self
            .gix
            .rev_walk([tip])
            .first_parent_only()
            .all()
            .map_err(odb_err)?;
        let mut out = Vec::new();
        for info in walk.take(limit) {
            let info = info.map_err(odb_err)?;
            let commit = self.gix.find_commit(info.id).map_err(odb_err)?;
            let subject = commit
                .message_raw_sloppy()
                .lines()
                .next()
                .unwrap_or_default()
                .to_str_lossy()
                .into_owned();
            out.push((info.id, subject));
        }
        debug!(rev, count = out.len(), "first-parent subjects read");
        Ok(out)
    }
}

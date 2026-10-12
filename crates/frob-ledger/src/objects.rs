//! Generic object access for crates that store other ledger objects beside tickets.
//!
//! Milestones and cycles (`frob-pm`) live under the tickets directory in
//! their own sub-directories (`_milestones/<ULID>/`), event-sourced like
//! tickets (releases.md section 6a). This module is the whole of what such a
//! crate needs from the ledger: read files of the ledger tip and commit
//! files through the same compare-and-swap path every ticket verb uses. It
//! knows nothing about the formats it carries, and ticket reads never see
//! these paths (a ticket is a `<ULID>/ticket.md` directly below the tickets
//! directory).

// frob:ticket 01M4069QWSJEH5KW8K0YR8CA0D
use gob_git::{CommitOptions, Oid, RelPath};

use crate::error::Result;
use crate::ledger::Ledger;

impl Ledger {
    /// The current ledger tip as a hex commit id, or `None` before the first commit.
    ///
    /// # Errors
    ///
    /// [`crate::LedgerError::RefMissing`], detached HEAD in branch mode, or git failures.
    pub fn tip_hex(&self) -> Result<Option<String>> {
        let ref_name = self.ledger_ref()?;
        Ok(self.tip_of(&ref_name)?.map(|t| t.to_string()))
    }

    /// Repo-relative paths of every file below `dir` at commit `tip`, relative to `dir`; empty when absent.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn list_files_below(&self, tip: &str, dir: &str) -> Result<Vec<String>> {
        self.list_files(&format!("{tip}:{dir}"))
    }

    /// The UTF-8 text of `path` at commit `tip`, or `None` when the file does not exist.
    ///
    /// # Errors
    ///
    /// Git read failures or [`crate::LedgerError::Malformed`] for non-UTF-8 content.
    pub fn read_text_at(&self, tip: &str, path: &str) -> Result<Option<String>> {
        self.text(tip, path)
    }

    /// Commit `changes` (`None` deletes) on the ledger ref in one commit with CAS retry.
    ///
    /// Paths are repo-relative and must lie below the tickets directory. This
    /// is the append path for non-ticket objects: callers write event files
    /// and re-folded frontmatter together, exactly as ticket verbs do.
    ///
    /// # Errors
    ///
    /// A path error, or git failures including exhausted compare-and-swap retries.
    pub fn commit_files(
        &self,
        message: &str,
        changes: &[(String, Option<Vec<u8>>)],
    ) -> Result<Oid> {
        let ref_name = self.ledger_write_ref()?;
        let mut rel = Vec::with_capacity(changes.len());
        for (path, bytes) in changes {
            if let Some(b) = bytes {
                self.refuse_private(&String::from_utf8_lossy(b))?;
            }
            rel.push((RelPath::new(path.clone())?, bytes.clone()));
        }
        let opts = CommitOptions {
            cas_retries: self.cfg.cas_retries,
            author: None,
        };
        let out = self.repo.commit_paths(&ref_name, &rel, message, &opts)?;
        tracing::info!(commit = %out.oid, files = changes.len(), retries = out.retries, message, "ledger object commit");
        Ok(out.oid)
    }
}

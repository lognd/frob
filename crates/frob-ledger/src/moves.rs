//! `TICK008`: only a reindex commit may rename or delete a ticket file or touch an existing event file.
// frob:ticket 01M3ZX86W1P62F80ZNR17Q0SQ9

use std::collections::BTreeMap;

use gob_git::Oid;
use gob_rules::{Finding, Severity};

use crate::error::Result;
use crate::layout::Layout;
use crate::ledger::Ledger;
use crate::legacy::{Tick008, id_of};
use crate::reindex::GENERATED_MARKER_PREFIX;
use crate::replay::reindex_trailer;

/// How many of the newest first-parent commits one check inspects.
const SCAN_LIMIT: usize = 100;
/// Trailer key that lets one ledger commit move or edit files outside a reindex; its value is the reason.
const ALLOW_TRAILER: &str = "Frob-Allow-Move:";
/// Subjects of commits that rewrite or relocate ledger files by design.
const EXEMPT_SUBJECTS: &[&str] = &[
    "tickets(scrub)",
    "tickets(migrate)",
    "tickets(init)",
    "tickets(reconcile)",
];

/// Whether a commit message carries a non-empty `Frob-Allow-Move:` trailer.
fn allow_trailer(message: &str) -> bool {
    message
        .lines()
        .rev()
        .find_map(|l| l.strip_prefix(ALLOW_TRAILER))
        .is_some_and(|v| !v.trim().is_empty())
}

/// Paths whose blob differs between two trees (added, removed or changed).
fn changed_paths(before: &BTreeMap<String, Oid>, after: &BTreeMap<String, Oid>) -> Vec<String> {
    before
        .keys()
        .chain(after.keys())
        .filter(|p| before.get(*p) != after.get(*p))
        .cloned()
        .collect::<std::collections::BTreeSet<_>>()
        .into_iter()
        .collect()
}

impl Ledger {
    /// Whether `after` (a commit's tree) restores, on every path it changed, the state before an earlier commit.
    fn reverts_earlier(
        &self,
        before: &BTreeMap<String, Oid>,
        after: &BTreeMap<String, Oid>,
        older: &[gob_git::CommitInfo],
    ) -> Result<bool> {
        let mine = changed_paths(before, after);
        if mine.is_empty() {
            return Ok(false);
        }
        for r in older {
            let [rp] = r.parents.as_slice() else {
                continue;
            };
            let (r_before, r_after) = (self.blob_ids_at(rp)?, self.blob_ids_at(&r.id)?);
            let theirs = changed_paths(&r_before, &r_after);
            if mine
                .iter()
                .all(|p| theirs.contains(p) && after.get(p) == r_before.get(p))
            {
                return Ok(true);
            }
        }
        Ok(false)
    }

    fn blob_ids_at(&self, commit: &Oid) -> Result<BTreeMap<String, Oid>> {
        Ok(self
            .list_blobs(&format!("{commit}^{{tree}}"))?
            .into_iter()
            .collect())
    }

    /// `TICK008` findings for the newest non-reindex commits of the ledger branch; none outside the branch layout.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn move_outside_reindex_findings(&self) -> Result<Vec<Finding>> {
        // frob:ticket 01M3ZX86W1P62F80ZNR17Q0SQ9
        if self.layout() != Layout::Branch {
            return Ok(Vec::new());
        }
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(Vec::new());
        };
        let commits = self
            .repo()
            .first_parent_commits(&tip.to_string(), SCAN_LIMIT)?;
        let mut out = Vec::new();
        for (i, c) in commits.iter().enumerate() {
            let subject = c.message.lines().next().unwrap_or_default();
            // A merge or root commit has no single parent to diff against.
            let [parent] = c.parents.as_slice() else {
                continue;
            };
            if reindex_trailer(&c.message).is_some()
                || allow_trailer(&c.message)
                || EXEMPT_SUBJECTS.iter().any(|s| subject.starts_with(s))
            {
                continue;
            }
            let (before, after) = (self.blob_ids_at(parent)?, self.blob_ids_at(&c.id)?);
            let mut bad: Vec<String> = Vec::new();
            for (path, oid) in &before {
                let kept = after.get(path);
                if path.starts_with(".events/") {
                    if kept != Some(oid) {
                        bad.push(format!("changed event {path}"));
                    }
                } else if kept.is_none()
                    && std::path::Path::new(path)
                        .extension()
                        .is_some_and(|e| e == "md")
                    && !self
                        .repo()
                        .read_blob(oid)?
                        .starts_with(GENERATED_MARKER_PREFIX.as_bytes())
                {
                    bad.push(format!("moved or deleted {path}"));
                }
            }
            if bad.is_empty() {
                continue;
            }
            if self.reverts_earlier(&before, &after, &commits[i + 1..])? {
                tracing::info!(commit = %c.id, "ledger revert of an earlier commit tolerated");
                continue;
            }
            let at = format!("ledger commit {}", c.id.to_hex_with_len(12));
            let msg = format!(
                "{at} (`{subject}`) is not a reindex commit but {} ({} in all); \
                 ticket files move only in a `Frob-Reindex` commit and events are append-only",
                bad[..bad.len().min(3)].join(", "),
                bad.len()
            );
            out.push(Finding::new(
                id_of(&Tick008),
                Severity::Error,
                None,
                msg,
                &at,
            ));
        }
        tracing::info!(findings = out.len(), "move-outside-reindex scan finished");
        Ok(out)
    }
}

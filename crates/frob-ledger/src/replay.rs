//! `TICK007`: replay each recent reindex commit in memory and compare trees.
// frob:ticket 01M3ZX86R5V67MT726K3X7KVWM

use gob_git::CommitInfo;
use gob_rules::{Finding, Severity, UnresolvedReason};

use crate::error::Result;
use crate::layout::Layout;
use crate::ledger::Ledger;
use crate::legacy::{Tick007, id_of};
use crate::reindex::{ReindexOptions, Tree, reindex};

/// How many of the newest reindex commits one check replays.
const REPLAY_LIMIT: usize = 20;
/// How many first-parent commits are scanned for reindex commits.
const SCAN_LIMIT: usize = 500;

/// The `Frob-Reindex` trailer value of a commit message, when it has one.
pub fn reindex_trailer(message: &str) -> Option<&str> {
    message
        .lines()
        .rev()
        .find_map(|l| l.strip_prefix("Frob-Reindex:"))
        .map(str::trim)
}

impl Ledger {
    fn tree_at(&self, commit: &gob_git::Oid) -> Result<Tree> {
        let mut out = Tree::new();
        for (path, oid) in self.list_blobs(&format!("{commit}^{{tree}}"))? {
            out.insert(path, self.repo().read_blob(&oid)?);
        }
        Ok(out)
    }

    /// `TICK007` findings for the newest reindex commits of the ledger branch; none outside the branch layout.
    ///
    /// # Errors
    ///
    /// Git read and reindex failures.
    pub fn reindex_replay_findings(&self) -> Result<Vec<Finding>> {
        // frob:ticket 01M3ZX86R5V67MT726K3X7KVWM
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
        let mut replayed = 0;
        for c in &commits {
            let Some(version) = reindex_trailer(&c.message) else {
                continue;
            };
            if replayed == REPLAY_LIMIT {
                break;
            }
            replayed += 1;
            out.extend(self.replay_one(c, version)?);
        }
        tracing::info!(replayed, findings = out.len(), "reindex replay finished");
        Ok(out)
    }

    fn replay_one(&self, c: &CommitInfo, version: &str) -> Result<Option<Finding>> {
        let short = c.id.to_hex_with_len(12);
        let at = format!("reindex commit {short}");
        let Some(parent) = c.parents.first() else {
            return Ok(None);
        };
        if version != env!("CARGO_PKG_VERSION") {
            let msg = format!(
                "{at}: its trailer names frob {version}, which is not the running {}; the replay was not run",
                env!("CARGO_PKG_VERSION")
            );
            let f = Finding::new(id_of(&Tick007), Severity::Unresolved, None, msg, &at)
                .with_reason(UnresolvedReason::Opaque("generator-version".to_owned()));
            return Ok(Some(f));
        }
        let before = self.tree_at(parent)?;
        let opts = ReindexOptions {
            version: env!("CARGO_PKG_VERSION"),
            handle_min_len: self.config().handle_min_len,
            // frob:ticket 01M3ZX868H7TQ34ZDPXY13NRRG
            generators: crate::r#gen::GENERATORS,
        };
        let want = reindex(&before, &opts)?.tree;
        let got = self.tree_at(&c.tree)?;
        if want == got {
            return Ok(None);
        }
        let mut diff: Vec<&String> = want
            .keys()
            .chain(got.keys())
            .filter(|k| want.get(*k) != got.get(*k))
            .collect();
        // Paths the commit itself carries (a hand edit) come before pages it lacks.
        diff.sort_by_key(|k| (!got.contains_key(*k), *k));
        diff.dedup();
        // frob:ticket 01M3ZX86G8HFRDA78PBVFSTJNW
        let names: Vec<&str> = diff.iter().take(3).map(|s| s.as_str()).collect();
        let msg = format!(
            "{at} is not the pure reindex of its parent: {} path(s) differ (first: {}); \
             a hand edit rode in on a reindex commit, so move it to its own commit",
            diff.len(),
            names.join(", ")
        );
        Ok(Some(Finding::new(
            id_of(&Tick007),
            Severity::Error,
            None,
            msg,
            &at,
        )))
    }
}

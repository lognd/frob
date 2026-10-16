//! The hand-written Markdown files of a ticket-branch ledger (ticket bodies, `EPIC.md`), for `TICK006`.
// frob:ticket 01M4P8M16T2T3Y311ER1Z77KSE

use crate::error::Result;
use crate::layout::Layout;
use crate::ledger::Ledger;
use crate::reindex::GENERATED_MARKER_PREFIX;

impl Ledger {
    /// `(path, text)` of every hand-written Markdown file at the tip of a ticket-branch ledger.
    ///
    /// Generated pages (marker on the first line), `indexes/` and non-UTF-8 files are skipped; event files are
    /// TOML and never listed. Empty for a ledger that is not a ticket branch or has no tip.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn hand_written_texts(&self) -> Result<Vec<(String, String)>> {
        if self.layout() != Layout::Branch {
            return Ok(Vec::new());
        }
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(Vec::new());
        };
        let Some(tree) = self.tickets_tree(Some(tip))? else {
            return Ok(Vec::new());
        };
        let mut out = Vec::new();
        for (rel, oid) in self.list_blobs(&tree.to_string())? {
            let is_md = std::path::Path::new(&rel)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("md"));
            if !is_md || rel.starts_with("indexes/") {
                continue;
            }
            let Ok(text) = self.text_of(&rel, &oid) else {
                tracing::debug!(path = %rel, "ledger file is not UTF-8; not scanned for TICK006");
                continue;
            };
            if text.starts_with(GENERATED_MARKER_PREFIX) {
                continue;
            }
            out.push((rel, text));
        }
        tracing::debug!(files = out.len(), "collected hand-written ledger files");
        Ok(out)
    }
}

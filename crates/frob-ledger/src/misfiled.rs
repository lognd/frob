//! `TICK009`: every ticket file on the branch tip sits at its computed path.
// frob:ticket 01M3ZX86ZX0SCN2FHTDBQF97FD

use gob_rules::{Finding, Severity};

use crate::error::Result;
use crate::layout::Layout;
use crate::ledger::Ledger;
use crate::legacy::{Tick009, id_of};

impl Ledger {
    /// `TICK009` findings, one per ticket file that a reindex would move; none outside the branch layout.
    ///
    /// # Errors
    ///
    /// Git read and reindex failures.
    pub fn misfiled_ticket_findings(&self) -> Result<Vec<Finding>> {
        // frob:ticket 01M3ZX86ZX0SCN2FHTDBQF97FD
        if self.layout() != Layout::Branch {
            return Ok(Vec::new());
        }
        let plan = self.reindex_plan()?;
        let out: Vec<Finding> = plan
            .moves
            .iter()
            .map(|m| {
                let msg = format!(
                    "ticket file {} is not at its computed path {}; run `frob ticket reindex` to move it",
                    m.from, m.to
                );
                Finding::new(id_of(&Tick009), Severity::Error, None, msg, &m.from)
            })
            .collect();
        tracing::info!(findings = out.len(), "misfiled-ticket scan finished");
        Ok(out)
    }
}

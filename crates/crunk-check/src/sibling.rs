//! The `gob.sibling/1` document (sibling-contract 3): what `crunk check --json` prints as `data`.

use std::collections::HashSet;

use gob_check::sibling::{SiblingInput, document, fidelity_reason};
use serde_json::Value;

use crate::{CrunkRun, PRODUCT};

pub use gob_check::sibling::SCHEMA_VERSION;

/// The sibling document of `run` (the `data` of the check envelope).
pub fn sibling_document(run: &CrunkRun) -> Value {
    document(&SiblingInput {
        product: PRODUCT,
        product_version: env!("CARGO_PKG_VERSION"),
        root: &run.root,
        report: &run.report,
        compute: &run.compute,
        ticket_scope: run.ticket_scope.as_deref(),
        base: run.base.as_deref(),
        elapsed_ms: run.elapsed_ms,
        fidelity: Vec::new(),
        not_applicable: &HashSet::new(),
        reason: &fidelity_reason,
        exception_of: &|_| String::new(),
        exceptions: Vec::new(),
        entities: Vec::new(),
        bindings: Vec::new(),
        packs: None,
    })
}

//! crunk as a [`gob_check::Product`]: no rules yet, so the pipeline runs its neutral groups only.

use std::sync::Arc;

use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, NoScope, Product, RepoGroup, Snapshot,
};
use gob_rules::{Finding, Resolved, apply_exceptions};
use gob_text::FileInterner;

use crate::PRODUCT;

/// Thread-safe facts the pipeline reads for applicability and cache keys (none yet).
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkShared;

/// Everything crunk's rules read besides the walk (nothing yet).
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkInputs;

/// The crunk product driving the shared check pipeline.
#[derive(Debug, Clone, Copy, Default)]
pub struct Crunk;

impl Product for Crunk {
    type Shared = CrunkShared;
    type Inputs = CrunkInputs;
    type Scope = NoScope;

    fn name(&self) -> &'static str {
        PRODUCT
    }

    fn collect(&self, _cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        tracing::debug!("crunk collect: no inputs yet");
        Ok(Collected {
            shared: CrunkShared,
            inputs: CrunkInputs,
            findings: Vec::new(),
        })
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        Vec::new()
    }

    fn repo_digest(&self, _snap: &Snapshot<Self>) -> Vec<u8> {
        b"crunk/empty/1".to_vec()
    }

    fn resolve_exceptions(
        &self,
        _snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved {
        let ctx = gob_rules::ExceptionCtx { files };
        let resolved = apply_exceptions(raw, &[], &ctx);
        Resolved {
            findings: resolved.findings,
            suppressed: resolved.suppressed,
        }
    }
}

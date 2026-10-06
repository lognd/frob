//! crunk as a [`gob_check::Product`]: the design spec as input and the rule groups of [`crate::rules`].

use std::sync::Arc;

use gob_check::{
    CheckError, CollectCx, Collected, FileCheck, NoScope, Product, RepoGroup, Snapshot,
};
use gob_rules::{Finding, Resolved, apply_exceptions};
use gob_text::FileInterner;

use crunk_spec::DesignSpec;

use crate::PRODUCT;
use crate::rules::color001;

/// Thread-safe facts the pipeline reads for applicability and cache keys (none yet).
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkShared;

/// Everything crunk's rules read besides the walk: the validated design spec, when `crunk.toml` has one.
#[derive(Debug, Default)]
pub struct CrunkInputs {
    /// `None` when `crunk.toml` is absent or invalid; the spec rules are then not applicable.
    pub spec: Option<DesignSpec>,
}

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

    fn collect(&self, cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        let spec = match crunk_spec::load_spec(&cx.core.root) {
            Ok(spec) => Some(spec),
            Err(err) => {
                tracing::info!(%err, "crunk collect: no usable design spec; spec rules do not apply");
                None
            }
        };
        Ok(Collected {
            shared: CrunkShared,
            inputs: CrunkInputs { spec },
            findings: Vec::new(),
        })
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        Vec::new()
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        vec![color001::group()]
    }

    fn repo_digest(&self, snap: &Snapshot<Self>) -> Vec<u8> {
        let mut digest = b"crunk/rules/1".to_vec();
        if let Some(spec) = &snap.inputs.spec {
            digest.extend(serde_json::to_vec(spec).unwrap_or_default());
        }
        digest
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

//! The F0 adapter: any file no real adapter claims is one `opaque` unit (G19).

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use gob_languages::ParseLimits;

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
};
use crate::fold::opaque_file;
use crate::pipeline::EXTRACTOR_VERSION;

/// The adapter of last resort: locations and whole-artifact digests only.
#[derive(Debug, Clone, Copy, Default)]
pub struct OpaqueAdapter;

impl Adapter for OpaqueAdapter {
    fn language(&self) -> &'static str {
        "opaque"
    }

    fn identity(&self) -> String {
        format!("gob-symbols/v{EXTRACTOR_VERSION}/opaque")
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F0
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
    }

    fn parse(&self, _text: &str, _limits: &ParseLimits) -> ConcreteTree {
        ConcreteTree::Leaf
    }

    fn fold(&self, _tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        let ext = std::path::Path::new(input.path)
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        opaque_file(input, &ext)
    }
}

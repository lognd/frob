//! The live side of the lock rules: every bound-able symbol as it stands now, with its five
//! facet digests and how much of them can be trusted (binding.md 5.3 item 1, 6.7).

// frob:ticket 01M3Z714820D1SK6X44T9R1B70

use std::collections::BTreeMap;

use gob_ir::{Facet, FacetStream};
use gob_lock::FacetSet;
use gob_symbols::Fidelity;

use crate::code::Code;
use crate::types::Reason;

/// The minimum fidelity at which a facet digest counts as Exact (scope graph and normal forms).
pub const MIN_EXACT_FIDELITY: Fidelity = Fidelity::F2;

/// One symbol as it stands now.
#[derive(Clone, Debug)]
pub struct LiveSymbol {
    /// The five facet digests (hex).
    pub facets: FacetSet,
    /// Names of facets whose stream holds a parse hole (no digest can be claimed).
    pub unknown: Vec<String>,
    /// The fidelity the file was folded at.
    pub fidelity: Fidelity,
    /// Repo-relative path of the file.
    pub path: String,
    /// Byte range of the item in its file.
    pub span: (usize, usize),
}

impl LiveSymbol {
    /// Why the facets cannot be treated as Exact, or `None` when they can.
    pub fn inexact(&self) -> Option<Reason> {
        if self.fidelity < MIN_EXACT_FIDELITY {
            Some(Reason::Fidelity)
        } else if !self.unknown.is_empty() {
            Some(Reason::UnseenRemainder)
        } else {
            None
        }
    }
}

/// Every symbol of the walk by symref text.
#[derive(Clone, Debug, Default)]
pub struct Live {
    /// Symbols by symref.
    pub symbols: BTreeMap<String, LiveSymbol>,
    /// Paths of files that could not be read or folded (all of them is an unseen remainder).
    pub unreadable: Vec<String>,
}

impl Live {
    /// Collect the facet digests of every symbol of `code`.
    pub fn build(code: &Code) -> Self {
        let mut out = Self::default();
        for file in &code.files {
            let Some(syms) = file.symbols() else {
                out.unreadable.push(file.path.clone());
                continue;
            };
            for rec in &syms.symbols {
                let unknown = syms
                    .extras
                    .iter()
                    .find(|x| x.symref == rec.symref)
                    .map(|x| x.unknown.clone())
                    .unwrap_or_default();
                let d = &rec.digests;
                out.symbols.insert(
                    rec.symref.to_string(),
                    LiveSymbol {
                        facets: FacetSet {
                            sig: d.sig.to_string(),
                            body: d.body.to_string(),
                            doc: d.doc.to_string(),
                            attr: d.attr.to_string(),
                            contract: d.contract.to_string(),
                        },
                        unknown,
                        fidelity: file.fidelity,
                        path: file.path.clone(),
                        span: (
                            u32::from(rec.span.start()) as usize,
                            u32::from(rec.span.end()) as usize,
                        ),
                    },
                );
            }
        }
        tracing::info!(
            symbols = out.symbols.len(),
            unreadable = out.unreadable.len(),
            "live symbols collected"
        );
        out
    }
}

/// How many atoms the canonical Body stream of `symref` holds; 0 when it has none or is unknown.
///
/// A stand-in for the token count of binding.md 5.4 item 3: the stream is the alpha-normal
/// S-expression print, so its atoms are the tokens that matter.
pub fn body_tokens(code: &Code, path: &str, symref: &str) -> usize {
    let Some(file) = code.file(path) else {
        return 0;
    };
    let Some(folded) = file.folded() else {
        return 0;
    };
    let Some(unit) = file.units().into_iter().find(|u| u.symref == symref) else {
        return 0;
    };
    match folded.term.facet_stream(unit.node, Facet::Body) {
        FacetStream::Stream(s) => s
            .split(|c: char| c.is_whitespace() || c == '(' || c == ')')
            .filter(|t| !t.is_empty())
            .count(),
        FacetStream::Absent | FacetStream::Unknown => 0,
    }
}

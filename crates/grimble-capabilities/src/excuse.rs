//! Matrix-build excuses (packs.md 6.7) and CAP004: an excuse never masks an observed use.
//!
//! An [`Excuse`] is a template `excuse ATOM for SELECTOR because` whose selector the caller has
//! already resolved to the files it covers. [`derive_input`] turns the observed uses, the grants
//! and the excuses of one node into a [`NodeInput`]; [`cap004`] lists the excused atoms that are
//! nevertheless used in covered code.

// frob:ticket 01M59RWT16TFNSACMMTTXX200T

use std::collections::{BTreeMap, BTreeSet};

use crate::{NodeInput, covers};

/// A matrix-build template excuse with its selector resolved to files.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Excuse {
    /// The excused atom.
    pub atom: String,
    /// The files the excuse's `for` selector covers.
    pub files: BTreeSet<String>,
    /// The written reason.
    pub because: String,
}

/// One observed use of an atom at a file, as the matrix sees it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UseSite {
    /// The atom used.
    pub atom: String,
    /// The file of the use.
    pub file: String,
    /// A human-readable site (`file:line callee`) for messages.
    pub site: String,
    /// False for a May use (unresolved receiver or May ownership): never a certain finding.
    pub certain: bool,
}

/// A CAP004 subject: an excused atom used in code the excuse covers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Cap004 {
    /// The node whose code uses the atom.
    pub node: String,
    /// The excused atom.
    pub atom: String,
    /// The excuse's reason.
    pub because: String,
    /// The use sites in covered code.
    pub sites: Vec<String>,
    /// True when every site is a certain use (an Error); false when any is a May use (Unresolved).
    pub certain: bool,
}

/// The excuses covering `atom` used at `file`.
fn covering<'a>(excuses: &'a [Excuse], atom: &str, file: &str) -> impl Iterator<Item = &'a Excuse> {
    let (atom, file) = (atom.to_owned(), file.to_owned());
    excuses
        .iter()
        .filter(move |x| covers(&x.atom, &atom) && x.files.contains(&file))
}

/// Build the matrix input of one node from its observed `sites`, `grants` and `excuses`.
///
/// Every certain use counts as a use; an excuse is recorded for its atom whenever it covers
/// any file of the node, but the cell stays `uses`/`undeclared` where a use exists.
pub fn derive_input(
    node: &str,
    lang: &str,
    grants: &BTreeSet<String>,
    sites: &[UseSite],
    excuses: &[Excuse],
    node_files: &BTreeSet<String>,
) -> NodeInput {
    let uses = sites
        .iter()
        .filter(|s| s.certain)
        .map(|s| s.atom.clone())
        .collect();
    let covered = excuses
        .iter()
        .filter(|x| x.files.iter().any(|f| node_files.contains(f)))
        .map(|x| x.atom.clone())
        .collect();
    tracing::debug!(node, lang, "matrix input derived from observed uses");
    NodeInput {
        node: node.to_owned(),
        lang: lang.to_owned(),
        grants: grants.clone(),
        uses,
        excused: covered,
    }
}

/// CAP004 subjects for `node`: excused atoms whose use is observed in code the excuse covers.
pub fn cap004(node: &str, sites: &[UseSite], excuses: &[Excuse]) -> Vec<Cap004> {
    let mut by_key: BTreeMap<(String, String), Cap004> = BTreeMap::new();
    for s in sites {
        for x in covering(excuses, &s.atom, &s.file) {
            let e = by_key
                .entry((x.atom.clone(), s.atom.clone()))
                .or_insert_with(|| Cap004 {
                    node: node.to_owned(),
                    atom: s.atom.clone(),
                    because: x.because.clone(),
                    sites: Vec::new(),
                    certain: true,
                });
            e.sites.push(s.site.clone());
            e.certain &= s.certain;
        }
    }
    let out: Vec<Cap004> = by_key.into_values().collect();
    tracing::debug!(node, subjects = out.len(), "CAP004 evaluated");
    out
}

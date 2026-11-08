//! The taffy tree of a solve, with text leaves carrying a measure context.

// frob:ticket 01M5XCWYB9M2YSJ5EGABMREX1B

use std::collections::BTreeMap;

use taffy::{NodeId, Style, TaffyTree};

use super::SolveError;
use super::prepare::{Prepared, TextCtx};

/// One output node, in preorder.
#[derive(Debug)]
pub(crate) struct Entry {
    pub id: NodeId,
    pub name: String,
    /// Index of the parent entry.
    pub parent: Option<usize>,
    pub text: Option<TextCtx>,
    pub tokens: BTreeMap<String, String>,
    pub unknown_tag: Option<String>,
}

/// The tree plus its output entries.
pub(crate) struct Built {
    pub tree: TaffyTree<TextCtx>,
    pub entries: Vec<Entry>,
}

fn engine(e: &taffy::TaffyError) -> SolveError {
    SolveError::Engine(e.to_string())
}

/// Build the tree from non-hidden nodes; a text element with children gets a synthetic text child.
pub(crate) fn build(prep: &[Prepared]) -> Result<Built, SolveError> {
    let has_children = |i: usize| prep.iter().any(|p| !p.hidden && p.parent == Some(i));
    let mut tree: TaffyTree<TextCtx> = TaffyTree::new();
    tree.disable_rounding();
    let mut entries: Vec<Entry> = Vec::new();
    let mut slot: BTreeMap<usize, usize> = BTreeMap::new();
    for (i, p) in prep.iter().enumerate().filter(|(_, p)| !p.hidden) {
        let parent = p.parent.and_then(|q| slot.get(&q).copied());
        let leaf_text = p.text.clone().filter(|_| !has_children(i));
        let id = match &leaf_text {
            Some(t) => tree.new_leaf_with_context(p.style.clone(), t.clone()),
            None => tree.new_leaf(p.style.clone()),
        }
        .map_err(|e| engine(&e))?;
        if let Some(pe) = parent {
            tree.add_child(entries[pe].id, id).map_err(|e| engine(&e))?;
        }
        slot.insert(i, entries.len());
        entries.push(entry_of(p, id, parent, leaf_text));
        if let Some(t) = p.text.clone().filter(|_| has_children(i)) {
            add_synthetic(&mut tree, &mut entries, t)?;
        }
    }
    tracing::debug!(entries = entries.len(), "solve tree built");
    Ok(Built { tree, entries })
}

fn entry_of(p: &Prepared, id: NodeId, parent: Option<usize>, text: Option<TextCtx>) -> Entry {
    Entry {
        id,
        name: p.data_id.clone(),
        parent,
        text,
        tokens: p.tokens.clone(),
        unknown_tag: p.unknown_tag.clone(),
    }
}

/// Adds `<owner>::text` as the first child of the last entry.
fn add_synthetic(
    tree: &mut TaffyTree<TextCtx>,
    entries: &mut Vec<Entry>,
    ctx: TextCtx,
) -> Result<(), SolveError> {
    let owner = entries.len() - 1;
    let id = tree
        .new_leaf_with_context(Style::default(), ctx.clone())
        .map_err(|e| engine(&e))?;
    tree.add_child(entries[owner].id, id)
        .map_err(|e| engine(&e))?;
    entries.push(Entry {
        id,
        name: format!("{}::text", entries[owner].name),
        parent: Some(owner),
        text: Some(ctx),
        tokens: BTreeMap::new(),
        unknown_tag: None,
    });
    Ok(())
}

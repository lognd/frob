//! Model-side inputs of the binding relation (grmb-spec 10): `owns` selectors and
//! `grimble:binds` directives. G10 combines them with code terms; this crate only extracts.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use gob_walk::{EntityName, Selector};

use crate::ast::{ClauseKind, EntityKind};
use crate::fold::fold_file;
use crate::model::{Index, LoadedRoot};
use crate::span::Span;

/// An explicit rank-1 binding: `grimble:binds SYMREF` on an entity (grmb-spec 8.2).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct ExplicitBind {
    /// The anchor of the bound item (`node/cli`, or `flow/f/producer[0]` for a flow end).
    pub anchor: String,
    /// The entity part of the anchor (`node/cli`).
    pub entity: String,
    /// The symref text the entity is bound to.
    pub symref: String,
    /// True when written `via="manual"` (the only accepted source).
    pub manual: bool,
    /// The path of the .grmb file.
    pub file: String,
    /// The directive span in that file.
    pub span: Span,
}

/// The `(node full name, selector)` pairs of every `owns` clause of the model, extensions included.
pub fn owner_inputs(root: &LoadedRoot) -> Vec<(EntityName, Selector)> {
    let idx = Index::build(root);
    let mut out = Vec::new();
    for rec in idx.entities.iter().chain(idx.extensions.iter()) {
        if rec.entity.kind != EntityKind::Node {
            continue;
        }
        for c in &rec.entity.clauses {
            if let ClauseKind::Owns(sel) = &c.kind
                && let Ok(s) = &sel.parsed
            {
                out.push((EntityName::from(rec.full.clone()), s.clone()));
            }
        }
    }
    out
}

/// Every `grimble:binds` directive of the model bound to an entity or clause.
pub fn explicit_binds(root: &LoadedRoot) -> Vec<ExplicitBind> {
    let mut out = Vec::new();
    for f in &root.files {
        let Ok(folded) = fold_file(&f.parsed, &f.mount) else {
            continue;
        };
        for d in &folded.directives {
            if d.hit.namespace != "grimble" || d.hit.verb != "binds" {
                continue;
            }
            let mut parts = d.hit.args.split_whitespace();
            let Some(symref) = parts.next() else { continue };
            let manual = parts.any(|p| p == "via=\"manual\"");
            let entity = d
                .anchor
                .splitn(3, '/')
                .take(2)
                .collect::<Vec<_>>()
                .join("/");
            out.push(ExplicitBind {
                anchor: d.anchor.clone(),
                entity,
                symref: symref.to_owned(),
                manual,
                file: f.parsed.path.clone(),
                span: d.hit.span,
            });
        }
    }
    out
}

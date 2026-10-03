//! The model side of binding: entities with their binding clauses, read from `grimble-model`.
//!
//! Clause anchors are `kind/full/role[n]` (`node/cli/owns[0]`), the same spelling the sibling
//! document uses for provenance (binding.md 2.2 item 5).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::collections::BTreeMap;

use gob_walk::Selector;
use grimble_model::ast::{ClauseKind, EntityKind, Evidence, Header};
use grimble_model::binding::{ExplicitBind, explicit_binds};
use grimble_model::model::{Index, LoadedRoot, load_roots};
use grimble_model::{ModelFiles, span::Span};

use crate::types::Role;

/// One binding clause of an entity.
#[derive(Clone, Debug)]
pub struct Clause {
    /// `kind/full/role[n]`.
    pub anchor: String,
    /// The role it contributes.
    pub role: Role,
    /// The .grmb file it is written in.
    pub file: String,
    /// The clause span in that file.
    pub span: Span,
    /// The selector, when the clause carries one that parsed.
    pub selector: Option<Selector>,
    /// The symref text of a `ref "S"` or `evidence ref "S"` clause.
    pub symref: Option<String>,
}

/// A `may` or `excuses` clause: only the atom matters to SYS012.
#[derive(Clone, Debug)]
pub struct AtomClause {
    /// The atom as written (`fs.read`, `pack::net`).
    pub atom: String,
    /// The .grmb file.
    pub file: String,
    /// The clause span.
    pub span: Span,
}

/// An entity of the model (binding.md 1.1, the set E).
#[derive(Clone, Debug)]
pub struct Entity {
    /// `kind/full-name`.
    pub anchor: String,
    /// The kind.
    pub kind: EntityKind,
    /// The .grmb file of the declaration.
    pub file: String,
    /// The whole item span of the declaration.
    pub span: Span,
    /// Binding clauses in declaration then extension order.
    pub clauses: Vec<Clause>,
    /// For a flow: the anchors of the `from` and `to` nodes, when they resolve to nodes.
    pub ends: Option<(Option<String>, Option<String>)>,
    /// True for a node with `kind external` (it owns no code).
    pub external: bool,
    /// The proof rung of a claim, `1` to `5`, when written.
    pub proof: Option<u8>,
    /// True when the claim is `assumed`.
    pub assumed: bool,
    /// True when the entity asked for pack inference (`attr infer`).
    pub infer_requested: bool,
    /// `may` grants.
    pub grants: Vec<AtomClause>,
    /// `excuses` clauses.
    pub excuses: Vec<AtomClause>,
}

impl Entity {
    /// True when some clause is an `owns` clause (the node is expected to own code).
    pub fn owns_code(&self) -> bool {
        self.clauses.iter().any(|c| c.role == Role::Owns)
    }

    /// The clauses of `role`.
    pub fn clauses_of(&self, role: Role) -> impl Iterator<Item = &Clause> {
        self.clauses.iter().filter(move |c| c.role == role)
    }
}

/// Everything binding reads from the model files.
#[derive(Clone, Debug, Default)]
pub struct Model {
    /// Entities by anchor.
    pub entities: BTreeMap<String, Entity>,
    /// `grimble:binds` directives written inside .grmb entities (rank 1, model side).
    pub explicit: Vec<ExplicitBind>,
}

impl Model {
    /// The `(node anchor, selector)` pairs of every `owns` clause, for the owner function.
    pub fn owner_inputs(&self) -> Vec<(gob_walk::EntityName, Selector)> {
        let mut out = Vec::new();
        for e in self
            .entities
            .values()
            .filter(|e| e.kind == EntityKind::Node)
        {
            for c in e.clauses_of(Role::Owns) {
                if let Some(sel) = &c.selector {
                    out.push((gob_walk::EntityName::from(e.anchor.clone()), sel.clone()));
                }
            }
        }
        out
    }
}

const fn role_keyword(role: Role) -> &'static str {
    role.as_str()
}

fn parse_proof(text: &str) -> Option<u8> {
    text.strip_prefix('L')?.parse().ok()
}

fn selector_role(kind: &ClauseKind) -> Option<(Role, &grimble_model::ast::Sel)> {
    match kind {
        ClauseKind::Owns(s) => Some((Role::Owns, s)),
        ClauseKind::Producer(s) => Some((Role::Producer, s)),
        ClauseKind::Consumer(s) => Some((Role::Consumer, s)),
        ClauseKind::Shape(s) => Some((Role::Shape, s)),
        ClauseKind::Runnable(s) => Some((Role::Runnable, s)),
        ClauseKind::Evidence(Evidence::Tests(s)) => Some((Role::Evidence, s)),
        _ => None,
    }
}

/// Add the binding facts of one AST clause to `ent`.
fn add_clause(ent: &mut Entity, file: &str, c: &grimble_model::ast::Clause) {
    let push = |ent: &mut Entity, role: Role, sel: Option<&Selector>, sym: Option<String>| {
        let n = ent.clauses.iter().filter(|x| x.role == role).count();
        ent.clauses.push(Clause {
            anchor: format!("{}/{}[{n}]", ent.anchor, role_keyword(role)),
            role,
            file: file.to_owned(),
            span: c.span,
            selector: sel.cloned(),
            symref: sym,
        });
    };
    if let Some((role, s)) = selector_role(&c.kind) {
        if let Ok(sel) = &s.parsed {
            push(ent, role, Some(sel), None);
        } else {
            tracing::debug!(entity = %ent.anchor, role = role.as_str(), "selector did not parse; clause skipped");
        }
        return;
    }
    match &c.kind {
        ClauseKind::Evidence(Evidence::Ref(s)) => {
            push(ent, Role::Evidence, None, Some(s.value.clone()));
        }
        ClauseKind::Ref(s) => push(ent, Role::Ref, None, Some(s.value.clone())),
        ClauseKind::Kind(k) if k.text == "external" => ent.external = true,
        ClauseKind::Proof(p) => ent.proof = parse_proof(&p.text),
        ClauseKind::Assumed(_) => ent.assumed = true,
        ClauseKind::Attr { key, .. } if key.text == "infer" => ent.infer_requested = true,
        ClauseKind::May(m) => ent.grants.push(AtomClause {
            atom: m.atom.written(),
            file: file.to_owned(),
            span: c.span,
        }),
        ClauseKind::Excuses(x) => ent.excuses.push(AtomClause {
            atom: x.atom.written(),
            file: file.to_owned(),
            span: c.span,
        }),
        _ => {}
    }
}

fn collect(root: &LoadedRoot, out: &mut Model) {
    let idx = Index::build(root);
    let node_anchor = |ctx: &[String], p: &grimble_model::ast::RefPath| -> Option<String> {
        let r = idx.resolve(ctx, p)?;
        (idx.kind(r.rec) == EntityKind::Node).then(|| format!("node/{}", idx.entities[r.rec].full))
    };
    for rec in idx.entities.iter().chain(idx.extensions.iter()) {
        let e = rec.entity;
        let anchor = format!("{}/{}", e.kind.keyword(), rec.full);
        let file = idx.path(rec.file).to_owned();
        let ent = out
            .entities
            .entry(anchor.clone())
            .or_insert_with(|| Entity {
                anchor: anchor.clone(),
                kind: e.kind,
                file: file.clone(),
                span: e.span,
                clauses: Vec::new(),
                ends: None,
                external: false,
                proof: None,
                assumed: false,
                infer_requested: false,
                grants: Vec::new(),
                excuses: Vec::new(),
            });
        if let Header::Flow { from, to } = &e.header {
            ent.ends = Some((node_anchor(&rec.ctx, from), node_anchor(&rec.ctx, to)));
        }
        for c in &e.clauses {
            add_clause(ent, &file, c);
        }
    }
    out.explicit.extend(explicit_binds(root));
}

/// Load every model of `files` and collect its entities and binding clauses.
pub fn load(files: &ModelFiles) -> Model {
    let mut out = Model::default();
    for root in load_roots(files) {
        collect(&root, &mut out);
    }
    tracing::info!(
        entities = out.entities.len(),
        explicit = out.explicit.len(),
        "model loaded for binding"
    );
    out
}

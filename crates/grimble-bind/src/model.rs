//! The model side of binding: entities with their binding clauses, read from `grimble-model`.
//!
//! Clause anchors are `kind/full/role[n]` (`node/cli/owns[0]`), the same spelling the sibling
//! document uses for provenance (binding.md 2.2 item 5).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC
// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067

use std::collections::BTreeMap;

use gob_walk::Selector;
use grimble_model::ast::{ClauseKind, EntityKind, Evidence, Header, Value};
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

/// A `may ATOM [at SEL]` grant of a node (binding.md 7.2: the grants of the capability cell).
#[derive(Clone, Debug)]
pub struct Grant {
    /// The granted atom name without its pack prefix (`fs.read`, or the parent `fs`).
    pub atom: String,
    /// The atom as written, for messages.
    pub written: String,
    /// The `at` selector when it parsed; `None` grants the atom over the whole node.
    pub at: Option<Selector>,
    /// The .grmb file the grant is written in.
    pub file: String,
    /// The clause span in that file.
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
    /// The `may` grants (nodes only carry them).
    pub grants: Vec<Grant>,
    /// The proof rung of a claim, `1` to `5`, when written.
    pub proof: Option<u8>,
    /// True when the claim is `assumed`.
    pub assumed: bool,
    /// True when the entity asked for pack inference (`attr infer`).
    pub infer_requested: bool,
    /// For a flow: the anchor of the contract its `contract` clause names, when it resolves.
    pub contract: Option<String>,
    /// For a contract: the `compat=` value of its `versioning` clause (grmb-spec 4.3).
    pub compat: Option<String>,
}

/// The contract a flow names and what its `versioning` clause allows skew to be.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FlowContract {
    /// The contract anchor, `contract/full-name`.
    pub anchor: String,
    /// The contract's `versioning compat=` value, when written.
    pub compat: Option<String>,
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
    /// Flow anchor to the contract it names; flows without a resolvable `contract` are absent.
    pub fn flow_contracts(&self) -> BTreeMap<String, FlowContract> {
        self.entities
            .values()
            .filter_map(|e| {
                let anchor = e.contract.clone()?;
                let compat = self.entities.get(&anchor).and_then(|c| c.compat.clone());
                Some((e.anchor.clone(), FlowContract { anchor, compat }))
            })
            .collect()
    }

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
        ClauseKind::May(m) => {
            let at = match m.at.as_ref().map(|s| s.parsed.as_ref()) {
                None => None,
                Some(Ok(sel)) => Some(sel.clone()),
                Some(Err(_)) => {
                    tracing::debug!(entity = %ent.anchor, atom = %m.atom.name, "grant selector did not parse; grant skipped");
                    return;
                }
            };
            ent.grants.push(Grant {
                atom: m.atom.name.clone(),
                written: m.atom.written(),
                at,
                file: file.to_owned(),
                span: c.span,
            });
        }
        ClauseKind::Ref(s) => push(ent, Role::Ref, None, Some(s.value.clone())),
        ClauseKind::Kind(k) if k.text == "external" => ent.external = true,
        ClauseKind::Proof(p) => ent.proof = parse_proof(&p.text),
        ClauseKind::Assumed(_) => ent.assumed = true,
        ClauseKind::Attr { key, .. } if key.text == "infer" => ent.infer_requested = true,
        ClauseKind::Versioning(v) => {
            ent.compat = v.attrs.iter().find_map(|kv| match &kv.value.value {
                Value::Ident(i) if kv.key.text == "compat" => Some(i.clone()),
                _ => None,
            });
        }
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
                grants: Vec::new(),
                proof: None,
                assumed: false,
                infer_requested: false,
                contract: None,
                compat: None,
            });
        if let Header::Flow { from, to } = &e.header {
            ent.ends = Some((node_anchor(&rec.ctx, from), node_anchor(&rec.ctx, to)));
        }
        for c in &e.clauses {
            add_clause(ent, &file, c);
            if let ClauseKind::Contract(p) = &c.kind
                && let Some(r) = idx.resolve(&rec.ctx, p)
                && idx.kind(r.rec) == EntityKind::Contract
            {
                ent.contract = Some(format!("contract/{}", idx.entities[r.rec].full));
            }
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

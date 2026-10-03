//! The binding relation B and the SYS binding rules (design: `binding.md`, ticket G11).
//!
//! B is `(entity, role, identity, status, source, provenance)`, built from four ranked sources:
//!
//! | Rank | Source | Module |
//! |---|---|---|
//! | 1 | `grimble:binds` directives, in code and inside `.grmb` entities | [`directives`], [`relation`] |
//! | 2 | model selector clauses (`owns`, `producer`, `consumer`, `shape`, `runnable`, `evidence`, `ref`) | [`relation`] |
//! | 3 | pack inference | a stub: packs do not load yet (G04); an `attr infer` request is `inference-unavailable` |
//! | 4 | nothing: the hidden remainder, as rows with status `unknown` | [`relation`] |
//!
//! [`owner`] merges the ranks into the owner function of binding.md 2.6 and [`rules`] evaluates
//! `SYS001`-`SYS005` and `SYS009`-`SYS011` ([`rule_defs`]). [`bind`] runs the whole pipeline.
//!
//! # Known limits, each a decision-log proposal
//!
//! - A directive's row is Must even when its target unit sits behind a May edge
//!   (`rank1/through-phase` of binding.md 10 is not implemented).
//! - Oversized files never reach this crate (the check core drops them), so they are not an
//!   unseen remainder; unreadable files are.
//! - `SYS005` does not consult effects (no `effects` query exists) and `SYS010`/`SYS011`
//!   recognise tests by path and qualified name (no `test_items` query exists).
//! - `SYS001`, `SYS002` roll up per directory and per file.
//! - `SYS012` is not here: it moved to the capability-matrix ticket (G14) by owner decision.
//! - The `grimble:node`, `grimble:channel` and `grimble:boundary` sugar spellings are not
//!   registered; only `grimble:binds` is.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

pub mod ack;
pub mod code;
pub mod directives;
pub mod drift;
pub mod live;
pub mod model;
pub mod owner;
pub mod relation;
pub mod rule_defs;
pub mod rules;
pub mod types;

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_walk::{FileEntry, Selector};
use grimble_model::ModelFiles;
use serde_json::Value;

pub use rule_defs::{
    Sys001, Sys002, Sys003, Sys004, Sys005, Sys006, Sys007, Sys008, Sys009, Sys010, Sys011,
};
pub use types::{BindFinding, REASON_PREFIX, Reason, Role, Row, Source, Status, reason_of_message};

/// The rule ids this crate evaluates.
pub const RULES: [&str; 11] = [
    "SYS001", "SYS002", "SYS003", "SYS004", "SYS005", "SYS006", "SYS007", "SYS008", "SYS009",
    "SYS010", "SYS011",
];

/// The product name: the lock is `grimble.lock`.
pub const PRODUCT: &str = "grimble";

/// What binding reads.
pub struct BindInput<'a> {
    /// Repository root.
    pub root: &'a Path,
    /// The walked files.
    pub entries: &'a [FileEntry],
    /// The `.grmb` files.
    pub model: &'a ModelFiles,
    /// `[grimble] modeled`: selectors whose public units must have an owner (SYS005).
    pub modeled: &'a [String],
    /// `[grimble] strict`.
    pub strict: bool,
    /// `[grimble] rename_min_tokens`: smaller Bodies are never paired as a rename.
    pub rename_min_tokens: usize,
}

/// B, its findings and the subject counts.
#[derive(Debug, Default)]
pub struct Binding {
    /// Rows of B.
    pub rows: Vec<Row>,
    /// Findings of the SYS rules.
    pub findings: Vec<BindFinding>,
    /// Subjects examined per rule; empty when the model has no entity.
    pub subjects: BTreeMap<&'static str, usize>,
    /// Ownership per identity.
    pub owners: owner::Owners,
    /// The relation C (code-to-code `binds`).
    pub edges: Vec<relation::CEdge>,
    /// Every symbol of the walk with its facet digests (what an ack records).
    pub live: live::Live,
    /// For each flow anchor, the contract it names (`contract` clause) and that contract's compat.
    pub flow_contracts: BTreeMap<String, model::FlowContract>,
}

impl Binding {
    /// The rows as the sibling document's `bindings` array.
    pub fn bindings_json(&self) -> Vec<Value> {
        self.rows.iter().map(Row::to_json).collect()
    }
}

fn expand_files(
    rel: &relation::Relation,
    modeled: &[Selector],
    code: &code::Code,
) -> BTreeSet<String> {
    let mut out: BTreeSet<String> = rel
        .dir_owns
        .keys()
        .map(|s| rules::path_of(s).to_owned())
        .collect();
    for r in &rel.rows {
        if matches!(r.role, Role::Producer | Role::Consumer)
            && let Some(id) = &r.identity
        {
            out.insert(rules::path_of(id).to_owned());
        }
    }
    for s in modeled {
        out.extend(
            gob_walk::select_files(s, &code.walk)
                .into_iter()
                .map(|m| m.path),
        );
    }
    out
}

/// Build B and evaluate the SYS rules for one snapshot.
///
/// Returns an empty [`Binding`] when the model declares no entity: with nothing to bind there
/// is no subject, and every file reading as unowned would be noise.
pub fn bind(input: &BindInput<'_>) -> Binding {
    let model = model::load(input.model);
    if model.entities.is_empty() {
        tracing::info!("no model entities; binding skipped");
        return Binding::default();
    }
    let code = code::Code::build(input.root, input.entries);
    let directives = directives::scan(&code);
    let mut rel = relation::build(&model, &code, &directives);
    let modeled: Vec<Selector> = input
        .modeled
        .iter()
        .filter_map(|t| match Selector::parse(t) {
            Ok(s) => Some(s),
            Err(err) => {
                tracing::warn!(selector = %t, ?err, "modeled selector does not parse; ignored");
                None
            }
        })
        .collect();
    let expand = expand_files(&rel, &modeled, &code);
    let owners = owner::build(&model.owner_inputs(), &code, &rel, &expand);
    for r in &mut rel.rows {
        if r.role == Role::Owns
            && let Some(uo) = r.identity.as_ref().and_then(|i| owners.units.get(i))
            && let gob_walk::Owner::Must(n) = &uo.merged.owner
        {
            r.overridden = n.as_str() != r.entity;
        }
    }
    let cx = rules::Cx {
        model: &model,
        code: &code,
        rel: &rel,
        owners: &owners,
        modeled: &modeled,
        strict: input.strict,
    };
    let mut out = rules::evaluate(&cx);
    let live = live::Live::build(&code);
    let flow_contracts = model.flow_contracts();
    let lock_path = input.root.join(gob_lock::file_name(PRODUCT));
    match gob_lock::LockFile::load(&lock_path) {
        Ok(lock) => drift::evaluate(
            &drift::DriftCx {
                code: &code,
                live: &live,
                rows: &rel.rows,
                lock: &lock,
                contracts: &flow_contracts,
                rename_min_tokens: input.rename_min_tokens,
            },
            &mut out,
        ),
        Err(err) => {
            tracing::error!(%err, "grimble.lock is unreadable; SYS006 to SYS008 cannot run");
            out.unresolved(
                "SYS007",
                Reason::LockUnreadable,
                &format!("grimble.lock cannot be read: {err}"),
                drift::LOCK_ANCHOR,
                Some((drift::LOCK_ANCHOR, (0, 0))),
            );
        }
    }
    Binding {
        rows: rel.rows,
        findings: out.findings,
        subjects: out.subjects,
        owners,
        edges: rel.edges,
        live,
        flow_contracts,
    }
}

//! COH002 "decision with effects" (cohesion.md 1): a unit that branches on computed data and
//! performs effects inside those branches mixes the functional core with the imperative shell.
//! A unit with a declared role is judged against it: a verified `grimble:shell` may mix, a
//! `grimble:core` or role-less unit may not.
//!
//! A decision is an `if`/`elif`/`match`-style branch whose condition is computed: it contains a
//! call, or reads a variable the body itself defined (a def-use edge whose definition is not the
//! unit's parameter list). A guard on a bare parameter is a dispatch guard (NEAT031), not a
//! decision. An effect is a call in a branch body whose callee is in the effect vocabulary;
//! trivial calls (logging) are not effects. P+: the rule fires only on a proven effect. A branch
//! whose bodies call something outside both vocabularies leaves the verdict Unresolved with
//! those callees named, never a silent pass. Nested functions and lambdas are other units.

// frob:ticket 01M4CXSRE3YHY7FV30R8GMB58A

use std::collections::BTreeSet;

use gob_ir::{DefUseEdge, NodeId, Operator, Term, Universal};
use gob_symbols::{Folded, def_use_of, syntax_for};
use tracing::{debug, trace};

use crate::coh001::{CohOptions, is_within, statements};

/// Knobs of COH002 (the `[coh]` table of cohesion.md, defaults here until the table lands).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Coh002Options {
    /// Callee names (last path segment) that perform an effect: IO, messaging, persistence.
    pub effect_calls: Vec<String>,
    /// Callee names that are trivial (logging, metrics, asserts); never an effect.
    pub trivial: Vec<String>,
}

impl Default for Coh002Options {
    fn default() -> Self {
        Self {
            effect_calls: [
                "write",
                "write_all",
                "writeln",
                "send",
                "send_all",
                "sendall",
                "emit",
                "publish",
                "dispatch",
                "save",
                "persist",
                "commit",
                "execute",
                "delete",
                "remove",
                "unlink",
                "remove_file",
                "mkdir",
                "create_dir",
                "rename",
                "open",
                "fetch",
                "post",
                "put",
                "request",
                "sleep",
                "spawn",
                "exit",
                "flush",
            ]
            .map(str::to_owned)
            .to_vec(),
            trivial: CohOptions::default().trivial,
        }
    }
}

/// The role a unit declares for itself (`grimble:shell`, `grimble:core`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnitRole {
    /// No role claim: judged as written.
    None,
    /// `grimble:core`: no effects at all, so a decision with effects contradicts the claim.
    Core,
    /// `grimble:shell`: may mix; `verified` is the verdict of the effects rules on the claim.
    Shell {
        /// True when the effects rules verified the claim (VERIFIED), false for any other outcome.
        verified: bool,
    },
}

/// One effect call performed inside a decision's branches.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EffectCall {
    /// The call node.
    pub call: NodeId,
    /// The callee's last path segment.
    pub callee: String,
}

/// One computed decision that performs effects.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MixedDecision {
    /// The branch node (`if`, `elif`, ...).
    pub decision: NodeId,
    /// The effect calls in its branches, in source order.
    pub effects: Vec<EffectCall>,
}

/// Why a verdict is Unresolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coh002Unresolved {
    /// The decisions mix, but the `grimble:shell` claim that would excuse them is not verified.
    UnverifiedShell {
        /// The mixed decisions the shell claim would excuse.
        decisions: Vec<MixedDecision>,
    },
    /// No effect is proven, but branches call things with an unknown effect.
    UnknownCallees {
        /// The sorted callee names whose effect is unknown.
        callees: Vec<String>,
    },
}

/// COH002's judgement of one unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Coh002 {
    /// A computed decision performs effects and the unit is not a verified shell.
    Fire {
        /// The role the unit declared.
        role: UnitRole,
        /// Every mixed decision.
        decisions: Vec<MixedDecision>,
    },
    /// No mixing proven, or a verified shell.
    Clean,
    /// Neither proven nor excluded.
    Unresolved(Coh002Unresolved),
}

fn ident_of(term: &Term, n: NodeId) -> Option<&str> {
    match term.node(n).op() {
        Operator::Universal(Universal::Ref { name }) => Some(name),
        Operator::Universal(Universal::Lit { kind, lexeme })
            if kind == "identifier" || is_word(lexeme) =>
        {
            Some(lexeme)
        }
        _ => None,
    }
}

fn is_word(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_alphanumeric() || c == '_')
}

/// The last identifier of a call head (`a.b.send` gives `send`, `fs::write` gives `write`).
fn callee_of(term: &Term, call: NodeId) -> Option<String> {
    fn last(term: &Term, n: NodeId) -> Option<String> {
        term.node(n)
            .children()
            .iter()
            .rev()
            .find_map(|&c| last(term, c))
            .or_else(|| {
                ident_of(term, n)
                    .map(|s| s.trim_start_matches('.').trim_end_matches('!').to_owned())
            })
    }
    last(term, *term.node(call).children().first()?)
}

fn is_call(term: &Term, n: NodeId) -> bool {
    matches!(term.node(n).op(), Operator::Universal(Universal::Apply { kind }) if kind == "call" || kind == "method")
}

fn is_nested_unit(term: &Term, n: NodeId) -> bool {
    matches!(
        term.node(n).op(),
        Operator::Universal(Universal::Unit { .. } | Universal::Anon { .. })
    )
}

fn is_punct(term: &Term, n: NodeId) -> bool {
    matches!(
        term.node(n).op(),
        Operator::Universal(Universal::Lit { .. })
    )
}

/// A decision: its condition node and its branch-body nodes.
struct Decision {
    node: NodeId,
    condition: NodeId,
    bodies: Vec<NodeId>,
}

fn decision_of(term: &Term, n: NodeId, syntax: &gob_ir::DefUseSyntax) -> Option<Decision> {
    match term.node(n).op() {
        Operator::Universal(Universal::Bind { kind, .. }) if kind == "if-let" => {
            let [body, scrutinee, ..] = term.node(n).children() else {
                return None;
            };
            Some(Decision {
                node: n,
                condition: *scrutinee,
                bodies: vec![*body],
            })
        }
        Operator::Adapter(a)
            if (syntax.branches.contains(&a.name.as_str()) && a.name != "try_statement")
                || a.name.starts_with("elif") =>
        {
            let mut parts = term
                .node(n)
                .children()
                .iter()
                .copied()
                .filter(|&c| !is_punct(term, c));
            let condition = parts.next()?;
            let blocklike = matches!(term.node(condition).op(), Operator::Adapter(c)
                if syntax.alternatives.contains(&c.name.as_str()) || c.name.ends_with("block"));
            (!blocklike).then(|| Decision {
                node: n,
                condition,
                bodies: parts.collect(),
            })
        }
        _ => None,
    }
}

fn collect_decisions(
    term: &Term,
    n: NodeId,
    syntax: &gob_ir::DefUseSyntax,
    out: &mut Vec<Decision>,
) {
    for &c in term.node(n).children() {
        if is_nested_unit(term, c) {
            continue;
        }
        if let Some(d) = decision_of(term, c, syntax) {
            out.push(d);
        }
        collect_decisions(term, c, syntax, out);
    }
}

fn has_call(term: &Term, n: NodeId) -> bool {
    is_call(term, n)
        || term
            .node(n)
            .children()
            .iter()
            .any(|&c| !is_nested_unit(term, c) && has_call(term, c))
}

/// True when the condition depends on computed data: a call, or a local the body defined.
fn is_computed(term: &Term, unit: NodeId, cond: NodeId, edges: &[DefUseEdge]) -> bool {
    has_call(term, cond)
        || edges
            .iter()
            .any(|e| e.def != unit && (e.use_site == cond || is_within(term, e.use_site, cond)))
}

fn calls_in(term: &Term, n: NodeId, out: &mut Vec<(NodeId, String)>) {
    for &c in term.node(n).children() {
        if is_nested_unit(term, c) {
            continue;
        }
        if is_call(term, c)
            && let Some(name) = callee_of(term, c)
        {
            out.push((c, name));
        }
        calls_in(term, c, out);
    }
}

/// Judge `unit` of `folded` (language tag `lang`); `None` when def-use does not support the language.
pub fn coh002(
    folded: &Folded,
    lang: &str,
    unit: NodeId,
    role: UnitRole,
    opts: &Coh002Options,
) -> Option<Coh002> {
    let edges = def_use_of(folded, lang, unit)?;
    Some(judge(&folded.term, lang, unit, &edges, role, opts))
}

/// Judge a unit from precomputed def-use edges (the pure core of [`coh002`]).
pub fn judge(
    term: &Term,
    lang: &str,
    unit: NodeId,
    edges: &[DefUseEdge],
    role: UnitRole,
    opts: &Coh002Options,
) -> Coh002 {
    let Some(syntax) = syntax_for(lang) else {
        return Coh002::Clean;
    };
    let mut found = Vec::new();
    for stmt in statements(term, unit) {
        if let Some(d) = decision_of(term, stmt, syntax) {
            found.push(d);
        }
        collect_decisions(term, stmt, syntax, &mut found);
    }
    let mut mixed = Vec::new();
    let mut unknown = BTreeSet::new();
    for d in found
        .iter()
        .filter(|d| is_computed(term, unit, d.condition, edges))
    {
        let mut calls = Vec::new();
        for &b in &d.bodies {
            if is_call(term, b)
                && let Some(name) = callee_of(term, b)
            {
                calls.push((b, name));
            }
            calls_in(term, b, &mut calls);
        }
        calls.sort();
        let mut effects = Vec::new();
        for (call, callee) in calls {
            if opts.trivial.contains(&callee) {
                continue;
            }
            if opts.effect_calls.contains(&callee) {
                effects.push(EffectCall { call, callee });
            } else {
                unknown.insert(callee);
            }
        }
        trace!(decision = ?d.node, effects = effects.len(), "coh002 decision");
        if !effects.is_empty() {
            mixed.push(MixedDecision {
                decision: d.node,
                effects,
            });
        }
    }
    debug!(unit = ?unit, mixed = mixed.len(), unknown = unknown.len(), ?role, "coh002 judged");
    match (role, mixed.is_empty()) {
        (UnitRole::Shell { verified: true }, _) => Coh002::Clean,
        (UnitRole::Shell { verified: false }, false) => {
            Coh002::Unresolved(Coh002Unresolved::UnverifiedShell { decisions: mixed })
        }
        (_, false) => Coh002::Fire {
            role,
            decisions: mixed,
        },
        (_, true) if !unknown.is_empty() => Coh002::Unresolved(Coh002Unresolved::UnknownCallees {
            callees: unknown.into_iter().collect(),
        }),
        (_, true) => Coh002::Clean,
    }
}

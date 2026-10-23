//! COH002 "decision with effects" (cohesion.md 1): a unit that branches on computed data and
//! performs effects inside those branches mixes the functional core with the imperative shell.
//! A unit with a declared role is judged against it: a verified `grimble:shell` may mix, a
//! `grimble:core` or role-less unit may not.
//!
//! A decision is an `if`/`elif`/`match`-style branch whose condition is computed: it contains a
//! call, or reads a variable the body itself defined (a def-use edge whose definition is not the
//! unit's parameter list). A guard on a bare parameter is a dispatch guard (NEAT031), not a
//! decision. An effect is a call in a branch body that the language's effects capability
//! ([`crate::effects`]) classifies as an effect from its qualified path; trivial calls (logging)
//! are not effects. The `[coh]` lists only add project overrides on top of the capability.
//! P+: the rule fires only on a proven effect. A branch whose bodies call something the capability
//! cannot place leaves the verdict Unresolved with those callees named, never a silent pass; a
//! language without an effects capability is Unresolved whenever a decision has calls to classify.
//! Nested functions and lambdas are other units.

// frob:ticket 01M4CXSRE3YHY7FV30R8GMB58A
// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C
// frob:ticket 01M5HJ07B6E0NZ47RCV0HWZR5Y

use std::collections::BTreeSet;

use gob_ir::{DefUseEdge, GroupOrder, NodeId, Operator, Term, Universal};
use gob_symbols::{Folded, def_use_of, syntax_for};
use tracing::{debug, trace};

use crate::coh001::{is_within, statements};
use crate::config::CohTable;
use crate::effects::{EffectClass, EffectsCapability, effects_for};

/// The built-in `[coh] effect_calls` default: empty, the adapter capability supplies the effects.
pub fn default_effect_calls() -> Vec<String> {
    Vec::new()
}

/// The built-in `[coh] trivial` default: empty, the adapter capability supplies the trivial calls.
pub fn default_trivial() -> Vec<String> {
    Vec::new()
}

/// Knobs of COH002: project overrides added on top of the language effects capability.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Coh002Options {
    /// Extra callee names (last path segment, any language) that perform an effect.
    pub effect_calls: Vec<String>,
    /// Extra callee names that are trivial (logging, metrics, asserts); trivial wins over effect.
    pub trivial: Vec<String>,
}

impl Default for Coh002Options {
    fn default() -> Self {
        Self {
            effect_calls: default_effect_calls(),
            trivial: default_trivial(),
        }
    }
}

impl From<&CohTable> for Coh002Options {
    /// The overrides of a loaded `[coh]` table; they add to the capability's classification.
    fn from(table: &CohTable) -> Self {
        debug!(
            effect_calls = table.effect_calls.len(),
            trivial = table.trivial.len(),
            "COH002 options from the [coh] table"
        );
        Self {
            effect_calls: table.effect_calls.clone(),
            trivial: table.trivial.clone(),
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
    /// The language has no effects capability, so its calls cannot be classified.
    NoEffectsCapability {
        /// The language tag lacking the capability.
        lang: String,
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
pub(crate) fn callee_of(term: &Term, call: NodeId) -> Option<String> {
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

/// The path segments of a name (`os.path.remove` and `fs::write` split on `.` and `::`).
fn segments(name: &str) -> impl Iterator<Item = String> + '_ {
    name.trim_end_matches('!')
        .split(['.', ':'])
        .filter(|s| !s.is_empty())
        .map(str::to_owned)
}

/// The head identifiers of a call in order, qualifiers first (`a.b.send` gives `[a, b, send]`).
///
/// A method call's receiver supplies the qualifiers; a call nested in the receiver contributes its
/// own head only (`foo(x).send(y)` gives `[foo, send]`). A head of any other shape falls back to
/// its last identifier.
pub(crate) fn callee_path(term: &Term, call: NodeId) -> Vec<String> {
    let kids = term.node(call).children();
    let Some(&head) = kids.first() else {
        return Vec::new();
    };
    let Some(name) = ident_of(term, head) else {
        return callee_of(term, call).into_iter().collect();
    };
    let mut path = Vec::new();
    if matches!(term.node(call).op(), Operator::Universal(Universal::Apply { kind }) if kind == "method")
        && let Some(&recv) = kids.get(1)
    {
        if is_call(term, recv) {
            path = callee_path(term, recv);
        } else if let Some(r) = ident_of(term, recv) {
            path = segments(r).collect();
        }
    }
    path.extend(segments(name));
    path
}

pub(crate) fn is_call(term: &Term, n: NodeId) -> bool {
    matches!(term.node(n).op(), Operator::Universal(Universal::Apply { kind }) if kind == "call" || kind == "method")
}

pub(crate) fn is_nested_unit(term: &Term, n: NodeId) -> bool {
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

/// True when `n` is a sequence group.
fn is_sequence(term: &Term, n: NodeId) -> bool {
    matches!(
        term.node(n).op(),
        Operator::Universal(Universal::Group {
            order: GroupOrder::Sequence
        })
    )
}

/// True when `n` is a Rust match arm: a `pattern` bind.
fn is_arm(term: &Term, n: NodeId) -> bool {
    matches!(term.node(n).op(), Operator::Universal(Universal::Bind { kind, .. }) if kind == "pattern")
}

/// A Rust `match`: the adapter folds it to a sequence of the scrutinee and a sequence of arm binds.
fn match_of(term: &Term, n: NodeId) -> Option<Decision> {
    if !is_sequence(term, n) {
        return None;
    }
    let [scrutinee, arms] = term.node(n).children() else {
        return None;
    };
    let arm_list = term.node(*arms).children();
    (is_sequence(term, *arms) && !arm_list.is_empty() && arm_list.iter().all(|&a| is_arm(term, a)))
        .then(|| Decision {
            node: n,
            condition: *scrutinee,
            bodies: vec![*arms],
        })
}

fn decision_of(term: &Term, n: NodeId, syntax: &gob_ir::DefUseSyntax) -> Option<Decision> {
    if let Some(m) = match_of(term, n) {
        return Some(m);
    }
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

fn calls_in(term: &Term, n: NodeId, out: &mut Vec<(NodeId, Vec<String>)>) {
    for &c in term.node(n).children() {
        if is_nested_unit(term, c) {
            continue;
        }
        if is_call(term, c) {
            out.push((c, callee_path(term, c)));
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
    let effects = effects_for(lang);
    Some(judge(&folded.term, lang, unit, &edges, role, effects, opts))
}

/// Judge a unit from precomputed def-use edges (the pure core of [`coh002`]).
pub fn judge(
    term: &Term,
    lang: &str,
    unit: NodeId,
    edges: &[DefUseEdge],
    role: UnitRole,
    effects: Option<&EffectsCapability>,
    opts: &Coh002Options,
) -> Coh002 {
    let Some(syntax) = syntax_for(lang) else {
        return Coh002::Unresolved(Coh002Unresolved::NoEffectsCapability {
            lang: lang.to_owned(),
        });
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
    let mut no_capability = false;
    for d in found
        .iter()
        .filter(|d| is_computed(term, unit, d.condition, edges))
    {
        let mut calls = Vec::new();
        for &b in &d.bodies {
            if is_call(term, b) {
                calls.push((b, callee_path(term, b)));
            }
            calls_in(term, b, &mut calls);
        }
        calls.sort();
        let mut effect_calls = Vec::new();
        for (call, path) in calls {
            let Some(callee) = path.last().cloned() else {
                continue;
            };
            if opts.trivial.contains(&callee) {
                continue;
            }
            let class = if opts.effect_calls.contains(&callee) {
                EffectClass::Effect
            } else if let Some(cap) = effects {
                cap.classify(&path)
            } else {
                no_capability = true;
                continue;
            };
            match class {
                EffectClass::Trivial => {}
                EffectClass::Effect => effect_calls.push(EffectCall { call, callee }),
                EffectClass::Unknown => {
                    unknown.insert(callee);
                }
            }
        }
        trace!(decision = ?d.node, effects = effect_calls.len(), "coh002 decision");
        if !effect_calls.is_empty() {
            mixed.push(MixedDecision {
                decision: d.node,
                effects: effect_calls,
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
        (_, true) if no_capability => Coh002::Unresolved(Coh002Unresolved::NoEffectsCapability {
            lang: lang.to_owned(),
        }),
        (_, true) if !unknown.is_empty() => Coh002::Unresolved(Coh002Unresolved::UnknownCallees {
            callees: unknown.into_iter().collect(),
        }),
        (_, true) => Coh002::Clean,
    }
}

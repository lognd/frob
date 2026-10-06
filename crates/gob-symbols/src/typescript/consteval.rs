//! Bounded constant evaluation of TypeScript expressions across files (D96, language-engines.md section 2,
//! `const_value`).
//!
//! The evaluator itself is `gob_ir::const_value` (one evaluator for every language); this module only
//! supplies what a single term cannot know. The folder lowers literals, template literals, `+`, `&&`, `||`,
//! `?:`, array and object literals, spreads and call arguments to the `const_value` forms (`fold/jsx.rs`);
//! [`ConstProject`] holds the folded files of a repository and plugs into the evaluator as its
//! [`ExternalRefs`] hook:
//!
//! - a name the scope graph cannot resolve but that is an import binding goes through the module graph
//!   ([`SymbolGraph::ts_import_targets`]); only a Must answer naming one `const` unit is followed, in the
//!   target file's own term, with the remaining step budget (a re-export chain is part of that answer);
//! - a call is a class-name joiner when its callee is imported from `clsx` or `classnames`, or is a function
//!   of the repository (this file or an import) whose body calls such a joiner (the `cn` wrapper). The
//!   arguments are joined as `clsx` does; a wrapper that also merges conflicting utilities (`twMerge`) is
//!   read as the plain join, so its result is a superset of the tokens that survive the merge.
//!
//! Everything else (unresolved names, member access, other calls, over-budget chains) stays `Unknown`, and
//! [`Evaluated::unresolved`] says why. Unresolved is a value state, never an error.

// frob:ticket 01M43ARXVD5PXP6ZBVFC2F4ZMQ

use std::cell::RefCell;
use std::collections::BTreeMap;

use gob_ir::const_value::{
    Budget, CallKind, ConstEval, ConstValue, External, ExternalRefs, const_value_node,
};
use gob_ir::{Location, Model, NodeId, Operator, Status, Universal};
use tracing::{debug, trace};

use crate::adapter::Folded;
use crate::graph::SymbolGraph;

/// Packages whose default or named export joins class names.
const CLASS_JOINERS: [&str; 3] = ["clsx", "clsx/lite", "classnames"];

/// Why an evaluation is not fully known.
#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
pub enum Unresolved {
    /// A constant (transitively) depends on itself.
    #[error("reference cycle between constants")]
    Cycle,
    /// The step budget ran out before the value was known.
    #[error("step budget exhausted")]
    Budget,
    /// Part of the expression is not statically known (a parameter, a call, an unresolved name).
    #[error("not statically known")]
    Dynamic,
}

/// Where a constant that contributed to a value is declared.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Origin {
    /// Repo-relative path of the file holding the constant's value expression.
    pub path: String,
    /// Start byte of the value expression.
    pub start: u32,
    /// End byte of the value expression (exclusive).
    pub end: u32,
}

/// The answer of an evaluation: the value, the constants it was read from, and why it is not fully known.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Evaluated {
    /// The bounded value.
    pub value: ConstValue,
    /// The value expressions of every constant consulted, in the order they were reached.
    pub origins: Vec<Origin>,
    /// Why the value is not `Known` or `OneOf`; `None` when it is.
    pub unresolved: Option<Unresolved>,
}

/// State shared by the hooks of one evaluation (they nest across files).
#[derive(Debug, Default)]
struct Shared {
    /// Symrefs of the constants being evaluated, outermost first (cycle guard across files).
    stack: Vec<String>,
    /// Origins recorded in files other than the one evaluated.
    origins: Vec<Origin>,
}

/// The folded files of a repository and the module graph over them, ready to evaluate expressions.
#[derive(Debug)]
pub struct ConstProject<'g> {
    graph: &'g SymbolGraph,
    models: BTreeMap<String, Model>,
}

impl<'g> ConstProject<'g> {
    /// An empty project over the module graph `graph`.
    pub fn new(graph: &'g SymbolGraph) -> Self {
        Self {
            graph,
            models: BTreeMap::new(),
        }
    }

    /// Adds the folded file `path`; a second add replaces the first.
    pub fn add_file(&mut self, path: &str, folded: &Folded) {
        trace!(path, "const project file added");
        self.models.insert(
            path.to_owned(),
            Model::new(folded.term.clone(), folded.scopes.clone()),
        );
    }

    /// The model of file `path`, if added.
    pub fn model(&self, path: &str) -> Option<&Model> {
        self.models.get(path)
    }

    /// The bounded value of the expression `node` of file `path`, following imports through the module graph.
    ///
    /// An unknown `path` yields `Unknown` with [`Unresolved::Dynamic`].
    pub fn evaluate(&self, path: &str, node: NodeId, budget: Budget) -> Evaluated {
        let Some(model) = self.models.get(path) else {
            debug!(path, "const evaluation of a file not in the project");
            return Evaluated {
                value: ConstValue::Unknown,
                origins: Vec::new(),
                unresolved: Some(Unresolved::Dynamic),
            };
        };
        let shared = RefCell::new(Shared::default());
        let hook = Hook {
            project: self,
            path,
            shared: &shared,
        };
        let mut ev = ConstEval::new(model, budget).with_external(&hook);
        let value = ev.eval(node);
        let mut origins: Vec<Origin> = ev
            .consulted()
            .iter()
            .filter_map(|&n| origin_of(path, model, n))
            .collect();
        origins.extend(std::mem::take(&mut shared.borrow_mut().origins));
        dedup(&mut origins);
        let unresolved = match value {
            ConstValue::Known(_) | ConstValue::OneOf(_) => None,
            _ if ev.cyclic() => Some(Unresolved::Cycle),
            _ if ev.exhausted() => Some(Unresolved::Budget),
            _ => Some(Unresolved::Dynamic),
        };
        debug!(
            path,
            ?unresolved,
            origins = origins.len(),
            "const evaluation done"
        );
        Evaluated {
            value,
            origins,
            unresolved,
        }
    }
}

/// Removes repeated origins, keeping the first of each.
fn dedup(origins: &mut Vec<Origin>) {
    let mut seen = Vec::new();
    origins.retain(|o| {
        let fresh = !seen.contains(o);
        if fresh {
            seen.push(o.clone());
        }
        fresh
    });
}

/// The source span of `node` as an [`Origin`] in `path`.
fn origin_of(path: &str, model: &Model, node: NodeId) -> Option<Origin> {
    match model.term().node(node).location() {
        Location::Text { range, .. } => Some(Origin {
            path: path.to_owned(),
            start: u32::from(range.start()),
            end: u32::from(range.end()),
        }),
        _ => None,
    }
}

/// The name of a `ref` node.
fn ref_name(model: &Model, node: NodeId) -> Option<&str> {
    match model.term().operator(node) {
        Operator::Universal(Universal::Ref { name }) => Some(name),
        _ => None,
    }
}

/// The evaluator hook of one file within one evaluation.
struct Hook<'a, 'g> {
    project: &'a ConstProject<'g>,
    path: &'a str,
    shared: &'a RefCell<Shared>,
}

impl Hook<'_, '_> {
    /// The unit of `symref` in its file's model: (path, model, unit node).
    fn unit_of(&self, symref: &crate::Symref) -> Option<(&str, &Model, NodeId)> {
        let (path, model) = self.project.models.get_key_value(symref.path())?;
        let want = symref.to_string();
        let unit = model
            .term()
            .units()
            .into_iter()
            .find(|u| u.symref.to_string() == want)?;
        Some((path.as_str(), model, unit.node))
    }

    /// Whether `local` of this file is a direct import of a class-name joiner package.
    fn is_joiner_import(&self, local: &str) -> bool {
        self.project
            .graph
            .ts_import_source(self.path, local)
            .is_some_and(|(spec, member)| CLASS_JOINERS.contains(&spec.as_str()) && member != "*")
    }

    /// Whether the callee name `local` stands for a class-name joiner at this file: a direct import, or a
    /// function of the repository whose body calls one.
    fn is_joiner(&self, model: &Model, callee: NodeId, local: &str) -> bool {
        if self.is_joiner_import(local) {
            return true;
        }
        // A wrapper declared here, or imported from a repository file (one hop).
        let unit = if let gob_ir::Resolution::Must(d) = model.resolve_node(callee) {
            model
                .scopes()
                .decl(d)
                .nodes
                .first()
                .map(|&u| (self.path, model, u))
        } else {
            let targets = self.project.graph.ts_import_targets(self.path, local);
            match targets.as_slice() {
                [(sym, Status::Must)] => self.unit_of(sym),
                _ => None,
            }
        };
        let Some((path, wmodel, unit)) = unit else {
            return false;
        };
        let inner = Hook {
            project: self.project,
            path,
            shared: self.shared,
        };
        inner.body_calls_joiner(wmodel, unit)
    }

    /// Whether the unit's body holds a call whose callee is a direct joiner import.
    fn body_calls_joiner(&self, model: &Model, unit: NodeId) -> bool {
        let term = model.term();
        term.descendants(unit).into_iter().any(|n| {
            matches!(term.operator(n), Operator::Universal(Universal::Apply { kind }) if kind == "call")
                && term
                    .children(n)
                    .first()
                    .and_then(|&h| ref_name(model, h))
                    .is_some_and(|name| self.is_joiner_import(name))
        })
    }
}

impl ExternalRefs for Hook<'_, '_> {
    fn resolve_ref(&self, model: &Model, node: NodeId, steps: u32) -> Option<External> {
        let name = ref_name(model, node)?;
        let targets = self.project.graph.ts_import_targets(self.path, name);
        let [(symref, Status::Must)] = targets.as_slice() else {
            trace!(
                path = self.path,
                name,
                targets = targets.len(),
                "import not followed"
            );
            return None;
        };
        let (tpath, tmodel, unit) = self.unit_of(symref)?;
        let value = const_value_node(tmodel, unit)?;
        let key = symref.to_string();
        if self.shared.borrow().stack.contains(&key) {
            debug!(path = self.path, name, "import cycle");
            return Some(External {
                value: ConstValue::Unknown,
                used: 0,
                exhausted: false,
                cyclic: true,
            });
        }
        self.shared.borrow_mut().stack.push(key);
        let hook = Hook {
            project: self.project,
            path: tpath,
            shared: self.shared,
        };
        let mut sub = ConstEval::new(tmodel, Budget(steps)).with_external(&hook);
        let got = sub.eval(value);
        self.shared.borrow_mut().stack.pop();
        let spans = std::iter::once(value)
            .chain(sub.consulted().iter().copied())
            .filter_map(|n| origin_of(tpath, tmodel, n));
        self.shared.borrow_mut().origins.extend(spans);
        trace!(from = self.path, to = tpath, name, "import followed");
        Some(External {
            value: got,
            used: steps - sub.remaining(),
            exhausted: sub.exhausted(),
            cyclic: sub.cyclic(),
        })
    }

    fn call_kind(&self, model: &Model, callee: NodeId) -> Option<CallKind> {
        let name = ref_name(model, callee)?;
        self.is_joiner(model, callee, name)
            .then_some(CallKind::ClassNames)
    }
}

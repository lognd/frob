//! Utility tokens of class-name sites: the `className`/`class` JSX attribute, the
//! `createElement`/`cloneElement` props entry and the class-string constants of plain `.ts`
//! files (the Python `jsx._classnames`, `_calls`, `_consts` and `_ts_constants`).
//!
//! Statically known text becomes [`LocatedUtility`]s; anything else is recorded as a
//! [`DynamicClass`] site so a later rule knows more classes may apply than the sheet lists.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

use gob_ir::const_value::{Budget, ConstValue, Fragment};
use gob_ir::{NodeId, markup};
use gob_symbols::ConstProject;

use super::cx::Cx;
use super::literals::{blind_segments, is_literal, literal_segments};
use super::tokens::{Segment, is_utility_class_list, tokenize_text, utilities_of};
use crate::model::{DynamicClass, LocatedUtility};

/// Attribute and props-entry names that carry class names.
const CLASS_NAMES: [&str; 2] = ["className", "class"];

/// Callee names (or final member names) that build an element from a props object.
const CREATORS: [&str; 2] = ["createElement", "cloneElement"];

/// The class tokens found in one file.
#[derive(Debug, Default)]
pub(super) struct Found {
    /// Utility tokens in source order.
    pub utilities: Vec<LocatedUtility>,
    /// Sites with a part that is not statically known.
    pub dynamic: Vec<DynamicClass>,
}

impl Found {
    /// Tokenize `segments`; with `gate`, a segment must look like a class list to count.
    fn push_segments(&mut self, cx: &Cx<'_>, segments: &[Segment], gate: bool) {
        for seg in segments {
            let tokens = tokenize_text(&seg.text, seg.left, seg.right);
            if gate && !is_utility_class_list(&tokens.join(" ")) {
                continue;
            }
            self.utilities
                .extend(utilities_of(&tokens, cx.lines.line_of(seg.start)));
        }
    }
}

impl Found {
    /// Append `sites` in source order (the folded term is built children first, so node order is
    /// not source order).
    fn extend_sorted(&mut self, mut sites: Vec<(usize, Found)>) {
        sites.sort_by_key(|(start, _)| *start);
        for (_, site) in sites {
            self.utilities.extend(site.utilities);
            self.dynamic.extend(site.dynamic);
        }
    }
}

/// Every `className`/`class` attribute: any literal anywhere in its value is a class list.
pub(super) fn from_attributes(cx: &Cx<'_>, found: &mut Found) {
    let mut sites: Vec<(usize, Found)> = Vec::new();
    for element in markup::elements(cx.model) {
        for attr in &element.attributes {
            let named = attr
                .name
                .as_deref()
                .is_some_and(|n| CLASS_NAMES.contains(&n));
            let Some(value) = attr.value.filter(|_| named) else {
                continue;
            };
            let mut site = Found::default();
            let mut segments = Vec::new();
            blind_segments(cx, value, &mut segments);
            site.push_segments(cx, &segments, false);
            if markup::class_tokens(cx.model, attr).dynamic {
                tracing::debug!(
                    line = cx.line(attr.node),
                    "jsx className has a dynamic part"
                );
                site.dynamic.push(DynamicClass {
                    line: cx.line(attr.node),
                });
            }
            sites.push((cx.range(attr.node).map_or(0, |r| r.0), site));
        }
    }
    found.extend_sorted(sites);
}

/// Every literal of a plain `.ts` file that looks like a Tailwind class list: the plain strings
/// first, then the template literals (each pass in source order, as the Python scan runs them).
pub(super) fn from_ts_constants(cx: &Cx<'_>, found: &mut Found) {
    let mut segments = Vec::new();
    blind_segments(cx, cx.model.term().root(), &mut segments);
    segments.sort_by_key(|s| s.template);
    found.push_segments(cx, &segments, true);
}

/// True when `name` (a callee as written) is `createElement`/`cloneElement`, bare or on an object.
fn is_creator(name: &str) -> bool {
    let last = name.rsplit('.').next().unwrap_or(name);
    CREATORS.contains(&last)
}

/// One entry of a props object: its key and value node.
struct Entry {
    key: String,
    value: NodeId,
}

/// The `key: value` entries of an object literal node, in either folded shape.
fn object_entries(cx: &Cx<'_>, obj: NodeId) -> Option<Vec<Entry>> {
    let mut out = Vec::new();
    if cx.is_op(obj, "object") {
        for &c in &cx.kids(obj)[1..] {
            if !cx.is_op(c, "prop") {
                continue;
            }
            if let [_, key, value] = cx.kids(c)
                && let Some((_, key)) = cx.lit(*key)
            {
                out.push(Entry {
                    key: key.to_owned(),
                    value: *value,
                });
            }
        }
        return Some(out);
    }
    if cx.is_adapter(obj, "object") {
        for &c in cx.kids(obj) {
            if cx.is_adapter(c, "pair") {
                if let [key, _, value] = cx.kids(c)
                    && let Some((kind, text)) = cx.lit(*key)
                {
                    let key = if kind == "string" {
                        text.trim_matches(['"', '\'']).to_owned()
                    } else {
                        text.to_owned()
                    };
                    out.push(Entry { key, value: *value });
                }
            } else if let Some(name) = cx.reference(c) {
                out.push(Entry {
                    key: name.to_owned(),
                    value: c,
                });
            }
        }
        return Some(out);
    }
    None
}

/// The operands of a left-or-right nested `+` chain; `None` when `id` is not one or any nested
/// binary expression is another operator.
fn plus_chain(cx: &Cx<'_>, id: NodeId) -> Option<Vec<NodeId>> {
    let operands = if cx.is_op(id, "+") {
        cx.kids(id)[1..].to_vec()
    } else if cx.is_adapter(id, "binary_expression") {
        match cx.kids(id) {
            [l, op, r] if cx.lit(*op).is_some_and(|(k, _)| k == "+") => vec![*l, *r],
            _ => return None,
        }
    } else {
        return None;
    };
    let mut flat = Vec::new();
    for operand in operands {
        let is_binary = cx.is_op(operand, "+") || cx.is_adapter(operand, "binary_expression");
        if is_binary {
            flat.extend(plus_chain(cx, operand)?);
        } else {
            flat.push(operand);
        }
    }
    Some(flat)
}

/// Tokens of a constant's value: `Known` text, or the known pieces of a partly known string
/// (boundary tokens next to an unknown piece are dropped).
fn value_tokens(value: &ConstValue) -> Option<Vec<String>> {
    match value {
        ConstValue::Known(gob_ir::const_value::Value::Str(s)) => {
            Some(s.split_whitespace().map(str::to_owned).collect())
        }
        ConstValue::Fragments(frags) => {
            let mut out = Vec::new();
            let mut any_known = false;
            for (i, frag) in frags.iter().enumerate() {
                let Fragment::Known(text) = frag else {
                    continue;
                };
                any_known = true;
                let left = i > 0 && matches!(frags[i - 1], Fragment::Unknown);
                let right = matches!(frags.get(i + 1), Some(Fragment::Unknown));
                out.extend(
                    tokenize_text(text, left, right)
                        .into_iter()
                        .map(str::to_owned),
                );
            }
            any_known.then_some(out)
        }
        _ => None,
    }
}

/// What a `createElement` class value turned out to be.
enum Resolved {
    /// Statically known tokens, and whether a part of the value was not.
    Tokens(Vec<LocatedUtility>, bool),
    /// Nothing can be claimed (computed, ambiguous or an unsupported shape).
    Dynamic,
}

struct Resolver<'a, 'g> {
    cx: &'a Cx<'a>,
    project: &'a ConstProject<'g>,
    path: &'a str,
}

impl Resolver<'_, '_> {
    /// An identifier operand: the constant it names, tokenized, on the line of its declaration
    /// (line 1 when the constant lives in another file).
    fn reference(&self, id: NodeId) -> Resolved {
        let evaluated = self.project.evaluate(self.path, id, Budget::default());
        let Some(tokens) = value_tokens(&evaluated.value) else {
            tracing::debug!(name = ?self.cx.reference(id), "jsx createElement: constant not static");
            return Resolved::Dynamic;
        };
        let partial = matches!(&evaluated.value, ConstValue::Fragments(f)
            if f.iter().any(|x| matches!(x, Fragment::Unknown)));
        let line = match evaluated.origins.first() {
            Some(o) if o.path == self.path => self
                .cx
                .lines
                .line_of(usize::try_from(o.start).unwrap_or_default()),
            Some(_) => 1,
            None => self.cx.line(id),
        };
        let tokens: Vec<&str> = tokens.iter().map(String::as_str).collect();
        Resolved::Tokens(utilities_of(&tokens, line), partial)
    }

    /// One operand: an identifier or a string/template literal.
    fn operand(&self, id: NodeId) -> Resolved {
        if self.cx.reference(id).is_some() {
            return self.reference(id);
        }
        match literal_segments(self.cx, id) {
            Some(segments) => {
                let mut found = Found::default();
                found.push_segments(self.cx, &segments, false);
                Resolved::Tokens(found.utilities, false)
            }
            None => Resolved::Dynamic,
        }
    }

    /// The class value of a props entry.
    fn value(&self, id: NodeId) -> Resolved {
        if self.cx.reference(id).is_some() || is_literal(self.cx, id) {
            return self.operand(id);
        }
        let Some(chain) = plus_chain(self.cx, id) else {
            return Resolved::Dynamic;
        };
        let mut all = Vec::new();
        let mut partial = false;
        for operand in chain {
            match self.operand(operand) {
                Resolved::Tokens(t, p) => {
                    all.extend(t);
                    partial |= p;
                }
                Resolved::Dynamic => return Resolved::Dynamic,
            }
        }
        Resolved::Tokens(all, partial)
    }
}

/// Every `createElement`/`cloneElement` call's props-object class entry.
pub(super) fn from_create_element(
    cx: &Cx<'_>,
    project: &ConstProject<'_>,
    path: &str,
    found: &mut Found,
) {
    let resolver = Resolver { cx, project, path };
    let mut sites: Vec<(usize, Found)> = Vec::new();
    for id in cx.model.term().ids() {
        let is_call = matches!(cx.op(id),
            gob_ir::Operator::Universal(gob_ir::Universal::Apply { kind }) if kind == "call");
        if !is_call {
            continue;
        }
        let kids = cx.kids(id);
        let creator = kids
            .first()
            .and_then(|&c| cx.reference(c))
            .is_some_and(is_creator);
        let Some(entries) = creator
            .then(|| kids.get(2))
            .flatten()
            .and_then(|&props| object_entries(cx, props))
        else {
            continue;
        };
        let Some(entry) = entries
            .iter()
            .find(|e| CLASS_NAMES.contains(&e.key.as_str()))
        else {
            continue;
        };
        let mut site = Found::default();
        match resolver.value(entry.value) {
            Resolved::Tokens(tokens, partial) => {
                site.utilities = tokens;
                if partial {
                    site.dynamic.push(DynamicClass {
                        line: cx.line(entry.value),
                    });
                }
            }
            Resolved::Dynamic => {
                tracing::debug!(
                    line = cx.line(entry.value),
                    "jsx createElement class is dynamic"
                );
                site.dynamic.push(DynamicClass {
                    line: cx.line(entry.value),
                });
            }
        }
        sites.push((cx.range(id).map_or(0, |r| r.0), site));
    }
    found.extend_sorted(sites);
}

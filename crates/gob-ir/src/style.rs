//! The `style` capability: rules, declarations, at-rules, custom properties and
//! `var()` references (language-engines.md section 2, universal-model.md 5.1,
//! query Q49).
//!
//! # Lowered forms
//!
//! - A rule is `unit(style-rule)` named by its selector text; its children are
//!   declarations, nested rules and at-rules.
//! - An at-rule (`@media`, `@layer`, `@supports`) is `unit(at-rule)` named
//!   without the `@`, with the prelude text in attribute `prelude`.
//! - A declaration is the `Sigma_L` operator [`declaration_op`] named by its
//!   property, with the raw value text in attribute `raw`, an optional boolean
//!   `important`, and the component values as children.
//! - A component value is a `lit` whose kind is the CSS token class (`ident`,
//!   `number`, `dimension`, `string`, `color`, `function`) or, for `var(--x)`,
//!   a `ref` named `--x`.
//! - A custom property definition is `unit(custom-property)` named `--x`, with
//!   the same `raw` attribute and component value children.
//!
//! A `var()` reference answers at status [`Status::May`]: the cascade decides
//! at runtime which definition applies, so no static resolution is certain.

use tracing::trace;

use crate::operator::{Operator, Sort, Universal};
use crate::query::Model;
use crate::scope::Status;
use crate::term::NodeId;

/// Language tag of the style `Sigma_L` operators.
pub const LANG: &str = "style";
/// Unit kind of a style rule.
pub const STYLE_RULE: &str = "style-rule";
/// Unit kind of an at-rule.
pub const AT_RULE: &str = "at-rule";
/// Unit kind of a custom property definition.
pub const CUSTOM_PROPERTY: &str = "custom-property";
/// Attribute holding an at-rule prelude.
pub const PRELUDE: &str = "prelude";
/// Attribute holding the raw value text of a declaration or custom property.
pub const RAW: &str = "raw";
/// Boolean attribute marking `!important`.
pub const IMPORTANT: &str = "important";

/// The operator of one declaration.
pub fn declaration_op() -> Operator {
    Operator::adapter(LANG, "declaration", Sort::Exp)
}

/// A style rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StyleRule {
    /// The rule node.
    pub node: NodeId,
    /// The selector text.
    pub selector: String,
}

/// An at-rule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtRule {
    /// The at-rule node.
    pub node: NodeId,
    /// The name without `@`.
    pub name: String,
    /// The prelude text, empty when none.
    pub prelude: String,
}

/// A `var(--x)` reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VarRef {
    /// The `ref` node.
    pub node: NodeId,
    /// The custom property name, including `--`.
    pub name: String,
    /// Always `May`: the cascade decides at runtime.
    pub status: Status,
}

/// One component value of a declaration or custom property.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ValuePart {
    /// A plain token.
    Lit {
        /// The token class (`ident`, `number`, ...).
        kind: String,
        /// The token text.
        text: String,
    },
    /// A `var()` reference.
    Var(VarRef),
}

/// A declaration `property: value`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Declaration {
    /// The declaration node.
    pub node: NodeId,
    /// The property name.
    pub property: String,
    /// The value as written.
    pub raw: String,
    /// Whether `!important` was written.
    pub important: bool,
    /// The component values in order.
    pub values: Vec<ValuePart>,
    /// The nearest enclosing style rule or at-rule.
    pub owner: Option<NodeId>,
}

/// A custom property definition `--x: value`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CustomProperty {
    /// The definition node.
    pub node: NodeId,
    /// The name including `--`.
    pub name: String,
    /// The value as written.
    pub raw: String,
    /// The component values in order.
    pub values: Vec<ValuePart>,
    /// The nearest enclosing style rule or at-rule.
    pub owner: Option<NodeId>,
}

fn unit_kind(model: &Model, node: NodeId) -> Option<&str> {
    match &model.term().node(node).op {
        Operator::Universal(Universal::Unit { kind, .. }) => Some(kind),
        _ => None,
    }
}

fn is_declaration(model: &Model, node: NodeId) -> bool {
    matches!(&model.term().node(node).op,
        Operator::Adapter(a) if a.lang == LANG && a.name == "declaration")
}

fn values(model: &Model, node: NodeId) -> Vec<ValuePart> {
    let term = model.term();
    term.node(node)
        .children
        .iter()
        .filter_map(|&c| match &term.node(c).op {
            Operator::Universal(Universal::Lit { kind, lexeme }) => Some(ValuePart::Lit {
                kind: kind.clone(),
                text: lexeme.clone(),
            }),
            Operator::Universal(Universal::Ref { name }) => Some(ValuePart::Var(VarRef {
                node: c,
                name: name.clone(),
                status: Status::May,
            })),
            _ => None,
        })
        .collect()
}

fn owner(model: &Model, node: NodeId) -> Option<NodeId> {
    model
        .term()
        .ancestors(node)
        .into_iter()
        .find(|&a| matches!(unit_kind(model, a), Some(STYLE_RULE | AT_RULE)))
}

fn raw(model: &Model, node: NodeId) -> String {
    model
        .term()
        .node(node)
        .attrs()
        .get_str(RAW)
        .unwrap_or_default()
        .to_owned()
}

/// Every style rule in node order.
pub fn style_rules(model: &Model) -> Vec<StyleRule> {
    let term = model.term();
    term.ids()
        .filter(|&n| unit_kind(model, n) == Some(STYLE_RULE))
        .map(|n| StyleRule {
            node: n,
            selector: term.node(n).name().unwrap_or_default().to_owned(),
        })
        .collect()
}

/// Every at-rule in node order (`media`, `layer`, `supports`, ...).
pub fn at_rules(model: &Model) -> Vec<AtRule> {
    let term = model.term();
    term.ids()
        .filter(|&n| unit_kind(model, n) == Some(AT_RULE))
        .map(|n| AtRule {
            node: n,
            name: term.node(n).name().unwrap_or_default().to_owned(),
            prelude: term
                .node(n)
                .attrs()
                .get_str(PRELUDE)
                .unwrap_or_default()
                .to_owned(),
        })
        .collect()
}

/// Every declaration in node order.
pub fn declarations(model: &Model) -> Vec<Declaration> {
    let term = model.term();
    let out: Vec<Declaration> = term
        .ids()
        .filter(|&n| is_declaration(model, n))
        .map(|n| Declaration {
            node: n,
            property: term.node(n).name().unwrap_or_default().to_owned(),
            raw: raw(model, n),
            important: matches!(
                term.node(n).attrs().get(IMPORTANT),
                Some(crate::AttrValue::Bool(true))
            ),
            values: values(model, n),
            owner: owner(model, n),
        })
        .collect();
    trace!(count = out.len(), "style declarations read");
    out
}

/// Every custom property definition in node order.
pub fn custom_properties(model: &Model) -> Vec<CustomProperty> {
    let term = model.term();
    term.ids()
        .filter(|&n| unit_kind(model, n) == Some(CUSTOM_PROPERTY))
        .map(|n| CustomProperty {
            node: n,
            name: term.node(n).name().unwrap_or_default().to_owned(),
            raw: raw(model, n),
            values: values(model, n),
            owner: owner(model, n),
        })
        .collect()
}

/// Every `var()` reference of declarations and custom properties, in node order.
pub fn var_refs(model: &Model) -> Vec<VarRef> {
    let mut out = Vec::new();
    for d in declarations(model) {
        out.extend(d.values.into_iter().filter_map(var_of));
    }
    for c in custom_properties(model) {
        out.extend(c.values.into_iter().filter_map(var_of));
    }
    out.sort_by_key(|v| v.node);
    out
}

fn var_of(p: ValuePart) -> Option<VarRef> {
    match p {
        ValuePart::Var(v) => Some(v),
        ValuePart::Lit { .. } => None,
    }
}

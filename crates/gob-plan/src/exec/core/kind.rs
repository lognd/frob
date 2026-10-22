//! Node kinds: which U nodes a `find` or a quantifier iterates (grl-spec.md section 6).
//!
//! A kind word of the catalog is tested against a node's operator and attributes. The test
//! answers a [`Truth`]: a spread attribute is a member at status May, every other member is
//! certain. A kind this executor has no node test for is refused before the run starts
//! ([`KindTest::from_word`] returns `None`), never answered as "no members".

use crate::plan::ANY_NODES;
use gob_ir::markup;
use gob_ir::style;
use gob_ir::{AttrValue, Model, NodeId, Operator, Truth, Universal};

/// Unit kinds that count as a type declaration.
const TYPE_KINDS: &[&str] = &[
    "struct",
    "enum",
    "trait",
    "class",
    "interface",
    "type",
    "record",
    "union",
];
/// Unit kinds that count as a module.
const MODULE_KINDS: &[&str] = &["module", "namespace", "package"];
/// Control kinds that count as a `branch` role.
const BRANCH_KINDS: &[&str] = &["if", "branch", "match", "switch", "ternary", "cond"];
/// Control kinds that count as a `loop` role.
const LOOP_KINDS: &[&str] = &["loop", "while", "for", "foreach", "do"];
/// Suffixes a tree-sitter style adapter node name carries after its construct word
/// (`if_statement`, `for_expression`); stripped to compare the word with the control lists.
const CONTROL_SUFFIXES: &[&str] = &["_statement", "_expression"];
/// The suffix of an adapter node name that makes the node a statement.
const STATEMENT_SUFFIX: &str = "_statement";
/// Adapter node names that are a statement without the suffix.
const STATEMENT_NAMES: &[&str] = &["let_declaration"];
/// The adapter statement that only wraps one expression (`f(x)` as a statement).
const EXPRESSION_STATEMENT: &str = "expression_statement";
/// Kinds of `apply` that are an assignment.
const ASSIGN_KINDS: &[&str] = &["assign", "assignment"];

/// The unit kind a data-file adapter (YAML) gives a mapping key or a sequence item.
pub(crate) const KEY_KIND: &str = "key";

/// The node test behind one catalog kind word.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum KindTest {
    /// The artifact root: a file is an artifact with text.
    Artifact,
    /// Every node (the internal range of a snippet binder; no GRL word spells it).
    Any,
    /// Any named `unit`.
    Unit,
    /// A `unit` whose kind is one of the listed spellings.
    UnitKind(&'static [&'static str]),
    /// A `unit` carrying the boolean attribute `test`.
    Test,
    /// An `apply` of the given kind.
    Apply(&'static str),
    /// An `apply` or `bind` whose kind is one of the listed spellings.
    Control(&'static [&'static str]),
    /// An `apply` whose kind is one of the listed spellings.
    ApplyKinds(&'static [&'static str]),
    /// A statement: an adapter node named `*_statement` (a Python `expression_statement`).
    Stmt,
    /// A comment.
    Comment,
    /// A markdown link: an `apply` of kind `link` (inline links and reference definitions).
    Link,
    /// A markdown heading: the `section` unit that carries it.
    Heading,
    // frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
    /// A comment that carries a `frob:<name>` directive; its `name` field is the directive name.
    Directive,
    /// A literal other than a markup tag head.
    Literal,
    /// A markup element.
    Element,
    /// A markup attribute (a spread is a member at status May).
    Attribute,
    /// A style rule.
    StyleRule,
    /// A class selector in a style rule's selector list.
    ClassSelector,
    /// A style declaration.
    Declaration,
    /// A custom property definition.
    CustomProperty,
}

impl KindTest {
    /// The test for the catalog kind `word`, or `None` when this executor cannot test it.
    pub(crate) fn from_word(word: &str) -> Option<Self> {
        Some(match word {
            "artifact" | "file" => Self::Artifact,
            ANY_NODES => Self::Any,
            "unit" => Self::Unit,
            "function" => Self::UnitKind(&["function"]),
            "method" => Self::UnitKind(&["method"]),
            "type" => Self::UnitKind(TYPE_KINDS),
            "module" => Self::UnitKind(MODULE_KINDS),
            "field" => Self::UnitKind(&["field"]),
            "key" => Self::UnitKind(&[KEY_KIND]),
            "param" => Self::UnitKind(&["param", "parameter"]),
            "test" => Self::Test,
            "call" => Self::Apply("call"),
            "import" => Self::ApplyKinds(&["import", "use"]),
            "assignment" => Self::ApplyKinds(ASSIGN_KINDS),
            "branch" => Self::Control(BRANCH_KINDS),
            "loop" => Self::Control(LOOP_KINDS),
            "stmt" => Self::Stmt,
            "comment" => Self::Comment,
            "link" => Self::Link,
            "heading" => Self::Heading,
            "directive" => Self::Directive,
            "literal" => Self::Literal,
            "element" => Self::Element,
            "attribute" => Self::Attribute,
            "style_rule" => Self::StyleRule,
            "class_selector" => Self::ClassSelector,
            "declaration" => Self::Declaration,
            "custom_property" => Self::CustomProperty,
            _ => return None,
        })
    }

    /// Whether `node` is a member: `None` when it is not, else the membership truth.
    pub(crate) fn member(self, model: &Model, node: NodeId) -> Option<Truth> {
        let term = model.term();
        let n = term.node(node);
        let universal = match n.op() {
            Operator::Universal(u) => Some(u),
            Operator::Adapter(_) => None,
        };
        let yes = |b: bool| b.then_some(Truth::Yes);
        match self {
            Self::Artifact => yes(node == term.root()),
            Self::Any => Some(Truth::Yes),
            Self::Unit => yes(is_canonical_unit(model, node) || is_external_unit(model, node)),
            Self::UnitKind(kinds) => match universal {
                Some(Universal::Unit { kind, .. }) => {
                    yes(kinds.contains(&kind.as_str()) && is_canonical_unit(model, node))
                }
                _ => None,
            },
            Self::Test => match universal {
                Some(Universal::Unit { .. }) if is_canonical_unit(model, node) => {
                    yes(matches!(n.attrs().get("test"), Some(AttrValue::Bool(true))))
                }
                _ => None,
            },
            Self::Apply(k) => match universal {
                Some(Universal::Apply { kind }) => yes(kind == k),
                _ => None,
            },
            Self::ApplyKinds(ks) => match (universal, n.op()) {
                (Some(Universal::Apply { kind }), _) => yes(ks.contains(&kind.as_str())),
                // An adapter statement node (a Python `import`) carries its kind as its name.
                (None, Operator::Adapter(a)) => yes(ks.contains(&a.name.as_str())),
                _ => None,
            },
            Self::Control(ks) => match (universal, n.op()) {
                (Some(Universal::Apply { kind } | Universal::Bind { kind, .. }), _) => {
                    yes(ks.contains(&kind.as_str()))
                }
                // An adapter control node (a Python `if_statement`) names its construct.
                (None, Operator::Adapter(a)) => yes(ks.contains(&control_word(&a.name))),
                _ => None,
            },
            Self::Stmt => match n.op() {
                Operator::Adapter(a) => yes(is_statement_name(&a.name)),
                Operator::Universal(_) => None,
            },
            Self::Link => match universal {
                Some(Universal::Apply { kind }) => yes(kind == "link"),
                _ => None,
            },
            Self::Heading => match universal {
                Some(Universal::Unit { kind, .. }) => {
                    yes(kind == "section" && is_canonical_unit(model, node))
                }
                _ => None,
            },
            Self::Comment => yes(matches!(universal, Some(Universal::Comment { .. }))),
            Self::Directive => match universal {
                Some(Universal::Comment { text }) => yes(directive_name(text).is_some()),
                _ => None,
            },
            Self::Literal => match universal {
                Some(Universal::Lit { kind, .. }) => yes(kind != markup::TAG),
                _ => None,
            },
            Self::Element => yes(markup::element(model, node).is_some()),
            Self::Attribute => match n.op() {
                Operator::Adapter(a) if a.lang == markup::LANG && a.name == "attribute" => {
                    Some(Truth::Yes)
                }
                Operator::Adapter(a) if a.lang == markup::LANG && a.name == "spread" => {
                    Some(Truth::Unknown)
                }
                _ => None,
            },
            Self::StyleRule => yes(unit_kind_is(model, node, style::STYLE_RULE)),
            Self::ClassSelector => yes(style::is_class_selector(model, node)),
            Self::CustomProperty => yes(unit_kind_is(model, node, style::CUSTOM_PROPERTY)),
            Self::Declaration => yes(matches!(n.op(),
                Operator::Adapter(a) if a.lang == style::LANG && a.name == "declaration")),
        }
    }
}

/// The construct word of an adapter node name: `if_statement` is `if`, `for_expression` is `for`.
fn control_word(name: &str) -> &str {
    CONTROL_SUFFIXES
        .iter()
        .find_map(|suffix| name.strip_suffix(suffix))
        .unwrap_or(name)
}

/// Whether an adapter node name is a statement (`return_statement`, `let_declaration`).
fn is_statement_name(name: &str) -> bool {
    name.ends_with(STATEMENT_SUFFIX) || STATEMENT_NAMES.contains(&name)
}

impl KindTest {
    /// Whether `x is <kind>` on a statement wrapper looks through to the expression it wraps.
    ///
    /// Only the expression kinds do: a wrapper is a statement, never itself a call, but the
    /// statement `f(x)` "is a call" in the sense a rule means. `find` still iterates the
    /// wrapped call alone, so nothing is counted twice.
    pub(crate) fn looks_through_statement(self) -> bool {
        matches!(
            self,
            Self::Apply(_) | Self::ApplyKinds(_) | Self::Control(_)
        )
    }
}

/// Whether `node` is a bare group: sequencing structure that is no level of nesting itself.
pub(crate) fn is_group(model: &Model, node: NodeId) -> bool {
    matches!(
        model.term().node(node).op(),
        Operator::Universal(Universal::Group { .. })
    )
}

/// The expression an `expression_statement` adapter wraps, or `node` itself when it is no wrapper.
pub(crate) fn unwrap_statement(model: &Model, node: NodeId) -> NodeId {
    let term = model.term();
    let n = term.node(node);
    match n.op() {
        Operator::Adapter(a) if a.name == EXPRESSION_STATEMENT => match n.children() {
            [only] => *only,
            _ => node,
        },
        _ => node,
    }
}

/// The name of the first `frob:<name>` directive in a comment's text (`frob:todo` is `todo`).
pub(crate) fn directive_name(text: &str) -> Option<&str> {
    let rest = &text[text.find("frob:")? + "frob:".len()..];
    let end = rest
        .find(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '-'))
        .unwrap_or(rest.len());
    (end > 0).then(|| &rest[..end])
}

fn unit_kind_is(model: &Model, node: NodeId, want: &str) -> bool {
    matches!(model.term().node(node).op(),
        Operator::Universal(Universal::Unit { kind, .. }) if kind == want)
}

/// Whether `node` is a canonical `key` unit (a data-file mapping key or sequence item).
// frob:ticket 01M5ETB80YYSQNEDP9PG86WKD4
pub(crate) fn is_key(model: &Model, node: NodeId) -> bool {
    unit_kind_is(model, node, KEY_KIND) && is_canonical_unit(model, node)
}

/// The key path of a `key` unit: "/" then the names of its enclosing keys and itself, joined by "/".
// frob:ticket 01M5ETB80YYSQNEDP9PG86WKD4
pub(crate) fn key_path(model: &Model, node: NodeId) -> String {
    let term = model.term();
    let mut names = Vec::new();
    let mut cur = Some(node);
    while let Some(id) = cur {
        if is_key(model, id) {
            names.push(term.node(id).name().unwrap_or_default().to_owned());
        }
        cur = term.node(id).parent();
    }
    names.reverse();
    let path = format!("/{}", names.join("/"));
    tracing::trace!(%path, "key path");
    path
}

/// A unit that is not the `sig` facet child of another unit (one identity is one subject).
pub(crate) fn is_canonical_unit(model: &Model, node: NodeId) -> bool {
    let n = model.term().node(node);
    matches!(n.op(), Operator::Universal(Universal::Unit { .. }))
        && n.attrs().get_str(gob_ir::reserved::FACET) != Some("sig")
}

/// Whether `node` stands for an external ambient unit: a `ref` that resolves to nothing in the
/// file but names a registered ambient source (`time.time`), so `c resolves to v` can bind `v`.
// frob:ticket 01M539NQGFCK3VJGRBM3H6CT56
pub(crate) fn is_external_unit(model: &Model, node: NodeId) -> bool {
    let n = model.term().node(node);
    let Operator::Universal(Universal::Ref { name }) = n.op() else {
        return false;
    };
    let unresolved = model
        .scopes()
        .ref_at(node)
        .is_some_and(|r| matches!(model.scopes().resolve(r), gob_ir::Resolution::Unknown));
    unresolved && gob_symbols::is_ambient_name(n.lang(), name)
}

/// Whether some part of the model is unread (an opaque region or a hole), so that any kind may
/// have members the executor cannot see (grl-spec.md 7.2, review 2.2 item 7).
pub(crate) fn may_hide_members(model: &Model) -> bool {
    let term = model.term();
    term.ids().any(|n| {
        let op = term.node(n).op();
        op.is_opaque() || op.is_hole()
    })
}

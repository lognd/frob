//! Node kinds: which U nodes a `find` or a quantifier iterates (grl-spec.md section 6).
//!
//! A kind word of the catalog is tested against a node's operator and attributes. The test
//! answers a [`Truth`]: a spread attribute is a member at status May, every other member is
//! certain. A kind this executor has no node test for is refused before the run starts
//! ([`KindTest::from_word`] returns `None`), never answered as "no members".

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
/// Kinds of `apply` that are an assignment.
const ASSIGN_KINDS: &[&str] = &["assign", "assignment"];

/// The node test behind one catalog kind word.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum KindTest {
    /// The artifact root: a file is an artifact with text.
    Artifact,
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
    /// A comment.
    Comment,
    /// A literal other than a markup tag head.
    Literal,
    /// A markup element.
    Element,
    /// A markup attribute (a spread is a member at status May).
    Attribute,
    /// A style rule.
    StyleRule,
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
            "unit" => Self::Unit,
            "function" => Self::UnitKind(&["function"]),
            "method" => Self::UnitKind(&["method"]),
            "type" => Self::UnitKind(TYPE_KINDS),
            "module" => Self::UnitKind(MODULE_KINDS),
            "field" => Self::UnitKind(&["field"]),
            "param" => Self::UnitKind(&["param", "parameter"]),
            "test" => Self::Test,
            "call" => Self::Apply("call"),
            "import" => Self::ApplyKinds(&["import", "use"]),
            "assignment" => Self::ApplyKinds(ASSIGN_KINDS),
            "branch" => Self::Control(BRANCH_KINDS),
            "loop" => Self::Control(LOOP_KINDS),
            "comment" => Self::Comment,
            "literal" => Self::Literal,
            "element" => Self::Element,
            "attribute" => Self::Attribute,
            "style_rule" => Self::StyleRule,
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
            Self::Unit => yes(is_canonical_unit(model, node)),
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
            Self::ApplyKinds(ks) => match universal {
                Some(Universal::Apply { kind }) => yes(ks.contains(&kind.as_str())),
                _ => None,
            },
            Self::Control(ks) => match universal {
                Some(Universal::Apply { kind } | Universal::Bind { kind, .. }) => {
                    yes(ks.contains(&kind.as_str()))
                }
                _ => None,
            },
            Self::Comment => yes(matches!(universal, Some(Universal::Comment { .. }))),
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
            Self::CustomProperty => yes(unit_kind_is(model, node, style::CUSTOM_PROPERTY)),
            Self::Declaration => yes(matches!(n.op(),
                Operator::Adapter(a) if a.lang == style::LANG && a.name == "declaration")),
        }
    }
}

fn unit_kind_is(model: &Model, node: NodeId, want: &str) -> bool {
    matches!(model.term().node(node).op(),
        Operator::Universal(Universal::Unit { kind, .. }) if kind == want)
}

/// A unit that is not the `sig` facet child of another unit (one identity is one subject).
fn is_canonical_unit(model: &Model, node: NodeId) -> bool {
    let n = model.term().node(node);
    matches!(n.op(), Operator::Universal(Universal::Unit { .. }))
        && n.attrs().get_str(gob_ir::reserved::FACET) != Some("sig")
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

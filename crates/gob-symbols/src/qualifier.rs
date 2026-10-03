//! Call qualifiers: what an unresolved call tells us about its callee.
//!
//! A call the graph cannot resolve still says something: `Type::new` names a
//! type, `self.run` names the enclosing impl, `x.run` names nothing but is
//! certainly a method. [`CallQualifier`] keeps that, and
//! [`SymbolGraph::admits`](crate::SymbolGraph::admits) decides which callables
//! the call could still be. Soundness: a qualifier only ever narrows by facts
//! the syntax proves; anything it cannot prove stays [`Admit::Maybe`].

/// What an unresolved call says about its callee.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum CallQualifier {
    /// A path call (`Type::new`, `module::f`): the last qualifying segment, `Self` and imports resolved.
    Path(String),
    /// `self.m(..)` inside an impl of this type.
    SelfType(String),
    /// `x.m(..)` where `x` has this syntactically evident declared type.
    Typed(String),
    /// `expr.m(..)` with an unknown receiver type: certainly a method taking `self`, called with `args`
    /// arguments (`None` when not syntactically known).
    Receiver {
        /// Argument count of the call, receiver excluded.
        args: Option<usize>,
    },
}

impl CallQualifier {
    /// The call as a short phrase for messages.
    pub fn describe(&self) -> String {
        match self {
            Self::Path(q) => format!("path `{q}::`"),
            Self::SelfType(t) => format!("`self.` in `{t}`"),
            Self::Typed(t) => format!("receiver of type `{t}`"),
            Self::Receiver { .. } => "receiver of unknown type".to_owned(),
        }
    }
}

/// Whether a callable can be the target of a qualified unresolved call.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Admit {
    /// The qualifier rules the callable out.
    No,
    /// The qualifier names the callable's own type or module.
    Pinned,
    /// The callable cannot be ruled out (trait default method, re-exported module, unknown receiver).
    Maybe,
}

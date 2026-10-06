//! The universal structural model U: sorted ABT terms, a scope graph with status,
//! the canonical facet stream, the syntactic queries of Theorem 2 and a Kleene
//! rule evaluator (universal-model.md, decision D56).
//!
//! # Model (universal-model.md section numbers)
//!
//! - 2.1 and 2.3, [`Term`], [`Operator`], [`Universal`]: arena-allocated sorted
//!   abstract binding trees over the thirteen universal operators plus adapter
//!   operators. Bound variables are the `binders` of a node, named externally and
//!   de Bruijn levels in the printer, so alpha-equivalent terms are
//!   indistinguishable.
//! - 2.2 item 2 and 2.6, [`Identity`], [`Symref`]: identities anchored on symrefs;
//!   the content digest is a facet, not the identity.
//! - 2.2 item 3, [`ScopeGraph`]: scopes, declarations, references and labelled
//!   edges with [`Status`] `Must | May | Unknown`; the lexical view is derived from
//!   binders; opaque regions downgrade resolution.
//! - 2.5, [`Location`]: addresses with a total order and containment.
//! - 4.1, [`Answer`], [`Truth`]: the answer lattice and Kleene logic.
//! - 4.2 and 4.3, [`eval`]: stratified relations, polarity and subject accounting.
//! - 5, [`Term`] query methods and [`Model`]: the syntactic queries.
//! - 4.4 and 5.1, [`const_value`], [`markup`], [`style`]: the web-engine answer types
//!   and queries (language-engines.md D96).
//! - 7.1, [`Facet`], [`FacetDigest`]: digest scheme 2.
//!
//! # Conventions of this crate
//!
//! - `attr` and `comment` nodes are children of the node they attach to (the target is
//!   the parent); an attribute's payload is its own children.
//! - A `unit` child with attribute `ir.facet = "sig"` belongs to the Sig facet,
//!   `attr("doc")` children to Doc, other `attr` children and the unit's attribute map
//!   to Attr, `comment` children are trivia, everything else is Body.
//! - Reserved attribute keys start with `ir.` and are listed in [`reserved`].
//!
//! ```
//! use gob_ir::{Location, NodeSpec, Operator, TermBuilder};
//! use gob_text::FileInterner;
//!
//! let mut files = FileInterner::new();
//! let f = files.intern("a.rs");
//! let mut b = TermBuilder::new("a.rs", "rust");
//! let x = b.node(NodeSpec::new(Operator::reference("x"), Location::text(f, 4, 5)), &[]).unwrap();
//! let func = b
//!     .node(
//!         NodeSpec::new(Operator::unit("function", "impl"), Location::text(f, 0, 9))
//!             .named("id")
//!             .binders(&["x"]),
//!         &[x],
//!     )
//!     .unwrap();
//! let term = b.finish(func).unwrap();
//! assert_eq!(term.symref_of(func).unwrap().to_string(), "a.rs::id");
//! assert!(term.free_vars(func).is_empty());
//! ```

/// Convert an arena length to a dense `u32` index.
pub(crate) fn idx32(n: usize) -> u32 {
    u32::try_from(n).expect("arena exceeds u32::MAX entries")
}

mod answer;
mod attrs;
pub mod const_value;
mod digest;
pub mod eval;
mod location;
pub mod markup;
mod operator;
mod print;
mod query;
pub mod registry;
mod scope;
mod select;
pub mod style;
mod symref;
mod term;

pub use answer::{Answer, Truth};
pub use attrs::{AttrValue, Attributes, reserved};
pub use digest::{DIGEST_SCHEME, Digest, Facet, FacetDigest};
pub use eval::{
    Ctx, EvalConfig, EvalError, Observation, Poison, PoisonReason, Polarity, Relation, RuleFinding,
    RuleOutcome, RuleProgram, SubjectResult, ThresholdKind, Verdict,
};
pub use location::Location;
pub use operator::{AdapterOp, GroupOrder, Operator, Sort, Universal};
pub use print::{FacetStream, PrintOpts};
pub use query::{BinderRef, Model, Occurrence, OccurrenceKind, SymrefLookup, UnitInfo};
pub use registry::{AtomEntry, DetectorEntry, DetectorKind, VocabEntry};
pub use scope::{
    Decl, DeclId, DeclKind, Edge, Label, MayDefine, OpaqueHint, RefId, Reference, Resolution,
    ScopeGraph, ScopeId, Status,
};
pub use select::{
    Hidden, HiddenReason, UnitMatch, UnitSelection, owner_of_unit, select, select_units,
};
pub use symref::{Anchor, Identity, IdentityDelta, Segment, Symref, SymrefError};
pub use term::{Node, NodeId, NodeSpec, Term, TermBuilder, TermError};

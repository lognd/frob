//! A stratified-Datalog-style evaluator with Kleene semantics (universal-model.md 4.2, 4.3).
//!
//! The relations are the term relations of Theorem 2: operator, parent, child
//! order, attachment, scope edges with status, and location order, plus
//! relations derived by ordered strata. Rules are Rust closures over the
//! relations ([`RuleProgram`]); a textual Datalog front end can be added later
//! without changing the semantics, because every accessor already answers in
//! [`Truth`](crate::Truth) and poisons the dependency cone.

mod ctx;
mod program;
mod relation;

pub use ctx::{Ctx, Poison, PoisonReason};
pub use program::{
    EvalConfig, EvalError, Observation, Polarity, RuleFinding, RuleOutcome, RuleProgram,
    SubjectResult, ThresholdKind, Verdict,
};
pub use relation::Relation;

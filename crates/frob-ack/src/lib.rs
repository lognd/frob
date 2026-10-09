//! `frob ack`: acknowledge bound symbols into `frob.lock`, explain and query
//! the graph, and flag drift (D28, code-model sections 2 and 6).
//!
//! # Overview
//!
//! - [`Inputs`]: everything a rule needs, built once by [`Inputs::collect`]
//!   (gob-walk, the gob-symbols graph through the `.frob/` gob-cache, the
//!   `frob:doc` directives from gob-directives, and `frob.lock`).
//! - [`ack`]: resolve symrefs or paths, record their current digests in
//!   `frob.lock` ([`gob_lock`]) and commit the file on the current branch.
//! - Rules [`Drift001`], [`Drift002`], [`Drift003`], [`Drift004`], [`Affect001`], run by
//!   [`evaluate`] (cached per repo in the gob-cache `repo_rule` table) or
//!   [`check`] (uncached).
//! - Verbs [`Ack`], [`GraphWhy`], [`GraphAffects`], added to a product root
//!   by [`register`].
//!
//! # Semantics
//!
//! An ack records the digests of a symbol at a point in time (the five facets sig,
//! body, doc, attr and contract) and, for each `frob:doc path#slug` directive bound to the
//! symbol, the digest of the named markdown section. Drift is the bound
//! target changing afterwards, in either direction: the code changed under
//! the doc, or the doc changed under the code.

mod ack;
mod cmd;
mod error;
mod inputs;
mod repo_rule;
mod rules;

pub use ack::{AckOutcome, ack, plan_ack};
pub use cmd::{Ack, AckData, GraphAffects, GraphWhy, register};
pub use error::AckError;
pub use gob_lock::Plan;
pub use inputs::{DocDirective, Inputs, PRODUCT, doc_pair, section_digest};
pub use rules::{
    Affect001, Drift001, Drift002, Drift003, Drift004, check, evaluate, partial_parse_files,
};

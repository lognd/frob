//! The plan executor: runs a validated [`Plan`](crate::plan::Plan) over gob-ir models with
//! Kleene semantics (grl-spec.md section 7, plugins.md section 6).
//!
//! The core ([`Run`], [`run`]) binds `find` variables and evaluates conditions; later layers add
//! relations and outcomes on top of it.

mod core;
pub mod relations;

pub use self::core::{
    Datum, Doubt, ExecError, Input, Row, Run, Scalar, Val, Verdict, compare, count, run, run_with,
};

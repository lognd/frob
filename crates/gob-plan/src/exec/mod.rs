//! The plan executor: runs a validated [`Plan`](crate::plan::Plan) over gob-ir models with
//! Kleene semantics (docs/design/shared/grl-spec.md section 7, docs/design/shared/packs-and-plugins.md section 6).
//!
//! The core ([`Run`], [`run`]) binds `find` variables and evaluates conditions; later layers add
//! relations and outcomes on top of it.

mod core;
pub mod fix;
pub mod outcome;
pub mod prefilter;
pub mod relations;

pub use self::core::{
    BUCKET_ATTR, COMPONENT_ATTR, Datum, Doubt, ExecError, Input, Row, Run, Scalar, Val, Verdict,
    compare, count, run, run_with,
};
pub(crate) use self::core::{PATH_ATTR, WORKSPACE_ATTR, is_external_unit, is_test_word};

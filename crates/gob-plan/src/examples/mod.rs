//! Examples are tests (grl-spec.md section 9): the expectation markers an example carries and the
//! judge that compares them with what a run reported.
//!
//! This layer is pure: it reads marker comments and `expect` lines, takes the findings a run
//! produced as plain [`Actual`] values and says pass or GRL016 with the expected-versus-actual
//! diff. Producing those findings (lowering the rule, building the example's model, running the
//! executor) is the caller's job.

pub mod judge;
pub mod markers;

pub use judge::{ExampleResult, GRL016, judge, judge_fixed};
pub use markers::{Actual, Expected, Level, Mark, expect_line, parse_markers};

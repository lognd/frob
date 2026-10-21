//! Examples are tests (grl-spec.md section 9): the expectation markers an example carries and the
//! judge that compares them with what a run reported.
//!
//! This layer is pure: it reads marker comments and `expect` lines, takes the findings a run
//! produced as plain [`Actual`] values and says pass or GRL016 with the expected-versus-actual
//! diff. [`runner`] produces those findings: it lowers the rule, builds the example's model, runs
//! the executor and hands the result to the judge.

#[cfg(test)]
mod corpus_tests;
pub mod judge;
pub mod markers;
mod model_reader;
mod resolves;
pub mod runner;
mod side;

pub use judge::{ExampleResult, GRL016, judge, judge_fixed};
pub use markers::{Actual, Expected, Level, Mark, expect_line, parse_markers};
pub use model_reader::{ModelNodeRow, ModelReader, install_model_reader};
pub use runner::{RunError, run_example};

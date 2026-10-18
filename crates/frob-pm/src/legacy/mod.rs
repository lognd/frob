//! PM rules kept on the legacy `#[derive(Rule)]` shape, which the declared `src/rules/` layout cannot express.

pub mod aging;
pub mod cycle_plan;
pub mod good_first;
pub mod pm032;
pub mod story;

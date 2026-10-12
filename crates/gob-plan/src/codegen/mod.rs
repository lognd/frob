//! Ahead-of-time Rust for a lowered std rule (plugins.md 6.1, grl-spec.md D80).
//!
//! The generated module embeds the rule's canonical plan bytes as a static and runs them through
//! the executor's own outcome layer, so its findings are the plan's findings by construction.
//! It forbids `unsafe`, performs no I/O and names no ambient capability. The output is a pure
//! function of the plan: generating twice is byte-identical.

// frob:ticket 01M3ZX7HGX4HXKW1X8VKHW9BKW

use std::fmt::Write as _;

use crate::plan::Plan;

/// The Rust source of the module that runs `plan`.
pub fn generate(plan: &Plan) -> String {
    let bytes = plan.to_bytes();
    let mut out = String::new();
    let _ = writeln!(
        out,
        "//! Generated from rule {} by `gob_plan::codegen`. Do not edit.\n",
        plan.rule()
    );
    out.push_str("#![forbid(unsafe_code)]\n\n");
    out.push_str("use gob_plan::exec::outcome::{Outcomes, outcomes};\n");
    out.push_str("use gob_plan::exec::relations::Relations;\n");
    out.push_str("use gob_plan::exec::{ExecError, Input};\n");
    out.push_str("use gob_plan::plan::{Plan, PlanError};\n\n");
    let _ = writeln!(out, "/// The canonical plan bytes of rule {}.", plan.rule());
    let _ = writeln!(out, "pub static PLAN_BYTES: [u8; {}] = [", bytes.len());
    for chunk in bytes.chunks(16) {
        let row: Vec<String> = chunk.iter().map(|b| format!("0x{b:02x}")).collect();
        let _ = writeln!(out, "    {},", row.join(", "));
    }
    out.push_str("];\n\n");
    out.push_str("/// The embedded plan.\n///\n/// # Errors\n/// A [`PlanError`] when the bytes are malformed.\n");
    out.push_str(
        "pub fn plan() -> Result<Plan, PlanError> {\n    Plan::load_embedded(&PLAN_BYTES)\n}\n\n",
    );
    out.push_str(RUN);
    tracing::debug!(
        rule = plan.rule(),
        bytes = bytes.len(),
        "generated rule module"
    );
    out
}

/// The fixed tail of every generated module: its error type and `run`.
const RUN: &str = "/// Why the generated rule could not run.
#[derive(Debug)]
pub enum RunError {
    /// The embedded bytes are malformed.
    Plan(PlanError),
    /// The executor refused the plan.
    Exec(ExecError),
}

/// Runs the rule over `input`.
///
/// # Errors
/// A [`RunError`] when the embedded plan is malformed or the executor refuses it.
pub fn run(input: &Input<'_>, rels: &Relations) -> Result<Outcomes, RunError> {
    let plan = plan().map_err(RunError::Plan)?;
    outcomes(&plan, input, rels).map_err(RunError::Exec)
}
";

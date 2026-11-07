//! Unit discovery through the universal model.

// frob:ticket 01M6VRR46TR8D8C4TG0GYNK2NK

use super::ScanError;
use super::unit::Unit;
use crate::fn_spans;

/// The adapter path whose extension selects the Rust universal-model fold.
const MODEL_PATH: &str = "neat.rs";

/// Byte spans of every function and method of the Rust `text`, from the model.
pub(super) fn function_spans(text: &str) -> Result<Vec<(usize, usize)>, ScanError> {
    fn_spans::function_spans(MODEL_PATH, text).map_err(ScanError::Model)
}

/// True when the model has a function unit over the tree `unit`.
pub(super) fn gates(spans: &[(usize, usize)], unit: &Unit<'_>) -> bool {
    let kept = fn_spans::covers(spans, unit.node.start_byte(), unit.node.end_byte());
    if !kept {
        tracing::trace!(unit = %unit.name, "neat: tree unit has no model function unit");
    }
    kept
}

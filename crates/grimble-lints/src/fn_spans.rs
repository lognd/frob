//! Function spans of a file from the universal model, shared by the families that gate discovery.

// frob:ticket 01M6SNTWTRT3CWHE94KKM8C4P3

use gob_ir::{Location, Operator, Universal};
use gob_symbols::model_of_source_at;

/// Byte spans of every function, method and anonymous function of `text`, from the model.
///
/// `path` selects the model fold by extension; the error is the model's message.
pub(crate) fn function_spans(path: &str, text: &str) -> Result<Vec<(usize, usize)>, String> {
    let model = model_of_source_at(path, text).map_err(|e| e.to_string())?;
    let term = model.term();
    let mut out = Vec::new();
    for id in term.ids() {
        let node = term.node(id);
        let is_fn = match node.op() {
            Operator::Universal(Universal::Unit { kind, .. }) => {
                matches!(kind.as_str(), "function" | "method")
            }
            Operator::Universal(Universal::Anon { kind }) => kind == "function",
            _ => false,
        };
        let Location::Text { range, .. } = node.location() else {
            continue;
        };
        if is_fn {
            out.push((
                u32::from(range.start()) as usize,
                u32::from(range.end()) as usize,
            ));
        }
    }
    tracing::debug!(path, functions = out.len(), "function spans from model");
    Ok(out)
}

/// True when a model function span covers the tree function at `start..end`.
///
/// A decorated unit starts at its decorator or attribute, so only the end must agree.
pub(crate) fn covers(spans: &[(usize, usize)], start: usize, end: usize) -> bool {
    spans.iter().any(|&(s, e)| e == end && s <= start)
}

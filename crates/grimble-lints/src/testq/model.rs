//! Test-function discovery through the universal model.

// frob:ticket 01M6SNTWQRHXXVPKX4CH3W82PE

use gob_ir::{Location, Operator, Universal};
use gob_languages::Language;
use gob_symbols::model_of_source_at;

use super::ScanError;
use crate::effect;

/// The adapter path whose extension selects the universal-model fold for `language`.
fn model_path(language: Language) -> &'static str {
    match language {
        Language::Rust => "testq.rs",
        Language::Python => "testq.py",
        Language::CSharp => "testq.cs",
        other => effect::model_path(other),
    }
}

/// Byte spans of every function, method and anonymous function of `text`, from the model.
pub(super) fn function_spans(
    language: Language,
    text: &str,
) -> Result<Vec<(usize, usize)>, ScanError> {
    let model = model_of_source_at(model_path(language), text)
        .map_err(|e| ScanError::Model(e.to_string()))?;
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
    tracing::debug!(
        language = language.name(),
        functions = out.len(),
        "testq function spans from model"
    );
    Ok(out)
}

/// True when a model function span covers the tree function at `start..end`.
///
/// A decorated Python function's unit starts at its decorator, so only the end must agree.
pub(super) fn covers(spans: &[(usize, usize)], start: usize, end: usize) -> bool {
    spans.iter().any(|&(s, e)| e == end && s <= start)
}

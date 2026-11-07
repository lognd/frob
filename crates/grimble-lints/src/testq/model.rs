//! Test-function discovery through the universal model.

// frob:ticket 01M6SNTWQRHXXVPKX4CH3W82PE

use gob_languages::Language;

use super::ScanError;
use crate::effect;
use crate::fn_spans;

pub(super) use crate::fn_spans::covers;

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
    fn_spans::function_spans(model_path(language), text).map_err(ScanError::Model)
}

//! `rule why`: trace one rule at one `FILE:LINE` of a source file.

// frob:ticket 01M3ZX7H8FPEAY1X1WVW1PNXXN

use crate::exec::Input;
use crate::exec::relations::Relations;
use crate::why::{Why, WhyError, why};

use super::parse_clean;

/// Why a `rule why` request could not be answered.
#[derive(Debug, thiserror::Error)]
pub enum WhyVerbError {
    /// The rule file has syntax errors.
    #[error("the rule file does not parse; run `rule check` first")]
    Parse,
    /// The file defines no rule with this id.
    #[error("no rule `{0}` in the rule file")]
    NoRule(String),
    /// The target source could not be folded into a model.
    #[error("cannot build the model of the target: {0}")]
    Model(String),
    /// The trace failed.
    #[error(transparent)]
    Why(#[from] WhyError),
}

/// Trace rule `id` of the rule file `rule_path`/`rule_src` at `line` of `text` written in `lang`.
///
/// # Errors
/// [`WhyVerbError`] when the rule file does not parse or lacks `id`, the target cannot be
/// modelled, or the executor refuses the rule.
pub fn why_source(
    rule_path: &str,
    rule_src: &str,
    id: &str,
    lang: &str,
    text: &str,
    line: u32,
) -> Result<Why, WhyVerbError> {
    let file = parse_clean(rule_path, rule_src).ok_or(WhyVerbError::Parse)?;
    let rule = file
        .rules
        .iter()
        .find(|r| r.id.text == id)
        .ok_or_else(|| WhyVerbError::NoRule(id.to_owned()))?;
    let model =
        gob_symbols::model_of_source(lang, text).map_err(|e| WhyVerbError::Model(e.to_string()))?;
    let source = gob_text::SourceText::new(text.to_owned())
        .map_err(|e| WhyVerbError::Model(format!("{e:?}")))?;
    let input = Input {
        model: &model,
        source: Some(&source),
    };
    tracing::debug!(rule = id, line, "rule why");
    Ok(why(rule, rule_src, &input, &Relations::new(), line)?)
}

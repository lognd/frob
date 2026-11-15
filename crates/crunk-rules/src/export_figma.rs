//! The Figma plan-limit check behind EXPORT003: does the variables export fit the `[figma]` plan.

// frob:ticket 01M5XCVZFESE41V1GVEYC5VP5X

use crunk_spec::DesignSpec;
use crunk_tokens::TokenSet;
use crunk_tokens::export::plan_overruns;

/// One message per Figma collection that exceeds the configured plan limits.
///
/// Empty when the spec has no `[figma]` table (nothing to check against) or the export fits.
///
/// # Errors
///
/// Returns the [`crunk_tokens::TokenError`] when the spec's tokens cannot be resolved.
pub fn plan_findings(spec: &DesignSpec) -> Result<Vec<String>, crunk_tokens::TokenError> {
    let Some(figma) = spec.figma.as_ref() else {
        tracing::debug!("figma plan check skipped: no [figma] table");
        return Ok(Vec::new());
    };
    let tokens = TokenSet::from_spec_with_authored(spec)?;
    let found: Vec<String> = plan_overruns(figma, &tokens)
        .iter()
        .map(ToString::to_string)
        .collect();
    tracing::debug!(count = found.len(), "figma plan check done");
    Ok(found)
}

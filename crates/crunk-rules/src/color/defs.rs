//! The custom-property definition set COLOR002 judges `var()` references against.
//!
//! A reference is defined when the spec's token export contains it or any ingested sheet defines
//! it. The set is only complete when every place a definition can live was indexed;
//! [`unindexed_sources`] names the ones that were not, and COLOR002 is then Unresolved for a
//! reference nothing defines, never clean.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use std::collections::BTreeSet;

use crunk_ingest::ProjectStyles;
use crunk_spec::DesignSpec;
use crunk_tokens::{TokenError, TokenSet};

use crate::sheets::site_path;

/// Every custom property name defined by the spec's token export or by an ingested sheet.
///
/// # Errors
///
/// [`TokenError`] when the spec's token set cannot be built (two entries collide on a name), in
/// which case the export set is unknown.
pub fn defined_names(
    spec: &DesignSpec,
    styles: &ProjectStyles,
) -> Result<BTreeSet<String>, TokenError> {
    let mut names: BTreeSet<String> = TokenSet::from_spec(spec)?
        .names()
        .into_iter()
        .map(str::to_owned)
        .collect();
    for sheet in &styles.sheets {
        names.extend(sheet.custom_props.iter().map(|p| p.name.clone()));
    }
    tracing::debug!(
        defined = names.len(),
        "custom property definition set built"
    );
    Ok(names)
}

/// The definition sources that were not indexed, one reason each; empty when the set is complete.
///
/// The generated tokens sheet is a source whether or not the spec export already lists its
/// names (a hand edit may add more), css files outside `css_root` that nothing governs can
/// define properties, and a file that failed to parse hides its definitions.
pub fn unindexed_sources(spec: &DesignSpec, styles: &ProjectStyles) -> Vec<String> {
    let mut missing = Vec::new();
    let tokens = site_path(spec, &spec.tokens_path());
    if !styles
        .sheets
        .iter()
        .any(|s| site_path(spec, &s.path) == tokens)
    {
        missing.push(format!(
            "the generated tokens sheet {tokens} is not indexed"
        ));
    }
    if !styles.ungoverned.is_empty() {
        missing.push(format!(
            "{} css file(s) outside css_root are not indexed",
            styles.ungoverned.len()
        ));
    }
    if !styles.diagnostics.is_empty() {
        missing.push(format!(
            "{} file(s) failed to ingest",
            styles.diagnostics.len()
        ));
    }
    missing
}

//! Model-backed kinds: the `owned by` ownership globs read from the `model.selectors` rows.

use std::collections::HashMap;

use globset::{Glob, GlobSet, GlobSetBuilder};

use super::{Datum, Scalar};
use crate::exec::relations::SideTable;

/// The globs each model node owns, keyed by node name, from `model.selectors` rows.
///
/// Selector text may arrive quoted (`"src/**"`), as the model source writes it; the quotes are
/// stripped. On a bad glob, returns the offending selector and the reason.
///
/// frob:ticket 01M5ETB7SWJPH7EVK97WHEVEHY
pub(super) fn owners(selectors: &SideTable) -> Result<HashMap<String, GlobSet>, (String, String)> {
    let mut builders: HashMap<String, GlobSetBuilder> = HashMap::new();
    for row in 0..selectors.len() {
        let row = u32::try_from(row).expect("side tables are far below u32::MAX rows");
        let (Datum::Known(Scalar::Str(node)), Datum::Known(Scalar::Str(sel))) =
            (selectors.cell(row, "node"), selectors.cell(row, "selector"))
        else {
            continue;
        };
        let src = sel.trim_matches('"');
        let glob = Glob::new(src).map_err(|e| (src.to_owned(), e.to_string()))?;
        builders
            .entry(node)
            .or_insert_with(GlobSetBuilder::new)
            .add(glob);
    }
    let mut out = HashMap::new();
    for (node, b) in builders {
        let set = b.build().map_err(|e| (node.clone(), e.to_string()))?;
        tracing::debug!(node = node.as_str(), "ownership globs compiled");
        out.insert(node, set);
    }
    Ok(out)
}

//! The flat JSON exporter: `{ "color-ink": "#1a1a1a", ... }`, keys sorted.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::collections::BTreeMap;
use std::path::PathBuf;

use crunk_spec::DesignSpec;

use super::{Comparison, Exporter, Json, Target};
use crate::model::TokenSet;
use crate::naming::bare_name;

/// Renders the flat token-name to value JSON export.
#[derive(Debug, Clone, Copy, Default)]
pub struct FlatJsonExporter;

impl Exporter for FlatJsonExporter {
    fn target(&self) -> Target {
        Target::Json
    }

    /// Every CSS entry keyed by its custom property name without the leading `--`.
    fn render(&self, _spec: &DesignSpec, tokens: &TokenSet) -> String {
        let flat: BTreeMap<String, Json> = tokens
            .css_entries()
            .into_iter()
            .map(|(name, value)| (bare_name(name).to_owned(), Json::Str(value)))
            .collect();
        Json::Map(flat).to_python_pretty()
    }

    fn path(&self, spec: &DesignSpec) -> Option<PathBuf> {
        spec.json_tokens_path()
    }

    fn comparison(&self) -> Comparison {
        Comparison::Json
    }
}

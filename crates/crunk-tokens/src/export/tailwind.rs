//! The Tailwind exporter: a `theme.extend` JSON mapping of the token set.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::collections::BTreeMap;
use std::path::PathBuf;

use crunk_spec::DesignSpec;

use super::{Comparison, Exporter, Json, Target};
use crate::model::{THEME_SECTIONS, TokenKind, TokenSet, TokenValue};

/// Renders the Tailwind theme mapping (`colors`, `spacing`, ..., `fontFamily`).
#[derive(Debug, Clone, Copy, Default)]
pub struct TailwindExporter;

impl Exporter for TailwindExporter {
    fn target(&self) -> Target {
        Target::Tailwind
    }

    /// The eleven theme sections honoring `[tailwind] namespace_keys` and `alpha_channels`, plus
    /// `fontFamily` as `base` and one entry per declared stack.
    fn render(&self, spec: &DesignSpec, tokens: &TokenSet) -> String {
        let namespaced = spec.tailwind.namespace_keys;
        let alpha = spec.tailwind.alpha_channels;
        let mut theme: BTreeMap<String, Json> = BTreeMap::new();
        for section in THEME_SECTIONS {
            let rows: BTreeMap<String, Json> = tokens
                .theme_section(section, namespaced, alpha)
                .into_iter()
                .map(|(key, value)| (key, Json::Str(value)))
                .collect();
            theme.insert(section.name().to_owned(), Json::Map(rows));
        }
        let families: BTreeMap<String, Json> = tokens
            .of_kind(TokenKind::FontFamily)
            .filter_map(|t| match &t.value {
                TokenValue::FontFamily(names) => Some((t.key.clone(), Json::List(names.clone()))),
                _ => None,
            })
            .collect();
        theme.insert("fontFamily".to_owned(), Json::Map(families));
        Json::Map(theme).to_python_pretty()
    }

    fn path(&self, spec: &DesignSpec) -> Option<PathBuf> {
        spec.tailwind_tokens_path()
    }

    fn comparison(&self) -> Comparison {
        Comparison::Json
    }
}

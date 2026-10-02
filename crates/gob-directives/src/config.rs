//! The `[directives]` config table: which comment namespaces the scanner honours.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};

/// The product whose `frob.toml` carries the table.
const PRODUCT: &str = "frob";

/// Which directive namespaces are honoured (code-model section 4, decision D63).
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "directives", materialize)]
pub struct DirectivesConfig {
    /// Comment namespaces the scanner reads; comments in any other are ignored.
    #[config(default = vec!["frob".to_owned(), "grimble".to_owned(), "crunk".to_owned()], enforcement)]
    pub namespaces: Vec<String>,
}

impl DirectivesConfig {
    /// Load `[directives]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        let loaded = gob_config::load::<Self>(root, PRODUCT)?.value;
        tracing::debug!(namespaces = ?loaded.namespaces, "loaded [directives]");
        Ok(loaded)
    }
}

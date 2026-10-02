//! Typed errors for config loading, materializing and checking.

use std::path::PathBuf;

/// Why config could not be loaded, written or checked.
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    /// The config file could not be read or written.
    #[error("cannot access {}: {source}", path.display())]
    Io {
        /// File involved.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// The config file is not valid TOML.
    #[error("cannot parse {}: {message}", path.display())]
    Parse {
        /// File involved.
        path: PathBuf,
        /// Parser message.
        message: String,
    },
    /// A key is not declared by its table.
    #[error("unknown key `{key}` in [{table}]{}", suggestion_text(suggestion.as_deref()))]
    UnknownKey {
        /// Table the key was found in.
        table: String,
        /// The offending key.
        key: String,
        /// Nearest valid key by edit distance, when one is close enough.
        suggestion: Option<String>,
    },
    /// A table exists but has the wrong shape or a value of the wrong type.
    #[error("invalid [{table}]: {message}")]
    Invalid {
        /// Table involved.
        table: String,
        /// What is wrong.
        message: String,
    },
}

fn suggestion_text(suggestion: Option<&str>) -> String {
    suggestion.map_or_else(String::new, |s| format!("; did you mean `{s}`?"))
}

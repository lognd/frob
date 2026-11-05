//! The `[neat]` config table of `grimble.toml`, materialized into [`Options`].

// frob:ticket 01M59QKE60PDB1GDWTDEBAQ4JG

use super::Options;
use super::effects::Atom;

/// Why a `[neat]` entry was refused.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum ConfigError {
    /// The key is not a `[neat]` knob.
    #[error("E-NEAT-CONFIG: unknown key `{0}`")]
    UnknownKey(String),
    /// The value does not fit the knob.
    #[error("E-NEAT-CONFIG: `{key}` does not accept `{value}`")]
    BadValue {
        /// The knob.
        key: String,
        /// The refused value.
        value: String,
    },
}

fn bad(key: &str, value: &str) -> ConfigError {
    ConfigError::BadValue {
        key: key.to_owned(),
        value: value.to_owned(),
    }
}

fn number(key: &str, value: &str) -> Result<usize, ConfigError> {
    value.trim().parse().map_err(|_| bad(key, value))
}

fn flag(key: &str, value: &str) -> Result<bool, ConfigError> {
    match value.trim() {
        "true" | "on" => Ok(true),
        "false" | "off" => Ok(false),
        _ => Err(bad(key, value)),
    }
}

fn list(value: &str) -> Vec<String> {
    value
        .split(',')
        .map(|w| w.trim().trim_matches('"').to_owned())
        .filter(|w| !w.is_empty())
        .collect()
}

impl Options {
    /// Materialize the `[neat]` table from its `(key, value)` entries over the defaults.
    ///
    /// Number knobs: `guard_weight`, `max_params`, `max_depth`, `max_fn_lines`, `max_cognitive`,
    /// `raw_loop_statements`, `hook_statements`, `param_object_params`. Flags (`true`/`false`):
    /// `magic_values`, `require_effects`. Comma lists: `core_paths`, `hook_prefixes`. A key
    /// `effects.<path>` with an atom word as value adds a callee to the vocabulary
    /// (`[neat.effects]`), replacing an entry for the same path.
    ///
    /// # Errors
    ///
    /// [`ConfigError`] on an unknown key or a value that does not fit.
    pub fn from_config(entries: &[(&str, &str)]) -> Result<Self, ConfigError> {
        let mut o = Self::default();
        for (key, value) in entries {
            tracing::debug!(key, value, "neat config entry");
            match *key {
                "guard_weight" | "dispatcher_guard_weight" => o.guard_weight = number(key, value)?,
                "max_params" => o.max_params = number(key, value)?,
                "max_depth" => o.max_depth = number(key, value)?,
                "max_fn_lines" => o.max_fn_lines = number(key, value)?,
                "max_cognitive" => o.max_cognitive = number(key, value)?,
                "raw_loop_statements" => o.raw_loop_statements = number(key, value)?,
                "hook_statements" => o.hook_statements = number(key, value)?,
                "param_object_params" => o.param_object_params = number(key, value)?,
                "magic_values" => o.magic_values = flag(key, value)?,
                "require_effects" => o.require_effects = flag(key, value)?,
                "core_paths" => o.core_paths = list(value),
                "hook_prefixes" => o.hook_prefixes = list(value),
                k if k.starts_with("effects.") => {
                    let path = k.trim_start_matches("effects.").to_owned();
                    let atom = Atom::from_word(value.trim().trim_matches('"'))
                        .ok_or_else(|| bad(key, value))?;
                    o.vocabulary.retain(|(p, _)| *p != path);
                    o.vocabulary.push((path, atom));
                }
                other => return Err(ConfigError::UnknownKey(other.to_owned())),
            }
        }
        Ok(o)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-lints/src/neat/config.rs::Options.from_config
    #[test]
    fn entries_override_defaults_and_bad_ones_are_refused() {
        let o = Options::from_config(&[
            ("max_params", "7"),
            ("require_effects", "true"),
            ("core_paths", "\"src/core/\", src/pure/"),
            ("effects.my::clock", "clock"),
        ])
        .expect("valid table");
        assert_eq!(o.max_params, 7);
        assert!(o.require_effects);
        assert_eq!(o.core_paths, vec!["src/core/", "src/pure/"]);
        assert!(
            o.vocabulary
                .contains(&("my::clock".to_owned(), Atom::from_word("clock").unwrap()))
        );
        assert_eq!(
            Options::from_config(&[("nope", "1")]),
            Err(ConfigError::UnknownKey("nope".to_owned()))
        );
        assert!(Options::from_config(&[("max_depth", "deep")]).is_err());
        assert!(Options::from_config(&[("effects.x", "teleport")]).is_err());
    }
}

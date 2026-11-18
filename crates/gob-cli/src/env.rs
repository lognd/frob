//! The environment a verb sees: the process environment with per-run overrides.

use std::collections::BTreeMap;
use std::ffi::{OsStr, OsString};

/// The environment variables a verb reads, injected through [`crate::Context`] so tests can set them in process.
///
/// Lookups fall through to the live process environment unless a name was overridden
/// ([`Env::with`]) or hidden ([`Env::without`]). Only the variables the CLI itself reads go
/// through here; variables inherited by child processes (`GIT_*`) still come from the process.
#[derive(Debug, Clone, Default)]
pub struct Env {
    /// `Some` sets a name, `None` hides it from lookups.
    overrides: BTreeMap<OsString, Option<OsString>>,
}

impl Env {
    /// The live process environment, no overrides.
    pub fn process() -> Self {
        Self::default()
    }

    /// Set `key` to `value` for lookups.
    #[must_use]
    pub fn with(mut self, key: impl AsRef<OsStr>, value: impl AsRef<OsStr>) -> Self {
        self.overrides.insert(
            key.as_ref().to_os_string(),
            Some(value.as_ref().to_os_string()),
        );
        self
    }

    /// Hide `key` from lookups even when the process has it.
    #[must_use]
    pub fn without(mut self, key: impl AsRef<OsStr>) -> Self {
        self.overrides.insert(key.as_ref().to_os_string(), None);
        self
    }

    /// True when no name is overridden or hidden.
    pub fn is_process(&self) -> bool {
        self.overrides.is_empty()
    }

    /// The raw value of `key`.
    pub fn get_os(&self, key: &str) -> Option<OsString> {
        match self.overrides.get(OsStr::new(key)) {
            Some(over) => over.clone(),
            None => std::env::var_os(key),
        }
    }

    /// The value of `key` when set and valid UTF-8.
    #[allow(
        clippy::disallowed_methods,
        reason = "an environment value is text, not a path"
    )]
    pub fn get(&self, key: &str) -> Option<String> {
        self.get_os(key).and_then(|v| v.into_string().ok())
    }

    /// True when `key` is set to a non-empty value.
    pub fn is_set_nonempty(&self, key: &str) -> bool {
        self.get_os(key).is_some_and(|v| !v.is_empty())
    }

    /// The `PATH` value, empty when unset.
    pub fn path(&self) -> OsString {
        self.get_os("PATH").unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn overrides_win_and_hide() {
        let env = Env::process().with("GOB_ENV_TEST_SET", "1").without("PATH");
        assert_eq!(env.get("GOB_ENV_TEST_SET").as_deref(), Some("1"));
        assert_eq!(env.get_os("PATH"), None);
        assert!(env.path().is_empty());
        assert!(!env.is_process());
        assert!(Env::process().is_process());
    }

    #[test]
    fn empty_value_is_not_set_nonempty() {
        let env = Env::process().with("GOB_ENV_TEST_EMPTY", "");
        assert!(!env.is_set_nonempty("GOB_ENV_TEST_EMPTY"));
    }
}

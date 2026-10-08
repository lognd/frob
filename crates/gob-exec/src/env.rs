//! The environment a child process receives: inherited whole, or scrubbed to an allowlist.
//!
//! Design: `security.md` sections 2.4 and 2.5 (a tool stage runs with a scrubbed environment; the
//! worker holds no secrets). [`EnvPolicy::Scrub`] starts the child from an empty environment and
//! copies only the named variables from the parent, so an unrelated token in the parent never
//! reaches a child that did not ask for it. A secret-shaped name ([`is_secret_shaped`]) on the
//! allowlist is refused (logged, skipped): a secret goes to a child only as an explicit
//! per-spawn addition in `Spec::env`, never by inheritance.

// frob:ticket 01M40VH6HES1X3P57WZS0S9G93

use std::ffi::OsString;

use tracing::{debug, warn};

/// Names a child needs to find programs and a home directory; add per-caller names on top.
#[cfg(not(windows))]
pub const BASELINE: &[&str] = &["PATH", "HOME"];

/// Names a child needs to find programs and a home directory; add per-caller names on top.
#[cfg(windows)]
pub const BASELINE: &[&str] = &[
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "TEMP",
    "TMP",
    "USERPROFILE",
];

/// Variable-name fragments that mark a name secret-shaped (case-insensitive substring).
const SECRET_FRAGMENTS: &[&str] = &["TOKEN", "SECRET", "KEY", "PASSWORD", "PASSWD", "CREDENTIAL"];

/// Variable-name prefixes that mark a name secret-shaped (case-insensitive).
const SECRET_PREFIXES: &[&str] = &[
    "ACTIONS_",
    "AWS_",
    "AZURE_",
    "GOOGLE_",
    "NPM_",
    "CARGO_REGISTRY_",
];

/// True when `name` looks like it carries a secret (security.md section 2.3 `env.secret`).
pub fn is_secret_shaped(name: &str) -> bool {
    let upper = name.to_ascii_uppercase();
    upper == "SSH_AUTH_SOCK"
        || SECRET_PREFIXES.iter().any(|p| upper.starts_with(p))
        || SECRET_FRAGMENTS.iter().any(|f| upper.contains(f))
}

/// How a child's environment is built from the parent's.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum EnvPolicy {
    /// Inherit the parent's whole environment (what [`Runner::run`](crate::Runner::run) does).
    #[default]
    Inherit,
    /// Start empty; copy only these exact names from the parent when set there.
    Scrub {
        /// Variable names to copy from the parent, exact match (case-insensitive on Windows).
        allow: Vec<String>,
    },
}

impl EnvPolicy {
    /// A scrubbed environment of [`BASELINE`] plus `extra` names.
    pub fn scrubbed<I, S>(extra: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        let allow = BASELINE
            .iter()
            .map(|s| (*s).to_owned())
            .chain(extra.into_iter().map(Into::into))
            .collect();
        Self::Scrub { allow }
    }

    /// The inherited variables a child gets from `parent`: all of them under
    /// [`EnvPolicy::Inherit`] (returned as `None`, meaning "do not clear"), or exactly the
    /// allowlisted, non-secret-shaped ones under [`EnvPolicy::Scrub`].
    pub fn resolve(
        &self,
        parent: impl IntoIterator<Item = (OsString, OsString)>,
    ) -> Option<Vec<(OsString, OsString)>> {
        let Self::Scrub { allow } = self else {
            return None;
        };
        for name in allow.iter().filter(|n| is_secret_shaped(n)) {
            warn!(name = %name, "secret-shaped name on the env allowlist is refused; pass it as an explicit addition");
        }
        let kept: Vec<(OsString, OsString)> = parent
            .into_iter()
            .filter(|(name, _)| {
                let Some(name) = name.to_str() else {
                    return false;
                };
                !is_secret_shaped(name) && allow.iter().any(|a| names_equal(a, name))
            })
            .collect();
        debug!(
            kept = ?kept.iter().map(|(n, _)| n).collect::<Vec<_>>(),
            "scrubbed environment resolved"
        );
        Some(kept)
    }
}

/// Environment names compare case-insensitively on Windows and exactly elsewhere.
fn names_equal(a: &str, b: &str) -> bool {
    if cfg!(windows) {
        a.eq_ignore_ascii_case(b)
    } else {
        a == b
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parent() -> Vec<(OsString, OsString)> {
        [
            ("PATH", "/bin"),
            ("HOME", "/home/u"),
            ("GITHUB_TOKEN", "ghp_x"),
            ("AWS_REGION", "us-east-1"),
            ("NODE_ENV", "production"),
            ("MY_API_KEY", "k"),
            ("EDITOR", "vi"),
        ]
        .map(|(k, v)| (OsString::from(k), OsString::from(v)))
        .to_vec()
    }

    fn names(kept: Option<Vec<(OsString, OsString)>>) -> Vec<String> {
        kept.expect("scrubbed")
            .into_iter()
            .map(|(n, _)| n.to_string_lossy().into_owned())
            .collect()
    }

    // frob:tests crates/gob-exec/src/env.rs::EnvPolicy.resolve
    #[test]
    fn scrub_keeps_only_allowlisted_names() {
        let policy = EnvPolicy::Scrub {
            allow: vec!["PATH".into(), "NODE_ENV".into()],
        };
        assert_eq!(names(policy.resolve(parent())), ["PATH", "NODE_ENV"]);
    }

    // frob:tests crates/gob-exec/src/env.rs::EnvPolicy.resolve
    #[test]
    fn a_secret_shaped_name_on_the_allowlist_is_still_dropped() {
        let policy = EnvPolicy::Scrub {
            allow: vec![
                "PATH".into(),
                "GITHUB_TOKEN".into(),
                "AWS_REGION".into(),
                "MY_API_KEY".into(),
            ],
        };
        assert_eq!(names(policy.resolve(parent())), ["PATH"]);
    }

    // frob:tests crates/gob-exec/src/env.rs::EnvPolicy.resolve
    #[test]
    fn inherit_does_not_clear() {
        assert!(EnvPolicy::Inherit.resolve(parent()).is_none());
    }

    // frob:tests crates/gob-exec/src/env.rs::EnvPolicy.scrubbed
    #[test]
    fn scrubbed_adds_the_baseline() {
        let EnvPolicy::Scrub { allow } = EnvPolicy::scrubbed(["NODE_ENV"]) else {
            panic!("scrubbed builds a Scrub policy");
        };
        assert!(allow.iter().any(|n| n == "PATH"));
        assert!(allow.iter().any(|n| n == "NODE_ENV"));
    }

    // frob:tests crates/gob-exec/src/env.rs::is_secret_shaped
    #[test]
    fn secret_shapes_follow_the_security_design() {
        for secret in [
            "GH_TOKEN",
            "npm_token",
            "MY_SECRET",
            "DB_PASSWORD",
            "SSH_AUTH_SOCK",
            "ACTIONS_RUNTIME_URL",
            "AWS_REGION",
            "AZURE_CLIENT_ID",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "NPM_CONFIG_USERCONFIG",
            "CARGO_REGISTRY_TOKEN",
            "API_KEY",
        ] {
            assert!(is_secret_shaped(secret), "{secret}");
        }
        for plain in ["PATH", "HOME", "NODE_ENV", "LANG", "TEMP", "RUST_LOG"] {
            assert!(!is_secret_shaped(plain), "{plain}");
        }
    }
}

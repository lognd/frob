//! Errors for path construction and the host bridges.

/// Why a repository path could not be built.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PathError {
    /// The text is not a clean repo-relative path (empty, absolute, dot segment, `.git`, NUL).
    #[error("E-PATH-INVALID: invalid repo-relative path `{0}`")]
    Invalid(String),
    /// A component cannot exist on a supported platform.
    #[error("E-PATH-COMPONENT: component `{component}` is invalid on {platform}: {reason}")]
    BadComponent {
        /// The offending component text.
        component: String,
        /// The platform that refuses it.
        platform: &'static str,
        /// Why it is refused.
        reason: &'static str,
    },
    /// The host path is not under the root.
    #[error("E-PATH-OUTSIDE: `{path}` is not under `{root}`")]
    Outside {
        /// The path given.
        path: String,
        /// The root it had to be under.
        root: String,
    },
    /// The host path is not valid UTF-8.
    #[error("E-PATH-UTF8: host path is not valid UTF-8: `{0}`")]
    NotUtf8(String),
}

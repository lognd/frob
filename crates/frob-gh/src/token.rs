//! The API token, read from the environment and never printed.

use crate::Error;

/// A GitHub token; `Debug` and `Display` never show the secret.
#[derive(Clone)]
pub struct Token(String);

impl Token {
    /// Wrap a token value (tests pass placeholders; the secret is never logged).
    pub fn new(value: impl Into<String>) -> Self {
        Self(value.into())
    }

    /// Read `GH_TOKEN`, then `GITHUB_TOKEN`, through `lookup` (so tests inject a fake env).
    ///
    /// # Errors
    /// [`Error::NoToken`] when neither variable is set to a non-empty value.
    pub fn from_lookup(lookup: impl Fn(&str) -> Option<String>) -> Result<Self, Error> {
        for name in ["GH_TOKEN", "GITHUB_TOKEN"] {
            if let Some(value) = lookup(name).filter(|v| !v.trim().is_empty()) {
                tracing::debug!(variable = name, "github token found in environment");
                return Ok(Self(value.trim().to_string()));
            }
        }
        tracing::warn!("no github token in GH_TOKEN or GITHUB_TOKEN");
        Err(Error::NoToken)
    }

    /// Read the token from the process environment.
    ///
    /// # Errors
    /// [`Error::NoToken`] when neither variable is set.
    pub fn from_env() -> Result<Self, Error> {
        Self::from_lookup(|name| std::env::var(name).ok())
    }

    /// The `Authorization` header value; the only place the secret leaves this type.
    pub(crate) fn bearer(&self) -> String {
        format!("Bearer {}", self.0)
    }
}

impl std::fmt::Debug for Token {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Token(<redacted>)")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gh_token_wins_and_debug_is_redacted() {
        let t = Token::from_lookup(|n| Some(format!("value-of-{n}"))).unwrap();
        assert_eq!(t.bearer(), "Bearer value-of-GH_TOKEN");
        assert!(!format!("{t:?}").contains("value-of"));
    }

    #[test]
    fn falls_back_then_reports_absence() {
        let t = Token::from_lookup(|n| (n == "GITHUB_TOKEN").then(|| "x".to_string())).unwrap();
        assert_eq!(t.bearer(), "Bearer x");
        assert!(matches!(
            Token::from_lookup(|_| Some("  ".into())),
            Err(Error::NoToken)
        ));
    }
}

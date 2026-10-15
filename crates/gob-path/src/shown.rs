//! Display paths: text for people, home directory shown as `~`.

use std::path::Path;

/// A path rendered for a person (render-only; never parse or persist it).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Shown(String);

impl Shown {
    /// Render `p` with the home directory (`HOME` or `USERPROFILE`) shown as `~`.
    pub fn of(p: &Path) -> Self {
        let home = ["HOME", "USERPROFILE"].iter().find_map(std::env::var_os);
        Self::with_home(p, home.as_deref().map(Path::new))
    }

    /// Render `p` with an explicit `home` (none skips the rule); the one scrub function.
    #[expect(
        clippy::disallowed_methods,
        reason = "gob-path is the one crate that renders paths to text"
    )]
    pub fn with_home(p: &Path, home: Option<&Path>) -> Self {
        let shown = match home
            .filter(|h| !h.as_os_str().is_empty())
            .and_then(|h| p.strip_prefix(h).ok())
        {
            Some(rest) if rest.as_os_str().is_empty() => "~".to_owned(),
            Some(rest) => format!("~/{}", rest.display()),
            None => p.display().to_string(),
        };
        tracing::trace!(shown = %shown, "path shown");
        Self(shown)
    }

    /// The rendered text.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for Shown {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

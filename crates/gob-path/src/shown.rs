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

/// `p` as exact text, or `None` when it is not valid Unicode (never lossy, never `~`-collapsed).
///
/// For callers that must refuse a non-text path rather than render it; accepts `&Path`,
/// `&OsStr` and anything else `AsRef<Path>`.
#[expect(
    clippy::disallowed_methods,
    reason = "gob-path is the one crate that converts paths to text"
)]
pub fn exact_text<P: AsRef<Path> + ?Sized>(p: &P) -> Option<&str> {
    let text = p.as_ref().to_str();
    if text.is_none() {
        tracing::trace!(path = ?p.as_ref(), "path is not valid unicode");
    }
    text
}

impl std::fmt::Display for Shown {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

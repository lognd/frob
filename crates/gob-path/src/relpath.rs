//! Validated repo-relative paths: the one persisted path type.

use std::path::{Path, PathBuf};

use crate::style::PathStyle;
use crate::{PathError, validate_component};

/// A slash-separated, repo-relative path with no `.`, `..`, empty or absolute components.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct RelPath(String);

impl RelPath {
    /// Validate `s` as a repo-relative path.
    ///
    /// # Errors
    /// [`PathError::Invalid`] for empty, absolute, backslashed or dot-segment paths;
    /// [`PathError::BadComponent`] for a component invalid on a supported platform.
    pub fn new(s: impl Into<String>) -> Result<Self, PathError> {
        let s = s.into();
        let ok = !s.is_empty()
            && !s.starts_with('/')
            && !s.contains('\\')
            && !s.contains('\0')
            && s.split('/')
                .all(|c| !c.is_empty() && c != "." && c != ".." && c != ".git");
        if !ok {
            tracing::debug!(path = %s, "refused repo-relative path");
            return Err(PathError::Invalid(s));
        }
        s.split('/').try_for_each(validate_component)?;
        Ok(Self(s))
    }

    /// The path as a slash-separated string.
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Bridge a host path under `root` to a `RelPath`, by components, in the host's style.
    ///
    /// # Errors
    /// See [`RelPath::from_host_style`]; also [`PathError::NotUtf8`].
    #[expect(
        clippy::disallowed_methods,
        reason = "gob-path is the one crate that bridges host paths to text"
    )]
    pub fn from_host(root: &Path, p: &Path) -> Result<Self, PathError> {
        let text = |x: &Path| {
            x.to_str()
                .map(str::to_owned)
                .ok_or_else(|| PathError::NotUtf8(x.to_string_lossy().into_owned()))
        };
        Self::from_host_style(PathStyle::host(), &text(root)?, &text(p)?)
    }

    /// Bridge `p` under `root`, both read in `style`: strip the root by components, refuse
    /// outside paths, join with `/`, refuse components invalid on any supported platform.
    ///
    /// # Errors
    /// [`PathError::Outside`] when `p` is not strictly under `root` (or holds `..`);
    /// [`PathError::BadComponent`] or [`PathError::Invalid`] for the remainder.
    pub fn from_host_style(style: PathStyle, root: &str, p: &str) -> Result<Self, PathError> {
        let outside = || PathError::Outside {
            path: p.to_owned(),
            root: root.to_owned(),
        };
        let (r, q) = style.split(root).zip(style.split(p)).ok_or_else(outside)?;
        let under = r.anchor == q.anchor
            && q.names.len() > r.names.len()
            && r.names.iter().zip(&q.names).all(|(a, b)| style.same(a, b));
        if !under {
            tracing::debug!(root, path = p, "host path outside root");
            return Err(outside());
        }
        let rel = q.names[r.names.len()..].join("/");
        tracing::trace!(%rel, "host path bridged");
        Self::new(rel)
    }

    /// Join onto a host `root` with `Path::join`, one component at a time.
    pub fn to_host(&self, root: &Path) -> PathBuf {
        self.0
            .split('/')
            .fold(root.to_path_buf(), |acc, c| acc.join(c))
    }

    /// Join onto `root` text in `style`, with that style's separator.
    pub fn to_host_style(&self, style: PathStyle, root: &str) -> String {
        let sep = style.sep();
        let mut out = root.trim_end_matches(['/', '\\']).to_owned();
        for c in self.0.split('/') {
            out.push(sep);
            out.push_str(c);
        }
        out
    }
}

impl std::fmt::Display for RelPath {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

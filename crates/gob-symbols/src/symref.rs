//! Symbol addresses: `path`, `path::Qual.Name` and `path#slug`.

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

/// Why a string is not a valid symref.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum SymrefError {
    /// The path part is empty or contains whitespace.
    #[error("symref path is empty or contains whitespace: {0:?}")]
    BadPath(String),
    /// A qualified-name segment is empty or contains whitespace.
    #[error("symref has an empty or malformed name segment: {0:?}")]
    BadSegment(String),
    /// A markdown anchor slug is empty or contains whitespace.
    #[error("symref anchor slug is empty or contains whitespace: {0:?}")]
    BadSlug(String),
}

/// What a [`Symref`] points at inside its file.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Target {
    /// The whole file.
    File,
    /// A code symbol; segments nest with `.` (a segment may carry an opaque
    /// `[...]` suffix).
    Symbol(Vec<String>),
    /// A markdown anchor slug.
    Anchor(String),
}

/// A parsed, validated symbol address; `Display` round-trips `parse`.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Symref {
    path: String,
    target: Target,
}

fn bad_ws(s: &str) -> bool {
    s.is_empty() || s.chars().any(char::is_whitespace)
}

/// Splits `qual` on `.` outside `[...]`.
pub(crate) fn split_qual(qual: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut depth = 0u32;
    let mut cur = String::new();
    for ch in qual.chars() {
        match ch {
            '[' => {
                depth += 1;
                cur.push(ch);
            }
            ']' => {
                depth = depth.saturating_sub(1);
                cur.push(ch);
            }
            '.' if depth == 0 => out.push(std::mem::take(&mut cur)),
            _ => cur.push(ch),
        }
    }
    out.push(cur);
    out
}

impl Symref {
    /// Parses `path`, `path::Qual.Name` or `path#slug`.
    ///
    /// # Errors
    ///
    /// [`SymrefError`] when the path, a segment or the slug is empty or has
    /// whitespace.
    pub fn parse(s: &str) -> Result<Self, SymrefError> {
        if let Some((path, qual)) = s.split_once("::") {
            if bad_ws(path) {
                return Err(SymrefError::BadPath(path.to_owned()));
            }
            let segs = split_qual(qual);
            if segs.iter().any(|g| bad_ws(g)) {
                return Err(SymrefError::BadSegment(qual.to_owned()));
            }
            return Ok(Self {
                path: path.to_owned(),
                target: Target::Symbol(segs),
            });
        }
        if let Some((path, slug)) = s.split_once('#') {
            if bad_ws(path) {
                return Err(SymrefError::BadPath(path.to_owned()));
            }
            if bad_ws(slug) {
                return Err(SymrefError::BadSlug(slug.to_owned()));
            }
            return Ok(Self {
                path: path.to_owned(),
                target: Target::Anchor(slug.to_owned()),
            });
        }
        if bad_ws(s) {
            return Err(SymrefError::BadPath(s.to_owned()));
        }
        Ok(Self::file(s))
    }

    /// The whole-file symref for `path`.
    pub fn file(path: &str) -> Self {
        Self {
            path: path.to_owned(),
            target: Target::File,
        }
    }

    /// A code symbol symref from already-split segments.
    pub fn symbol(path: &str, segments: Vec<String>) -> Self {
        Self {
            path: path.to_owned(),
            target: Target::Symbol(segments),
        }
    }

    /// A markdown anchor symref.
    pub fn anchor(path: &str, slug: &str) -> Self {
        Self {
            path: path.to_owned(),
            target: Target::Anchor(slug.to_owned()),
        }
    }

    /// The repo-relative file path.
    pub fn path(&self) -> &str {
        &self.path
    }

    /// What the symref points at inside the file.
    pub fn target(&self) -> &Target {
        &self.target
    }

    /// Qualified-name segments (empty for files and anchors).
    pub fn segments(&self) -> &[String] {
        match &self.target {
            Target::Symbol(s) => s,
            _ => &[],
        }
    }

    /// The final segment of a code symbol, or the slug of an anchor.
    pub fn name(&self) -> Option<&str> {
        match &self.target {
            Target::Symbol(s) => s.last().map(String::as_str),
            Target::Anchor(a) => Some(a),
            Target::File => None,
        }
    }

    /// Same symbol address under a different file path.
    #[must_use]
    pub fn with_path(&self, path: &str) -> Self {
        Self {
            path: path.to_owned(),
            target: self.target.clone(),
        }
    }

    /// Same file, replacing the code-symbol segments.
    #[must_use]
    pub fn with_segments(&self, segments: Vec<String>) -> Self {
        Self {
            path: self.path.clone(),
            target: Target::Symbol(segments),
        }
    }
}

impl fmt::Display for Symref {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.target {
            Target::File => f.write_str(&self.path),
            Target::Symbol(s) => write!(f, "{}::{}", self.path, s.join(".")),
            Target::Anchor(a) => write!(f, "{}#{a}", self.path),
        }
    }
}

impl FromStr for Symref {
    type Err = SymrefError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::parse(s)
    }
}

impl Serialize for Symref {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for Symref {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        Self::parse(&s).map_err(serde::de::Error::custom)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trips() {
        for s in [
            "a/b.rs",
            "a/b.rs::Foo.bar",
            "a/b.rs::Foo[std::fmt::Display].fmt",
            "docs/x.md#intro-1",
            "t.py::T.test[a.b]",
        ] {
            assert_eq!(Symref::parse(s).unwrap().to_string(), s);
        }
    }

    #[test]
    fn bracket_dots_stay_in_segment() {
        let r = Symref::parse("t.py::T.test[a.b]").unwrap();
        assert_eq!(r.segments(), ["T", "test[a.b]"]);
    }

    #[test]
    fn rejects_malformed() {
        assert!(Symref::parse("").is_err());
        assert!(Symref::parse("a.rs::").is_err());
        assert!(Symref::parse("a.rs::A..b").is_err());
        assert!(Symref::parse("a.rs#").is_err());
        assert!(Symref::parse("a b.rs").is_err());
        assert!(Symref::parse("::A").is_err());
    }
}

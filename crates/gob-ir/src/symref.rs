//! Symrefs, the human names of identities (code-model.md 2, universal-model.md 2.6),
//! and identities themselves: a stable anchor with content as a facet (2.2 item 2).

use std::fmt;
use std::str::FromStr;

use crate::digest::Digest;

/// A parse failure for [`Symref`].
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum SymrefError {
    /// The locator before `::` is empty.
    #[error("symref has an empty locator")]
    EmptyLocator,
    /// `::` is present but no qualified name follows.
    #[error("symref has `::` but an empty qualname")]
    EmptyQualname,
    /// A qualname segment is empty or malformed.
    #[error("malformed qualname segment `{0}`")]
    BadSegment(String),
    /// Brackets are not balanced.
    #[error("unbalanced brackets in `{0}`")]
    Unbalanced(String),
    /// The `@lang` tag is not an identifier.
    #[error("malformed language tag `{0}`")]
    BadLang(String),
}

/// One segment of a qualified name.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Segment {
    /// A named container or member, with an optional opaque `[qualifier]`.
    Name {
        /// The identifier text.
        name: String,
        /// Text inside `[...]`, opaque to the parser.
        qualifier: Option<String>,
    },
    /// An anonymous unit: positional index `{n}`.
    Anon(u32),
}

impl fmt::Display for Segment {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Name {
                name,
                qualifier: None,
            } => f.write_str(name),
            Self::Name {
                name,
                qualifier: Some(q),
            } => write!(f, "{name}[{q}]"),
            Self::Anon(n) => write!(f, "{{{n}}}"),
        }
    }
}

/// A symref: `locator [:: qualname] [@ lang]`.
///
/// ```
/// use gob_ir::Symref;
/// let s: Symref = "src/a.rs::Type[Trait].method.{0}@rust".parse().unwrap();
/// assert_eq!(s.locator(), "src/a.rs");
/// assert_eq!(s.to_string(), "src/a.rs::Type[Trait].method.{0}@rust");
/// let doc: Symref = "docs/x.md#intro".parse().unwrap();
/// assert!(doc.qual().is_empty());
/// ```
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Symref {
    locator: String,
    qual: Vec<Segment>,
    lang: Option<String>,
}

fn is_ident(s: &str) -> bool {
    let mut chars = s.chars();
    matches!(chars.next(), Some(c) if c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

/// Index of the last `@` at bracket depth zero.
fn last_top_level_at(s: &str) -> Option<usize> {
    let mut depth = 0i32;
    let mut found = None;
    for (i, c) in s.char_indices() {
        match c {
            '[' | '{' => depth += 1,
            ']' | '}' => depth -= 1,
            '@' if depth == 0 => found = Some(i),
            _ => {}
        }
    }
    found
}

fn parse_segment(raw: &str) -> Result<Segment, SymrefError> {
    if let Some(inner) = raw.strip_prefix('{').and_then(|r| r.strip_suffix('}')) {
        return inner
            .parse::<u32>()
            .map(Segment::Anon)
            .map_err(|_| SymrefError::BadSegment(raw.to_owned()));
    }
    let (name, qualifier) = match raw.find('[') {
        Some(i) => {
            let q = raw[i + 1..]
                .strip_suffix(']')
                .ok_or_else(|| SymrefError::BadSegment(raw.to_owned()))?;
            (&raw[..i], Some(q.to_owned()))
        }
        None => (raw, None),
    };
    if name.is_empty() || name.contains(['{', '}', ']']) {
        return Err(SymrefError::BadSegment(raw.to_owned()));
    }
    Ok(Segment::Name {
        name: name.to_owned(),
        qualifier,
    })
}

fn parse_qualname(s: &str) -> Result<Vec<Segment>, SymrefError> {
    let mut out = Vec::new();
    let (mut depth, mut start) = (0i32, 0usize);
    for (i, c) in s.char_indices() {
        match c {
            '[' => depth += 1,
            ']' => depth -= 1,
            '.' if depth == 0 => {
                out.push(parse_segment(&s[start..i])?);
                start = i + 1;
            }
            _ => {}
        }
        if depth < 0 {
            return Err(SymrefError::Unbalanced(s.to_owned()));
        }
    }
    if depth != 0 {
        return Err(SymrefError::Unbalanced(s.to_owned()));
    }
    out.push(parse_segment(&s[start..])?);
    Ok(out)
}

impl Symref {
    /// A symref naming only a locator (a file, a document, a cell).
    pub fn locator_only(locator: impl Into<String>) -> Self {
        Self {
            locator: locator.into(),
            qual: Vec::new(),
            lang: None,
        }
    }

    /// Build from parts.
    pub fn new(locator: impl Into<String>, qual: Vec<Segment>, lang: Option<String>) -> Self {
        Self {
            locator: locator.into(),
            qual,
            lang,
        }
    }

    /// The locator (path, `path#slug`, `path#cell=A1`, adapter text).
    pub fn locator(&self) -> &str {
        &self.locator
    }

    /// The qualified-name segments.
    pub fn qual(&self) -> &[Segment] {
        &self.qual
    }

    /// The explicit language tag, if any.
    pub fn lang(&self) -> Option<&str> {
        self.lang.as_deref()
    }

    /// This symref extended by one segment.
    #[must_use]
    pub fn child(&self, seg: Segment) -> Self {
        let mut c = self.clone();
        c.qual.push(seg);
        c
    }

    /// The enclosing symref, or `None` at the locator root.
    pub fn parent(&self) -> Option<Self> {
        if self.qual.is_empty() {
            return None;
        }
        let mut p = self.clone();
        p.qual.pop();
        Some(p)
    }

    /// Whether `self` is a proper ancestor of `other` (same locator, prefix qualname).
    pub fn is_ancestor_of(&self, other: &Self) -> bool {
        self.locator == other.locator
            && self.qual.len() < other.qual.len()
            && other.qual.starts_with(&self.qual)
    }
}

impl FromStr for Symref {
    type Err = SymrefError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let (locator, rest) = match s.find("::") {
            Some(i) => (&s[..i], Some(&s[i + 2..])),
            None => (s, None),
        };
        let (locator, qual, lang) = if let Some(rest) = rest {
            if rest.is_empty() {
                return Err(SymrefError::EmptyQualname);
            }
            let (q, lang) = match last_top_level_at(rest) {
                Some(i) => (&rest[..i], Some(&rest[i + 1..])),
                None => (rest, None),
            };
            if let Some(l) = lang
                && !is_ident(l)
            {
                return Err(SymrefError::BadLang(l.to_owned()));
            }
            (locator, parse_qualname(q)?, lang)
        } else {
            match locator.rfind('@') {
                Some(i) if is_ident(&locator[i + 1..]) => {
                    (&locator[..i], Vec::new(), Some(&locator[i + 1..]))
                }
                _ => (locator, Vec::new(), None),
            }
        };
        if locator.is_empty() {
            return Err(SymrefError::EmptyLocator);
        }
        Ok(Self {
            locator: locator.to_owned(),
            qual,
            lang: lang.map(str::to_owned),
        })
    }
}

impl fmt::Display for Symref {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.locator)?;
        if !self.qual.is_empty() {
            f.write_str("::")?;
            for (i, s) in self.qual.iter().enumerate() {
                if i > 0 {
                    f.write_str(".")?;
                }
                write!(f, "{s}")?;
            }
        }
        if let Some(l) = &self.lang {
            write!(f, "@{l}")?;
        }
        Ok(())
    }
}

/// What a unit's identity is anchored on.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Anchor {
    /// The default: the unit's symref.
    Symref(Symref),
    /// An adapter-defined anchor (Unison hash, cell address, generated node id).
    Custom {
        /// Scheme name, for example `unison-hash`.
        scheme: String,
        /// Scheme-specific value.
        value: String,
    },
}

/// How two observations of an identity relate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityDelta {
    /// Same anchor, same content.
    Unchanged,
    /// Same anchor, new content: a change.
    Modified,
    /// Different anchor, same content: a rename (grimble-model.md 9.2).
    Renamed,
    /// Different anchor and content.
    Unrelated,
}

/// A stable identity: the anchor is the identity, the content hash is a facet of it.
///
/// ```
/// use gob_ir::{Anchor, Digest, Identity, IdentityDelta, Symref};
/// let a = Identity::new(Anchor::Symref("a.rs::f".parse().unwrap()), Some(Digest::of("t", b"1")));
/// let b = Identity::new(Anchor::Symref("a.rs::f".parse().unwrap()), Some(Digest::of("t", b"2")));
/// assert_eq!(a.compare(&b), IdentityDelta::Modified);
/// ```
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Identity {
    /// What the identity is anchored on.
    pub anchor: Anchor,
    /// The content facet (typically the Body digest), not part of the identity.
    pub content: Option<Digest>,
}

impl Identity {
    /// An identity from an anchor and an optional content digest.
    pub fn new(anchor: Anchor, content: Option<Digest>) -> Self {
        Self { anchor, content }
    }

    /// The default identity of a symref.
    pub fn of_symref(symref: Symref, content: Option<Digest>) -> Self {
        Self::new(Anchor::Symref(symref), content)
    }

    /// Relate this (old) observation to a `newer` one.
    pub fn compare(&self, newer: &Self) -> IdentityDelta {
        let same_anchor = self.anchor == newer.anchor;
        let same_content = self.content.is_some() && self.content == newer.content;
        match (same_anchor, same_content) {
            (true, true) => IdentityDelta::Unchanged,
            (true, false) => IdentityDelta::Modified,
            (false, true) => IdentityDelta::Renamed,
            (false, false) => IdentityDelta::Unrelated,
        }
    }
}

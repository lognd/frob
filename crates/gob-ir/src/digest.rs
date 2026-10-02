//! BLAKE3 digests, the facet set and the digest scheme number (universal-model.md 7.1).

use std::fmt;

/// The digest scheme implemented here (scheme 2, the canonical facet stream).
pub const DIGEST_SCHEME: u32 = 2;

/// A BLAKE3 digest.
#[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Digest([u8; 32]);

impl Digest {
    /// Digest `bytes` under a domain-separation `domain` string.
    pub fn of(domain: &str, bytes: &[u8]) -> Self {
        let mut h = blake3::Hasher::new();
        h.update(&(domain.len() as u64).to_le_bytes());
        h.update(domain.as_bytes());
        h.update(bytes);
        Self(*h.finalize().as_bytes())
    }

    /// Combine digests in order (used for multi-part identities).
    pub fn combine(domain: &str, parts: &[Self]) -> Self {
        let mut buf = Vec::with_capacity(parts.len() * 32);
        for p in parts {
            buf.extend_from_slice(&p.0);
        }
        Self::of(domain, &buf)
    }

    /// Lowercase hex form.
    pub fn to_hex(&self) -> String {
        blake3::Hash::from_bytes(self.0).to_hex().to_string()
    }

    /// The raw bytes.
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl fmt::Debug for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Digest({})", &self.to_hex()[..12])
    }
}

impl fmt::Display for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.to_hex())
    }
}

/// The five facets of digest scheme 2.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Facet {
    /// The declared signature (binders, annotations), names of binders erased by alpha-normality.
    Sig,
    /// The unit's content with trivia excluded.
    Body,
    /// The doc comment or docstring payload.
    Doc,
    /// The attribute and decorator set.
    Attr,
    /// The normalized signature rendering with names erased.
    Contract,
}

impl Facet {
    /// Every facet, in digest-scheme order.
    pub const ALL: [Self; 5] = [Self::Sig, Self::Body, Self::Doc, Self::Attr, Self::Contract];

    /// Lowercase facet name as recorded in locks.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Sig => "sig",
            Self::Body => "body",
            Self::Doc => "doc",
            Self::Attr => "attr",
            Self::Contract => "contract",
        }
    }
}

/// The answer to `facet_digest(sym, facet)` (query Q38).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FacetDigest {
    /// The facet exists and its stream is complete.
    Exact(Digest),
    /// The unit has no such facet.
    Absent,
    /// The stream contains a hole, so no digest can be claimed.
    Unknown,
}

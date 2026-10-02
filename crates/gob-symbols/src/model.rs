//! Data model: kinds, visibility, facet digests, records and per-file output.

use std::fmt;

use gob_text::{TextRange, TextSize};
use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::symref::Symref;

/// A blake3 digest of a normalized facet.
///
/// A local type because `gob_walk::Digest` has no way to be rebuilt from
/// bytes, which the serialized per-file cache payload needs.
#[derive(Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Debug, Serialize, Deserialize)]
pub struct FacetDigest([u8; 32]);

impl FacetDigest {
    /// Hashes `bytes`.
    pub fn of(bytes: &[u8]) -> Self {
        Self(*blake3::hash(bytes).as_bytes())
    }

    /// Wraps raw digest bytes.
    pub const fn from_bytes(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    /// The raw 32 bytes.
    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl From<gob_walk::Digest> for FacetDigest {
    fn from(d: gob_walk::Digest) -> Self {
        Self(*d.as_bytes())
    }
}

impl fmt::Display for FacetDigest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for b in self.0 {
            write!(f, "{b:02x}")?;
        }
        Ok(())
    }
}

/// The kind of a symbol.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub enum SymbolKind {
    /// A module (`mod`) or, in the graph, a whole file.
    Module,
    /// A free function.
    Function,
    /// A function inside an impl or trait.
    Method,
    /// A struct or union.
    Struct,
    /// An enum.
    Enum,
    /// An enum variant.
    Variant,
    /// A trait.
    Trait,
    /// An impl block.
    Impl,
    /// A constant.
    Const,
    /// A static.
    Static,
    /// A type alias.
    TypeAlias,
    /// A `macro_rules!` macro.
    Macro,
    /// A markdown heading.
    Heading,
}

/// Item visibility as seen from outside the crate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Visibility {
    /// `pub`.
    Public,
    /// `pub(crate)`, `pub(super)` or `pub(in path)`.
    Crate,
    /// No modifier (or `pub(self)`).
    Private,
}

/// The three digest facets of a symbol.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Digests {
    /// Signature text with the body removed, whitespace collapsed.
    pub sig: FacetDigest,
    /// Body text, whitespace collapsed.
    pub body: FacetDigest,
    /// Doc comment text.
    pub doc: FacetDigest,
}

impl Digests {
    /// Digests the three already-normalized facet texts.
    pub fn of_facets(sig: &str, body: &str, doc: &str) -> Self {
        Self {
            sig: FacetDigest::of(sig.as_bytes()),
            body: FacetDigest::of(body.as_bytes()),
            doc: FacetDigest::of(doc.as_bytes()),
        }
    }
}

/// Collapses every whitespace run to one space and trims the ends.
pub fn collapse_ws(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

#[allow(clippy::trivially_copy_pass_by_ref, reason = "serde `with` signature")]
mod range_serde {
    use super::{Deserialize, Deserializer, Serialize, Serializer, TextRange, TextSize};

    pub fn serialize<S: Serializer>(r: &TextRange, s: S) -> Result<S::Ok, S::Error> {
        (u32::from(r.start()), u32::from(r.end())).serialize(s)
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<TextRange, D::Error> {
        let (a, b) = <(u32, u32)>::deserialize(d)?;
        Ok(TextRange::new(TextSize::new(a), TextSize::new(b)))
    }
}

/// One extracted symbol.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SymbolRecord {
    /// The symbol's address.
    pub symref: Symref,
    /// What kind of symbol it is.
    pub kind: SymbolKind,
    /// Byte range of the whole item inside its file.
    #[serde(with = "range_serde")]
    pub span: TextRange,
    /// Visibility from the crate's outside.
    pub visibility: Visibility,
    /// The three facet digests.
    pub digests: Digests,
    /// The enclosing symbol (`None` for top-level items; the graph attaches
    /// those to their file node).
    pub parent: Option<Symref>,
    /// For members of `impl Trait for Type` and the impl block itself, the
    /// whitespace-free trait text.
    pub implements: Option<String>,
}

/// A flattened `use` import.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ImportEdge {
    /// Repo-relative path of the importing file.
    pub from_file: String,
    /// `crate::a::b` for crate-internal imports (`self::`/`super::` resolved
    /// against the file's module path), else the verbatim external path.
    /// Glob imports end in `::*`.
    pub target: String,
}

impl ImportEdge {
    /// True when the target is inside the importing crate.
    pub fn is_internal(&self) -> bool {
        self.target == "crate" || self.target.starts_with("crate::")
    }
}

/// A call expression found in a function body, before resolution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CallSite {
    /// The function or method containing the call.
    pub caller: Symref,
    /// Simple callee name (last path segment or method name).
    pub callee: String,
    /// Last segment of the qualifying path (`Foo` in `Foo::new()`), if any.
    pub qualifier: Option<String>,
    /// True for `x.name()` method-call syntax.
    pub method: bool,
}

/// The per-file extraction result (the cached payload).
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct FileSymbols {
    /// Repo-relative path.
    pub path: String,
    /// Hex digest of the file content.
    pub file_digest: String,
    /// Size of the file in bytes.
    pub size: u32,
    /// Symbols in source order.
    pub symbols: Vec<SymbolRecord>,
    /// Imports in source order.
    pub imports: Vec<ImportEdge>,
    /// Call sites in source order.
    pub calls: Vec<CallSite>,
    /// True when no tree could be produced (never cached).
    pub degraded: bool,
}

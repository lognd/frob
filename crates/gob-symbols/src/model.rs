//! Data model: kinds, visibility, facet digests, records and per-file output.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::fmt;

use gob_text::{TextRange, TextSize};
use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::adapter::{Fidelity, ParseStatus};
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

/// The facet digests of a symbol (digest scheme 2, universal-model.md 7.1).
///
/// A facet the unit lacks digests the empty string; a facet whose stream holds
/// a parse hole digests the partial print and is listed in
/// [`UnitExtras::unknown`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Digests {
    /// Canonical signature stream, outer attributes included (G7).
    pub sig: FacetDigest,
    /// Canonical body stream, trivia excluded (G8).
    pub body: FacetDigest,
    /// Doc comment payload.
    pub doc: FacetDigest,
    /// The attribute and decorator set (G7).
    pub attr: FacetDigest,
    /// Name-erased, language-neutral signature rendering.
    pub contract: FacetDigest,
}

impl Digests {
    /// Digests three already-normalized facet texts; `attr` and `contract` are empty.
    pub fn of_facets(sig: &str, body: &str, doc: &str) -> Self {
        let empty = FacetDigest::of(b"");
        Self {
            sig: FacetDigest::of(sig.as_bytes()),
            body: FacetDigest::of(body.as_bytes()),
            doc: FacetDigest::of(doc.as_bytes()),
            attr: empty,
            contract: empty,
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

/// What the file's own scope graph says about a call's callee name.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum LocalBinding {
    /// Not bound locally; resolve against the crate.
    #[default]
    None,
    /// A nested item (`fn` inside a body): static, resolved, no crate edge.
    Item,
    /// A parameter, `let` binding or closure: a dynamic call, Unknown target.
    Value,
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
    /// The file-local binding of the callee name, from the scope graph.
    pub local: LocalBinding,
    /// True when the call sits in a macro argument (status capped at May).
    pub in_macro: bool,
}

/// What a non-call reference site is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RefKind {
    /// A name used as a value (a function passed as an argument, G4).
    Value,
    /// A markdown link (`apply(kind=link)`); `name` is the raw destination.
    Link,
}

/// A reference that is not a call (references are a superset of calls).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RefSite {
    /// The symbol containing the reference.
    pub from: Symref,
    /// The simple name (`Value`) or the raw link destination (`Link`).
    pub name: String,
    /// Last path segment before the name, if the reference was a path.
    pub qualifier: Option<String>,
    /// What kind of reference this is.
    pub kind: RefKind,
}

/// A `use` binding, kept with its local name (aliases, globs, `pub use`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UseBinding {
    /// Repo-relative path of the importing file.
    pub from_file: String,
    /// The name the import binds locally (`c` in `use a::b as c`); `*` for globs.
    pub local: String,
    /// The normalized target path (`crate::a::b`, or an external path).
    pub target: String,
    /// True for `pub use` (a re-export, G10).
    pub public: bool,
    /// The innermost enclosing symbol, `None` at file level.
    pub container: Option<Symref>,
}

impl UseBinding {
    /// True when the target is inside the importing crate.
    pub fn is_internal(&self) -> bool {
        self.target == "crate" || self.target.starts_with("crate::")
    }
}

/// Facts about one symbol that do not fit [`SymbolRecord`] (no new fields there).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnitExtras {
    /// The symbol these facts belong to.
    pub symref: Symref,
    /// Facets whose stream holds a parse hole (no digest can be claimed).
    pub unknown: Vec<String>,
    /// Markdown: sig, own body and all nested sections (G9); `None` elsewhere.
    pub subtree: Option<FacetDigest>,
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
    /// The adapter language tag; empty for an adapter-less file.
    pub language: String,
    /// The fidelity this file was folded at (F0 for adapter-less files).
    pub fidelity: Fidelity,
    /// How completely the file parsed (G11).
    pub parse_status: ParseStatus,
    /// Non-call references in source order (G4).
    pub refs: Vec<RefSite>,
    /// `use` bindings with local names, aliases and `pub` flags (G10).
    pub uses: Vec<UseBinding>,
    /// Extra per-symbol facts, one per symbol.
    pub extras: Vec<UnitExtras>,
}

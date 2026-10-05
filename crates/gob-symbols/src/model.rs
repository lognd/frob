//! Data model: kinds, visibility, facet digests, records and per-file output.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::collections::HashMap;
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
    /// A model `node` entity.
    Node,
    /// A model `flow` entity.
    Flow,
    /// A model `contract` entity.
    Contract,
    /// A model `claim` entity.
    Claim,
    /// A model `vmodel` entity.
    VModel,
    /// A model `pack` entity.
    Pack,
    /// A model `boundary` entity.
    Boundary,
    /// A Python or C# class.
    Class,
    /// A C# namespace (one unit per dotted component).
    Namespace,
    /// A C# interface.
    Interface,
    /// A C# record or record struct.
    Record,
    /// A C# delegate type.
    Delegate,
    /// A C# property.
    Property,
    /// A C# indexer.
    Indexer,
    /// A C# field.
    Field,
    /// A C# event (field-like or with accessors).
    Event,
    /// A C# instance or static constructor.
    Constructor,
    /// A C# user-defined or conversion operator.
    Operator,
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

/// How a method or function takes `self`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SelfKind {
    /// No `self` parameter: an associated function, never callable with method syntax.
    None,
    /// `&self`.
    Ref,
    /// `&mut self`.
    RefMut,
    /// `self` by value, or a typed `self: Box<Self>` and the like.
    Value,
}

impl SelfKind {
    /// The attribute text for this kind (`none`, `ref`, `refmut`, `value`).
    pub const fn as_attr(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Ref => "ref",
            Self::RefMut => "refmut",
            Self::Value => "value",
        }
    }

    /// Reads the attribute text written by [`Self::as_attr`].
    pub fn from_attr(s: &str) -> Option<Self> {
        match s {
            "none" => Some(Self::None),
            "ref" => Some(Self::Ref),
            "refmut" => Some(Self::RefMut),
            "value" => Some(Self::Value),
            _ => None,
        }
    }
}

/// A declared return type reduced to what a method call on its value can reach.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct RetType {
    /// The plain head type (`Foo` in `&Foo`, `Result` in `Result<Foo, E>`, `Self` for the impl type).
    pub head: String,
    /// The plain first generic argument (`Foo` in `Result<Foo, E>`), when it is a plain type.
    pub arg: Option<String>,
    /// The plain second generic argument (`V` in `HashMap<K, V>`), when it is a plain type.
    #[serde(default)]
    pub arg2: Option<String>,
    /// The plain type of each tuple element (`None` where it is not a plain type): the type's own
    /// elements when `head` is `(tuple)`, else the elements of the first generic argument when that is a tuple.
    pub tuple: Option<Vec<Option<String>>>,
}

/// The calling shape of a function or method: its `self` kind, argument count and return type.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct MethodSig {
    /// How the callable takes `self`.
    pub self_kind: SelfKind,
    /// Number of parameters other than `self`.
    pub arity: usize,
    /// The declared return type, when it is a plain path type (wrappers and non-path types are not recorded).
    pub ret: Option<RetType>,
}

impl MethodSig {
    /// Whether `x.m(args)` with `args` arguments (receiver excluded) can call a callable of this shape.
    pub fn accepts_method_call(&self, args: Option<usize>) -> bool {
        self.self_kind != SelfKind::None && args.is_none_or(|n| n == self.arity)
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
    /// The calling shape of a function or method; `None` for every other symbol.
    pub signature: Option<MethodSig>,
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
    /// What a method call's receiver is, when syntactically evident; `None` for non-method calls.
    #[serde(default)]
    pub receiver: Option<Receiver>,
    /// True when the qualifying path is a generic parameter or a bracketed type: no usable qualifier.
    #[serde(default)]
    pub opaque_qualifier: bool,
    /// The std macro (`assert_eq`, `format`, ...) whose arguments were parsed as ordinary expressions around
    /// this call: the call is as certain as one outside a macro unless the repository declares a macro of that name.
    #[serde(default)]
    pub macro_exact: Option<String>,
    /// Number of call arguments (receiver excluded); `None` when not syntactically known (macro arguments).
    #[serde(default)]
    pub args: Option<usize>,
    /// The full qualifying path of a path call, generics stripped (`frob_ack::inputs` in `frob_ack::inputs::collect()`).
    #[serde(default)]
    pub qual_path: Vec<String>,
    /// Trait bounds of a generic qualifier (`C::from_matches(..)` with `C: Command`); `opaque_qualifier` stays set.
    #[serde(default)]
    pub bound: Vec<String>,
    /// One-based source line of the call.
    #[serde(default)]
    pub line: u32,
    /// The callee expression as written, for diagnostics (`Type::new(..)`, `x.run(..)`).
    #[serde(default)]
    pub text: String,
}

/// What a method call's receiver syntactically is.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Receiver {
    /// The `self` value.
    SelfValue,
    /// A local or parameter whose declared type is syntactically evident.
    Typed(String),
    /// A declared type that carries generic arguments or tuple elements (`Vec<Foo>`, `HashMap<K, V>`, `Option<(A, B)>`).
    Decl(Box<RetType>),
    /// The item an iteration over the receiver yields (`for x in v`, an iterator-closure parameter).
    Item(Box<Receiver>),
    /// `recv.map(|x| body)`: the iterator, `Option` or `Result` `recv` with its items replaced by the type of `result`.
    Mapped {
        /// The mapped iterator, `Option` or `Result`.
        recv: Box<Receiver>,
        /// The type of the closure body.
        result: Box<Receiver>,
        /// Which adaptor takes the closure.
        kind: MapKind,
    },
    /// `let v: Vec<_> = source.collect()`: the declared collection with its `_` element filled in from the items of `source`.
    Collected {
        /// The declared collection type, `_` where inferred.
        shape: Box<RetType>,
        /// The iterator that is collected.
        source: Box<Receiver>,
    },
    /// `base[a..b]`: the `str`, slice or `Vec` receiver sliced by a range.
    Slice(Box<Receiver>),
    /// The associated constant or unit variant `base::NAME` of the type `base` stands for.
    Assoc(Box<Receiver>, String),
    /// A tuple expression: the receiver of each element (destructured by tuple patterns; never a method receiver).
    Tuple(Vec<Receiver>),
    /// The element `base[i]` of a `Vec`, slice, array or map receiver (never a range index).
    Index(Box<Receiver>),
    /// A field of an enum variant bound by a pattern (`Kind::A(x)`, `Kind::B { f }`): `path` is the pattern
    /// path (`Kind::A`) and `field` the tuple index or field name.
    Variant {
        /// The pattern path, enum then variant (`Self::A`, `module::Kind::A`).
        path: Vec<String>,
        /// The tuple index or field name.
        field: String,
    },
    /// A field of the receiver `base` (`self.paths`, `x.node`): typed through the struct field table.
    Field(Box<Receiver>, String),
    /// The value of a call whose callee has a declared return type (`store_in(..)`, `Type::open(..)`, `x.term()`).
    Ret(Box<CallRef>),
    /// Element `i` of a tuple-valued receiver (`let (a, b) = f()` binds `a` to element 0).
    Elem(Box<Receiver>, usize),
    /// The success value of a `Result` or `Option` receiver (`e?`, `e.unwrap()`, `e.expect(..)`).
    Unwrap(Box<Receiver>),
    /// A value known only by its trait bounds (`&dyn A`, `impl A`, a generic `T: A + B`): trait names, sorted.
    Bound(Vec<String>),
    /// An upper-case name used as a value that is no local or constant (`Drift001.meta()`): a unit struct when
    /// the graph finds exactly one struct of that name, otherwise untyped.
    Unit(String),
    /// Any other expression: its type is unknown.
    Expr,
}

/// The adaptors whose closure result types the adapted value.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MapKind {
    /// `map`: each item becomes the closure result.
    Map,
    /// `and_then` on `Option`/`Result`: the closure returns the new `Option`/`Result`.
    AndThen,
    /// `filter_map` on an iterator: the closure returns an `Option` of the new item.
    FilterMap,
}

/// The callee of a call whose value is used as a receiver, kept so the graph can look up its return type.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct CallRef {
    /// Simple callee name.
    pub name: String,
    /// The full qualifying path (`Type` in `Type::open(..)`), empty for bare and method calls.
    pub path: Vec<String>,
    /// Trait bounds of a generic qualifier (`C::new(..)` with `C: Command`): `path` is then just that generic.
    pub bound: Vec<String>,
    /// For a method call, its receiver.
    pub recv: Option<Receiver>,
    /// Argument count, receiver excluded.
    pub args: usize,
}

/// The traits a struct or enum derives (`#[derive(Clone, gob_rules::Rule)]`), by last path segment.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeriveDecl {
    /// The derived type's simple name.
    pub owner: String,
    /// The derive names, in source order.
    pub traits: Vec<String>,
}

/// A struct field whose declared type is a concrete path type (the field type table).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FieldDecl {
    /// The declaring struct's or enum's simple name.
    pub owner: String,
    /// The field name; for an enum variant field `Variant.name` or `Variant.0`.
    pub field: String,
    /// The field's plain declared type with its plain generic arguments (wrappers, generics and non-path types are never recorded).
    pub ty: RetType,
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

// frob:ticket 01M44YQSZ3YEXRDW9RKER9HRA2
/// One attribute applied to a unit, kept for later vocabulary matching (`[MenuItem("x")]`).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct AttributeFact {
    /// The attribute type name as written, whitespace removed (`SerializeField`, `UnityEngine.Header`).
    pub name: String,
    /// The argument text between the parentheses, whitespace collapsed; empty when there are none.
    pub args: String,
    /// The attribute target (`field` in `[field: SerializeField]`), if one is written.
    pub target: Option<String>,
}

/// One declaring span of a partial type, with the preprocessor conditions it sits under.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnitSpan {
    /// Repo-relative path of the declaring file.
    pub path: String,
    /// Byte range of this part inside that file.
    #[serde(with = "range_serde")]
    pub span: TextRange,
    /// The conditions of this part (see [`UnitFacts::conditions`]).
    pub conditions: Vec<String>,
}

/// Language facts about one unit that the symbol record has no field for (C# today).
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct UnitFacts {
    /// The attributes applied to the unit, in source order.
    pub attributes: Vec<AttributeFact>,
    /// Preprocessor conditions the unit is declared under, outermost first: `UNITY_EDITOR` for the
    /// `#if` branch, `!(UNITY_EDITOR)` for its `#else`; both branches always yield units.
    pub conditions: Vec<String>,
    /// Base types and interfaces of a type unit, whitespace removed (`MonoBehaviour`, `IFoo<int>`).
    pub bases: Vec<String>,
    /// The modifier keywords written on the unit (`public`, `static`, `partial`).
    pub modifiers: Vec<String>,
    /// True for a `partial` type: the graph merges its parts into one unit.
    pub partial: bool,
    /// The declaring spans of a partial type, one per part in path order; empty for any other unit.
    pub spans: Vec<UnitSpan>,
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
    /// C# facts: attributes, conditions, base types, modifiers and partial spans.
    pub facts: UnitFacts,
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
    /// Struct fields with a concrete declared type, in source order.
    pub fields: Vec<FieldDecl>,
    /// Names of `Result`/`Option` type aliases here whose first parameter is not the Ok/Some type.
    pub opaque_aliases: Vec<String>,
    /// The `#[derive(..)]` traits of each struct and enum declared here.
    #[serde(default)]
    pub derives: Vec<DeriveDecl>,
}

// frob:ticket 01M44YQSZ3YEXRDW9RKER9HRA2
/// The unit key of a partial type: its symref segments without the `[dupN]` mark on the last one.
fn partial_key(symref: &Symref) -> Vec<String> {
    let mut segs = symref.segments().to_vec();
    if let Some(last) = segs.last_mut()
        && let Some(i) = last.rfind("[dup")
        && last.ends_with(']')
    {
        last.truncate(i);
    }
    segs
}

/// Digest of `parts` in order under a fixed domain, standing in for the digest of a merged unit.
fn merged_digest(parts: &[FacetDigest]) -> FacetDigest {
    let mut h = blake3::Hasher::new();
    h.update(b"gob-symbols/partial/1");
    for p in parts {
        h.update(p.as_bytes());
    }
    FacetDigest::from_bytes(*h.finalize().as_bytes())
}

/// Merges the parts of every `partial` type into one unit with several spans (D94).
///
/// `files` must be sorted by path. Parts are matched by namespace-qualified name across all
/// files (until the project model maps files to assemblies, two assemblies declaring the same
/// partial name merge); the first part in path order keeps its symref and record. Later parts
/// are removed, their members re-parented onto the kept unit, and the kept unit gains every
/// part's span, attributes and base types plus a digest over all parts.
pub(crate) fn merge_partials(files: &mut [FileSymbols]) {
    let mut kept: HashMap<Vec<String>, Symref> = HashMap::new();
    let mut canon_of: HashMap<Symref, Symref> = HashMap::new();
    let mut merged: HashMap<Symref, Symref> = HashMap::new();
    for f in files.iter() {
        for (s, e) in f.symbols.iter().zip(&f.extras) {
            if !e.facts.partial {
                continue;
            }
            let canon = kept
                .entry(partial_key(&s.symref))
                .or_insert_with(|| s.symref.clone());
            if *canon != s.symref {
                merged.insert(s.symref.clone(), canon.clone());
            }
            canon_of.insert(s.symref.clone(), canon.clone());
        }
    }
    if merged.is_empty() {
        return;
    }
    // Collect each part (kept first, then later parts in file order) before editing anything.
    let mut parts: HashMap<Symref, Vec<(SymbolRecord, UnitExtras)>> = HashMap::new();
    for f in files.iter() {
        for (s, e) in f.symbols.iter().zip(&f.extras) {
            if let Some(c) = canon_of.get(&s.symref) {
                parts
                    .entry(c.clone())
                    .or_default()
                    .push((s.clone(), e.clone()));
            }
        }
    }
    for f in files.iter_mut() {
        let path = f.path.clone();
        let mut i = 0;
        while i < f.symbols.len() {
            if merged.contains_key(&f.symbols[i].symref) {
                f.symbols.remove(i);
                f.extras.remove(i);
                continue;
            }
            if let Some(p) = f.symbols[i]
                .parent
                .as_ref()
                .and_then(|p| merged.get(p))
                .cloned()
            {
                f.symbols[i].parent = Some(p);
            }
            if let Some(all) = parts.get(&f.symbols[i].symref).filter(|a| a.len() > 1) {
                fold_parts(&mut f.symbols[i], &mut f.extras[i], all);
                tracing::debug!(
                    path = %path,
                    symref = %f.symbols[i].symref,
                    parts = all.len(),
                    "partial type parts merged"
                );
            }
            i += 1;
        }
    }
}

/// Folds `all` parts of one partial type into its kept `rec` and `extras`.
fn fold_parts(rec: &mut SymbolRecord, extras: &mut UnitExtras, all: &[(SymbolRecord, UnitExtras)]) {
    let mut spans = Vec::new();
    let mut attributes: Vec<AttributeFact> = Vec::new();
    let mut bases: Vec<String> = Vec::new();
    for (r, e) in all {
        spans.extend(e.facts.spans.iter().cloned());
        for a in &e.facts.attributes {
            if !attributes.contains(a) {
                attributes.push(a.clone());
            }
        }
        for b in &e.facts.bases {
            if !bases.contains(b) {
                bases.push(b.clone());
            }
        }
        for u in &e.unknown {
            if !extras.unknown.contains(u) {
                extras.unknown.push(u.clone());
            }
        }
        if r.visibility == Visibility::Public {
            rec.visibility = Visibility::Public;
        }
    }
    let of = |pick: fn(&Digests) -> FacetDigest| -> FacetDigest {
        merged_digest(
            &all.iter()
                .map(|(r, _)| pick(&r.digests))
                .collect::<Vec<_>>(),
        )
    };
    rec.digests = Digests {
        sig: of(|d| d.sig),
        body: of(|d| d.body),
        doc: of(|d| d.doc),
        attr: of(|d| d.attr),
        contract: of(|d| d.contract),
    };
    extras.facts.spans = spans;
    extras.facts.attributes = attributes;
    extras.facts.bases = bases;
}

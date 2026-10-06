//! The TypeScript and JavaScript adapter (fidelity F2): tree-sitter tree to a U term plus scope graph,
//! for `.ts`, `.tsx`, `.mts`, `.cts`, `.js`, `.jsx`, `.mjs` and `.cjs` (D96, language-engines.md
//! sections 2 and 3; code-model.md section 3).
//!
//! # Mapping (rho)
//!
//! - The file is a `unit(file, impl)`. Units, named like Python's (`path::Class.method`,
//!   `outer.inner`): `function` (declarations, and module-level `const f = () => ..`), `class`, `method`
//!   (class methods, constructors, accessors and `handle = () => ..` fields), `interface`, `type`, `enum`,
//!   `namespace` (one unit per dotted component), and `const` or `static` for other module-level
//!   declarators. An `export default` function or class without a name is the unit `default`.
//! - Every unit has children in groups: `attr("doc")` (the preceding `JSDoc` comment), one `attr` per
//!   decorator (also in the signature, G7), a `group` marked `ir.facet = "sig"` with the name, type
//!   parameters, parameters, return type and modifiers as tokens, and the body as one `group`. An
//!   interface, type alias or enum is all signature.
//! - Visibility: a declaration is `public` when it is exported (`export`, `export { a as b }`,
//!   `export default a`, `module.exports = ..`, `exports.x = a`), else `private`; a class member is
//!   `private` for `private` or `#name`, `crate` for `protected`, else `public`.
//! - Scoping is function-level (see [`binders`]); imports bind no names in the scope graph, they are
//!   recorded as use bindings so a call through an import is never taken for a local value. A call is
//!   `apply(call)` (`method` for `obj.m()`, `new` for `new C()`), identifiers in expression position
//!   are `ref`s, an arrow or function expression is `anon(function)` over its parameters.
//! - JSX lowers to the `gob_ir::markup` forms (see `fold/jsx.rs`): an element is `apply(element)` with a
//!   `lit(tag)` head (intrinsic) or a `ref` head (component, also a call edge of the unit using it), attributes
//!   are `markup.attribute` (value in the `const_value` forms, absent means `true`), spreads `markup.spread`
//!   (status May), a fragment, conditional or mapped child a `group`. The tag, kind, attribute names and line
//!   stay on the node ([`jsx_elements`]). A `style={{..}}` object adds a `region(css)` of `style.declaration`
//!   nodes (Known literals tokenised, computed values one `lit(unknown)`), and a `css` tagged template is a
//!   `region(css)` island. Call arguments, spreads, `&&` and `||` lower to the same forms; constants across files, imports and class-name
//!   joiners (`clsx`, `cn`) evaluate through [`ConstProject`] (`consteval.rs`, ~C2F4ZMQ).
//! - Test items: a `describe`, `it`, `test`, `test.describe` (with modifiers such as `only` or `skip`) call
//!   with a literal title and a function argument is marked on its `apply` node ([`test_items`]) when the
//!   name comes from vitest, `@jest/globals`, `@playwright/test`, `bun:test` or `node:test`, or the file is a
//!   test file ([`is_typescript_test_file`], framework `globals`).
//! - Not modelled, reported as a partial parse: `with` statements. Syntax errors are `hole(parse-error)`.
//!
//! # Imports and exports
//!
//! ESM `import`, `import x = require()`, `export .. from`, CJS `require` (bound by `const x =` or
//! destructuring) and dynamic `import()` become [`crate::ImportEdge`]s and [`crate::UseBinding`]s in the
//! wire form of `imports`. A static import and an unconditional top-level `require` are Must, a literal dynamic
//! `import("m")` or a `require` under a condition or inside a function is May, a computed specifier is Unknown
//! (the edge is kept, never dropped). The module graph (`graph/typescript.rs`) resolves relative
//! specifiers against the repository's files; bare specifiers (packages, tsconfig `paths` and workspace
//! packages, `#` imports) are Unknown until the project model (~C3DEAQX) answers them.
//!
//! The parse needs the file's path to choose the grammar, so [`Adapter::parse`] only keeps the source and
//! `fold` parses it (with the default [`ParseLimits`], which is what the pipeline passes).

// frob:ticket 01M43ARXMH7RJ63G8096KKJF80
// frob:ticket 01M47QKSBYX7YFQHV3VVGKB025
// frob:ticket 01M43ARXVD5PXP6ZBVFC2F4ZMQ

mod binders;
mod consteval;
mod fold;
pub(crate) mod imports;
mod style;

pub use consteval::{ConstProject, Evaluated, Origin, Unresolved};
use gob_ir::{Operator, Term, Universal};
use gob_languages::{Language, ParseLimits, grammar_identity};

use crate::adapter::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded,
    Precision,
};
use crate::pipeline::EXTRACTOR_VERSION;

/// The fidelity this adapter claims.
pub(crate) const FIDELITY: Fidelity = Fidelity::F2;

/// Node attribute: the tag of a JSX element as written (empty for a fragment).
pub(crate) const ATTR_JSX_TAG: &str = "jsx.tag";
/// Node attribute: `intrinsic`, `component`, `member` or `fragment`.
pub(crate) const ATTR_JSX_KIND: &str = "jsx.kind";
/// Node attribute: the attribute names of a JSX element, comma-separated, `...` for a spread.
pub(crate) const ATTR_JSX_ATTRS: &str = "jsx.attrs";
/// Node attribute: the one-based line of a JSX element.
pub(crate) const ATTR_JSX_LINE: &str = "jsx.line";
/// Node attribute: what a `group` or `region` of the markup lowering stands for (`fragment`, `conditional`,
/// `mapped`, `inline-style`, `css-in-js`); shared with the HTML adapter.
pub(crate) const ATTR_MARKUP_GROUP: &str = "markup.group";
/// Node attribute: `suite` or `case` on the `apply` of a test-runner call.
pub(crate) const ATTR_TEST_ROLE: &str = "test.role";
/// Node attribute: the literal title of a test-runner call.
pub(crate) const ATTR_TEST_TITLE: &str = "test.title";
/// Node attribute: `vitest`, `jest`, `playwright`, `bun`, `node` or `globals`.
pub(crate) const ATTR_TEST_FRAMEWORK: &str = "test.framework";
/// Node attribute: the one-based line of a test-runner call.
pub(crate) const ATTR_TEST_LINE: &str = "test.line";

/// File extensions (lowercase, no dot) the adapter claims.
pub(crate) const EXTENSIONS: &[&str] = &["ts", "tsx", "mts", "cts", "js", "jsx", "mjs", "cjs"];

/// The TypeScript and JavaScript adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct TypeScriptAdapter;

impl Adapter for TypeScriptAdapter {
    fn language(&self) -> &'static str {
        "typescript"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}+{}+{}+{}",
            grammar_identity(Language::TypeScript),
            grammar_identity(Language::Tsx),
            grammar_identity(Language::JavaScript),
            grammar_identity(Language::Jsx)
        )
    }

    fn fidelity(&self) -> Fidelity {
        FIDELITY
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
            .with(Capability::ResolveRef, Precision::Lexical)
            .with(Capability::ApplyTargets, Precision::ByNameInCrate)
            .with(Capability::Visibility, Precision::Keyword)
            .with(Capability::Imports, Precision::LexicalImports)
            .with(Capability::TestItems, Precision::Syntactic)
            .with(Capability::ProjectModel, Precision::Manifest)
    }

    fn parse(&self, text: &str, _limits: &ParseLimits) -> ConcreteTree {
        ConcreteTree::Source(text.into())
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Source(text) => fold::fold_source(text, input),
            ConcreteTree::Parsed(_) | ConcreteTree::Unparsed(_) | ConcreteTree::Leaf => {
                crate::fold::failed_file(
                    input,
                    "typescript",
                    gob_languages::UnresolvedReason::GrammarUnavailable,
                )
            }
        }
    }
}

/// True when `path` is a TypeScript or JavaScript source file (`ts`, `tsx`, `mts`, `cts`, `js`, `jsx`, `mjs`, `cjs`, any case).
pub fn is_typescript_path(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| EXTENSIONS.iter().any(|x| e.eq_ignore_ascii_case(x)))
}

/// True when `path` is a test file by the vitest, jest and playwright conventions.
///
/// `*.test.*` and `*.spec.*` files, anything under `__tests__`, `tests`, `test`, `e2e` or `__mocks__`,
/// and `*.setup.*` helpers.
pub fn is_typescript_test_file(path: &str) -> bool {
    if !is_typescript_path(path) {
        return false;
    }
    let mut parts: Vec<&str> = path.split('/').collect();
    let base = parts.pop().unwrap_or_default();
    let stem_marks = base
        .split('.')
        .skip(1)
        .any(|seg| matches!(seg, "test" | "spec" | "setup"));
    stem_marks
        || parts
            .iter()
            .any(|d| matches!(*d, "__tests__" | "tests" | "test" | "e2e" | "__mocks__"))
}

/// What a JSX tag names, as the folder read it from the syntax alone.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum JsxKind {
    /// A lowercase tag (`div`): a built-in element.
    Intrinsic,
    /// A capitalised identifier (`Button`): a component reference.
    Component,
    /// A dotted tag (`ui.Card`, `motion.div`): a reference through a namespace or object.
    Member,
    /// `<>..</>`.
    Fragment,
}

/// One JSX element of a file, for listings (`frob explore` style views).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JsxElement {
    /// The tag as written (empty for a fragment).
    pub tag: String,
    /// What the tag names.
    pub kind: JsxKind,
    /// Attribute names in source order; `...` is a spread, which may add any attribute.
    pub attributes: Vec<String>,
    /// One-based source line.
    pub line: u32,
}

fn attr_of<'t>(term: &'t Term, id: gob_ir::NodeId, key: &str) -> Option<&'t str> {
    term.node(id).attrs().get_str(key)
}

/// The byte offset where `id` starts in its source (0 for a node without a text location).
fn start_of(term: &Term, id: gob_ir::NodeId) -> u32 {
    match term.node(id).location() {
        gob_ir::Location::Text { range, .. } => u32::from(range.start()),
        _ => 0,
    }
}

fn int_attr(term: &Term, id: gob_ir::NodeId, key: &str) -> u32 {
    use gob_ir::AttrValue;
    term.node(id)
        .attrs()
        .iter()
        .find(|(k, _)| *k == key)
        .and_then(|(_, v)| match v {
            AttrValue::Int(i) => u32::try_from(*i).ok(),
            _ => None,
        })
        .unwrap_or(0)
}

/// Every JSX element in `term`, in document order (the `markup` seam: lowering is ~VGKB025).
pub fn jsx_elements(term: &Term) -> Vec<JsxElement> {
    let mut out: Vec<(u32, JsxElement)> = Vec::new();
    for id in term.ids() {
        let Some(kind) = attr_of(term, id, ATTR_JSX_KIND) else {
            continue;
        };
        let kind = match kind {
            "component" => JsxKind::Component,
            "member" => JsxKind::Member,
            "fragment" => JsxKind::Fragment,
            _ => JsxKind::Intrinsic,
        };
        out.push((
            start_of(term, id),
            JsxElement {
                tag: attr_of(term, id, ATTR_JSX_TAG)
                    .unwrap_or_default()
                    .to_owned(),
                kind,
                attributes: attr_of(term, id, ATTR_JSX_ATTRS)
                    .unwrap_or_default()
                    .split(',')
                    .filter(|s| !s.is_empty())
                    .map(str::to_owned)
                    .collect(),
                line: int_attr(term, id, ATTR_JSX_LINE),
            },
        ));
    }
    out.sort_by_key(|(start, _)| *start);
    out.into_iter().map(|(_, e)| e).collect()
}

/// Whether a test item groups others or is one test.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TestRole {
    /// `describe`, `suite`, `test.describe`.
    Suite,
    /// `it`, `test`.
    Case,
}

/// One test-runner call of a file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TestItem {
    /// Suite or case.
    pub role: TestRole,
    /// The literal title.
    pub title: String,
    /// `vitest`, `jest`, `playwright`, `bun`, `node`, or `globals` when the name is not imported from a runner.
    pub framework: String,
    /// One-based source line.
    pub line: u32,
}

/// Every test-runner call in `term`, in document order (test items answer, syntactic precision).
pub fn test_items(term: &Term) -> Vec<TestItem> {
    let mut out: Vec<(u32, TestItem)> = Vec::new();
    for id in term.ids() {
        if !matches!(
            term.operator(id),
            Operator::Universal(Universal::Apply { .. })
        ) {
            continue;
        }
        let Some(role) = attr_of(term, id, ATTR_TEST_ROLE) else {
            continue;
        };
        out.push((
            start_of(term, id),
            TestItem {
                role: if role == "suite" {
                    TestRole::Suite
                } else {
                    TestRole::Case
                },
                title: attr_of(term, id, ATTR_TEST_TITLE)
                    .unwrap_or_default()
                    .to_owned(),
                framework: attr_of(term, id, ATTR_TEST_FRAMEWORK)
                    .unwrap_or_default()
                    .to_owned(),
                line: int_attr(term, id, ATTR_TEST_LINE),
            },
        ));
    }
    out.sort_by_key(|(start, _)| *start);
    out.into_iter().map(|(_, t)| t).collect()
}

# frob.lang -- uniform tree-sitter parsing

One sentence: a single `parse_file`/`ParsedFile` contract over five
tree-sitter grammars (python, typescript/tsx, rust, c, cpp), so that
`frob.graph` never has to know which language a source file is in.

## Public API

```python
def parse_file(path: Path) -> Result[ParsedFile, LangError]
def supported_languages() -> frozenset[str]   # {"python","typescript","rust","c","cpp"}
```

Dispatch is by file extension:

| Extension | Grammar | `ParsedFile.language` |
|---|---|---|
| `.py` | python | python |
| `.ts` | typescript | typescript |
| `.tsx` | tsx | typescript |
| `.rs` | rust | rust |
| `.c`, `.h` | c | c |
| `.cpp`, `.hpp`, `.cc`, `.hh` | cpp | cpp |

A file with tree-sitter recoverable syntax errors still yields the symbols
tree-sitter could parse around the error (`ParseFailed` is reserved for a
totally unusable tree -- in practice, only when the root node has an error
and no children).

## The token contract

`sig_tokens` and `body_tokens` are the leaf-node text of a symbol's
tree-sitter subtree, in order, with comment-typed leaves and (for
`body_tokens`) the docstring/doc-comment statement excluded. Tree-sitter
never represents whitespace as a node, so this sequence is formatting-
insensitive by construction -- no per-language pretty-printer is needed.

- `sig_tokens`: leaves of the declaration node (name, parameters, types,
  return type, decorators/attributes, visibility keywords), with the body
  subtree's byte range excluded.
- `body_tokens`: leaves of the body subtree, with comment nodes and the
  docstring/doc-comment statement's byte range excluded.
- `doc_text`: python's own docstring (first body statement, whether a bare
  `string` node or an `expression_statement` wrapping one, depending on
  grammar version), or the contiguous leading comment block for the other
  four languages (`///`, `/** */`, `//`, `/* */`), whitespace-collapsed via
  `" ".join(text.split())`.

Verified invariants (see `tests/test_lang.py::TestFormattingInsensitivity`):
reformatting (whitespace/indentation only) changes neither `sig_tokens` nor
`body_tokens`; renaming a parameter changes `sig_tokens` only (unless the
body also references the old name); editing the body changes `body_tokens`
only; editing the docstring changes `doc_text` only.

**Deviation from a fully faithful "declaration vs body" split**: for
`CLASS`-kind symbols in rust/typescript/c/cpp, `body_tokens` is always
`()`. A struct's field list / an impl's method list is not a single
executable "body" the way a function's is -- and every method nested
inside is already extracted as its own `METHOD` symbol with its own
`body_tokens`. Re-deriving a synthetic class-body-minus-methods token
stream for four different grammars was judged not worth the complexity for
Phase 1; python classes are the one case with an addressable `block` body,
so python's `CLASS.body_tokens` does include class-level statements (with
nested `def`/`class` subtrees excluded).

Likewise, `CONST` and `TYPE` symbols have no separate body: `sig_tokens` is
the whole declaration and `body_tokens` is always `()`.

## Symbol kinds

| Kind | Meaning |
|---|---|
| `FUNCTION` | top-level function |
| `METHOD` | function nested in a class/impl/trait/struct(C++ only)/mod-impl context |
| `CLASS` | python `class`, rust `struct`/`trait`, ts `class`, c/cpp `struct`/`class` (with a body) |
| `CONST` | module/file-scope constant: python `UPPER_CASE = ...`, rust `const`/`static`, ts `export const`, c/cpp file-scope `const`-qualified declaration |
| `TYPE` | type aliases, typedefs, interfaces, enums: python `type X = ...` is not yet handled (deferred), rust `type`/`enum`, ts `interface`/`type`/`enum`, c `typedef`, cpp `typedef`/`using`/`enum` |

## Publicness per language

| Language | Rule |
|---|---|
| python | `not name.startswith("_")` |
| rust | presence of a `pub` (`visibility_modifier`) keyword on the item, **or** a PyO3 export attribute (`#[pyfunction]`/`#[pymodule]`/`#[pyclass]`/`#[pymethods]`) -- a native-extension export is the crate's real public surface even without `pub`, and every method in a `#[pymethods]` impl is exported |
| typescript | wrapped in an `export_statement` (`export`/`export default`); class members without an explicit `private`/`protected` `accessibility_modifier` default to public |
| c | file-scope symbol without a `static` storage-class specifier |
| cpp | file-scope symbol without `static`; class members are public unless the nearest preceding `access_specifier` in the enclosing `field_declaration_list` is `private`/`protected` (default access is `private` for `class`, `public` for `struct`, matching the language) |

## Comment extraction and binding

Every comment-typed leaf node in the tree becomes one `RawComment`, with
its delimiters stripped (`//`, `///`, `/* */`, `/** */`, `#`, and a leading
`*` on continuation lines of a block comment).

- `enclosing`: the qualname of the narrowest-span symbol whose
  `(start_line, end_line)` fully contains the comment's span, or `None`.
- `following`: the qualname of the symbol with the earliest start line
  strictly after the comment's end line and within 2 lines of it, or
  `None`.

Both are computed independently -- a comment can have `enclosing=None` and
still have a `following` (a comment directly above a top-level function),
or vice versa (a comment deep inside a function body with no symbol
starting nearby).

`COMMENT_TYPES` is the per-language table of tree-sitter comment node type
names the walker treats as comment-typed leaves.

## Per-language walker notes

Each language has its own recursive-descent walker in `_extract.py`
(`_walk_python`, `_walk_typescript`, `_walk_rust`, `_walk_c_family`
shared by c/cpp) built on the shared `_common.py` primitives
(`leaf_tokens`, `leading_doc_comment`, `strip_comment_delims`, `span_of`).
Notable per-language handling:

- **python**: `decorated_definition` is unwrapped to find the underlying
  `function_definition`/`class_definition`; the decorator tokens stay in
  `sig_tokens` because the unwrapped span still starts at the
  `decorated_definition` node. Nested closures inside function bodies are
  not walked for symbols (only module- and class-level defs are).
- **typescript**: `export_statement` is peeled off to get at the inner
  declaration and to determine `exported`; `.tsx` files use the `tsx`
  grammar (for JSX syntax) but are labeled `language="typescript"`.
- **rust**: `impl_item`/`trait_item`/`mod_item` are transparent qualname
  containers -- they do not themselves produce a symbol, but their
  `Self`-type or trait/mod name is pushed onto the qualname stack so
  nested `function_item`s become `METHOD`s named `Type.method`.
- **c/cpp**: the innermost identifier of a (possibly pointer-wrapping)
  `function_declarator` is found via `_find_declarator_name`, which walks
  the `declarator` field chain. `namespace_definition` is transparent like
  rust's `mod_item`.

## Data models

<!-- frob:describes src/frob/lang/_models.py::SymbolKind -->
<!-- frob:describes src/frob/lang/_models.py::RawSymbol -->
<!-- frob:describes src/frob/lang/_models.py::RawComment -->
<!-- frob:describes src/frob/lang/_models.py::ParsedFile -->

The value shapes `frob.lang` hands to `frob.graph`, all frozen so a
`ParsedFile` compares by value for the incremental-rebuild cache.

- `SymbolKind` -- the five extraction buckets every grammar collapses into
  (`FUNCTION`, `METHOD`, `CLASS`, `CONST`, `TYPE`).
- `RawSymbol` -- one extracted declaration: `qualname`, `kind`, `public`,
  `span`, `sig_tokens`, `body_tokens`, `doc_text`.
- `RawComment` -- one extracted comment with its `enclosing`/`following`
  symbol bindings resolved.
- `ParsedFile` -- the whole-file result: `symbols`, `comments`, and a
  `content_hash`.

## Extraction API

<!-- frob:describes src/frob/lang/_extract.py::extract -->
<!-- frob:describes src/frob/lang/_extract.py::extract_imports -->
<!-- frob:describes src/frob/lang/_extract.py::iter_identifiers -->

The per-language walkers behind `parse_file`, also usable directly on an
already-parsed tree.

- `extract(tree, source, language)` -- symbols then comments (in that order,
  so comments can bind to symbol spans).
- `extract_imports(tree, language)` -- raw import/include specifiers, empty
  for a language with no registered import walker.
- `iter_identifiers(tree, language)` -- `(name, 1-based line)` for every
  identifier-like leaf, empty for an unsupported language.

## Primitives

<!-- frob:describes src/frob/lang/_common.py::collapse_ws -->
<!-- frob:describes src/frob/lang/_common.py::leaf_tokens -->
<!-- frob:describes src/frob/lang/_common.py::strip_comment_delims -->
<!-- frob:describes src/frob/lang/_common.py::leading_doc_comment -->
<!-- frob:describes src/frob/lang/_common.py::span_of -->
<!-- frob:describes src/frob/lang/_common.py::child_text -->
<!-- frob:describes src/frob/lang/_common.py::export_tree -->
<!-- frob:describes src/frob/lang/_common.py::flatten_tree -->
<!-- frob:describes src/frob/lang/_common.py::iter_cpp_functions -->

The shared, language-agnostic tree-sitter helpers the five walkers are
built on -- kept in one place so the leaf-token/comment-delimiter/span
logic is never re-derived per grammar.

- `collapse_ws` -- whitespace-collapse doc text so reflow never perturbs it.
- `leaf_tokens` -- ordered leaf text under a node, comments and byte-range
  exclusions skipped (the sig/body token contract).
- `strip_comment_delims` -- strip `//`, `///`, `/* */`, `/** */`, `#`, and
  continuation `*` from one comment.
- `leading_doc_comment` -- the contiguous comment block directly above a
  node, as doc text.
- `span_of` -- 1-based inclusive `(start_line, end_line)`, folding the
  trailing-newline lexer artifact back onto the content line.
- `child_text` -- decode a node's text, `""` if absent.
- `export_tree` -- a comment-stripped `TreeNode` snapshot of a subtree (for
  R4's tree-edit kernel), truncated past a node budget rather than dropped.
- `flatten_tree` -- `(labels, parents)` preorder arrays in the shape
  `frob_core.apted_similarity` expects.
- `iter_cpp_functions` -- `(node, qualified_name)` for every C/C++ function
  under a root, shared by `frob.arch` and `frob.dup`.

## Error types

<!-- frob:describes src/frob/lang/__init__.py::LangError -->

```python
class LangError(ErrorSet):
    UnsupportedLanguage = "File extension has no registered grammar"
    ParseFailed         = "tree-sitter could not produce a usable tree"
    IoFailed            = "File could not be read"
```

## Dependencies

`tree-sitter`, `tree-sitter-language-pack` (grammar loading), `pydantic`
(frozen models), `typani` (`Result`/`ErrorSet`).

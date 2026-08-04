# frob.lang -- uniform tree-sitter parsing

One sentence: a single `parse_file`/`ParsedFile` contract over seven
tree-sitter grammars (python, typescript/tsx, rust, c, cpp, kotlin) plus
`.strata` (routed through strata-core, no tree-sitter grammar), so that
`frob.graph` never has to know which language a source file is in.

## Public API

```python
def parse_file(path: Path) -> Result[ParsedFile, LangError]
def supported_languages() -> frozenset[str]   # {"python","typescript","rust","c","cpp","kotlin","strata"}
```

Dispatch is by file extension:

| Extension | Grammar | `ParsedFile.language` |
|---|---|---|
| `.py` | python | python |
| `.ts` | typescript | typescript |
| `.tsx` | tsx | typescript |
| `.rs` | rust | rust |
| `.c`, `.h` | c | c |
| `.cpp`, `.hpp`, `.cc`, `.hh`, `.cxx` | cpp | cpp |
| `.kt`, `.kts` | kotlin | kotlin |
| `.strata` | (strata-core, no tree-sitter grammar) | strata |

A file with tree-sitter recoverable syntax errors still yields the symbols
tree-sitter could parse around the error (`ParseFailed` is reserved for a
totally unusable tree -- in practice, only when the root node has an error
and no children).

<!-- frob:invariant INV-015 -->

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
| kotlin | absence of a `private`/`protected`/`internal` visibility modifier (kotlin's own default visibility is `public`) |

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

Each language has its own recursive-descent walker (`_walk_python.py`,
`_walk_typescript.py`, `_walk_rust.py`, `_walk_c.py`'s `_walk_c_family`
shared by c/cpp, `_walk_kotlin.py`, `_walk_strata.py`) built on the shared
`_common.py` primitives (`_leaf_tokens`, `_leading_doc_comment`,
`_strip_comment_delims`, `_span_of`).
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

<!-- frob:describes frob-core/src/extract.rs::extract_tree_python -->

T-1220 (EPIC B candidate #1's first landed portion): `frob_core.
extract_tree_python(source: bytes) -> (comment_spans, docstring_spans,
identifiers, tokens)` is a PYTHON-ONLY native kernel computing this same
surface's four building blocks (comment spans, docstring spans, an
identifier `(name, line)` stream, and the whole-file leaf-token stream)
directly in Rust via `tree-sitter`/`tree-sitter-python`, rather than the
per-node Python recursion `_extract.py`/`_walk_python.py`/`frob.vet.
_capability_core` each still perform today. Golden-tested byte/line-
identical against the existing Python extraction path across this repo's
own `src/**/*.py` + `tests/**/*.py` corpus (917 files, 0 mismatches) --
see `frob-core/src/extract.rs`'s module docstring for the one documented,
justified delta (the three unwrapped/bare-string docstring-query patterns
are structurally impossible against the `tree-sitter-python` 0.25.0 Rust
crate's newer grammar generation, vs. `frob.lang`'s own
`tree_sitter_language_pack`-bundled older grammar where they can occur;
dropping them changes no observed span since the newer grammar has
already wrapped every such string). No consumer is rewired to this kernel
yet -- `perf`/`clones`/`deprecated`/`dead_symbols`/`opaque`/`sys` and the
remaining per-language (cpp/typescript) walkers remain future work under
this same ticket/its children.

<!-- frob:describes frob-core/src/extract.rs::extract_tree_rust -->

T-1220 (second landed portion): `frob_core.extract_tree_rust(source:
bytes) -> (comment_spans, identifiers, tokens)` is the rust-language
companion kernel, via `tree-sitter`/`tree-sitter-rust` (crates.io
0.24.2). A 3-tuple, not the python kernel's 4-tuple -- rust has no
python-style string-literal docstring facet, so there is no fourth
collection to compute; rust's `///`/`/** */` doc comments are
`line_comment`/`block_comment` leaves already, so they show up in
`comment_spans`, the same leaf kinds `frob.lang._walk_rust.
_leading_doc_comment` reads. This portion also extended `frob.lang.
_extract._IDENTIFIER_TYPES` with a `"rust"` entry (`identifier`,
`type_identifier`, `field_identifier`) -- rust had no identifier-walk
counterpart before this ticket, so the golden-parity comparison this
kernel is tested against is a new capability on the Python side too, not
a pre-existing one. One implementation note the golden-parity check
surfaced and fixed: unlike python's `comment` node, this grammar
generation's `line_comment`/`block_comment` nodes are never leaves
(`child_count() == 0`) -- each carries its own `//`/`/*` delimiter child
-- so the kernel's comment-span collector performs a type-match top-down
walk (mirroring `frob.lang._extract._collect_comment_nodes`) rather than
reusing the leaf-only walk `identifiers`/`tokens` share. Golden-tested
against this repo's own rust source tree (`frob-core/**/*.rs`,
`strata-core/**/*.rs`, plus fixture `.rs` files, 12 files, 0 mismatches
ad hoc; `tests/unit/test_extract_native.py::TestExtractTreeRustParity`
carries the committed regression lock). No consumer is rewired to this
kernel yet, same as the python kernel above -- cpp/typescript walkers and
the consumer rewiring remain future work.

## Primitives

<!-- frob:describes src/frob/lang/_common.py::_collapse_ws -->
<!-- frob:describes src/frob/lang/_common.py::_leaf_tokens -->
<!-- frob:describes src/frob/lang/_common.py::_strip_comment_delims -->
<!-- frob:describes src/frob/lang/_common.py::_leading_doc_comment -->
<!-- frob:describes src/frob/lang/_common.py::_span_of -->
<!-- frob:describes src/frob/lang/_common.py::_child_text -->
<!-- frob:describes src/frob/lang/_common.py::export_tree -->
<!-- frob:describes src/frob/lang/_common.py::flatten_tree -->
<!-- frob:describes src/frob/lang/_common.py::_iter_cpp_functions -->

The shared, language-agnostic tree-sitter helpers the seven walkers are
built on -- kept in one place so the leaf-token/comment-delimiter/span
logic is never re-derived per grammar.

- `_collapse_ws` -- whitespace-collapse doc text so reflow never perturbs it.
- `_leaf_tokens` -- ordered leaf text under a node, comments and byte-range
  exclusions skipped (the sig/body token contract).
- `_strip_comment_delims` -- strip `//`, `///`, `/* */`, `/** */`, `#`, and
  continuation `*` from one comment.
- `_leading_doc_comment` -- the contiguous comment block directly above a
  node, as doc text.
- `_span_of` -- 1-based inclusive `(start_line, end_line)`, folding the
  trailing-newline lexer artifact back onto the content line.
- `_child_text` -- decode a node's text, `""` if absent.
- `export_tree` -- a comment-stripped `TreeNode` snapshot of a subtree (for
  R4's tree-edit kernel), truncated past a node budget rather than dropped.
  Each node's `field` (T-0495) is its own tree-sitter field name as seen
  from its parent (`Node.field_name_for_child`), or `None` if it has
  none -- lets a consumer (`frob.dup._template`'s type-hole
  classification, T-0287) distinguish sibling positions some grammars
  (rust/c/cpp) mark only by field name, never by a wrapping node label.
- `flatten_tree` -- `(labels, parents)` preorder arrays in the shape
  `frob_core.apted_similarity` expects.
- `_iter_cpp_functions` -- `(node, qualified_name)` for every C/C++ function
  under a root, shared by `frob.arch` and `frob.dup`.

## Error types

<!-- frob:describes src/frob/lang/__init__.py::LangError -->

```python
class LangError(ErrorSet):
    UnsupportedLanguage      = "File extension has no registered grammar"
    ParseFailed              = "tree-sitter could not produce a usable tree"
    IoFailed                 = "File could not be read"
    NativeParserUnavailable  = "strata-core native extension unavailable in this install"
    FileTooLarge             = "File exceeds the max parseable size"
    ParseTimedOut            = "Parse did not finish inside the wall-clock budget"
```

`NativeParserUnavailable` (T-0133) is `.strata`-only: it is what `parse_file`
returns instead of `ParseFailed` when the `strata_core` maturin extension is
not installed (a bare `uv tool install frob`, before `make install-tool` --
see docs/guides/install.md). `.strata` stays a first-class listed extension
in `supported_extensions()` either way -- the graph still sees the files
exist -- but each one degrades to this typed `Err` rather than crashing the
process (the T-0077 regression this ticket fixed) or logging like a real
syntax error. Consumers (`frob.graph._process_source_file`) log this case at
debug, not warning, to avoid one warning line per `.strata` file per build in
every natives-less install.

<!-- frob:describes src/frob/lang/_walk_strata.py::NATIVE_UNAVAILABLE_MESSAGE -->

`frob.lang._walk_strata.NATIVE_UNAVAILABLE_MESSAGE` is the exact `Err`
message string `walk_strata` returns for this case; `frob.lang.parse_file`
matches on it to translate to `LangError.NativeParserUnavailable` rather than
the generic `ParseFailed` a real strata syntax rejection gets.

## Size cap and parse timeout (T-0893)

<!-- frob:describes src/frob/lang/__init__.py::_check_size_cap -->
<!-- frob:describes src/frob/lang/__init__.py::_run_parse_with_timeout -->

`frob.lang` visits files from a caller-supplied tree that may be an
untrusted, adopter-repo checkout, not just this repo's own source -- a
single oversized or pathologically-structured file must not be able to DoS
`frob check`. Both `_parse` (tree-sitter) and `_parse_strata_file`
(strata-core) apply two guards, in this order, before the actual parse
call:

1. **Size cap** (`_check_size_cap`, `_MAX_PARSE_FILE_BYTES = 8 MiB`):
   checked against `Path.stat().st_size` BEFORE `read_bytes()`, so an
   oversized file is never even fully read into memory. A file over the
   cap returns `Err(LangError.FileTooLarge)`.
2. **Parse timeout** (`_run_parse_with_timeout`,
   `_PARSE_TIMEOUT_SECONDS = 10.0`): the tree-sitter/strata-core parse call
   runs on a single-use daemon-pool thread; if it has not finished within
   the budget, the wrapper returns `Err(LangError.ParseTimedOut)`
   immediately rather than blocking the caller. Neither tree-sitter nor
   strata-core expose a cancellation hook, so the worker thread itself is
   abandoned (never joined or killed) -- the timeout bounds how long the
   CALLER waits, not how long the runaway parse actually keeps running in
   the background.

Both guards log a WARNING naming the file and the exact limit hit -- never
a silent skip (the T-0897 silent-drop class this exists to avoid). Both
error variants flow through the same path every other `LangError` does:
`frob.graph._process_source_file` turns any `Err` from `parse_file` into a
`ParseFailure` (`file`, `reason=str(err)`), which
`frob.gates._parse_failures.parse_failure_gate` (PARSE001) reports as an
ERROR-tier `frob check` violation -- so a skipped file is visible both as a
log line and as a gate finding, not just one or the other.

## Parse cache

<!-- frob:describes src/frob/lang/__init__.py::reset_parse_cache -->
<!-- frob:describes src/frob/lang/__init__.py::parse_cache_stats -->
<!-- frob:describes src/frob/lang/__init__.py::partial_parse_files -->

T-0414: `_parse` (the sole read+tree-sitter-parse chokepoint every public
entry point in this module funnels through -- `parse_file`,
`extract_imports`, `iter_identifiers`, `raw_tree`, `symbol_tree`) memoizes
its result in a process-lifetime, thread-safe dict keyed on
`(path, sha256(content))`. Before this cache, one `frob check` invocation
independently re-read and re-parsed each source file once per stage that
touched it (arch, vet, dup's R4 rung), 2-6x redundant tree-sitter parses
per file for a 213-file tree (docs/audits/perf.md H1/H4/H5).

Keying is content-hash-based, never mtime/size alone: a changed file
always misses and reparses; an unchanged file's tree is shared across
every stage/thread that asks for it in the same process, no matter how far
apart in the call graph. `frob.check._run_check_with_skips` calls
`reset_parse_cache()` once at the top of every `frob check` invocation so
`parse_cache_stats()`'s hit/miss counters reflect a single run --
correctness never depends on this reset (a stale entry can never be
returned for changed content either way), it only bounds memory and keeps
the anti-regression instrument (a test asserting each distinct file is
parsed, i.e. missed, at most once per invocation) meaningful.

```python
def reset_parse_cache() -> None
def parse_cache_stats() -> tuple[int, int]   # (hits, misses)
def partial_parse_files() -> tuple[str, ...]
```

T-0404 finding 9 / T-0905: `_parse` can also SALVAGE a tree-sitter tree
around a syntax error (`has_error=True` but the grammar still recovers
usable top-level structure) rather than failing outright -- treating that
as a hard `Err` would blank out doc/coverage checking for the file's
entire content over one typo, so `_parse` keeps the salvaged tree, logs a
WARNING (`_warn_if_partial_tree`), and records the file's display path
into `partial_parse_files()`. Every symbol after the error region is
silently absent from that tree, so `partial_parse_files()` is the only
structured, queryable signal of the loss. `frob.gates._parse_failures.
parse_failure_gate` (docs/modules/gates.md#rule-catalog, PARSE002, T-0905)
reads this accessor directly and turns each entry into an ERROR-tier
`frob check` violation, symmetric with PARSE001's hard-failure handling --
before T-0905, this accessor had zero consumers and the loss was visible
only to a WARNING-level log line.

## Dependencies

`tree-sitter`, `tree-sitter-language-pack` (grammar loading), `pydantic`
(frozen models), `typani` (`Result`/`ErrorSet`).

```python
GRAMMAR_FINGERPRINT_PACKAGES: frozenset[str]  # {"tree-sitter", "tree-sitter-language-pack"}
```

T-0433 (G6): the single source of truth for which installed distributions'
VERSIONS can change parse output for every tree-sitter grammar this module
supports -- `frob.graph.cache._compute_fingerprint` derives its cache-
invalidation fingerprint from this set (plus its own non-language packages,
`frob` and `strata-core`) instead of hand-copying a tuple. Extend this set
if a future grammar is ever loaded through some OTHER package (bypassing
`tree_sitter_language_pack`); every grammar loaded through the language
pack needs no update here at all.

## Language support contract

T-0405: `frob.lang._support` gives each registered language ONE typed
`LanguageSupport` record, enumerating every facet frob needs from a
language beyond raw grammar/extraction -- capability (`frob.vet`),
duplicate-detection (`frob.dup`), structural arch checks (`frob.arch`),
and DOC004 fenced-code-block doc-drift (`frob.gates._docblocks`). This
does not re-implement any of those registries; it derives a snapshot from
each one's live state, so this module is always checking today's reality.
Which languages are registered here at all is itself a standing decision,
not an open door: see `docs/design/language-adapter-tier-decision.md` for
the T-0691 call on the next tier (Go/Java/C#) and its reopen criterion.

```python
FACETS: tuple[str, ...]  # ("grammar", "capability", "dup", "arch", "docblock")

class FacetState(StrEnum):
    IMPLEMENTED
    NOT_APPLICABLE
    KNOWN_GAP

class FacetStatus(BaseModel):
    state: FacetState
    detail: str  # required non-empty for NOT_APPLICABLE/KNOWN_GAP

class LanguageSupport(BaseModel):
    language: str
    facets: dict[str, FacetStatus]

def derive_language_registry() -> dict[str, LanguageSupport]
def conformance_violations(registry: dict[str, LanguageSupport]) -> tuple[str, ...]
```

Every `(language, facet)` cell is accounted for one of three ways:
`IMPLEMENTED` (a real code path exists), `NOT_APPLICABLE` with a reason
(the facet genuinely does not apply -- e.g. `.strata` has no
clone-detection use case), or `KNOWN_GAP` with a reason naming the
tracking ticket (a real, acknowledged hole -- e.g. `frob.arch` has no
typescript/rust dispatch branch yet, tracked by T-0329). A cell entirely
ABSENT from `LanguageSupport.facets`, or a `NOT_APPLICABLE`/`KNOWN_GAP`
cell with a blank `detail`, is what `conformance_violations` fails on --
the unaccounted-for hole this whole contract exists to make loud (the
PyO3-publicness incident class: a language shipped with one facet quietly
unimplemented).

`frob.gates._lang_conformance.lang_conformance_gate` wires this into
`frob check` as LANG001 (ERROR severity, on by default) -- a fixture
language registered with a missing facet fails the gate by name; a fully
registered language (every facet implemented, or reasoned
not-applicable/known-gap) passes cleanly. `frob`'s own registry is clean
today: every gap the T-0405 survey found (arch's typescript/rust/c
branches, DOC004's c/cpp fenced-code bucket) is an explicit `KNOWN_GAP`
naming its tracking ticket, not a silent hole.

### Per-project conformance (LANG002/LANG003, T-0406)

LANG001 only ever checks languages `frob.lang` has ALREADY registered a
grammar for -- it says nothing about a downstream repo that contains a
language frob has NO registration for at all. `frob.gates._lang_
conformance.project_lang_conformance_gate(repo_root, queue)` closes that:
wired into `frob check` on by default in EVERY frob-enabled repo (not
just this one), it scans the repo's own tracked file tree.

```python
def project_lang_conformance_gate(repo_root: Path, queue: TicketQueue) -> tuple[Violation, ...]
```

- **LANG002** (ERROR, always): a tracked file matching a well-known
  candidate-language extension frob has zero grammar registration for at
  all (Kotlin/Swift/Go/Java/Ruby/C#) -- zero capability/dup/arch/doc-drift
  coverage for that file, and nothing said so before this gate.
- **LANG003**: a registered language's `KNOWN_GAP`/`NOT_APPLICABLE` facet
  cell whose language is actually PRESENT in this repo's tree.
  `NOT_APPLICABLE` never needs a ticket (the facet genuinely does not
  apply). A `KNOWN_GAP` cell whose `detail` names a real, currently open
  ticket is WARN (an honestly tracked gap, loud but not a build-breaker).
  A `KNOWN_GAP` cell whose ticket reference does not verify (missing,
  unparseable, or already closed/dropped -- the same anti-lie check
  `frob.gates._registry_exhaustiveness` performs for `handled_by`/
  `deferred`) escalates to ERROR: a claimed gap that does not actually
  check out is unsound coverage pretending to be tracked coverage.

Acceptance (T-0406): a synthetic repo containing only a `.kt` file reds
LANG002 by name; a synthetic repo containing only python passes cleanly;
a synthetic repo containing rust (arch is `KNOWN_GAP`, T-0329) warns
while T-0329 stays open and errors the moment it is marked done/dropped
without the gap actually being closed.

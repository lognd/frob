# Language grammar handlers

<!-- frob:describes src/frob/lang/_extract.py::extract -->

## What it is and where it lives

`frob.lang` parses five languages into a shared `RawSymbol`/comment model
that every other module (graph, gates, dup, vet, testing) builds on top
of. The dispatch table is `_WALKERS` in `src/frob/lang/_extract.py`, keyed
by the tree-sitter language name and mapping to a `_walk_<lang>` function:
`_walk_c` (also used for C++ and TSX via aliasing, see `_walk_cpp`/
`_walk_tsx` wrappers), plus dedicated walker modules
`src/frob/lang/_walk_python.py`, `_walk_rust.py`, `_walk_strata.py`,
`_walk_typescript.py`. `extract()` looks up `_WALKERS[language]` and walks
the tree-sitter root node into a `tuple[RawSymbol, ...]`.

## Add-an-entry recipe (new language)

1. Add the tree-sitter grammar dependency for the new language (a
   `tree-sitter-<lang>` package/crate).
2. Write `_walk_<lang>.py` (or a function in `_extract.py` for a small
   grammar, following the `_walk_c`/`_walk_cpp`/`_walk_tsx` pattern): walk
   the parse tree, emit `RawSymbol` per top-level definable (function,
   class, const, type), matching the fields every other walker already
   populates (name, kind, span, visibility).
3. Add the new language's entry to `_WALKERS`.
4. Add comment-delimiter awareness: `frob.graph.dsl` parsing assumes
   `_extract_comments` has already stripped `#`/`//`/`/* */` delimiters
   per-language before `dsl.py` ever sees directive text (comment DSL
   directives guide) -- confirm the new language's comment syntax is
   handled in the shared comment-extraction path, not just symbol walking.
5. Add fixture files under `tests/fixtures/lang/<new-lang>/` and unit
   tests asserting symbol extraction, comment-directive extraction, and
   import extraction all round-trip correctly.
6. Wire the new language into `frob.testing`'s runner registry (see
   `docs/guides/extending/test-runner-entries.md`) if it needs its own
   `[[test.runner]]` support, and into `frob.dup`/`frob.vet` capability
   scanning if those should cover the new language too (separate
   registries, see `docs/guides/extending/dup-detector-registry.md` and
   `docs/guides/extending/capability-registry.md`).

## Drift-locks that fire

- No `frob check` gate enforces "every tree-sitter grammar dependency has
  a `_WALKERS` entry" -- a language added to `pyproject.toml`/`Cargo.toml`
  with no walker is simply never parsed; files in that language are
  invisible to the obligation graph (no symbols, no directives, silent
  omission at the `frob.lang` layer, not a loud failure).
- **TEST00x** applies normally to the new public `_walk_<lang>` function.
- Adding a language to `_WALKERS` without adding it to `frob.dup`'s
  per-language detector coverage or `frob.vet`'s capability matrix leaves
  those registries' own "every language has coverage or an excuse"
  discipline (see `docs/modules/vet.md#coverage-matrix`,
  `docs/guides/extending/capability-registry.md`) unsatisfied for the new
  language -- those ARE gated (capability matrix cells must be patterned
  or excused), so a new language surfaces there even though `_WALKERS`
  itself has no gate.

## Worked example

`_walk_strata.py` is the newest walker (added for `.strata` design files
to participate in the same obligation graph as source code -- a `.strata`
file's `Node`/`Flow`/`Boundary` declarations get `RawSymbol` entries so
`frob:doc`/`frob:ticket` directives can anchor to them exactly like a
Python function). It follows the same shape as `_walk_python.py`: walk
top-level declarations, emit one `RawSymbol` per construct, delegate
comment extraction to the shared `_extract_comments` path.

## Common mistakes

- Writing a walker that emits `RawSymbol`s with a different field
  convention than the other four (e.g. a `kind` string that doesn't match
  what `frob.graph`'s digest/edge code expects) -- every downstream
  consumer (digests, gates, dup) assumes uniform `RawSymbol` shape across
  languages; test against `frob.graph.build_graph` on a real fixture, not
  just the walker in isolation.
- Forgetting the trailing-comment vs. preceding-comment binding rules
  `_extract_comments`/`_is_trailing_comment`/`_block_ends` already encode
  for the other five languages -- a naive walker can silently bind a
  directive comment to the wrong symbol in edge cases (3+ stacked
  directive comments above a `def`, see the caveat in `_extract.py`'s
  `_extract_comments` docstring).

## See also

- `docs/modules/lang.md` -- the tree-sitter parsing core reference.

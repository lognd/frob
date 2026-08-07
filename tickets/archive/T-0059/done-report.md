## Done report

Delivered a lexer + recursive-descent parser for the surface grammar v0
(module/node/flow/boundary/assert/assume; `refine` deferred to T-0062),
split per charter D3 (amended): the compute-heavy grammar lives in Rust,
Python keeps the open interface.

- `strata-core/src/parse.rs` (new): hand-rolled lexer (idents, numbers,
  strings, `->`, `..`, `<=`, unit-continuing `/`) and recursive-descent
  parser covering every construct in the grammar; fuzz-safe (no panics on
  any input, verified by a dedicated test feeding malformed/empty/partial
  source). Exposes `pub(crate) fn parse_source_impl` returning JSON
  (`serde`/`serde_json` added as new Cargo deps); `strata-core/src/lib.rs`
  wires it as the `parse_source` pyfunction. 22 cargo unit tests (up from
  4), all green, covering every property, every unit form (`req/s`, `%`,
  bare `min`), attr `k=v`, error line/col accuracy, module-missing,
  duplicate-module, unknown-keyword/property/metric, and a full round-trip
  design. `strata_core.pyi` updated with the new signature.
- `src/frob/strata/_ast.py` (new): frozen pydantic AST mirroring the
  parser's JSON shape -- `Module`, `NodeDecl`, `Capacity`, `FlowDecl`,
  `BoundaryDecl`, `ClaimDecl` -- reusing `Quantity` from `_models.py`.
- `src/frob/strata/_parse.py` (new): `parse_module(text) ->
  Result[Module, StrataError]` bridging the Rust JSON into the AST models;
  logs line/col/message at ERROR on failure, returns bare
  `Err(StrataError.ParseFailed)` on the typani contract.
- `src/frob/strata/_errors.py`: added `StrataError.ParseFailed`.
- `src/frob/strata/__init__.py`: exports `Module`, `NodeDecl`, `FlowDecl`,
  `BoundaryDecl`, `ClaimDecl`, `SurfaceCapacity` (aliased to avoid the
  kernel `Capacity` name clash), and `parse_module`.
- `docs/strata/surface.md`: new "## Parser" section with `frob:describes`
  anchors for every new public symbol (Rust `parse_source` and the six
  Python AST/parse symbols).
- `tests/unit/strata/test_parse.py` (new): 11 unit tests, one
  `frob:tests` directive per case, covering every construct/property,
  quantity units (`req/s`, `%`), `attr k=v`, error-path behavior (Err +
  `ParseFailed`), module-missing, duplicate-module, and a full round-trip.

Verified:
1. `cargo test --lib` (with `PYO3_PYTHON`/`LD_LIBRARY_PATH` set) -- 22
   passed, 0 failed.
2. `cd strata-core && uvx maturin develop --uv --release` (via `make
   core`, run from repo root so it targets the shared `.venv` rather than
   a stray per-crate venv) -- rebuilt and reinstalled cleanly.
3. `uv run pytest tests/unit/strata -q` -- all green (56 total, 11 new).
4. `uv run ruff format`, `uv run ruff check`, `uv run ty check` on
   `src/frob/strata` and `tests/unit/strata` -- all clean.
5. `frob graph build` then `frob ticket sweep T-0059` (last edit before
   sweep) then `frob check --ticket T-0059` -- exit 0. One self-inflicted
   gate finding (COV001/TEST001 on `parse_source_impl`, initially `pub`
   with no doc/test edge of its own) was fixed by making it
   `pub(crate)` and adding its own `frob:doc`/`frob:tests` directives; a
   residual TEST002 stub-coverage note on that same helper is
   non-blocking (`gates` tool reports "pass", 77 warn-level findings, 6
   pre-existing waivers, none newly introduced by this ticket).

Deviations: the grammar sketch's `capacity` node-property syntax in
`kernel.md`/`surface.md` examples wasn't literally reproduced (no worked
example existed); implemented exactly the v0 grammar given in the ticket
body (`capacity NUMBER UNIT replicas INT .. INT`). No other deviations.

Filed: none -- no out-of-scope structural issues found. Pre-existing
repo-wide `frob-arch`/PERF gate warnings on files this ticket touches only
incidentally (`_models.py`, `_facts.py`, `_claims.py`) predate T-0059 and
were left untouched, consistent with scope.

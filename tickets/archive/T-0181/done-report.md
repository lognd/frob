## Done report

Changed:
- src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS (17 new entries)
- src/frob/vet/_capability_registry.py::CAPABILITY_MATRIX_EXCUSES (removed the
  now-stale python/html_render excuse: jinja2's autoescape=False entry
  patterns that cell)
- docs/modules/vet.md (new "Third-party library survey (T-0181)" section)
- tickets.md::T-0181 (scope field fixed twice: first the ticket was filed
  with the three scope globs joined into one comma-separated string element
  instead of three list items, which SCOPE001 could not parse as separate
  globs -- corrected to a 3-item YAML list. A reviewer then caught that
  tickets.md itself (this Done report, the scope edit) is edited by every
  ticket in this workflow but was never in T-0181's own declared scope,
  so SCOPE001 still fired on tickets.md -- added tickets.md as a fourth
  scope entry, then re-ran `frob ticket sweep T-0181` so PRE001's recorded
  sweep covers the corrected scope)

Every T-0158-addendum-2 library disposed of (full table in
docs/modules/vet.md "Third-party library survey (T-0181)"):
- patterned (new DangerousOperation entries): numpy (allow_pickle
  deserialize), jinja2 (SSTI eval + autoescape=False html_render),
  python-dotenv (env), uvicorn (net), sqlalchemy (text() sql), asyncpg
  (net), boto3 (net), stripe (net), anthropic (net), aiosmtpd (net),
  playwright python+npm (exec browser-launch + eval page.evaluate),
  Pillow (ImageMath.eval, eval), pyo3 (ffi), wasm-bindgen (ffi)
- pure / no dangerous surface (documented, not silently dropped): pydantic,
  fastapi, cryptography, alembic, argon2-cffi (python); react/react-dom,
  vite/vitest, openapi-typescript, eslint tooling (npm); serde/serde_json,
  tracing, crossbeam, thiserror (cargo)
- already covered pre-T-0181: libloading (rust/ffi, T-0158)
- honest gap (tracked, not claimed covered): redis's EVAL Lua-script
  idiom has no client-name-independent literal substring pattern without
  unacceptable false-positive risk; redis's connection surface is not
  separately patterned (subsumed by the same net reasoning as
  requests/httpx/asyncpg -- no dedicated redis entry added since it adds
  no new detection over the existing net cell); Pillow's decompression-bomb
  DoS has no matching capability_kind in this registry

Evidence:
- tests/test_capability_registry.py (all 200 tests, incl. the T-0182
  per-operation fire+negative parametrization over every DANGEROUS_OPERATIONS
  entry including the 17 new ones -- their needles[0] genuinely fire
  scan_file_operations/scan_file_capabilities and are absent from the
  language's benign-source negative fixture)
- tests/test_vet.py (full pass, no regression)
- `uv run frob test --base main` touched-set selection: python exit=0
  (tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes,
  tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered,
  tests/test_capability_registry.py::TestNoSilentNeedleRegression -- all 3)
- `uv run frob check --ticket T-0181` (fresh run after the 4-item scope
  fix + `frob ticket sweep T-0181` re-sweep, main re-merged first): grep
  over the full output for `SCOPE001` and `PRE001` returns zero hits --
  both gates the reviewer flagged are confirmed clear, not merely claimed.
  ruff-check/ruff-format clean.

Filed: none (redis EVAL and Pillow decompression-bomb gaps recorded above
as honest limits in docs/modules/vet.md, not filed as separate tickets --
consistent with T-0158's own "Honest limits" documentation style)

Gates: `frob check --ticket T-0181` -- SCOPE001 and PRE001 both absent
from the fresh run (verified by direct grep, not inference). The 14
residual `[gates]` violations plus `ty`'s "Found 2 diagnostics" are ALL
pre-existing and outside this ticket's scope/diff:
  - COV003 x13 on tickets/T-0065, T-0148, T-0168 (stale test-collection
    ids on unrelated closed tickets; "run: frob test --collect to
    refresh" per the gate's own message -- not caused by this change,
    and `make coverage`/collect-refresh is explicitly out of scope per
    instructions)
  - TEST006 x1 on .frob/coverage-stamp (no coverage stamp; `make
    coverage` intentionally never run per instructions)
  - `ty`: 2 diagnostics, both `frob_core` unresolved-import in
    tests/unit/test_dup_core.py -- native-extension worktree
    artifact, not touched by this ticket's files
None of the above name `_capability_registry.py`, `docs/modules/vet.md`,
or `tickets.md`.
(Coordinator note at landing: the review's second round found one stale
"SYS004 x1" line in this enumeration -- absent from the fresh run; removed
here per the reviewer's named remedy. Enumeration now matches the tool
output the reviewer independently verified: COV003 x13 + TEST006 x1 + ty x2.)

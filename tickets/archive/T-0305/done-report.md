## Done report

Removed the bare `"napi"` plain needle from the typescript `ffi`
`node-ffi` `DangerousOperation` entry (`src/frob/vet/
_capability_registry.py`) and added `_has_word_boundary_napi` (`src/frob/
vet/_capability.py`), an identifier-boundary special check registered in
`_SPECIAL_CHECKS["typescript"]["ffi"]` -- mirrors the existing T-0151
`_has_bare_compile_call` precedent for the same "needle is a substring of
an unrelated word" bug class. `napi` still fires for `require('napi')`,
`ffi-napi`, `ffi_napi`, etc. (non-identifier or absent boundary on both
sides) but never for `openapi`/`OpenAPI` (preceding byte is
alphanumeric). Updated the `_RECLASSIFIED_NEEDLES` drift-lock table in
`tests/test_capability_registry.py` with an honest entry recording the
move (not a silent drop), plus a check that the `typescript/ffi` special
check is actually registered.

Verified directly against a reproduction of graphite's exact case: a
minimal fixture shaped like `frontend/src/api/api.generated.ts`
(openapi-typescript codegen header, `OpenAPI` type, `ApiClient` class, no
FFI) no longer observes `ffi`; a real `napi`-based import still does.

Evidence: recorded via `frob ticket evidence` (4 ids in the ticket's
`evidence:` list above).

Filed: none (closeable within the declared scope).

Gates:
- `uv run pytest tests/test_capability_registry.py -q`: all green (580+
  cases, including the full `TestPerOperationFireFixtures`/
  `TestNoSilentNeedleRegression` parametrized suites).
- `uv run pytest -q` (full repo): all green.
- `uv run frob check --stamp-baseline`: clean (see T-0303's Done report,
  same run).
- `uv run frob sys audit`: `capability coverage: ... 0 unexcused`.
- `git diff main --diff-filter=D --stat`: empty (deletion-filter clean).

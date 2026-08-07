## Done report

Investigation first (per dispatch instructions): most of this ticket's
scope had already landed under other tickets between filing (2026-07-18)
and this pass -- confirmed by reading the code, not assumed:

- fs-read (Path.read_text/open-for-read): FULLY landed by T-0304
  (`feat(vet): split fs into fs-read/fs-write capability kinds`, commit
  478a106) -- new `fs-read` kind in `CAPABILITY_KINDS`, patterned python/
  typescript/rust/c-cpp entries, `_selfconform.py` SYS101 backward-compat
  alias (a bare `may "fs"` is satisfied by either fs/fs-read observation;
  a narrow `may "fs-read"` is not satisfied by a write-only observation),
  and `tests/unit/strata/test_selfconform.py` coverage
  (`TestFsReadFsWriteAlias` and neighbors). Nothing left to do here.
- socket/uvicorn bind: `uvicorn.run(` (T-0181) and the c-cpp
  `socket()/connect()/bind()` entry (T-0158) both already pattern as
  `net` -- the tier-2 `may` vocabulary
  (`frob.strata._effects._KIND_MAP`) only delegates `net`/`fs`/`exec`, so
  a distinct `bind` kind would duplicate `net`, not add a new discharge
  shape (exactly the "confusing vocabularies" anti-pattern
  `docs/guides/extending/benign-capabilities.md#common-mistakes` warns
  against). No new kind added; documented the investigation and the one
  real residual gap (Python's `from socket import socket` idiom, no
  `socket.` substring) as a known, undischargeable-without-false-positive-
  risk gap in `docs/modules/vet.md` ("T-0222: socket/uvicorn 'bind'
  observability").
- Part B (per-node capability excuse channel): T-0174's
  `[[strata.benign_capabilities]]` / `load_repo_benign_capabilities`
  channel already exists, already carries `fs-read`, `net`, and `ffi`
  entries in `DEFAULT_BENIGN_CAPABILITIES` (`src/frob/strata/_threat.py`),
  and is already fully tested end-to-end
  (`tests/unit/strata/test_threat.py::test_repo_declared_excuse_resolves_
  threat002` and neighbors). No new mechanism built -- this ticket's Part
  B is pure confirmation that T-0174 already covers the ask; documented
  in the Description discussion above, no separate doc edit needed since
  `docs/guides/extending/benign-capabilities.md` already documents the
  per-repo channel in full (including the worked recipe and the "replace
  a `waive THREAT002:<kind>` with a first-class entry" guidance the
  ticket asked for).

The one genuinely missing needle this pass adds: compiled/native
extension import observed as `ffi` (`src/frob/vet/_capability_registry.py`,
new `DangerousOperation` python/importlib/
`importlib.machinery.ExtensionFileLoader` entry, capability_kind `ffi`).
A bare `import strata_core`-style native-extension import is scanner-
invisible by construction (indistinguishable from any other import by
substring); `ExtensionFileLoader` is the one unambiguous stdlib literal
naming "this is a compiled extension module loader," with no known
false-positive class (verified: zero other occurrences of the literal
anywhere else in `src/`). `docs/modules/vet.md`'s capability taxonomy
table row for `ffi` updated to name it.

Changed:
- src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS (new entry:
  python/importlib/importlib.machinery.ExtensionFileLoader -> ffi)
- docs/modules/vet.md (ffi taxonomy row + new "T-0222: socket/uvicorn
  'bind' observability" investigation subsection)
- tickets.md (scope widened to include src/frob/vet/_capability.py and
  docs/modules/vet.md per dispatch instructions; this Done report)

Evidence (fire/negative fixtures generated automatically per-entry by
T-0182's `TestPerOperationFireFixtures`, confirmed via
`pytest --collect-only`):
- tests/test_capability_registry.py::TestPerOperationFireFixtures::
  test_entry_fires_scan_file_operations[015-python-importlib-importlib.machinery.ExtensionFileLoader]
- tests/test_capability_registry.py::TestPerOperationFireFixtures::
  test_entry_fires_scan_file_capabilities[015-python-importlib-importlib.machinery.ExtensionFileLoader]
- tests/test_capability_registry.py::TestPerOperationFireFixtures::
  test_entry_absent_from_benign_source[015-python-importlib-importlib.machinery.ExtensionFileLoader]
- Regression (pre-existing, still green): tests/test_capability_registry.py
  full module, `tests/unit/strata/test_threat.py`,
  `tests/unit/strata/test_selfconform.py` -- 100% pass, 0 failures,
  `uv run pytest tests/test_capability_registry.py
  tests/unit/strata/test_threat.py tests/unit/strata/test_selfconform.py -q`.

Gates: `uv run ruff check` clean, `uv run ruff format --check` clean
(both PATH and project-pinned ruff, per playbook section 12),
`make typecheck` (`uv run ty check src/`) clean, `uv run frob check
--stamp-baseline` then `uv run frob check --delta`: `gates 0/4 new,
0 errors, 0 warnings, 24 waived` (the 4 baseline violations are all
pre-existing, none in touched files). `git diff main --diff-filter=D
--stat` empty (deletion-filter clean).

Filed: none -- no out-of-scope discoveries required a new ticket; the
"known gap" (low-level `from socket import socket` idiom) is documented
in-line in `docs/modules/vet.md` rather than ticketed, since adding a
discriminating needle for it was investigated and rejected as a false-
positive risk, not deferred work.

Worktree: 172308d base (main tip at start, confirmed via `git log
--oneline -1` before and after -- no drift). NOT closing per dispatch
instructions (review-gated) -- left in-progress for reviewer.

## Done report

Fixed `_python_import_specifiers` (src/frob/lang/_extract.py) dropping
every imported NAME for `from X import Y[, Z, ...]` -- only the bare
module specifier was ever extracted, so `resolve_local_import` could
never land on a submodule file, exactly the T-2205-discovered defect
this ticket was filed to close.

Fix: both readings of `from X import Y` (Y is a member of X, Y is a
submodule of X) are now emitted as candidate specifiers -- `X` and
`X.Y` for each imported name -- and `resolve_local_import`'s existing
filesystem check (through T-2195's declared-source-root path, unchanged)
decides which resolves. An aliased import (`Y as alias`) uses the
pre-alias name via `aliased_import`'s own `name` field; `from X import
*` contributes nothing extra (no name to pair with X).

Repro: `tests/test_lang.py::TestFromImportSubmoduleResolution::
test_from_package_import_submodule_resolves_to_the_file`, committed
alone at 9b2913849, watched FAIL against the pre-fix code
(`frob ticket evidence T-2211 --check-repro ... --base-ref 9b2913849`
reported FAILED_AT_PARENT). Fix committed separately at ea1baafaa.

Must-still-pass controls (all bound as evidence, all pass post-fix):
- `from pkg import _python` resolves to `pkg/__init__.py` AND
  `pkg/_python.py` (headline case, mirrors `frob.arch`)
- `from pkg import (_python, _cpp)` resolves each parenthesized name
- `from pkg import ticket_runner as _ticket_runner` resolves via the
  pre-alias name (mirrors `frob.app.ticket_runner`)
- `from pkg import name_defined_in_pkg` (a real member, not a
  submodule) still resolves ONLY to `pkg/__init__.py`, never fabricates
  `pkg/name_defined_in_pkg.py` -- the over-resolution control
- `from pytest import fixture` (third-party) resolves to nothing local
- `from pkg import *` still resolves the bare package (unaffected)

DEAD001 delta (measured by temporarily wiring
`build_reference_graph(..., verify_imports=True)` into
`frob.gates._dead_symbols` locally for measurement only, NOT committed
-- wiring it for real is T-2205's job, out of this ticket's scope):
baseline (verify_imports=False, current default) is 46 findings.
Pre-fix, verify_imports=True was 60 (14 new, 0 disappeared) -- T-2205's
own measurement. Post-fix, verify_imports=True is 51 (5 new, 0
disappeared): 9 of the original 14 false positives are gone, covering
every case T-2211's own body named concretely (`frob.arch._python`,
`frob.arch._cpp`, `frob.arch._patterns`, `frob.app.ticket_runner`).

5 findings remain, in two classes outside this ticket's scope
(`_extract.py`'s specifier extraction) -- filed as T-2219:
1. `frob.arch._abstraction`'s 3 symbols -- a TRANSITIVE re-export chain
   (`_python.py` re-imports these names from `_abstraction.py`, itself
   now correctly resolved by this fix; but the actual caller,
   `arch/__init__.py`, only imports `_python.py` directly, never
   `_abstraction.py`, so the single-hop import-edge check in
   `frob/graph/callgraph.py` misses it). Needs transitive reachability
   in `_local_imports_by_path`'s consumer, not a change to specifier
   extraction.
2. 2 test-file symbols (`_repo_root` in test_litmus_cwe.py, `_load` in
   test_coordinator_scripts.py) that are NOT caused by this fix --
   `_repo_root` has zero real callers and was previously masked by a
   same-named collision (a gap this gate's own docstring already
   discloses); `_load` is only called at module top level, suggesting
   `build_reference_graph` may not attribute a module-top-level
   statement as a call from any symbol under verify_imports=True.

`frob check --only cycle`: still 3 errors, 1 warning (T-2202's tracked
debt) -- unmoved by this change, confirmed via a direct measurement
before/after the fix.

Verification:
- `pytest tests/test_lang.py::TestFromImportSubmoduleResolution -o
  addopts="" -q`: 6 passed (SUITE-RESULT: exitstatus=0 collected=6
  failed=0), all red before the fix (3 of 6; the 3 controls already
  passed unmodified), all green after.
- `pytest tests/test_lang.py tests/unit/test_lang_primitives.py -o
  addopts="" -q`: 94 passed, 0 failed (no regression in the surrounding
  suite).
- `pytest tests/test_graph.py -o addopts="" -q`: 131 passed, 0 failed.
- `frob test --base main`: python exit=0, 8 outcomes recorded, all
  green.
- `frob check --only lint --json`: the one ruff E501 error is in
  src/frob/lang/_nodes.py, a file this ticket did NOT touch (confirmed
  via `git status` / `git diff --stat`) -- pre-existing repo debt, not
  introduced here.
- `frob check --ticket T-2211`: gate:SCOPE's single error is
  `tickets/T-2219/ticket.md` outside declared scope -- the
  residue ticket's own file, expected when filing outside scope per
  playbook sec 8. gate:TICK's 9 errors are pre-existing ticket-rot
  (T-0969/T-1135/.../T-1623), unrelated to this ticket. gate:DRIFT's
  finding on `src/frob/lang/_nodes.py::resolve_local_import` is also
  pre-existing (file untouched by this change).

Filed: T-2219 (verify_imports=True call-graph gap: transitive
re-export chain + call-site collision/attribution), residue of this
ticket's own DEAD001 measurement, scoped to
src/frob/graph/callgraph.py -- real id to be confirmed after land.

Gates: `frob check --ticket T-2211` -- no error attributable to this
ticket's own scoped files (src/frob/lang/_extract.py,
tests/test_lang.py); every FAIL line above is either pre-existing
repo-wide debt (confirmed unmoved by this change) or the residue
ticket's own file being outside scope by construction.

### Changed
```
 src/frob/lang/_extract.py          |  35 +++++++++-
 tests/test_lang.py                 | 130 +++++++++++++++++++++++++++++++++++++
 tickets/T-2211/ticket.md           |  19 +++++-
 tickets/T-2219/ticket.md |  83 +++++++++++++++++++++++
 4 files changed, 263 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_submodule_resolves_to_the_file` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_multiple_submodules_resolves_each` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_submodule_as_alias_resolves_by_real_name` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_member_control_does_not_fabricate_a_file` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_third_party_import_resolves_to_nothing_local` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestFromImportSubmoduleResolution::test_from_package_import_wildcard_still_resolves_the_package` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2211/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2211, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md

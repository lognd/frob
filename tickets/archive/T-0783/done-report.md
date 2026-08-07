## Done report

## Done report

Changed:
- src/frob/gates/__init__.py::_pyproject_version_at (new)
- src/frob/gates/__init__.py::_todo003_long_deferred (new -- TODO003)
- src/frob/gates/__init__.py::coverage_gate (wires TODO003 in, docstring updated)
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added "TODO003")
- src/frob/gates/__init__.py::_debt002_violations (docstring reworded to avoid an incidental "TODO" substring collaterally tripping TODO001 once this file became diff-touched)
- tests/test_gates.py::TestCoverageGate (3 new tests; class-level frob:ticket T-0783 binding added)
- tests/test_gates.py::TestTest013NativeUnverified, TestPiiStructuralCrossLanguage (frob:ticket bindings added/completed for T-0730/T-0762's own touched symbols -- discovered while running gates-fast under T-0783's active-ticket context, where two open tickets' scopes both cover tests/test_gates.py equally, making scope-based coverage ambiguous per `_scope_covers`; fixed with explicit per-symbol frob:ticket directives, the sanctioned resolution the gate itself names)
- docs/design/registry/check-coverage.yaml (CHK-GATE-TODO003 entry, filed via `frob registry audit --sync-gate-rules`; scope extended via `frob ticket scope T-0783 --add` with a recorded reason)

Design choice (disclosed): TODO003 derives "when the deferral comment landed" from `git blame` on the directive's own line plus `git show <sha>:pyproject.toml`, not a new persisted `.frob/` state file. This keeps the gate a pure function of (snapshot, queue, git log) with nothing to keep in sync or race against a concurrent `frob check`.

Scope gap (disclosed, per ticket acceptance wording): only the structured `frob:todo T-####` directive is covered. The ticket body's "that ticket's job shape" (informal prose deferral, no structured directive) is NOT detected -- no reliable structural signal exists for free-text deferral prose the way `EdgeKind.TODO` exists for the directive form. Left as an explicit follow-on gap in the function's own docstring, not silently dropped.

Evidence (all bound with --accepts 0), measured via `uv run pytest tests/test_gates.py -k todo003 -n0 -v -p no:cacheprovider` -- "3 passed":
- tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes

Also `uv run pytest tests/test_gates.py -p no:cacheprovider -q` -- full file green (7 batches of dots, no failures) both before and after merging main.

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket T-0783 --only <stage>` clean (exit 0) for lint, static, gates-native, gates-security. `gates-fast` is clean of anything TODO003/gates/__init__.py/test_gates.py-related; the two remaining findings there are unrelated pre-existing repo debt inherited via `main`'s own concurrent landings during this session (TICK006 phantom-filing on T-0738's Done report, not mine; several REG008 findings on unrelated already-registered rules DOC005/DEAD001/COMPLIANCE005/FMT001/ARCH101-103, confirmed present before my `check-coverage.yaml` touch by their unrelated rule ids). gate:FMT stayed PASS throughout (WARN-severity only; a handful of pre-existing T-0730/T-0762 directive lines were never in canonical wrapped form but this is non-blocking debt, not something T-0783 introduced).

Caution logged for future dispatches: `frob fmt <file>` reformatted far more of both touched files than intended on a first attempt (rewriting ~380-500 lines of pre-existing, unrelated directive comments across the whole file to canonical form) -- reverted both files and hand-wrote only the new/changed directive lines to the exact canonical form instead (verified via `frob.gates._fmt_directives.canonicalize_text` called directly on isolated snippets, with `limit` reduced by the surrounding indent since that function assumes zero indent).

Filed: none new for this ticket (the C/C++ collector gap was T-0730's, already filed as T-0886).

Scope: `git diff main --diff-filter=D --stat` is empty.

### Changed
```
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/gates.md                    |  38 +++-
 src/frob/gates/__init__.py               | 250 ++++++++++++++++++----
 src/frob/gates/_pii_structural.py        | 201 +++++++++++++++---
 tests/test_gates.py                      | 350 ++++++++++++++++++++++++++++++-
 tickets.md                               | 202 +++++++++++++++++-
 6 files changed, 961 insertions(+), 86 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

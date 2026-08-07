## Done report

Extracted the WAIVE/PLACE001 family out of `src/frob/gates/__init__.py`
into a new `src/frob/gates/_waive.py`, mirroring the existing
`_opaque.py`/`_design_invariants.py` sibling-module precedent:
`_waive_edges`/`_waivers_by_rule`, WAIVE001-007, DSL001, PLACE001, the
shared `_match_waiver`/`_apply_waivers` spine every other gate's
violation list filters through, `_severity_overrides`/
`_apply_severity_overrides`, and the `active_ticket`/`ticket_lease_pin`
helpers that ride along with it in the original module.

`src/frob/gates/__init__.py`: 12047 -> 10159 lines (-1888, after the
DRIFT002/AFFECT001 doc/test fixups below).
New: `src/frob/gates/_waive.py`: 1972 lines.

`__init__.py` imports everything back from `_waive.py` and re-exports it
unchanged (including underscore-prefixed names like `_match_waiver`/
`_UNWAIVABLE_RULES`/`_apply_waivers`/`known_gate_rule_ids`/
`active_ticket`/`ticket_lease_pin`/`SCOPED_RUN_FLAKY_RULE_IDS` that
other packages -- `frob.app.sys_runner`, `frob.app.registry_runner`,
`frob.app.check_runner`, `frob.check._python`, `frob.app.ticket_runner`
-- import directly via `from frob.gates import ...`), so every existing
call site keeps working with zero edits outside `src/frob/gates/**` plus
the directive fixups noted below.

Two internal cross-references needed a lazy (call-time) import instead of
a module-level one to avoid an init-time circular import between
`_waive.py` and `__init__.py`: `_design_dir` (used once, by
`_strata_waive_sites`) and `_site_from_edge_origin` (used 4x, by the
WAIVE003/004/005/006-strata violation builders). Both stay defined in
`__init__.py` (still used by many other gate families resident there)
and are imported inside the function body at call time -- the same
pattern `ticket_lease_pin`'s own `resolve_lease` import already used
before this split.

All `frob:ticket`/`frob:tests`/`frob:enforces`/`frob:waive` directives on
every moved function traveled with the function body (a straight text
move, no re-derivation) -- e.g. `waive006_gate`'s `frob:enforces
CHK-GATE-WAIVE006`, DSL001's two `frob:tests` bindings, and
T-0101/T-0399/T-1010's ticket comments anchored on `_KNOWN_GATE_RULES`.

Splitting the file physically moved several symbols, which broke every
`frob:tests`/`frob:describes` directive that hardcoded the old
`src/frob/gates/__init__.py::<symbol>` path (DRIFT002) and left 6
public-API doc entries untouched by the diff (AFFECT001). Fixed by
widening scope (`frob ticket scope T-1072 --add ...`, reason recorded on
the ticket) to the 3 carrier files and repointing each reference's module
path component to `_waive.py` (same symbol name, no semantic edit):
`tests/test_gates.py` (9 directives), `tests/test_secrets_gate.py` (1),
`docs/modules/gates.md` (5, in the "## Public API" section). `frob check
--ticket T-1072 --only gates-fast` now shows 0 AFFECT/DRIFT/WAIVE/COV
errors attributable to this change; the only 2 error classes left in that
run (COV003 under `tickets/T-1063`, TICK006 on `T-0667`'s stale draft
refs) are pre-existing and unrelated to this ticket's scope.

Honest partial: this ticket's full ask was every gate family in the
12047-line file; only the WAIVE/PLACE001 family landed this pass.
`__init__.py` is still 10159 lines, still the repo's largest file, still
far above the 800-line large-file threshold. Filed the remainder as
T-1077 ("arch: split remaining gate families out of
src/frob/gates/__init__.py (T-0395/T-1072 remainder)") naming every
family still resident (COV/TODO/FMT/DEBT/DEPR/SCOPE/PREWORK/INV/TEST/
DECISIONS/TICK/COMPLIANCE/SYS-DOC/DUP/REL/FUZZ/DOCLINK/DOCANCHOR/PERF
plus the `run_gates` orchestration spine).

### Verification
- `uv run pytest tests/test_gates.py tests/test_waive_gate.py
  tests/test_secrets_gate.py -q`: all pass except the one pre-existing,
  unrelated failure (`TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known`,
  fails identically on `main` -- SYS103/SYS205 rule ids missing from
  `_KNOWN_GATE_RULES`, nothing to do with this split).
- `uv run pytest --collect-only -q` (whole repo): 6922 tests collected,
  0 collection errors.
- `uv run ruff check src/frob/gates/_waive.py src/frob/gates/__init__.py`:
  clean.
- `git diff main --diff-filter=D --stat`: empty (no unintended deletions).

### Changed
```
 docs/modules/gates.md      |   10 +-
 src/frob/gates/__init__.py | 1966 +------------------------------------------
 src/frob/gates/_waive.py   | 1972 ++++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py        |   18 +-
 tests/test_secrets_gate.py |    2 +-
 tickets.md                 |  480 ++++++++++-
 6 files changed, 2502 insertions(+), 1946 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_waive002_known_gate_rule_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPlace001Gate::test_missed_following_binding_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_match_waiver_prefix_reach_gated_to_package_scoped_rules` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCov002ScopeCoverage::test_active_ticket_own_scope_wins_over_a_broader_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDsl001::test_waive_reason_and_tests_kind_not_double_flagged` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestFindsTokens::test_sec003_waiver_is_inert` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006Registration::test_waive006_gate_combines_both_channels` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive007Registration::test_waive007_gate_combines_both_channels` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 7 error(s), 917 warning(s), 419 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, COV003@tickets/T-1063, COV003@tickets/T-1066, COV003@tickets/T-1073, DUP001@tests/test_gates.py, PII012@src/frob/gates/_waive.py, TICK006@tickets.md

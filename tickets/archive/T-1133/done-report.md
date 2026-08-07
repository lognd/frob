## Done report

Changed:
src/frob/gates/_waive.py::_waive004_violations (new full_unscoped_run kwarg, defaults True)
src/frob/gates/__init__.py::_assemble_gate_report (wires full_unscoped_run=not cfg.gates and cfg.ticket is None)

`_waive004_violations` now short-circuits to `()` before any per-edge work
whenever the caller signals a scoped run (`--only` gate selection via
`cfg.gates`, or a `--ticket`-scoped diff via `cfg.ticket`) -- WAIVE004 only
ever fires on a full, unscoped `frob check`, where "matches 0 findings" is
actually meaningful rather than an artifact of the gate/diff-scope
excluding the rule. Full-run behavior (T-1021's sweep) is unchanged: the
default `full_unscoped_run=True` keeps every pre-existing test passing
unmodified. Confirmed live on a real scoped run: `frob check --ticket
T-1133 --only gates-fast` on this worktree produced ZERO WAIVE004
occurrences (measured: `grep -c WAIVE004` = 1, the module's own docstring
reference, no actual finding), versus ~400-447 per scoped run before this
change per the ticket's own observation.

`fake_marker_staleness_gate`/`_stale_fake_marker_violations` (the other
WAIVE004-emitting path, `frob:secret-fake` markers) is intentionally left
unchanged -- it re-derives staleness by re-scanning the file's own text
for real secret-pattern hits every call, independent of which gates
`--only` selected, so it does not exhibit the "gate did not run" false-
positive mechanism this ticket targets.

Evidence:
tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run (new, T-1133)
tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
6/6 WAIVE004-related tests pass: `pytest tests/test_gates.py -k waive004 -q` (measured: "......  [100%]").
Acceptance [0] bound to the new suppression test.

Filed: none

Gates: `frob check --ticket T-1133` chunked (gates-fast, gates-native,
gates-security, lint, static) -- gates-fast/gates-security/static all 0
errors. gates-native shows the same 5 pre-existing ARCH001 errors as
T-1155's land (already tracked by T-1162, none in files this diff
touches). lint shows pre-existing ruff-format/ty findings in unrelated
files; my touched files (src/frob/gates/_waive.py,
src/frob/gates/__init__.py, tests/test_gates.py) are individually
ruff-check clean and ruff-format applied.
`uv run frob sys sync-interface --check` not needed -- no public-surface
change (new kwarg is a private-function default-True addition, no new
export).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive004_suppressed_entirely_on_a_scoped_run` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

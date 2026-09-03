## Done report

Reformatted src/frob/check/__init__.py with ruff format, the one file T-3680's repo-wide sweep left untouched because reformatting it tripped the file's own COV001/COV002 diff obligations.

Closed the two coverage gaps in the same change (both pre-existing, only newly visible because ruff-format touches the file):
- COV001: FROB_CHECK_STOP_BEFORE_ENV had no frob:doc edge. Added a "CI diagnostics: pipeline stop points" section to docs/commands/check.md documenting the T-3675 stop-point knob, anchored with frob:describes/frob:doc.
- COV002: _check_stop_before changed with no frob:ticket edge. Added `# frob:ticket T-3675`.

Evidence: tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_true_only_for_the_matching_point (pytest -k check_stop_before: 8 passed, includes this one).

Filed: none.

Gates: `ruff format --check src/frob/check/__init__.py` clean. `frob check --only coverage` shows zero COV001/COV002 findings against src/frob/check/__init__.py (verified by filtering the --json output for that path); the only errors in that run are pre-existing/repo-wide and unrelated (DRIFT002 x111 on tests/system/test_frob_self_model.py -> design/frob.strata, untouched by this change; WAIVE011; claude-config-drift).

### Changed
```
 docs/commands/check.md     | 15 +++++++++++++++
 src/frob/check/__init__.py |  8 +++++---
 tickets/T-3682/ticket.md   |  2 ++
 3 files changed, 22 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_true_only_for_the_matching_point` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 7 error(s), 4264 warning(s), 909 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, DEPR006@frob-deprecated-baseline.lock.json, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json

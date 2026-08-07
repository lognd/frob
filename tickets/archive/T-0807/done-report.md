## Done report

## Done report

Changed:
src/frob/gates/__init__.py::_rel001_bump_suppressed_under_agent (docstring clarified: explicit FROB_AGENT override only)
src/frob/gates/__init__.py::_rel001_is_linked_worktree (new)
src/frob/gates/__init__.py::_rel001_land_owned (new)
src/frob/gates/__init__.py::release_gate (signature: +ticket_id param; branches on FROB_AGENT override vs context-derived land_owned vs plain error path)
src/frob/gates/__init__.py::_rel001_land_note (new)
src/frob/gates/__init__.py::_build_jobs (release job now passes st.ticket.id)

Detection design: REL001's bump/changelog demand is land-owned (WARN
informational note, not ERROR) when EITHER (a) ticket_id's cross-worktree
lease (resolve_lease, frob.tickets._leases, unchanged/reused) pins to
root, or (b) root is a linked git worktree (`git rev-parse --git-dir`
resolves to a worktree-private path distinct from `--git-common-dir`).
The pre-existing FROB_AGENT env-var override (T-0731) is preserved as a
SEPARATE, higher-priority path that still fully suppresses (no note at
all) -- this keeps the two existing T-0731 tests passing unchanged. A
plain root checkout with no --ticket and no live lease keeps erroring
exactly as before T-0807.

Evidence (pytest --collect-only confirmed resolving; frob test --base main green):
tests/test_gates.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent (pre-existing, still green)
tests/test_gates.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent (pre-existing, still green)
tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket (new)
tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket (new)
tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease (new)
tests/test_gates.py::TestDebtGate::test_rel001_linked_worktree_detected (new)
`uv run --frozen pytest tests/test_gates.py -q` -> 352 passed
`uv run --frozen pytest tests/test_release.py tests/test_ticket_land.py tests/unit/test_ticket_runner_land_release.py -q` -> all passed
`uv run --frozen frob test --base main` -> [PASS] python exit=0

Filed: none (no out-of-scope work found)

Gates: `uv run --frozen frob check --ticket T-0807 --only <stage>` clean
(0 errors) for all 5 stage groups (lint, static, gates-fast, gates-native,
gates-security) after `frob ticket sweep T-0807` and adding
tests/test_gates.py to scope (reason: T-0807's own verification tests
live there, alongside the T-0731 tests they extend -- COV002 needed the
new/changed test methods accounted for).

Deviation: scope was widened by one file, tests/test_gates.py, via
`frob ticket scope T-0807 --add tests/test_gates.py --reason-file ...`
per the playbook's normal scope-add mechanism (not a silent edit) --
the ticket's own acceptance criteria named "Tests" without a declared
test-file scope entry, and COV002/DRIFT002 confirmed a real gate
required it.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestDebtGate::test_release_gate_bump_fires_without_frob_agent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_release_gate_bump_suppressed_under_frob_agent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDebtGate::test_rel001_linked_worktree_detected` (pytest node id, verified passing when recorded)

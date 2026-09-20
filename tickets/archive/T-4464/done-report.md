## Done report

Changed:
- .github/workflows/release.yml (manylinux: 2_28 pin on both Linux matrix
  entries, with a comment explaining the glibc/_DEFAULT_SOURCE reason;
  OS-aware import-smoke step branching on RUNNER_OS with the venv under
  RUNNER_TEMP)
- tests/unit/test_release_workflow_gate.py (TestManylinuxPinAndWindowsSmoke
  class: test_manylinux_targets_pin_2_28, test_manylinux_pin_reason_is_documented,
  test_smoke_step_is_os_aware; extracted _find_step_by_name_prefix shared
  helper, also used by _assert_step_uses_faulthandler_and_marker, to fix DUP001)
- docs/guides/release.md (manylinux 2_28 floor and the le16toh/glibc reason)

Evidence: frob:tests T-4464
- tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_manylinux_targets_pin_2_28
- tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_manylinux_pin_reason_is_documented
- tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_smoke_step_is_os_aware
Full file run: 32 passed. yaml.safe_load confirms release.yml still parses
and manylinux resolves to the quoted strings "2_28"/"2_28"/"off"/"off"/"off".

BUG002 waived in the ticket body: check-repro's base-ref hits
TEST_ABSENT_AT_PARENT (T-2025 shape, brand-new test class); manually
confirmed fail-before by re-running the same 3 assertions against
`git show 3d2b0d72:.github/workflows/release.yml`, which has
manylinux: auto (unquoted, resolves to int) and no RUNNER_OS branching --
matches exactly what release run 34769124533 hit.

Filed: none

Gates: `uv run frob check --ticket T-4464` clean on gate:PRE and gate:DUP
after a re-sweep and the DUP001 helper-extraction fix. Two findings remain,
NOT waived, because they are pre-existing/repo-wide/out of this ticket's
scope (neither file is touched nor in scope:):
  - ruff-format: tests/test_tickets_triage_dates.py would be reformatted
  - gate:REF REF002: docs/design/macos-portability.md has one inbound
    reference (last touched by unrelated T-3586)
Acceptance (b) -- a green re-dispatch of release.yml across all five
targets -- requires an actual GitHub Actions run and cannot be measured
from this worktree.

### Changed
```
 .github/workflows/release.yml            | 31 ++++++++++--
 docs/guides/release.md                   | 15 ++++++
 tests/unit/test_release_workflow_gate.py | 82 +++++++++++++++++++++++++++++---
 tickets/T-4464/done-report.md            | 22 +++++++++
 tickets/T-4464/ticket.md                 |  4 ++
 5 files changed, 143 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_manylinux_targets_pin_2_28` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_manylinux_pin_reason_is_documented` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestManylinuxPinAndWindowsSmoke::test_smoke_step_is_os_aware` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4798 warning(s), 962 waived
- error-findings: REF002@docs/design/macos-portability.md

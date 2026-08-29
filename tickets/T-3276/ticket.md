---
id: T-3276
title: 'Missing external tools degrade quietly instead of failing loud: no central
  resolution, doctor checks one binary, xdist absence unaccounted'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
- tests/unit/test_doctor.py
- docs/guides/install.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_doctor.py
  reason: regression tests for the tool inventory/preflight
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/guides/install.md
  reason: COV001 doc anchor for the new tool-inventory public symbols
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_doctor.py::TestScanExternalTools::test_present_binary_reports_version
- tests/unit/test_doctor.py::TestScanExternalTools::test_missing_binary_reports_absent_with_install_hint
- tests/unit/test_doctor.py::TestScanExternalTools::test_present_package_reports_version_via_importlib
- tests/unit/test_doctor.py::TestScanExternalTools::test_missing_package_reports_absent
- tests/unit/test_doctor.py::TestExternalToolsRemediation::test_missing_required_tool_names_it_and_the_install_command
- tests/unit/test_doctor.py::TestExternalToolsRemediation::test_missing_optional_tool_is_silent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-08-28: account for xdist being missing; ensure every tool
frob uses is present; a "tool not found" must be LOUD.

MEASURED, and the answer is that tool resolution is ad hoc:

  - `shutil.which` appears in only 10 files across all of `src/frob/`.
  - `frob doctor` calls it exactly once -- for `frob` itself
    (`src/frob/doctor.py:542`). It checks for none of the tools frob actually
    spawns.
  - At least THREE different spawn conventions coexist for the same tool:
        sys.executable, "-m", "pytest"     gates/_bug_repro.py:823   CORRECT
        "uv", "run", "pytest"              app/ticket_runner/_verify.py:2165
        "pytest", "--collect-only"         refactor/_verify.py:440   BARE PATH
        "python", str(harness)             perf/_profile.py          BARE PATH
    A bare PATH lookup finds whatever interpreter or pytest happens to be
    first, which in a consumer environment is usually NOT the project's.

CONFIRMED CONSUMER IMPACT (../diax FROBLEMS.md F-011, real first use):
`frob coverage --full` spawned the global `~/.local/bin/pytest` -- a pytest 9
with neither pytest-cov NOR xdist installed -- which exited 4 (usage error).
frob then marked the run DEGRADED and continued; `coverage xml` failed
afterwards, so TEST006 could never be satisfied through `frob coverage` at all.
The user's workaround was to bypass frob entirely.

That is the failure mode this ticket exists to kill: a missing tool produced a
DEGRADED-but-continuing run and a downstream gate that can never be satisfied,
instead of one loud line naming the missing tool.

NOTE THE ADJACENT ALREADY-FILED WORK, do not duplicate it: T-3268 covers
`frob perf`'s hardcoded bare `python` (18 of 60 suite failures). This ticket is
the GENERAL rule and the preflight; T-3268 is one instance. Coordinate: if
T-3268 lands a `sys.executable` convention first, adopt it here rather than
inventing a second one.

WHAT TO BUILD:
  1. ONE resolution helper every external-tool spawn goes through. It decides
     the argv (interpreter, `uv run`, or PATH) by a stated rule, not per call
     site. No duplication -- two copies of a resolution rule is the desync bug
     this repo already knows.
  2. PREFLIGHT WITH A LOUD, TYPED FAILURE. A missing tool must produce a
     `Result` error naming: the tool, the operation that needed it, and how to
     install it. Never a silent skip, never DEGRADED-and-continue, never a bare
     FileNotFoundError traceback. T-0142 already fixed the crash case for
     ruff/ty; this is the same treatment applied systematically.
  3. XDIST SPECIFICALLY, per the owner's directive. frob's own pyproject sets
     `-n auto` in addopts. Determine what happens in a consumer repo, or in
     frob's own venv, when pytest-xdist is absent, and make that outcome loud
     and correct. `warn_if_xdist_bound_missing` already exists
     (`tickets/_worktree_guard.py`) -- check whether it covers ABSENCE of the
     plugin or only an unset bound; those are different conditions and the name
     suggests only the latter.
  4. `frob doctor` must enumerate and report every tool frob can spawn, with
     present/absent/version. That is what a doctor is for, and today it checks
     one binary.

DO NOT FIX THIS BY DEGRADING QUIETLY WHEN A TOOL IS MISSING. The scaffold's own
CI template already does exactly that -- it runs `frob graph --help` and, if it
fails, emits a `::notice::` and SKIPS the `frob check` step. A skipped gate that
reports a notice is indistinguishable from a passing gate in a green build.
Whatever you do here, that pattern should be reported (not necessarily fixed in
this ticket) as the same defect in the scaffolded CI.

DO NOT FIX IT BY REFUSING TO RUN WHEN AN OPTIONAL TOOL IS ABSENT EITHER. Some
tools are genuinely optional per language (cargo, npm, ctest). The rule is:
required-for-this-operation missing -> loud typed error; optional-and-unused ->
silent; optional-but-needed-for-a-gate -> the gate reports UNMEASURED, loudly,
never CLEAN. State which category each tool is in.

MUST-FIRE FIXTURE: an operation whose required tool is absent fails with a
message naming the tool and the install command.
MUST-STAY-QUIET FIXTURE: all tools present -> no new output, no slowdown.
THIRD FIXTURE: a gate whose optional tool is absent reports UNMEASURED, and
UNMEASURED is distinguishable from CLEAN in both the exit code and the output.

ACCEPTANCE
- A stated inventory of every external tool frob spawns, with its category.
- One resolution helper; the three divergent conventions above collapsed into
  it, or a stated reason each survivor differs.
- `frob doctor` reports the inventory.
- All three fixtures present.
- The scaffolded-CI silent-skip pattern reported.
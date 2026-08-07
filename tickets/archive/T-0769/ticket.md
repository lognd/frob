---
id: T-0769
title: 'vet observer: docstring prose counted as observed capability (exec false-positive
  on _concurrency.py docs)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet_capability.py
- src/frob/strata/_effects.py
- tests/unit/strata/test_effects.py
- tests/test_vet.py
- docs/modules/vet.md
- design/frob.strata
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_effects.py
  reason: 'Ticket body explicitly requires root-causing BOTH raw-text observation
    paths: the set-level scan in src/frob/vet/_capability.py AND the line-level observation
    used by strata''s THREAT004/check_capability_conformance delegate, which lives
    in src/frob/strata/_effects.py::_needle_matches/_line_effects. That function currently
    does a bare `needle in line` substring scan with zero comment or docstring exclusion
    at all -- it is the actual root cause of the reported _concurrency.py:56 false
    positive (a `#:` comment line), not the vet module''s already-comment-aware scanner.
    Fixing only _capability.py would leave the reported bug reproducible via the strata
    selfconform path exactly as it was found. Adding _effects.py (implementation)
    and its existing test file (regression coverage) so the fix matches the ticket''s
    own stated scope of work.

    '
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: 'Ticket body explicitly requires root-causing BOTH raw-text observation
    paths: the set-level scan in src/frob/vet/_capability.py AND the line-level observation
    used by strata''s THREAT004/check_capability_conformance delegate, which lives
    in src/frob/strata/_effects.py::_needle_matches/_line_effects. That function currently
    does a bare `needle in line` substring scan with zero comment or docstring exclusion
    at all -- it is the actual root cause of the reported _concurrency.py:56 false
    positive (a `#:` comment line), not the vet module''s already-comment-aware scanner.
    Fixing only _capability.py would leave the reported bug reproducible via the strata
    selfconform path exactly as it was found. Adding _effects.py (implementation)
    and its existing test file (regression coverage) so the fix matches the ticket''s
    own stated scope of work.

    '
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_vet.py
  reason: 'The T-0769 fix (excluding python docstring spans from the raw-text needle
    scan, matching the existing comment-span exclusion) directly changes the outcome
    of tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive,
    which locks a specific documented false positive ("cmdclass"/"os.environ" appearing
    ONLY in _capability.py''s own module DOCSTRING) that this exact fix is designed
    to eliminate. The locked assertion is now factually wrong post-fix and must be
    updated in the same change, not left red. This is a required consequence of the
    ticket''s own fix, not unrelated scope creep.

    '
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/vet.md
  reason: 'Reviewer finding: the new public symbol non_executable_line_numbers carries
    a frob:doc docs/modules/vet.md#public-api anchor but the doc file was never updated
    to add the frob:describes anchor plus prose entry -- COV001 debt. Adding docs/modules/vet.md
    to scope to close this gap in the same ticket, per reviewer instruction.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: design/frob.strata
  reason: 'land-together resolution of the unmasked stratamod may-net staleness (draft
    22aa6efc): removing the stale atom is a strictness-INCREASING narrowing required
    to keep TestRealGateGreen green at land'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'land-together resolution of the unmasked stratamod may-net staleness (draft
    22aa6efc): removing the stale atom is a strictness-INCREASING narrowing required
    to keep TestRealGateGreen green at land'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_docstring_and_comment_prose_yields_no_exec_capability
- tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_real_exec_call_still_observed
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_prose_only_lines_report_zero_exec_observation_via_selfconform
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_real_exec_call_still_flagged_via_selfconform
- tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_covers_docstring_and_comment
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
designated_repro_test: null
acceptance:
- text: GIVEN a module whose docstrings mention subprocess.Popen/os.fork prose but
    whose code never resolves an exec-capable call WHEN scan_file_capabilities runs
    THEN no exec capability is observed; GIVEN real exec calls outside docstrings
    THEN observation is unchanged; a regression test covers the docstring shape
  evidence:
  - tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_docstring_and_comment_prose_yields_no_exec_capability
  - tests/test_vet_capability.py::TestDocstringProseNotObservedSetLevel::test_real_exec_call_still_observed
  - tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_prose_only_lines_report_zero_exec_observation_via_selfconform
  - tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_real_exec_call_still_flagged_via_selfconform
  - tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_covers_docstring_and_comment
  - tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
threat: null
component: null
---
Found 2026-07-22 during the zero-drive: T-0695 landed src/frob/arch/_concurrency.py whose DOCSTRINGS document fork/pool hazards (literal subprocess.Popen(...), os.fork() prose). The raw-text needle scan (_needle_hits_outside_comments) excludes comment spans but NOT docstring string-literal spans, so selfconform saw capability exec observed at docstring lines on node graphlang -> 4 SYS100 violations -> TestRealGateGreen RED on main. Docstrings are non-executable string constants; they cannot spawn a process, so excluding them from raw-text observation is sound and does not weaken the fail-closed posture for executable code. Fix: compute docstring spans (module/class/function-head expression string statements) and treat them like comment spans in the raw-text path; keep binding-aware resolution untouched. Mitigation already on main: T-0695 docstrings reworded to avoid needle shapes; the observer fix must add the regression test so future doc prose cannot re-trip it. Note: T-draft-32e61ad6 (filed in the T-0717 worktree) proposed declaring may exec on graphlang instead -- that remedy is WRONG (falsely widens the declared threat surface) and should be dropped in favor of this ticket when it lands.
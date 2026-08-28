---
id: T-3249
title: 'Unowned 11-failure cluster: frob check fires spurious REF001/PRE001/SCOPE001
  only under concurrent load (T-2992 misattributed it to the already-landed T-3019)'
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
- tests/system/test_cli_check.py
- src/frob/check/__init__.py
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
- tests/system/test_cli_perf.py
- tests/system/test_cli_native_missing.py
- tickets/T-draft-db6c513a/**
- tickets/T-draft-460d9c7e/**
- tickets/T-draft-0ef9d7be/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/__init__.py
  reason: 'T-3249: comment_placement (T-3218) has the same registered-but-unreachable
    _STAGE_GROUPS omission shape T-3030 already fixed for 5 other gates; same fix,
    same file, confirmed one of the 11-failure cluster''s real root causes'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'T-3249: comment_placement (T-3218) has the same registered-but-unreachable
    _STAGE_GROUPS omission shape T-3030 already fixed for 5 other gates; same fix,
    same file, confirmed one of the 11-failure cluster''s real root causes'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_refs.py
  reason: 'T-3249: 5 of the 11-cluster failures are REF001 firing on tickets.md (a
    universal frob-tooling-owned root manifest with the same never-referenced-by-source
    shape T-3019/T-3031 already exempted for pyproject.toml/frob.toml/package.json)
    plus fixtures missing the REF001=warn adoption-baseline T-3019 already added to
    test_cli_check.py''s own _make_project but never propagated to these sibling fixtures'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_refs_gate.py
  reason: 'T-3249: 5 of the 11-cluster failures are REF001 firing on tickets.md (a
    universal frob-tooling-owned root manifest with the same never-referenced-by-source
    shape T-3019/T-3031 already exempted for pyproject.toml/frob.toml/package.json)
    plus fixtures missing the REF001=warn adoption-baseline T-3019 already added to
    test_cli_check.py''s own _make_project but never propagated to these sibling fixtures'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/system/test_cli_perf.py
  reason: 'T-3249: 5 of the 11-cluster failures are REF001 firing on tickets.md (a
    universal frob-tooling-owned root manifest with the same never-referenced-by-source
    shape T-3019/T-3031 already exempted for pyproject.toml/frob.toml/package.json)
    plus fixtures missing the REF001=warn adoption-baseline T-3019 already added to
    test_cli_check.py''s own _make_project but never propagated to these sibling fixtures'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/system/test_cli_native_missing.py
  reason: 'T-3249: 5 of the 11-cluster failures are REF001 firing on tickets.md (a
    universal frob-tooling-owned root manifest with the same never-referenced-by-source
    shape T-3019/T-3031 already exempted for pyproject.toml/frob.toml/package.json)
    plus fixtures missing the REF001=warn adoption-baseline T-3019 already added to
    test_cli_check.py''s own _make_project but never propagated to these sibling fixtures'
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-draft-db6c513a/**
  reason: draft tickets filed as follow-ups while working T-3249 for the 3 remaining
    root causes out of this ticket's own scope (native-missing SYS004 unhandled exception,
    render_lint pytest prefix loss, scaffold OPAQUE001/REF001); their own ticket.md
    files are otherwise flagged outside scope, same pattern T-3019 used for its own
    T-3028/29/30/31 follow-ups
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-draft-460d9c7e/**
  reason: draft tickets filed as follow-ups while working T-3249 for the 3 remaining
    root causes out of this ticket's own scope (native-missing SYS004 unhandled exception,
    render_lint pytest prefix loss, scaffold OPAQUE001/REF001); their own ticket.md
    files are otherwise flagged outside scope, same pattern T-3019 used for its own
    T-3028/29/30/31 follow-ups
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-draft-0ef9d7be/**
  reason: draft tickets filed as follow-ups while working T-3249 for the 3 remaining
    root causes out of this ticket's own scope (native-missing SYS004 unhandled exception,
    render_lint pytest prefix loss, scaffold OPAQUE001/REF001); their own ticket.md
    files are otherwise flagged outside scope, same pattern T-3019 used for its own
    T-3028/29/30/31 follow-ups
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: 'T-3249: recording the direct-measurement findings before close -- corrects
    T-2992''s own load/concurrency premise, states the answer to T-0089/T-0122 regression-vs-narrow
    question, and lists what was fixed here vs filed separately'
  actor: logan
  at: '2026-08-28'
  old_length: 3818
  new_length: 8640
evidence:
- tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_root_tickets_md_is_exempt_with_no_declaration
- tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_nested_tickets_md_still_subject_to_ref001
- tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
- tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
UNOWNED. T-2992's Done report attributes this cluster to T-3019 and states "NOT
double-filed, NOT double-fixed -- T-3019 owns this." BOTH HALVES OF THAT ARE
FALSE, measured 2026-08-28:

  - T-3019 was already DONE, landed at 0c4b152f5 on 2026-08-26 -- two days
    BEFORE the run that produced this histogram, and present in the tree that
    run measured (which was 2 commits behind main).
  - The cited repro, tests/system/test_cli_check.py::test_clean_code_exits_zero,
    PASSES in isolation on current main:
        SUITE-RESULT: exitstatus=0 collected=1 failed=0

So the cluster survived the fix it was attributed to, and has had no owner
since. Nothing is tracking it. I am filing it rather than leaving a closed
ticket's false reassurance standing.

THE CLUSTER (11 failures, from T-2992's Linux run of 12,035/12,039 tests, whose
Done report is on main at tickets/archive/T-2992/done-report.md):

    tests/system/test_cli_check.py            8
    tests/system/test_scaffold_dx.py          1
    tests/system/test_cli_native_missing.py   1
    tests/system/test_cli_perf.py             1

Reported symptom: `frob check` fires spurious REF001/PRE001/SCOPE001 on a
clean/scaffolded synthetic project.

THE CHARACTERISATION IN T-2992 IS WRONG AND MATTERS. It says these are spurious
findings "on any clean/scaffolded synthetic project". That predicts the repro
fails standalone. It does not -- it passes. The failures appear only in a
loaded, parallel, chunked run. So this is LOAD- OR CONCURRENCY-DEPENDENT, not a
property of clean projects. Anyone who takes the ticket on the original
description will try to reproduce it in isolation, succeed at passing, and
conclude it is fixed.

INDEPENDENTLY REPRODUCED ON CI. The 2026-08-28 CI run (ubuntu) failed exactly
this file set: test_cli_check.py (3), test_cli_native_missing.py (2),
test_cli_perf.py (3), test_scaffold_dx.py (1). Treat that run's list as
CORROBORATION OF THE FILE SET ONLY, not as counts -- it aborted with
exitstatus=3 (INTERNALERROR, see T-3246) so its numbers are a lower bound.

PRIOR ART, SAME SIGNATURE, ALREADY FIXED ONCE: T-0089 (done) is titled
"test_scaffold_dx flaky under full-suite run, passes in isolation" and its
recorded evidence is
tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
-- the very test failing again here. T-0089 was blocked_by T-0122 ("frob check
races concurrent build_graph calls against shared .frob/cache.db", also done).
Read both before starting. Either their fix regressed, or it was narrower than
the class. Determining WHICH is the first job; do not assume regression.

LIKELY DIRECTION, NOT VERIFIED -- MEASURE IT: shared mutable state across
concurrently-running system tests. `.frob/cache.db`, the graph cache, a memo
layer, or cwd contention are the candidates T-0122 already implicated. Several
tickets this drive asserted a cause that was never verified; do not add another.

DO NOT FIX THIS BY MARKING THE TESTS FLAKY, RETRYING THEM, OR SERIALISING THEM
AWAY. If `frob check` reports findings that depend on whether another check is
running concurrently, that is a product defect and users hit it -- the tests are
the messenger. A retry decorator would hide the only detector we have.

ACCEPTANCE
- A reproduction under load, with the exact command and the conditions needed.
  "Passes in isolation" is a required part of the repro, not a caveat.
- Root cause identified with evidence, and a stated answer to whether T-0089/
  T-0122's fix regressed or was too narrow.
- A fix in the product where the defect is in the product.
- A regression test that fails under the concurrent conditions before the fix.
- T-2992's false attribution corrected -- but its Done report is on main as a
  historical artifact and must NOT be rewritten. Record the correction here.


CORRECTION -- T-2992's characterization of this cluster is wrong in a
SECOND way, beyond the T-3019 misattribution T-2992's own filing already
flagged this ticket for:

T-2992/T-3249's shared premise -- "spurious REF001/PRE001/SCOPE001 ...
only under concurrent load" / "LOAD- OR CONCURRENCY-DEPENDENT, not a
property of clean projects" -- is FALSE for the majority of this
cluster. Measured directly: all 7 of the 11 node ids I could still
reproduce (the other 4 named in T-3019's own evidence list -- 
test_clean_code_exits_zero, test_skip_ruff, test_skip_exports,
test_only_gates_passes_once_bound_and_tested -- pass cleanly, both
serially and under load, confirming T-3019's fix holds) FAIL
DETERMINISTICALLY in plain serial isolation (`pytest -p no:xdist`, one
worker, no other process running, no `yes>/dev/null` CPU load) on
unmodified main:

  tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
  tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
  tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
  tests/system/test_cli_perf.py::TestCheckOnlyPerf::test_perf001_fixture_warns_but_check_exits_zero
  tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
  tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present
  tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately

I also reproduced them under load (12-core box, `yes >/dev/null` x6 +
`pytest -n 6 --dist=loadgroup`, twice) -- the SAME 7 fail, no more, no
fewer. Load changes nothing about which tests fail here. This directly
falsifies "passes in isolation" / "load-dependent" for this majority of
the cluster; T-2992's histogram entry A conflated at least 5 distinct,
unrelated, load-INDEPENDENT root causes into one "concurrency" bucket
because its own repro (test_clean_code_exits_zero only) happened to be
one of the few genuinely fixed-by-T-3019, passes-everywhere tests in the
group, and the rest were never individually re-run before filing.

T-0089/T-0122's fix (the swallowed-summary/quiet_stdout_logs race):
CONFIRMED STILL WORKING, NEITHER REGRESSED NOR TOO NARROW. Direct
concurrent-load repro of test_scaffold_dx.py's exact node id shows a
COMPLETE, well-formed check report every time (no missing summary line,
no swallowed output) -- it fails today for a wholly different reason (a
real OPAQUE001 finding whose message text does not match its own cited
line, plus REF001 on the scaffold's own generated root files). The
"passes in isolation" claim in this ticket's own body, inherited from
T-2992, is TRUE ONLY for test_clean_code_exits_zero; every other node id
in T-2992's histogram entry A needed direct root-causing, which is what
this ticket did.

Root cause and fix, IN this ticket's scope (2 of the ~5 real causes):

1. `_STAGE_GROUPS` (src/frob/check/__init__.py) never listed
   `comment_placement` (CPLACE001/CPLACE002, added by T-3218) in any
   group -- the exact same registered-but-unreachable omission shape
   T-3030 already fixed for 5 other gates (milestone, env_var_docs,
   root_asset_dirs, profile_boundary, narrative_blocks), just not
   extended to this later-added gate. Fixed by adding it to gates-fast
   (thread-pool, sub-second, not in `_PROCESS_POOL_GATES`, same as its
   siblings).

2. `_DEFAULT_ROOT_MANIFEST_EXEMPT` (src/frob/gates/_refs.py) never
   included `tickets.md` -- ledger-v1's own universal, exactly-one-per-
   repo ticket ledger, read only by frob tooling, the identical shape
   already exempted for pyproject.toml/frob.toml/package.json/
   tsconfig.json (T-3019/T-3031). Fixed by adding it. Also propagated
   T-3019's own established `REF001 = "warn"` adoption-baseline pattern
   (already used by test_cli_check.py's `_make_project`) to the two
   sibling fixtures that never got it (`_init_perf001_fixture_repo`,
   `_init_no_design_repo`) -- their own package/coverage-artifact files
   are genuine REF001 orphans by that gate's own design, same reasoning
   T-3019 already gave for `_make_project`'s own fixture package.

The remaining ~3 real root causes (TestCheckTicketLeasePinRefusal --
already covered by the existing QUEUED, unowned T-3028; the native-
missing SYS004 unhandled-exception crash; the render_lint pytest-mode
logging-prefix loss; the scaffold OPAQUE001 message mismatch + REF001
gaps) are each a genuinely separate, unrelated defect in a different
module, filed as their own tickets rather than force-fit into this
one's scope (see Filed below) -- same practice T-3019 itself used
(T-3028/29/30/31) and T-2992 used (T-3033..T-3041).

---
id: T-2971
title: Re-measure macOS CI after T-2943/T-2969 land
state: done
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- N/A
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-2971: fresh macOS CI re-measurement post T-2943/T-2969, per acceptance
    criterion'
  actor: logan
  at: '2026-08-28'
  old_length: 712
  new_length: 6751
evidence:
- cmd:/tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/t2971_evidence_check.sh
  exit=0 sha256=5c545b9f4724
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 013c97097502a2e7d1a22e51378a1eacb60a24d1
---
T-2969 audited all 12 candidate test_cli_*.py files for the T-2943
missing-git-init pattern and found none of them carry it (see T-2969's
Done report for the full per-file table). T-2969's acceptance item 2
asked for a real macOS CI run, post T-2943's land, to re-measure whether
the 156-failure macOS baseline shrank as expected and to check whether
any of the 12 candidate files still fail there specifically as a genuine
macOS-only remainder. That requires triggering/observing an actual macOS
CI run, which a worktree agent cannot do. File this as a coordinator-only
follow-up: trigger a macOS CI run on current main and compare the new
failure count/composition against the pre-T-2943 156-failure baseline.


RE-MEASURED (T-2971 acceptance): CI run 33135896391, job 98735671710
(macos-latest), Test stage. Fresh command used:
  gh run view --job 98735671710 --log-failed
  grep SUITE-RESULT-FAILED / grep "^build.*FAILED tests"

RESULT: `SUITE-RESULT: exitstatus=1 collected=12346 failed=68`.

68 is a genuine, substantial improvement over the pre-T-2943 156-failure
baseline this ticket exists to compare against -- roughly a 56% drop,
consistent with T-2943's own fix plus the two macOS clusters CY already
fixed separately (a hardcoded /proc/self/fd path, a too-tight perf
threshold) and the third CY found already tracked by T-2676. Both Lint
and Typecheck PASSED on macOS in this same run; only Test failed.

SPLIT: genuine repo findings vs a platform difference in the gate
machinery itself -- MEASURED per cluster, not inferred as a blanket
answer, since both kinds are present:

1. GENUINE repo findings (~10 of 68), not macOS-specific: the
   self-conformance/registry family --
   tests/unit/strata/test_selfconform.py (TestRealGateGreen,
   TestCoverageTotality), test_conform_eval_needle.py,
   test_sys003_calibration.py, test_frob_self_model.py
   (test_sys_gate_zero_violations), test_docptr_gate.py, test_gates.py
   (test_every_emitted_rule_literal_is_known),
   test_check_coverage_registry.py (both tests), test_waive_gate.py
   (WAIVE006), test_registry_exhaustiveness.py (REG008). Read
   `check_self_conformance`'s own docstring
   (src/frob/strata/_selfconform.py): SYS100/SYS003/DOC004/DOC006/REG008/
   WAIVE006 are all LANGUAGE-GENERIC PATTERN scanners over checked-in
   source TEXT (`_effects.py::_line_effects` uses `language_for`/
   `_PATTERNS`, explicitly not Python-AST-specific) -- their output is a
   pure function of the committed source, invariant to which OS or
   Python interpreter runs the scan. These are real, pre-existing
   capability-declaration/import-boundary/waiver-staleness gaps in this
   repo's own `design/frob.strata` model that were simply never observed
   on a completing macOS (or any) CI run before now, not something
   macOS's platform uniquely produces. Belongs to T-2992's triage queue
   (or a dedicated design-model-drift ticket), not treated as a macOS
   quirk.

2. LIKELY a platform/environment difference in the gate MACHINERY
   (~15 of 68), not genuine repo findings: tests/test_tickets_live_
   tracker.py (9 of its TestLiveTrackerCitations cases, all failing the
   identical shape "assert 0 == N" -- expected N citation hits, found
   zero), tests/unit/test_land_finish_guard.py (4 cases, all about
   detecting a live process cwd'd into a worktree),
   tests/test_ticket_leases.py::TestRemoveWorktree::
   test_keeps_a_live_process_worktree and tests/test_worktree_guard.py::
   TestSweepWorktreesLiveProcess::test_clean_no_lease_recent_head_live_
   process_kept (both "assert 'removed' == 'kept:live'" -- the SAME
   shape as the land_finish_guard cluster: a live process is expected to
   be detected as still-live and is not). The live-tracker cluster's
   9-for-9 identical "0 hits" shape and the process-liveness cluster's
   6-for-6 identical "removed vs kept:live" shape are each far too
   uniform to be six/nine independent real repo defects -- both point at
   ONE shared mechanism each behaving differently on macOS: live_tracker_
   citations (src/frob/tickets/_live_tracker.py) shells out to `git grep`
   against a test-fixture repo (macOS's differing default git config --
   e.g. core.ignoreCase, or a missing default commit identity in a fresh
   fixture repo -- is a known class of exactly this failure shape); the
   liveness cluster is a live-process-detection probe whose exact
   mechanism was NOT re-derived here (out of this ticket's own
   no_scope_declared investigation-only scope) but shares the same "runs
   fine on Linux, empty/false on macOS" signature as T-3191's own
   Windows-inverted findings -- worth checking for a POSIX-shaped
   assumption (e.g. `/proc`-based liveness, which does not exist on
   macOS/BSD at all) the same way T-3191 found for Windows. NOT
   confirmed by building/running on an actual macOS box (unavailable to
   a Linux-hosted agent) -- flagged as the leading hypothesis from
   reading the source and the failure shapes, for whoever triages this
   next to verify.

3. MIXED / needs individual triage (~43 of 68): native-extension-
   availability edge cases (test_cli_native_missing.py,
   test_natives_build_integration.py -- cargo/rust build output
   assertions), golden-file byte-diffs (test_export_golden.py, 3 cases),
   JSON-parser round-trip failures (test_parse.py, 2 cases), CRLF/
   autocrlf handling (test_gitattributes_merge.py -- macOS's own
   git-on-APFS default could matter here too), and a grab-bag of
   single-instance failures elsewhere. Not characterized further here --
   T-2971's own acceptance was RE-MEASURING and reporting the count/split,
   not resolving the backlog; per-failure triage is T-2992's job (already
   queued, `no_scope_declared_reason` there says exactly this: "file
   per-failure tickets once a clean unscoped run exists").

CROSS-REFERENCE with T-2992 (Linux hang triage): T-2980 already fixed the
Linux hang; T-2992 is still queued for the Linux full-suite failure list,
which has not yet been captured from a clean, uncontended run (per its
own body). No confirmed overlap measured yet between the macOS 68 and a
Linux failure list, since the latter does not exist yet -- both tickets
should re-cross-reference once T-2992 gets its own clean run.

CONCLUSION: the 156 -> 68 shrink is real and expected. The self-
conformance family (~10) is genuine, platform-invariant repo debt. The
live-tracker/process-liveness family (~15) is very likely a macOS-
specific bug in frob's OWN gate/land machinery, not a repo finding --
flagged with a concrete hypothesis for follow-up, not filed as a new
ticket here per this ticket's own instruction to update rather than
duplicate. The remainder needs T-2992's per-failure triage once that
ticket gets its clean run.
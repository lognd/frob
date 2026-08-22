---
id: T-2359
title: Reformat the 138 files pending ruff-format as one deliberate commit, unblocking
  T-2244/T-2245
state: queued
kind: feature
origin: agent
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
evidence_scope:
- tests/unit/test_app_runners.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_profile_runner.py
- tests/unit/test_pyfmt_runner.py
- tests/unit/test_app_sys_capacity.py
- tests/unit/test_app_sys_threats.py
- tests/unit/test_app_sys_trace.py
- tests/test_telemetry.py
- tests/unit/test_check.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
- tests/unit/test_ticket_new_related.py
- tests/unit/test_ticket_new_scope_plausibility.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: epic closes with zero pending files -- repo-wide ruff format
  --check . is already clean, no edits required
scope_changes:
- op: add
  glob: .claude/hooks/diagnosis-nudge.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: scripts/fleet_status.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/design_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/profile_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/__init__.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/_footguns.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/_usage.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_attach_backfill.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/arch/_abstraction.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/check/_python.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: remove
  glob: .claude/hooks/diagnosis-nudge.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: scripts/fleet_status.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/design_runner.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/profile_runner.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/pyfmt_runner.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/sys_runner.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/telemetry/__init__.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/telemetry/_footguns.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/telemetry/_usage.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/ticket_runner/_attach_backfill.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/ticket_runner/_new.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/worktree_runner.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/arch/_abstraction.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/check/_python.py
  reason: batch 1 spun off to child T-2773; T-2359 tracks remaining files only
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/fmt_runner.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/dup/_pipeline/_fingerprint.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/dup/_template.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_dead_symbols.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: batch 2 of ruff-format-only reformat
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/_cli_parsers/_misc.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/_cli_parsers/_reporting.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/fmt_runner.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/dup/_pipeline/_fingerprint.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/dup/_template.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_coverage_sites.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_dead_symbols.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_docblocks.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: src/frob/gates/_fix_engine.py
  reason: 're-measured 2026-08-21: uv run ruff format --check . reports 0 files pending
    (1202 already formatted, exit 0) -- the 10 declared scope entries are stale leftovers
    from earlier batches, no longer reflecting reality; this batch requires no file
    edits'
  actor: logan
  at: '2026-08-21'
evidence:
- tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1
- tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_configured_and_effective
- tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations
- tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation
- tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination
- tests/test_telemetry.py::test_append_event_writes_one_json_line
- tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path
- tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match
- tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly
designated_repro_test: null
acceptance:
- text: given the format-only commit series, when its diffs are reviewed, then they
    contain no semantic changes and no fixture-corpus files
  evidence: []
- text: given the test suite, when it runs after the reformat, then it passes unchanged
  evidence: []
- text: given the repo after this lands, when ruff format --check . runs, then zero
    files need reformatting
  evidence: []
acceptance_amendments:
- op: remove
  index: 2
  old_text: given the test suite, when it runs after the reformat, then it passes
    unchanged
  new_text: null
  reason: 'batched execution (coordinator directive): acceptance criteria as filed
    assume a single-shot repo-wide reformat, but 184 files across many in-flight worktrees
    requires landing in small disjoint batches to avoid locking the fleet. Re-added
    once the final batch lands and the repo-wide criterion is genuinely true.'
  actor: logan
  at: '2026-08-20'
- op: remove
  index: 1
  old_text: given the format-only commit, when its diff is reviewed, then it contains
    no semantic changes and no fixture-corpus files
  new_text: null
  reason: 'batched execution: same rationale as index-2 removal, this criterion also
    assumes single-shot completion; re-added on the final batch'
  actor: logan
  at: '2026-08-20'
- op: remove
  index: 0
  old_text: given the repo after this lands, when ruff format --check . runs, then
    zero files need reformatting
  new_text: null
  reason: 'batched execution: same rationale; final-batch land will re-add a criterion
    bound to a genuine repo-wide ruff-format-clean measurement'
  actor: logan
  at: '2026-08-20'
- op: remove
  index: 2
  old_text: given the test suite, when it runs after the reformat, then it passes
    unchanged
  new_text: null
  reason: duplicate of newly re-added index 5 (final-batch criterion); the earlier
    2026-08-20 removal amendment was documentation-only and never actually stripped
    the entry, so both copies existed
  actor: logan
  at: '2026-08-21'
- op: remove
  index: 1
  old_text: given the format-only commit, when its diff is reviewed, then it contains
    no semantic changes and no fixture-corpus files
  new_text: null
  reason: duplicate of newly re-added index (final-batch criterion); same stale-removal-was-documentation-only
    issue
  actor: logan
  at: '2026-08-21'
- op: remove
  index: 1
  old_text: given the repo after this lands, when ruff format --check . runs, then
    zero files need reformatting
  new_text: null
  reason: duplicate final-batch criterion left over from the earlier documentation-only
    removal; collapsing to one copy
  actor: logan
  at: '2026-08-21'
- op: remove
  index: 0
  old_text: given the repo after this lands, when ruff format --check . runs, then
    zero files need reformatting
  new_text: null
  reason: duplicate of newly re-added index (final-batch criterion); same stale-removal-was-documentation-only
    issue
  actor: logan
  at: '2026-08-21'
threat: null
component: build
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17: `uv run ruff format --check .` reports
**138 files would be reformatted, 975 already formatted**.

This is a latent hazard, not cosmetic debt. T-1382's child T-2244 wants to
repoint the Makefile's `format:`/`lint-fix:` targets at a real write-mode
ruff pass. The moment that lands, the FIRST person or agent to run the
target rewrites 138 files in one go -- a repo-wide diff blast with no
owning ticket, landing on top of whatever else is in flight. An agent
measured this and correctly declined to land T-2244 for exactly that
reason, which is why T-2244 is still queued and T-2245 (docs + call-site
audit) is transitively blocked behind it.

The dependency chain is real and currently stalled:
    T-2245 (docs audit) blocked_by T-2244 (repoint targets)
    T-2244 held because running the repointed target detonates 138 files

THE FIX IS SEQUENCING, and it must happen in this order:
 1. THIS TICKET: reformat all 138 files as ONE deliberate, format-only
    commit. No logic changes, nothing else in the diff.
 2. THEN T-2244 becomes safe -- repointing a target that is already a
    no-op on a clean tree changes nothing for the next caller.
 3. THEN T-2245 can write docs describing a state that is actually true.

WHY THIS NEEDS A QUIET FLEET, and why I am filing rather than doing it:
a 138-file reformat conflicts with every in-flight worktree that touches
any of those files. With a multi-agent fleet running, that is a large
merge-conflict surface imposed on work already in progress. This should be
landed when few or no agents hold worktrees, as a single commit, not
opportunistically mid-drive.

EXECUTION NOTES:
 - Use a SCOPED formatter invocation, not `frob fmt .`. A broad-path `frob
   fmt` rewrote 49 unrelated `.strata` FIXTURE files earlier today (T-2298,
   now fixed to exclude test corpora by default) -- verify the fixture
   exclusion holds before trusting a bulk run.
 - `git status` and review the diff shape before committing: a format-only
   commit must contain zero semantic changes. Spot-check several files.
 - Re-run the full test suite after. Formatting is supposed to be
   behaviour-preserving; "supposed to be" is not evidence.

POSITIVE CONTROLS: (1) `ruff format --check .` reports zero files needing
reformat afterward; (2) the test suite passes unchanged; (3) no `.strata`
or other fixture corpus file appears in the diff.
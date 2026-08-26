---
id: T-2929
title: rapid verification debt drifts silently and poisons attribution (post-land
  sweep files false regressions on a stale baseline)
state: done
kind: bug
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
- rapid-debt.jsonl
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: new debt-kind write and its doc anchor
  actor: logan
  at: '2026-08-25'
- op: add
  glob: rapid-debt.jsonl
  reason: new debt-kind write and its doc anchor
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: new debt-kind write and its doc anchor
  actor: logan
  at: '2026-08-25'
- op: add
  glob: rapid-debt.jsonl
  reason: new debt-kind write and its doc anchor
  actor: logan
  at: '2026-08-25'
- op: add
  glob: frob.lock
  reason: frob ack writes doc-drift acknowledgements to frob.lock
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt
- tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_fresh_baseline_files_normally_no_new_noise
designated_repro_test: tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED EVIDENCE:
  - `frob verify status` (2026-08-25, mid-drive) reported watermark age
    7,304s and 53 commits since watermark, unverified depth 4, oldest
    unverified entry 7,308s old. `rapid`'s own soft-warn thresholds
    (`frob.verify._backpressure._RAPID_SOFT_WARN_DEPTH`/`_AGE_S`) are 5
    commits / 3600s -- so the debt was roughly 10x past both thresholds
    and the ONLY consequence was a WARNING line nobody acted on
    (`rapid_soft_warning` never blocks a land, by design, T-2290).
  - The consequence is not cosmetic. `frob.app.ticket_runner._rapid_sweep.
    run_deferred_post_land_sweep` diffs the fresh unscoped-check error set
    against `.frob/rapid-sweep-baseline.json` and files a "post-land sweep
    regression" ticket for anything new, with no awareness of how stale
    the `frob.verify` watermark is at the moment it runs. Across this
    drive four such tickets were filed: T-2868, T-2881, T-2882 (all
    DOC006 dangling-doc-pointer findings on `tickets/T-####/ticket.md`
    paths) were dropped after independent measurement showed them
    pre-existing/attributable to ticket-ledger churn, not the land the
    sweep pinned them on; T-2899 (an I001 ruff-import-sort finding) was a
    GENUINE regression and was fixed. 3 of 4 -- real reviewer time and
    real agent tokens burned on phantom regressions, while the sweep's
    underlying DETECTION (the set-diff itself) is sound: the fourth case
    proves it catches real regressions fine.

ROOT CAUSE: `run_deferred_post_land_sweep` files a regression ticket
purely from its own rolling baseline diff (`fresh - baseline`), with zero
reference to `frob.verify`'s independently-computed watermark staleness
signal (`frob.verify.rapid_soft_warning`) that already exists elsewhere
in this same codebase for exactly this condition. A wide gap between the
rolling baseline and HEAD (or a stale `frob.verify` watermark, the same
underlying "how much unverified history is behind us" fact) means the
diff spans many commits and many unrelated ticket-ledger events, exactly
the conditions under which a doc-drift finding (DOC006 in particular,
which flips on/off as OTHER tickets get archived, not as code changes)
looks "new" without actually being caused by the land the sweep pins it
on. This is a silent-zero-class failure per the standing directive: a
CONFIDENT wrong answer (a filed, high-priority regression ticket naming a
specific land), not a visible error.

FIX, in order:
  (a) Drain the current debt with `frob verify now` (a single long-running
      foreground call, `timeout 540` shell wrapper + 600000ms tool
      timeout) and report the real before/after numbers -- if one pass
      cannot fully drain it, say so with the exact remaining depth/age,
      never loop it silently.
  (b) Escalate the staleness signal so it is impossible to ignore. Chosen
      option (of the three the coordinator offered: hard-error past a
      threshold / auto-drain / refuse-to-attribute): REFUSE TO ATTRIBUTE.
      `run_deferred_post_land_sweep` checks `frob.verify.rapid_soft_
      warning(root)` immediately before it would otherwise call `_file_
      regression_ticket`; when it fires, the sweep does NOT file a
      regression ticket for the new findings this pass -- it logs the
      refusal at ERROR (loud, same severity a filed regression already
      used) naming the exact staleness reason, and records a NEW
      `rapid-debt.jsonl` entry kind (`post-land-sweep-attribution-
      skipped-stale-baseline`) via the same `record_rapid_debt`/
      `_commit_rapid_debt` idiom `spawn_deferred_post_land_sweep` already
      uses, so the skip is durable and reviewable, not merely a log line
      that scrolls away. The rolling baseline is still rewritten to the
      freshly measured set either way (unchanged existing behavior) --
      only the CONFIDENT-TICKET step is gated, so the next sweep (once
      the debt is drained) compares against a clean, current baseline
      rather than compounding the stale window further.
      WHY THIS OPTION over the other two: a hard error at land time would
      violate rapid's own "never blocks" contract (T-1692's explicit
      design decision, not something to relitigate here) and a land
      commit that already succeeded should not be retroactively punished
      for debt accrued mostly by OTHER concurrent lands sharing the same
      root. Auto-drain from inside the sweep would make an already
      resource-contended detached child (competing with N other lands'
      own detached sweeps on the same box, per this drive's own measured
      "concurrent lands thrash" finding) responsible for draining a
      cross-cutting debt it did not create and has no special leverage
      to fix quickly. Refuse-to-attribute is the option that fixes the
      actual observed harm (false regression tickets) at the exact point
      it is produced, costs nothing extra in CPU/time, and leaves the
      real fix (draining the debt) to `frob verify now`, which is already
      the correct, existing tool for the job.
  (c) Prove both directions: a must-fire unit test (stale baseline
      present -> `run_deferred_post_land_sweep` skips filing and records
      the new debt kind) and a must-stay-quiet unit test (fresh baseline
      -> sweep files a regression ticket exactly as before, no new noise
      introduced). Re-measure `frob check`'s repo-wide finding counts
      before and after this change to confirm no new warning stream was
      added by the fix itself.

Scope: src/frob/app/ticket_runner/_rapid_sweep.py (the filing decision),
tests/unit/test_rapid_sweep.py (both proof directions).
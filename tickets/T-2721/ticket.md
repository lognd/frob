---
id: T-2721
title: waive-audit progress is gitignored per-checkout, so an agent's audit pass is
  destroyed with its worktree
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive_audit_watermark.py
- tests/unit/test_waive_audit_watermark.py
- .gitignore
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive_audit_watermark.py
  reason: narrow to the watermark persistence module fixing T-2721, its tests, and
    gitignore
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_waive_audit_watermark.py
  reason: narrow to the watermark persistence module fixing T-2721, its tests, and
    gitignore
  actor: logan
  at: '2026-08-20'
- op: add
  glob: .gitignore
  reason: narrow to the watermark persistence module fixing T-2721, its tests, and
    gitignore
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_waive_audit_watermark.py::TestSaveWatermarkGitTracking::test_commits_the_watermark_in_a_real_repo
- tests/unit/test_waive_audit_watermark.py::TestSaveWatermarkGitTracking::test_second_save_advances_with_its_own_commit
- tests/unit/test_waive_audit_watermark.py::TestSaveWatermarkGitTracking::test_non_git_root_still_succeeds_on_disk
- tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_worktree_pass_reaches_primary_without_a_land
- tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_two_worktree_passes_do_not_lose_either_ones_progress
- tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_calling_from_the_primary_checkout_itself_mirrors_nothing_extra
designated_repro_test: tests/unit/test_waive_audit_watermark.py::TestMirrorToPrimary::test_worktree_pass_reaches_primary_without_a_land
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 10faf35e2d7ac81c8d018323853f7cf8d522ca4a
---
## Measured, 2026-08-20

`frob ticket waive-audit` records its progress in
`.frob/waive-audit-watermark.json`. `.frob/` is gitignored
(`.gitignore:87`), so that state is PER-CHECKOUT and never reaches main.

Agents work in DISPOSABLE worktrees. So an audit pass run by an agent
records its progress only inside a directory that is deleted on cleanup.

Caught live: T-1614's pass classified 100 waiver directives (0 cop-outs,
100 judged still-necessary-and-honest). Afterwards:

    .claude/worktrees/t-1614/.frob/waive-audit-watermark.json   5113 bytes
    .frob/waive-audit-watermark.json                            ABSENT

A `waive-audit scan` from the primary checkout reported
`not_covered=967`. After copying the worktree's watermark to the root it
reported `not_covered=867` -- proving the 100 classifications were
genuinely absent from the root and would have been destroyed with the
worktree. I preserved that file by hand; the next agent will not know to.

## Why this defeats the mechanism's own purpose

T-2467 replaced T-1614's unreachable `runs_last` design with a PERIODIC,
watermark-based audit precisely so the work could be done incrementally
across many passes. That only works if progress accumulates. As built,
every pass run by an agent silently resets to zero when its worktree is
removed, so the 1067-directive backlog can never be driven down -- each
pass re-scans the same head of the list.

Note this is also invisible: nothing warns that progress is about to be
discarded, and the next scan simply reports the old denominator.

## What to decide

The watermark is audit BOOKKEEPING, not build output -- it is closer to
the ticket ledger than to a cache. Options:

(a) track it in git like the ledger, so progress is shared and durable;
(b) keep it gitignored but have `frob ticket land`/`--finish` mirror it to
    the primary checkout the way ledger writes are already mirrored;
(c) keep it per-checkout but make `waive-audit complete` REFUSE, loudly,
    when run from a worktree whose state will not survive -- least useful,
    but better than silent loss.

Prefer (a) or (b). If (a), consider whether a shared watermark needs
merge semantics (append-only union, like `rapid-debt.jsonl`) so two
concurrent passes do not clobber each other -- and note `union` is only
correct if the file is genuinely append-only; verify before copying that
pattern.

## Positive controls, both directions

- an audit pass run inside a worktree, followed by worktree removal,
  leaves the root's `not_covered` count REDUCED by that pass
- a pass that classifies nothing does not advance the watermark
- two passes in different worktrees do not lose either one's progress

## Related

The same "state written where it will not survive" shape as the unlanded
-work leak: work that is complete but lives only on a disposable branch
or directory is invisible and gets swept. See T-2711 for the ledger-state
analogue.
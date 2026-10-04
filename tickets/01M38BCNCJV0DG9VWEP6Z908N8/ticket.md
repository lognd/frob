+++
id = "01M38BCNCJV0DG9VWEP6Z908N8"
title = "land CAS: apply-failed ledger-only rebase must fall back to full recompose, not refuse (T-5491 follow-up)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5522"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/tickets/_land_squash.py", "tests/unit/test_land_cas_ledger_retry.py"]
+++

Measured on T-5477's own land (dev advanced by ONE ledger-only commit, chore(tickets): mirror body T-5444 from worktree; /tmp/land-T-3010.log lines ~31200-31255): _attempt_ledger_only_rebase (T-5491/src/frob/tickets/_land_squash.py) retried the apply attempt 5 times against the SAME sibling tip, each logging 'did not apply cleanly (ComposeFailed: building the out-of-tree commit ...)' followed by 'falling back to full recompose', then after attempt 5 the land refused with the CAS-miss message -- the announced full recompose never actually ran. Retrying an IDENTICAL apply against an UNCHANGED tip is deterministic (it will fail the same way every time), so all 5 attempts were wasted and the promised fallback (a real re-merge/re-squash/re-check/publish cycle against the sibling's current tip, not a diff-and-apply rebase) never happened.

Fix: the apply_failed branch in _publish_with_ledger_only_retry/_attempt_ledger_only_rebase must perform the ACTUAL full recompose (re-merge current tip into the worktree, re-squash, re-run the composed-tree check, publish) instead of retrying the same diff-and-apply rebase against an unchanged tip -- bounded by the existing drift-proportional retry limit, refusing only if the recompose itself conflicts (a genuine, unresolvable content conflict), not merely because the cheaper diff-and-apply shortcut failed.

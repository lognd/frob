---
id: T-2737
title: rapid-debt.jsonl dirt from a failed land defeats _check_already_landed's dirty-worktree
  guard
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_already_landed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: stale rapid-debt.jsonl dirt defeats _check_already_landed dirty guard
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_land_already_landed.py
  reason: stale rapid-debt.jsonl dirt defeats _check_already_landed dirty guard
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/tickets/_land.py
  reason: stale rapid-debt.jsonl dirt defeats _check_already_landed dirty guard
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_land_already_landed.py
  reason: stale rapid-debt.jsonl dirt defeats _check_already_landed dirty guard
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_clean_worktree_reads_as_clean
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_sole_rapid_debt_dirt_reads_as_clean
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_rapid_debt_plus_another_file_still_reads_dirty
- tests/unit/test_land_already_landed.py::TestDirtyIgnoringRapidDebt::test_a_different_lone_dirty_file_still_reads_dirty
- tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_stale_rapid_debt_dirt_does_not_block_already_landed_detection
- tests/unit/test_land_already_landed.py::TestAlreadyLandedStaleRapidDebtDirt::test_genuine_uncommitted_code_change_still_defers_even_with_stale_rapid_debt_dirt
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reproduced LIVE, TWICE, not reasoned about -- while actually landing
T-2718 in the T-2711/T-2718 series worktree (2026-08-20).

Both occurrences happened during real `frob ticket land T-2718` /
`frob ticket close T-2718` attempts against the shared worktree, not in
a test or a hypothetical:

Occurrence 1: after T-2711 landed (carrying T-2718's own fix as a
passenger via `--allow-cross-ticket`), `frob ticket land T-2718` on the
SAME worktree hit BUG002 (designated repro now passes at parent --
confirmatory-only, exactly the shape T-2711's own `_check_already_
landed` fix exists to catch and redirect to "close directly"). It did
NOT fire. `git status --porcelain` immediately after showed `rapid-
debt.jsonl` modified -- a row appended by the PRIOR failed land attempt
and left uncommitted. `_porcelain_dirty` saw real dirt (correctly, by
its own contract) and `_check_already_landed` deferred to the normal
pipeline, which then hit BUG002.

Occurrence 2: after committing that dirt and retrying, the SAME
sequence reproduced a second time in the same session -- another failed
land attempt (killed by the 540s shell timeout under heavy fleet load)
left ANOTHER uncommitted row in `rapid-debt.jsonl`, and the retried
`frob ticket land T-2718` again fell through `_check_already_landed`'s
dirty check straight into BUG002, confirmed by direct inspection
(`_check_already_landed(Path('.'), ticket, 'main')` returned `Ok(None)`
while `git diff main -- <T-2718's own scope files>` was independently
confirmed EMPTY by hand at the same moment).

A defect that fires during the land of its own companion fix, twice,
in the same session, is about as strong as evidence gets that this is
live and not theoretical.

Root cause: `_check_already_landed`'s dirty-worktree guard
(`_porcelain_dirty`) correctly no-ops when the worktree has real
uncommitted work, but it also fires on a completely mechanical,
land-owned artifact -- `rapid-debt.jsonl` -- that a PRIOR failed land
attempt writes into the worktree and leaves uncommitted (the rapid
profile's own debt-tracking append, not anything the agent touched).
The dirt itself is legitimate (land's own bookkeeping); its
un-committed-ness is an ARTIFACT of the previous failed attempt, not
disqualifying real work -- the dirty check cannot tell the two apart
today.

Fix direction: either (a) `_porcelain_dirty`'s callers exclude
land-owned bookkeeping paths (`rapid-debt.jsonl`, mirroring how
`LEDGER_PATH`/archive paths are already excluded from the SCOPE-diff
computation in `_check_already_landed` -- a different but adjacent
exclusion) from the dirty check specifically for `_check_already_
landed`, or (b) land itself commits `rapid-debt.jsonl` immediately
after appending to it on a failed attempt, so it never sits uncommitted
between land invocations.

Positive control: a worktree with genuine uncommitted CODE changes must
still defer (no false already-landed positive); a worktree dirty ONLY
on `rapid-debt.jsonl` from a prior failed land must not block the
already-landed detection.

Original draft T-draft-cf0b0af7 (filed 2026-08-20 from the T-2711/T-2718
series worktree, branch `t-2711`, commit ce1f406d3) never reached main --
the worktree closed T-2718 directly rather than landing it, so the draft
was never promoted/renumbered. Recovered and refiled here verbatim, with
the live-reproduction detail added, per the coordinator's request that
this record state it was reproduced live rather than reasoned about.
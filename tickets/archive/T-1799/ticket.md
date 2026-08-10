---
id: T-1799
title: DirtyMain/OutOfScopeWaiveDeletion refusals misattribute the writer -- surface
  actual identity, not a file-history guess
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: unit tests for _commits_touching_path and the OutOfScopeWaiveDeletion refusal
    message it feeds
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_ticket_land.py::TestCommitsTouchingPath::test_names_the_real_commit_that_touched_the_file
- tests/test_ticket_land.py::TestCommitsTouchingPath::test_empty_when_the_path_was_never_touched
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
designated_repro_test: null
threat: null
component: null
---
`frob ticket land`'s `DirtyMain`/`OutOfScopeWaiveDeletion` refusal
messages name a ticket id as the likely owner of uncommitted/dirty root
state, guessed from the dirty file's usual owner (recent git history/
file-to-ticket association heuristics), not from who actually staged or
wrote the uncommitted change. Observed today (T-1758's own investigation):
land blamed T-1699/T-1755 for dirt that direct investigation traced to
T-1222's detached post-land sweep child failing to commit its own
`rapid-debt.jsonl` write. Three separate agents were sent to debug the
wrong ticket before a human intervention corrected the trail.

T-1758 fixed the STRUCTURAL cause for `new_ticket`'s own callers (the
write boundary now auto-commits, so a `new_ticket`-originated write can
no longer be the source of this class of dirt going forward). This
ticket is about the SEPARATE, still-open problem: when SOME OTHER
process (a detached sweep, a stray `git add`, a manual write) leaves root
dirty, the failure message that surfaces should name the actual writer,
not a heuristic guess.

Investigate whether the actual writer identity is available at the
point of failure:
- `git status --porcelain`/`git diff --cached` on the dirty paths, at
  minimum, tells you WHAT changed -- cross-reference against
  `.frob/rapid-sweep/*.log` (detached sweep logs already name their own
  ticket id and pid) and any other known async ledger-writing process to
  attribute correctly BEFORE guessing from file-ownership history.
- If a detached child (rapid sweep, mutation sweep queue, etc.) is the
  actual writer, its own log/pid should be surfaced directly in the
  refusal message instead of (or alongside) the heuristic guess.
- Consider whether the heuristic guess should be labeled explicitly as
  a guess ("likely T-XXXX, based on recent file history -- verify before
  debugging") rather than presented as a determined fact, so a human/
  agent reading it does not spend time on a wrong lead the way this
  incident did three times.

Location: `frob.tickets._land`/`_land_git_ops.py` (the `DirtyMain`/
`OutOfScopeWaiveDeletion` refusal construction), not touched by T-1758.
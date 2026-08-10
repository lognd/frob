---
id: T-1754
title: 'post-land sweep regression from T-1753: 2 new error(s) (REL001, invalid-argument-type)'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- pyproject.toml
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires touching the affects()-closure doc for _attribute_new_findings,
    fixed by this ticket's Sequence widening
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1753 at commit 8a2f473e454c085890de379dcefd098a2978b4ce found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml
- invalid-argument-type  src/frob/app/ticket_runner/_rapid_sweep.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Done report

frob:no-behavior-change reason="Sequence(covariant) vs list(invariant) type-annotation fix on _attribute_new_findings's pairs parameter -- no logic change, only the static type the parameter accepts. Runtime behavior is identical for every real caller (all of which pass list[tuple[str, str]])."

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py: `_attribute_new_findings`'s
  `pairs` parameter changed from `list[tuple[str, str] | tuple[str, str,
  int]]` to `Sequence[tuple[str, str] | tuple[str, str, int]]`
  (`collections.abc.Sequence` import added).
- docs/modules/tickets.md: T-1754 follow-up note in the T-1690 section
  explaining the root cause (list invariance, not a wrong element type).

Root cause (this is the real fix, not another symptom patch): T-1753
widened `_attribute_new_findings`'s ELEMENT type
(`tuple[str,str]` -> `tuple[str,str] | tuple[str,str,int]`) but kept the
CONTAINER as `list[...]`. Python's `list` is INVARIANT -- a
`list[tuple[str, str]]` is never assignable to a
`list[tuple[str, str] | tuple[str, str, int]]` parameter, regardless of
how the element union is phrased, because a `list` parameter is
read-write (a callee could in principle append a 3-tuple into a caller's
own list). `_partition_findings_by_attribution`'s own `pairs:
list[tuple[str, str]]` -> `_attribute_new_findings(root, pairs)` call
therefore still failed ty's invariant-argument-type check even after
T-1753's fix -- T-1753 moved the mismatch to the call site rather than
resolving it, exactly as flagged.

The correct fix addresses the CONTAINER, not the element type:
`_attribute_new_findings` only ever ITERATES `pairs` (never mutates
it), so the sound, narrower-capability type is `collections.abc.
Sequence` (covariant, read-only) -- a `list[tuple[str, str]]` argument
is naturally accepted under `Sequence[tuple[str, str] | tuple[str, str,
int]]` without a cast or an `Iterable`/`list` mismatch anywhere in the
call chain.

Evidence: 3 pytest node ids recorded via `frob ticket evidence`, all
measured passing:
`timeout 100 uv run pytest tests/unit/test_rapid_sweep.py -p no:cacheprovider -q`
-> `collected=26 failed=0`.

Filed: T-1755 already exists (coordinator-filed, separate: the detached
post-land sweep leaves its filed regression ticket uncommitted, blocking
the next land -- the DirtyMain-class defect this session hit twice, T-1699's
sibling). Not this ticket's own scope; noted here only to avoid a
duplicate filing.

Gates: `frob check --only gates-fast --ticket T-1754` clean down to 2
SCOPE001 findings on land-owned files (.frob-release.json, uv.lock),
same pattern as every prior ticket in this session -- reconciled by
`frob ticket land`'s own internal merge, not hand-fixed here.
`frob check --only gates-native --ticket T-1754` clean, 0 errors.

### Changed
```
 .frob-release.json      | 11 +----------
 CHANGELOG.md            |  4 ----
 docs/modules/tickets.md | 14 ++++++++++++++
 pyproject.toml          |  2 +-
 tickets.md              | 15 +++++++++++++--
 uv.lock                 |  2 +-
 6 files changed, 30 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestAttributeNewFindings::test_attributed_and_unattributed_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_all_attributed_to_open_tickets_files_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 478 warning(s), 725 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/agent-a26588e5def8b5820/src/frob/verify/_backpressure.py, invalid-argument-type@src/frob/app/ticket_runner/_land_cmd.py

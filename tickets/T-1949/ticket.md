---
id: T-1949
title: 'ARCH001: _close_failure_hint (_close_cmd.py) exceeds the 60-line function
  threshold'
state: dropped
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED while working T-1934: `frob check --only archgate` fails with a
pre-existing ARCH001 error, unrelated to T-1934's own scope:

  src/frob/app/ticket_runner/_close_cmd.py:34  ARCH001
  function `_close_failure_hint` has 116 lines (threshold: 60)

`git diff main -- src/frob/app/ticket_runner/_close_cmd.py` is empty --
this function was already over the ARCH001 threshold before T-1934
touched anything. Split `_close_failure_hint` into smaller helpers (or
add a reasoned `frob:waive ARCH001` if a real cohesion argument applies,
matching this repo's own ARCH001 waiver precedents in
src/frob/arch/_python.py and friends) so `frob check --only archgate`
reads clean again.

## Drop reason
- 2026-08-10: stale: T-1933 already split _close_failure_hint into 11 named _hint_* helpers plus a dispatch dict (landed 934ecb4fc, T-1556 post-land sweep regression fix). Current _close_failure_hint body is lines 171-212 (41 lines), well under the 60-line ARCH001 threshold; verified via timeout 540 uv run frob check --only archgate --ticket T-1949, which reports zero ARCH001 findings anywhere in _close_cmd.py (only an unrelated, already-waived LARGE001 file-size finding). No regrowth occurred; nothing to split.

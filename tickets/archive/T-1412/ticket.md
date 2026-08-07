---
id: T-1412
title: Drain residual DOC006 findings to zero (post T-1372, 6 remaining)
state: done
kind: docs
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- CHANGELOG.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:uv run frob check --only docanchor --only doclink --only docblocks exit=0 sha256=5303ea7cf4a3
designated_repro_test: null
acceptance:
- text: frob check --only docanchor --only doclink --only docblocks reports 0 unwaived
    DOC006 findings in CHANGELOG.md and tickets.md
  evidence:
  - cmd:uv run frob check --only docanchor --only doclink --only docblocks exit=0
    sha256=5303ea7cf4a3
threat: null
component: null
---
A prior drive (T-1372) drained DOC006 from roughly 55 findings to 6 remaining
unwaived findings on main. This ticket finishes draining that residue to
zero: classify each of the 6 as a genuine stale reference (fix it), an
intentionally illustrative/future-facing example (waive with a reason
naming why it cannot resolve), or a pointer inside an append-only
historical record such as CHANGELOG.md (waive with a reason naming its
historical-record status, never rewrite the record).

Scope is narrow: only the prose lines in CHANGELOG.md and tickets.md that
currently trip DOC006, verified via
"frob check --only docanchor --only doclink --only docblocks". Does not
touch src/frob/gates/** or src/frob/tickets/_evidence.py, both held by
other in-flight tickets.
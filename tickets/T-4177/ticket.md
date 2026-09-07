---
id: T-4177
title: 'drop the uv, ruff, ty and pytest badges from the README: they advertise the
  toolchain, and the ty endpoint 404s into placeholder text'
state: queued
kind: docs
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the README badge block, when it is rendered, then it contains no toolchain
    badge and no unresolved endpoint
  evidence: []
- text: given the four retained badges, when each URL is requested, then it resolves
  evidence: []
- text: given the README outside the badge block, when diffed against main, then it
    is unchanged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DROP THE TOOLCHAIN BADGES FROM THE README. Owner request: the uv, ruff and pytest
badges are not wanted, and the ty badge renders as "custom badge: resource not
found".

WHY THEY ARE THERE AND WHY THAT WAS A MISREADING. The owner's original direction
was to make the README look professional "like uv, ruff, ty, pytest" -- naming
those projects as the STYLE to emulate. I passed that on as a badge list, and the
implementer added a badge per tool. The instruction was about the register of the
page, not its contents.

MEASURED: the ty badge endpoint returns 404, so shields.io renders its
placeholder text instead of a badge. The uv and ruff endpoints return 200 and
render correctly -- they are simply unwanted, not broken.

    uv endpoint     200
    ruff endpoint   200
    ty endpoint     404   <- renders as "custom badge: resource not found"

REMOVE four badge rows from the block at the top of README.md: uv, ruff, ty and
pytest. KEEP the four that say something about frob itself rather than about its
toolchain: released version, supported Python versions, license, CI status.

DO NOT restyle the rest of the page. The structure landed under an earlier ticket
and the owner has not asked for changes to it; this is a deletion of four lines.

ONE CHECK BEFORE CLOSING: a doc-pointer or link gate may have opinions about the
remaining badge URLs. Confirm the four survivors still resolve, and confirm no
gate was relying on the removed rows.

MUST-FIRE FIXTURE:   the rendered badge block contains no toolchain badge and no
                     unresolved endpoint.
MUST-STAY-QUIET:     the four retained badges still resolve and still link to
                     their real targets.
THIRD FIXTURE:       the rest of the README is unchanged, provable by diff.

ACCEPTANCE
- The four toolchain badge rows removed.
- The four retained badges verified to resolve.
- No other README content altered.

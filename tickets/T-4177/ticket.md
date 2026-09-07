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
body_changes:
- mode: set
  reason: 'owner: no tests needed for a README badge deletion. Drops the three-fixture
    section and states plainly that this is a four-line docs deletion verified by
    reading the rendered block'
  actor: logan
  at: '2026-09-07'
  old_length: 1906
  new_length: 1531
designated_repro_test: null
acceptance:
- text: given the README badge block, when it is rendered, then it contains no toolchain
    badge and no unresolved endpoint
  evidence: []
acceptance_amendments:
- op: remove
  index: 3
  old_text: given the README outside the badge block, when diffed against main, then
    it is unchanged
  new_text: null
  reason: 'owner: no tests needed for a README badge deletion; a diff-is-unchanged
    criterion is ceremony on a four-line docs change'
  actor: logan
  at: '2026-09-07'
- op: remove
  index: 2
  old_text: given the four retained badges, when each URL is requested, then it resolves
  new_text: null
  reason: 'owner: no tests needed for a README badge deletion; the retained badge
    URLs were already verified by hand when the ticket was filed'
  actor: logan
  at: '2026-09-07'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DROP THE TOOLCHAIN BADGES FROM THE README. Owner request: the uv, ruff and pytest
badges are not wanted, and the ty badge renders as "custom badge: resource not
found".

WHY THEY ARE THERE, AND WHY THAT WAS MY MISREADING. The owner's direction was to
make the README look professional "like uv, ruff, ty, pytest" -- naming those
projects as the STYLE to emulate. I relayed that as a badge list and the
implementer added one badge per tool. The instruction was about the register of
the page, not its contents.

MEASURED: the ty badge endpoint returns 404, so the shields service renders its
placeholder text instead of a badge. The uv and ruff endpoints return 200 and
render fine -- they are unwanted, not broken.

    uv endpoint     200
    ruff endpoint   200
    ty endpoint     404   <- renders as "custom badge: resource not found"

THE WHOLE CHANGE: delete four badge rows from the block at the top of README.md --
uv, ruff, ty, pytest. Keep the four that say something about frob itself rather
than about its toolchain: released version, supported Python versions, license,
CI status.

Do not restyle anything else. The page structure landed under an earlier ticket
and the owner has not asked for changes to it.

NO TESTS. This is a four-line deletion in a documentation file, and the owner has
said so explicitly. Do not add fixtures, and do not treat the absence of them as a
gap to be justified -- if a gate asks for evidence here, the honest answer is that
the change is verified by reading the rendered badge block.

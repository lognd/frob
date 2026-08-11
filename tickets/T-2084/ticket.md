---
id: T-2084
title: 'Ticket-state palette: dropped and queued are both DIM, so terminal work is
  indistinguishable from waiting work'
state: in-progress
kind: ux
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_style.py
- src/frob/logging/color.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/app.md
  reason: the palette is documented in docs/modules/app.md#shared-styling-helper-t-0179
    and the doc must change with the code
  actor: logan
  at: '2026-08-10'
designated_repro_test: null
acceptance:
- text: given a listing containing both a queued and a dropped ticket, when it is
    rendered with color enabled, then the two states render with different SGR codes
    -- this test MUST fail against current main
  evidence: []
- text: given color is disabled (--json, a pipe, or a non-TTY), when the same listing
    is rendered, then output is byte-identical to before this change
  evidence: []
threat: null
component: app
anchor: false
anchor_reason: null
---
STATE_STYLE in src/frob/app/_style.py maps both "queued" and "dropped" to DIM, so in every human-facing listing a dropped ticket looks identical to a queued one. That is the worst possible collision for these two states: queued means "waiting to be worked" and dropped is TERMINAL (there is no undrop verb -- frob ticket requeue refuses), so the two demand opposite reactions from a reader scanning a list. RED is already taken by blocked/failed and should stay reserved for states that want attention; dropped is closed-and-abandoned, not an error. frob/logging/color.py currently defines only RED/GREEN/YELLOW/CYAN/BOLD/DIM, so this needs one new SGR constant.
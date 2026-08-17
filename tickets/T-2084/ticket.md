---
id: T-2084
title: 'Ticket-state palette: dropped and queued are both DIM, so terminal work is
  indistinguishable from waiting work'
state: done
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
evidence_scope:
- tests/unit/test_app_style.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/app.md
  reason: the palette is documented in docs/modules/app.md#shared-styling-helper-t-0179
    and the doc must change with the code
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_app_style.py::test_dropped_state_is_visually_distinct_from_queued_and_blocked
- tests/unit/test_app_style.py::test_state_styling_is_a_noop_without_color
designated_repro_test: null
acceptance:
- text: given a listing containing both a queued and a dropped ticket, when it is
    rendered with color enabled, then the two states render with different SGR codes
    -- this test MUST fail against current main
  evidence:
  - tests/unit/test_app_style.py::test_dropped_state_is_visually_distinct_from_queued_and_blocked
- text: given color is disabled (--json, a pipe, or a non-TTY), when the same listing
    is rendered, then output is byte-identical to before this change
  evidence:
  - tests/unit/test_app_style.py::test_state_styling_is_a_noop_without_color
threat: null
component: app
anchor: false
anchor_reason: null
land_commit: null
---
STATE_STYLE in src/frob/app/_style.py maps both "queued" and "dropped" to DIM, so in every human-facing listing a dropped ticket looks identical to a queued one. That is the worst possible collision for these two states: queued means "waiting to be worked" and dropped is TERMINAL (there is no undrop verb -- frob ticket requeue refuses), so the two demand opposite reactions from a reader scanning a list. RED is already taken by blocked/failed and should stay reserved for states that want attention; dropped is closed-and-abandoned, not an error. frob/logging/color.py currently defines only RED/GREEN/YELLOW/CYAN/BOLD/DIM, so this needs one new SGR constant.

# Done report

## Changed

`STATE_STYLE` in `src/frob/app/_style.py` mapped both `queued` and
`dropped` to `DIM`, so in every human-facing listing a dropped ticket
rendered identically to a queued one. That is the worst collision available
between these two states: `queued` means "waiting to be picked up" and
`dropped` is TERMINAL -- there is no undrop verb, `frob ticket requeue`
refuses it -- so the two demand opposite reactions from a reader scanning a
list.

`dropped` is now `MAGENTA`. The choice is deliberate on both sides:

- NOT `DIM`, which is `queued` -- the collision being fixed.
- NOT `RED`, which is `blocked`/`failed`. Red is reserved for states that
  want attention; a dropped ticket is closed and abandoned, not an error.

`frob/logging/color.py` defined only RED/GREEN/YELLOW/CYAN/BOLD/DIM, so this
needed one new SGR constant: `MAGENTA = "35"`, carrying the same
`frob:doc docs/modules/logging.md#public-api` edge as its neighbours.

`docs/modules/app.md`'s palette list is updated in the same change,
including why `dropped` is neither dim nor red, so the next person to touch
the palette does not "tidy" it back.

## Evidence

- `tests/unit/test_app_style.py::test_dropped_state_is_visually_distinct_from_queued_and_blocked`
  asserts `dropped` differs from `queued`, `blocked`, and `failed`, at both
  the `STATE_STYLE` level and through `style_state`.
- `tests/unit/test_app_style.py::test_state_styling_is_a_noop_without_color`
  asserts the hard constraint that `--json`/pipe/non-TTY output stays
  byte-identical: `style_state(state, False) == state` for every state.

Measured: `pytest tests/unit/test_app_style.py -q -o addopts=""` ->
`collected=17 failed=0`. The file collected 15 before this change; the +2
delta is what confirms both new tests are actually present and running.

Also verified directly under the project interpreter:

    queued  -> '\x1b[2mqueued\x1b[0m'
    dropped -> '\x1b[35mdropped\x1b[0m'
    blocked -> '\x1b[31mblocked\x1b[0m'

## Notes

`-p no:xdist` is unusable in this repo (`pyproject.toml`'s `addopts`
injects `-n auto --dist=loadgroup`, and removing the plugin leaves nothing
to parse them); `-o addopts=""` is the working form. That gap is T-2068,
which still reproduces on main after T-2086 fixed the internal
coverage-retry path.

## Done report

### Changed

`STATE_STYLE` in `src/frob/app/_style.py` mapped both `queued` and
`dropped` to `DIM`, so in every human-facing listing a dropped ticket
rendered identically to a queued one. That is the worst collision available
between these two states: `queued` means "waiting to be picked up" and
`dropped` is TERMINAL -- there is no undrop verb, `frob ticket requeue`
refuses it -- so the two demand opposite reactions from a reader scanning a
list.

`dropped` is now `MAGENTA`. The choice is deliberate on both sides:

- NOT `DIM`, which is `queued` -- the collision being fixed.
- NOT `RED`, which is `blocked`/`failed`. Red is reserved for states that
  want attention; a dropped ticket is closed and abandoned, not an error.

`frob/logging/color.py` defined only RED/GREEN/YELLOW/CYAN/BOLD/DIM, so this
needed one new SGR constant: `MAGENTA = "35"`, carrying the same
`frob:doc docs/modules/logging.md#public-api` edge as its neighbours.

`docs/modules/app.md`'s palette list is updated in the same change,
including why `dropped` is neither dim nor red, so the next person to touch
the palette does not "tidy" it back.

### Evidence

- `tests/unit/test_app_style.py::test_dropped_state_is_visually_distinct_from_queued_and_blocked`
  asserts `dropped` differs from `queued`, `blocked`, and `failed`, at both
  the `STATE_STYLE` level and through `style_state`.
- `tests/unit/test_app_style.py::test_state_styling_is_a_noop_without_color`
  asserts the hard constraint that `--json`/pipe/non-TTY output stays
  byte-identical: `style_state(state, False) == state` for every state.

Measured: `pytest tests/unit/test_app_style.py -q -o addopts=""` ->
`collected=17 failed=0`. The file collected 15 before this change; the +2
delta is what confirms both new tests are actually present and running.

Also verified directly under the project interpreter:

    queued  -> '\x1b[2mqueued\x1b[0m'
    dropped -> '\x1b[35mdropped\x1b[0m'
    blocked -> '\x1b[31mblocked\x1b[0m'

### Notes

`-p no:xdist` is unusable in this repo (`pyproject.toml`'s `addopts`
injects `-n auto --dist=loadgroup`, and removing the plugin leaves nothing
to parse them); `-o addopts=""` is the working form. That gap is T-2068,
which still reproduces on main after T-2086 fixed the internal
coverage-retry path.

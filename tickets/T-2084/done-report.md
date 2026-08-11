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

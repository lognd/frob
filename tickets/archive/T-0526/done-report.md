## Done report

Implemented T-0412's DEBT<->TODO coherence follow-up requirements (1)-(3)
entirely inside `src/frob/graph/dsl.py`, this ticket's declared scope:

- New `_debt_todo_coherence(edges)` post-pass over one file's parsed edges,
  called from `parse_directives` after the normal per-line parse:
  - (1) An unpaired `frob:debt` (no explicit co-located `frob:todo` at the
    same `src`) implicitly REGISTERS a synthesized `TODO` edge (target =
    the debt's own `ticket=` attribute, `attrs={"implicit": "debt"}`), so
    the debt's payoff work is visible to every ordinary todo-edge consumer
    with zero changes to `frob.gates` -- it flows straight into the
    existing `_todo002_edges` open-ticket check for free.
  - (2) Both directives already require an open ticket (DEBT002 reuses
    TODO002's check per T-0412's own Done report); the implicit
    registration inherits that enforcement automatically, nothing new to
    add here.
  - (3) An explicit `frob:debt` + explicit `frob:todo` at the same `src`
    naming DIFFERENT tickets is a coherence error, surfaced by shaping the
    `MalformedDirective.reason` to contain the literal substring
    `"frob:debt"` -- DEBT001's existing `_debt001_violations` filter
    picks it up automatically, so no new gate rule id and no
    `frob.gates` change was needed at all (same "shape the malformed
    reason, reuse an established gate's substring filter" pattern
    DEBT001/TEST010 already use).

Requirement (4) -- symmetric resolution surfacing of both the debt and
the todo at ticket-close time -- is NOT implemented here: it is
ticket-lifecycle behavior belonging to `frob.tickets`/`frob.gates`, both
outside this ticket's declared scope (`src/frob/graph/dsl.py` only). Not Filed
as its own follow-up: T-draft-64ba9cf3 (never refiled) "frob:debt/frob:todo symmetric
resolution surfacing at ticket close (T-0412 req 4)", scoped to
`src/frob/tickets/` + `src/frob/gates/__init__.py`.

Scope was widened by one file via `frob ticket scope --add
tests/unit/graph/test_dsl.py` (the ticket's original scope named only the
implementation file, with no mirrored test path) to add the three
regression tests below to the existing dsl.py test file rather than
inventing a new untracked one.

Correction mid-pass: the new module comment's prose used the bare word
"TODO" (e.g. "TODO002"), which TODO001's bare-comment scanner flagged as
an unbound TODO; reworded to drop the literal word while keeping the
same explanation (see the follow-up commit).

Gates: `uv run frob check --ticket T-0526 --json` -> 0 errors (566
pre-existing warnings/118 waivers repo-wide, unrelated to this ticket's
touched files; gate:TODO clean after the reword). `ruff check`/`ruff
format --check` clean on both touched files under both the PATH `ruff`
and `uv run ruff`. `uv run pytest tests/unit/graph/test_dsl.py -q` -> 20
passed.

### Changed
```
 src/frob/graph/dsl.py        | 97 ++++++++++++++++++++++++++++++++++++++++++++
 tests/unit/graph/test_dsl.py | 57 ++++++++++++++++++++++++++
 tickets.md                   | 95 +++++++++++++++++++++++++++++++++++++++++--
 3 files changed, 246 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_unpaired_debt_registers_implicit_todo` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_explicit_paired_todo_same_ticket_no_implicit_duplicate` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_mismatched_explicit_todo_is_debt001_shaped_malformed` (pytest node id, verified passing when recorded)

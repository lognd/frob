## Done report

Implemented the "components/labels, priority-ordered board, epic->story->
task rollup" half of the professional-ticket-organization epic. Design
per the ticket body, using the EXISTING `parent` field for hierarchy
rather than inventing a second relationship, and additive/optional fields
throughout so every pre-existing ticket in tickets.md/tickets-archive.md
stays valid on load with no migration:

Schema (src/frob/tickets/_models.py): `Ticket`/`TicketSpec` gained
`component: str | None = None` (freeform module/area -- not an enum, the
component set grows with the codebase) and `labels: tuple[str, ...] = ()`
(freeform tags orthogonal to component), the latter comma-split the same
way `scope` entries are (`_split_scope_entries`, T-0241's normalization
reused as-is, not reimplemented). New `BOARD_STATES` (the fixed column
order `frob ticket board` renders), `BoardColumn`, `EpicRollup` (+ its
`percent_complete` property, 0.0-safe on a childless epic) models. New
`TicketError.LabelChangeEmpty` (mirrors `ScopeChangeEmpty`'s "don't call
this for nothing" discipline).

Library (src/frob/tickets/__init__.py): `set_component` (same
single-writer, ledger-locked pattern as `set_priority`), `mutate_labels`
(same shape as `mutate_scope` but with NO lease-conflict check and NO
audit trail -- a label is a plain tag, not a filesystem glob claim on the
tree), `board_view` (groups the active queue into BOARD_STATES columns,
each ordered by the existing `_doable_sort_key` T-0411 established,
optional component=/label= filters requiring BOTH to match when both are
given), `epic_rollup` (BFS over the `parent` chain to the full transitive
descendant subtree -- not just direct children -- with a done/total count
and the ids of any LEAF descendant, i.e. one with no children of its own,
currently BLOCKED). `_ticket_from_spec`/`new_ticket` forward
`spec.component`/`spec.labels` through to the constructed `Ticket`.

CLI (src/frob/app/ticket_runner.py, src/frob/app/config.py,
src/frob/__main__.py): `frob ticket component <id> <name>` (`"none"`
clears it), `frob ticket label <id> --add/--remove TAG...`, `frob ticket
board [--component NAME] [--label TAG] [--json]`, `frob ticket epic <id>
[--json]`; `frob ticket new` gained `--component NAME`/`--label TAG`
(repeatable). Every new runner function does nothing but forward to the
library (same "command does nothing but forward" discipline
`_scope`/`_priority` already established) plus render human/JSON output.

No half-landed schema, per the dispatch instruction's explicit
requirement: `tests/test_tickets_organization.py` (new, 16 tests) plus a
new round-trip test added to the existing
`tests/unit/test_ticket_store.py` cover EVERY new field/function --
serialize/parse round-trip, `write_ticket`+ledger round-trip (the T-0411
priority-field template the instruction pointed at), comma-split
normalization, `new_ticket` carrying both fields, `set_component`
(set + clear-to-None), `mutate_labels` (add+remove combined, and the
empty-call error), `board_view` (fixed column order, priority ordering
within a column, component filter, label filter), and `epic_rollup`
(NotFound, done/total counting across a 3-level subtree, a blocked leaf
surfaced, and the childless-epic zero-percent edge case).

Deliberately NOT built in this pass, filed as follow-ups rather than
half-implemented (both minted as provisional ids, real T-#### assigned at
land):
- T-draft-2586e92f: sprints/milestones (sprint/milestone field + `frob
  ticket sprint new/list/show/assign` CRUD) -- the ticket body's own "if
  they fit" qualifier, and a full sprint lifecycle is a second
  feature-sized surface on top of this pass's component/label/board/epic
  core.
- T-draft-b0a49b89: a component/label filter on `frob ticket doable`/
  `list` (currently only `board` filters) and bulk component/label
  reassignment (today one ticket at a time, matching every other
  single-ticket mutation command's granularity).
Both are recorded in docs/modules/tickets.md's new "Organization"
section alongside the design that WAS built, so the cut is visible in
the same place a future reader would look for the feature, not just in
the ticket ledger.

Version bumped 0.57.0 -> 0.58.0 (REL001 minor: new public
component/labels fields plus set_component/mutate_labels/board_view/
BoardColumn/BOARD_STATES/epic_rollup/EpicRollup API); `frob release
check` -> "since 0.58.0: none change -> need >= 0.58.0 (current 0.58.0):
OK".

Sequential single-worktree dispatch note: this ticket's scope was widened
by `src/frob/gates/__init__.py`, `src/frob/graph/dsl.py`,
`tests/test_gates.py`, and `tests/unit/graph/test_dsl.py` (T-0526/T-0527's
own committed files, whose commit subjects in this same worktree did not
all carry an explicit T-0526/T-0527 reference, so they kept showing as
out-of-scope in this ticket's own diff-vs-main SCOPE001 check -- the
T-0108/T-0412/T-0527 cross-ticket-exemption precedent) and by
pyproject.toml/CHANGELOG.md/.frob-release.json/uv.lock (this ticket's own
REL001 bump).

A mid-pass `git merge main` (this worktree's base had gone stale relative
to main advancing 100+ commits from other concurrent worktrees, including
32 new invariants/INV-*.md files and strata_core/threat/selfconform
changes) was verified with the deletion-filter check
(`git diff main --diff-filter=D --stat`) both before (which correctly
flagged the then-missing invariants/ files as a stale-base symptom, not a
real deletion) and after the merge (empty, clean) -- see
docs/guides/agent-playbook.md section 9.

Gates: `uv run frob check --ticket T-0454 --json` -> 0 errors (534
warnings/121 waived repo-wide, pre-existing and unrelated to this
ticket's touched files -- two new PERF004 findings in board_view/
epic_rollup were reviewed and waived inline with an honest reason: a
fixed 6-iteration sort per BOARD_STATES entry, and a single post-BFS sort
the checker's whole-function loop scan flagged textually, neither a real
hoistable-sort opportunity). `ruff check`/`ruff format --check` clean on
every touched file under both the PATH `ruff` and `uv run ruff`. `ty
check` clean. `uv run pytest tests/test_tickets_organization.py
tests/unit/test_ticket_store.py -q` -> 70 passed; `uv run pytest tests/
-k "ticket and not test_no_violation_off_default_branch" -q` -> full
ticket-related suite green (the one excluded test is a pre-existing,
unrelated date-drift TICK004 rot fixture, not touched by this ticket).

### Changed
```
 .frob-release.json                 |  10 +-
 CHANGELOG.md                       |  18 ++
 docs/modules/tickets.md            | 110 +++++++++
 pyproject.toml                     |   2 +-
 src/frob/__main__.py               |  96 +++++++-
 src/frob/app/config.py             |  18 ++
 src/frob/app/ticket_runner.py      | 171 ++++++++++++-
 src/frob/gates/__init__.py         |  64 +++--
 src/frob/graph/dsl.py              |  97 ++++++++
 src/frob/tickets/__init__.py       | 162 +++++++++++++
 src/frob/tickets/_models.py        |  86 +++++++
 tests/test_gates.py                |  70 ++++++
 tests/test_tickets_organization.py | 278 +++++++++++++++++++++
 tests/unit/graph/test_dsl.py       |  57 +++++
 tests/unit/test_ticket_store.py    |  16 ++
 tickets.md                         | 479 ++++++++++++++++++++++++++++++++++++-
 uv.lock                            |   2 +-
 17 files changed, 1702 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestFieldRoundTrip::test_serialize_parse_round_trip` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestFieldRoundTrip::test_write_ticket_ledger_round_trip` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestFieldRoundTrip::test_comma_joined_label_splits` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestFieldRoundTrip::test_new_ticket_carries_component_and_labels` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestSetComponent::test_clears_to_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestMutateLabels::test_add_and_remove_labels` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestMutateLabels::test_empty_call_is_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestBoardView::test_columns_in_fixed_order` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestBoardView::test_priority_ordered_within_column` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestBoardView::test_component_filter` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestBoardView::test_label_filter` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestEpicRollup::test_not_found_is_err` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestEpicRollup::test_counts_done_and_total` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestEpicRollup::test_blocked_leaf_surfaced` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestEpicRollup::test_childless_epic_is_zero_percent_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLoadAllAndWriteTicket::test_component_and_labels_round_trip` (pytest node id, verified passing when recorded)

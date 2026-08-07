## Done report

Extracted the field-setter/sprint-rollup family out of
src/frob/tickets/__init__.py into a new src/frob/tickets/_setters.py
module, per T-1123's per-family extraction pattern: verbatim moves,
directives (frob:ticket/frob:doc/frob:tests) carried intact, zero
caller-visible behavior change.

Moved (verbatim): _set_ticket_field, set_priority, set_kind, set_tier,
set_sprint, _tickets_committed_to, sprint_view, _STATE_LINE_RE,
_ticket_state_in_blob, _ledger_commit_history, _blob_at,
_mine_done_transitions, sprint_velocity, _FLOW_TRAILING_DAYS,
ticket_flow, set_component. __init__.py: 2740 -> ~2065 lines.

_load_ticket_and_queue and _OPEN_STATES intentionally stay in
frob.tickets.__init__ (shared by transition/add_evidence/
_open_descendant_ids); _setters.py late-imports both from the package
at call time, same load-order-safe indirection _doable.py already uses
(precedent for this split).

INV006 (exclusivity-vocabulary "only" hits, all inherited verbatim from
the moved docstrings) carried forward as a frob:waive INV006 on the new
module, same calibration-batch disposition as 0abc4e3a.

DRIFT002 fallout fixed: docs/modules/tickets.md's frob:describes anchors
for set_priority/set_component/set_tier repointed at _setters.py; the
frob:tests directives in tests/test_tickets_organization.py,
tests/test_tickets_tiers.py, tests/test_tickets_velocity.py repointed at
_setters.py for set_component/set_tier/set_sprint/sprint_view/
sprint_velocity/ticket_flow.

COV002 fallout fixed: added frob:ticket T-1151 edges to every test
class/method the above directive edits touched (TestSetComponent,
TestSetTier + its 3 methods, TestSprintAssign, TestSprintShow,
TestSprintVelocity + its 4 methods, TestTicketFlow + its 4 methods,
_commit_on helper) so COV002 (changed-with-no-open-ticket-edge) is
satisfied alongside each symbol's pre-existing T-1069/T-0938/T-1100
ticket tag.

_land.py (4762 lines) not touched this round -- still needs its own
split per the ticket's own note; requeuing as residue (see below).

Verification:
- `uv run python -c "import frob.tickets"` -- clean import.
- `uv run ruff check src/frob/tickets/__init__.py src/frob/tickets/_setters.py`
  -- 5 pre-existing F401s (verified identical on main's original
  __init__.py placed at the same package path; unrelated to this
  change), _setters.py itself: all checks passed.
- `uv run pytest tests/test_tickets_priority.py tests/test_ticket_evidence.py::TestSetKind
  tests/test_tickets_tiers.py tests/test_tickets_organization.py
  tests/test_tickets_velocity.py -p no:cacheprovider -q` -- 52 passed.
- `uv run pytest tests/test_tickets.py -p no:cacheprovider -q` -- 134 passed.
- `uv run frob check --ticket T-1151 --only coverage --only drift --only
  invariant --only prework --only registry`: DRIFT/INV/PRE all clean for
  this ticket's scope after the fixes above; remaining COV (24, all
  pre-existing strata-core/tickets.md debt unrelated to this move,
  verified by grep -- none reference _setters.py or the __init__.py
  lines this ticket touched) and REG (registry/gate-rule debt, also
  pre-existing and unrelated) are NOT new; left as-is (out of this
  ticket's scope, not silently introduced by this change).

Residue: this ticket's remaining families (evidence/transition,
done-report/review/drop/attach) and _land.py's own split are NOT done
this round -- filed as a follow-up ticket, T-1152 (verify the
real id on main after land renumbers this draft), so the queue does not
silently lose them.

### Changed
```
 tickets.md | 64 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 63 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSetTier::test_updates_tier_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSprintAssign::test_updates_sprint_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

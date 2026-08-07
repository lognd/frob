## Done report

Added a new REL38x reliability family (`src/frob/strata/_starvation.py`) building on T-0700's access-mode/resource grammar (`_access.py`, SYS204) and T-0702's demand-propagation fact (`_facts.py::FactBase.aggregate_demand`), both already landed (`[done]`) on local main.

Four new rule ids, one module, mirroring the existing REL2xx/REL3xx obligation-family pattern (`_spof.py`/`_reliability.py` precedent):

- REL380 serialization-point utilization over threshold -- every node that is an effective-concurrency-1 point for a resource (write/append/exclusive/alpha access mode, or a resource's own `arbitrated_by` node) whose `FactBase.aggregate_demand` exceeds its `Capacity.service_rate` (one replica's worth, deliberately not multiplied by `replicas_max`). A node with no declared `Capacity` falls back to a conservative default holding time (10ms / 100 per-second). The finding shows the arithmetic (demand, capacity, utilization multiple).
- REL381 serialization-point demand undeclared -- the same population, firing instead of REL380 whenever `FactBase.aggregate_demand(...).declared` is False: fail-closed, never silently skipped.
- REL382 writer starvation (advisory) -- a resource with a `read` accessor and a write-like accessor but no `alpha` accessor declared; fires regardless of utilization or arbiter presence.
- REL383 unbounded wait -- a node acquiring a contended resource (2+ accessors) in a write-like/alpha mode with no `timeout` attr declared on itself; reuses the T-0640 TIMEOUT vocabulary at a new population (resource acquisition, not `Flow`), per the ticket's "joins the T-0640 timeout obligation family" instruction, without touching `_reliability.py` itself.

REL380/381/382/383 join `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` (a node can access more than one resource, so a waive clause must carry a `RULE:RESOURCE_ID` sub-target). Documented in `docs/strata/reliability.md` (new `## REL38x` section) and `docs/strata/waive.md` (MULTI_INSTANCE_WAIVER_FAMILIES table entry) -- this required widening the ticket's declared scope to include `docs/strata/**` (recorded via `frob ticket scope --add`, reason on file in the ticket's `scope_changes`).

Ten new unit tests in `tests/unit/strata/test_starvation.py` cover all three acceptance-criterion scenarios verbatim: the 500k-users-vs-exclusive-db utilization error with arithmetic shown in the detail string (bound to the ticket's acceptance criterion via `--accepts 0`); the same db with demand undeclared firing the fail-closed REL381; and a read-heavy resource with a write accessor and no alpha accessor firing the REL382 advisory (plus REL382's alpha-discharge case, REL383's contended/lone-accessor/declared-timeout cases, and REL380's arbitrated_by-node-is-the-point and declared-capacity-clean cases).

Verification: `uv run pytest tests/unit/strata/test_starvation.py -q` -- 10 passed. `uv run frob check --only lint/static/gates-fast/gates-native/gates-security --ticket T-0703` -- every gate-summary line 0 errors (only pre-existing, unrelated ty diagnostics in `tests/test_gates.py` and ruff-format drift in two unrelated files this ticket never touches). `git diff main --diff-filter=D --stat` empty.

Filed then dropped: T-0957 was filed mid-ticket after comparing T-0700/T-0702's state against the stale `origin/main` remote (168 commits behind this drive's local main) -- a false alarm. Confirmed on local main both T-0700 and T-0702 are `[done]`; dropped the draft ticket with reason "false alarm: compared against stale origin/main; local main ledger is correct".
Gates: frob check --only lint/static/gates-fast/gates-native/gates-security --ticket T-0703 clean (0 errors each; only pre-existing unrelated ty/ruff-format items noted above).

### Changed
```
 docs/strata/reliability.md           |   128 +
 docs/strata/waive.md                 |     7 +-
 src/frob/strata/__init__.py          |    18 +
 src/frob/strata/_starvation.py       |   541 ++
 src/frob/strata/_waive.py            |     4 +
 tests/unit/strata/test_starvation.py |   227 +
 tickets-archive.md                   | 16733 +--------------------------------
 tickets.md                           | 12529 ++++++++++++++++++------
 8 files changed, 10882 insertions(+), 19305 deletions(-)
```

### Evidence
- `tests/unit/strata/test_starvation.py::TestUtilization::test_over_capacity_demand_fires_with_arithmetic` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUtilization::test_declared_capacity_within_bounds_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUtilization::test_undeclared_demand_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUtilization::test_arbitrated_by_node_is_the_serialization_point` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUtilization::test_read_only_accessor_is_not_a_serialization_point` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestWriterStarvation::test_read_heavy_writer_with_no_alpha_fires_advisory` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestWriterStarvation::test_alpha_accessor_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUnboundedWait::test_contended_write_access_with_no_timeout_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUnboundedWait::test_declared_timeout_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_starvation.py::TestUnboundedWait::test_lone_accessor_is_not_contended` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

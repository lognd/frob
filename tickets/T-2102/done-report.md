## Done report

### Changed
tests/system/test_frob_self_model.py::TestFrobSelfModel.test_parses_and_elaborates
tests/system/test_frob_self_model.py::TestFrobSelfModel.test_every_claim_proves

### Evidence
tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves

Full test_frob_self_model.py re-verified: 4 passed.

### Investigation and verdict (coordinator's question: downstream of
### T-2101's litmus leak, or independent?)

Independently confirmed, twice, per the coordinator's explicit request
before changing anything:

1. `_model`'s own fixture parses ONLY `design/frob.strata` directly
   (`parse_module`/`elaborate` on that one file's text) -- no merge
   machinery, no `load_design_ids`, litmus never enters this code path
   at all, regardless of T-2101's fix.
2. Ran the exact fixture logic by hand in T-2101's OWN worktree (with
   `3d230f210`'s fix already committed there) and confirmed: 25 nodes,
   all real frob ids (`checker`/`claude_hooks`/`cli`/`core`/`deploy`/
   `fleet`/`frob_core_native`/`gates`/`graph_cache`/`graphlang`/
   `mutate`/`natives`/`refactor`/`registry`/`registry_model`/
   `scripts_ops`/`security`/`serve`/`strata_core_native`/`stratamod`/
   `telemetry`/`testsuite`/`tickets_ledger`/`verify`/`vet`) -- zero
   duplicates, zero litmus-shaped ids, identical whether or not
   T-2101's fix is present.

25 is the real, uncorrupted current node count. This is independent,
organic model growth, not downstream of T-2101 -- confirmed rather than
assumed, exactly per the coordinator's instruction not to bump 23->25
without first checking this.

### Decision: floor invariant, not a re-measured exact count

Chose (b) from the ticket's own decision framing: replaced every exact
`== N` count assertion (nodes/flows/boundaries/claims, both in
`test_parses_and_elaborates` and the claim-count line in
`test_every_claim_proves`) with a `>=` FLOOR at the current measured
value. Rationale: `elaborate()` itself already fails closed on the real
corruption shapes a count could incidentally catch (duplicate ids,
dangling references -- `_model`'s own fixture asserts `is_ok` and would
fail this test first regardless); a count on top of that only
re-detects SHRINKAGE, which a floor already does exactly as well while
never failing on a legitimate addition. This docstring's own multi-
paragraph running history already discloses the exact cost of the
exact-count approach: five independent misses (T-0707, T-0864, T-1329,
T-1591, and this ticket's own 23-vs-25/31-vs-34).

Also dropped `test_every_claim_proves`' `assumed_ids` hardcoded
enumeration and its `seen_ids == proved_ids | assumed_ids` exact-set
assertion -- verified it added NO safety beyond the per-claim loop
already sitting above it (every claim result was already checked:
never REFUTED; PROVED iff in `proved_ids`; ASSUMED otherwise,
unconditionally). It only tested "did the hardcoded set enumerate
every claim id that currently exists," the identical golden-drift
trap. Kept `proved_ids` itself hardcoded and exact (3 ids, a genuinely
narrow, meaningful invariant: these are the model's only claims meant
to resolve PROVED rather than human-ASSUMED) plus added a check that
all 3 still exist and still resolve PROVED, closing the one real gap
dropping the exact-set check opened (a deleted PROVED-claim id going
unnoticed).

### Gates
`frob ticket evidence --check-repro`/`--designate-repro` against the
pre-fix commit (`3fc74f2563ddff8f4dcf6f4aa7a1060067cff44a`): genuine
FAILED_AT_PARENT.

Filed: none (sibling of T-2101, already filed together with this
ticket by the same coordinator request).

### Changed
```
 tests/system/test_frob_self_model.py | 137 ++++++++++++++++++-----------------
 tickets/T-2102/ticket.md             |  11 ++-
 2 files changed, 80 insertions(+), 68 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2102

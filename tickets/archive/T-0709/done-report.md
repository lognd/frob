## Done report

Epic close verification (T-0709): enumerated every child ticket referencing
`parent: T-0709` across tickets.md and tickets-archive.md --
T-0710 (collector + attribution), T-0711 (sketch store), T-0712 (query
surface + advisories + ratchet), T-0748 (cross-language collectors), and
T-0917 (MCP frontend, the T-0712 follow-up the coordinator named) -- all
five are `state: done`. No open/queued/in-progress child exists anywhere
in the ledger.

Verified the parent's own acceptance criterion against reality rather than
trusting the children's own claims: ran `frob perf collect --sampler --
tests/unit/perf/test_hotgraph.py -q` to actually populate
`.frob/hotgraph_sketches.db` in this worktree (a fresh worktree starts
with no store -- `frob perf collect` is documented as the store's only
current producer, per docs/modules/perf.md's "Hot-graph query surface"
section). Result: `.frob/hotgraph_sketches.db` is 12288 bytes (12KB),
comfortably under the 100KB acceptance bound and the configured
`store_cap_bytes` default. `frob perf hot --top 10` then read the store
back with real per-section p50/p90 (decile) readouts (Popen2IO.read,
Condition.wait, _read_pyc, _get_default_tempdir, and two branch sections
all returned distinct p50/p90 numbers from real sampled weight) --
confirming the FULL pipeline (collector -> attribution -> sketch store ->
decayed merge -> query surface) works end to end in a clean checkout, not
merely that each child's own unit tests pass in isolation.

No code changes were needed -- this ticket closes purely on verification
that the epic's children delivered what T-0709's acceptance criterion
asked for. `.frob/` is gitignored local state (the store artifact
generated during this verification is not committed).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hot_query.py::TestListSketches::test_empty_store_is_empty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2866 warning(s), 339 waived
- error-findings: none (measured, zero errors)

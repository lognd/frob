## Done report

docs/audits/gates-accounting.md B2/E2: `frob.graph.lock._DEFAULT_FACET =
"sig"`; an ack (`frob:doc`/`frob:describes` with no explicit facet, the
common case) locked only the signature digest. Rewriting a documented
function's BODY (the actual behavior a doc claims) after ack never tripped
DRIFT001 -- the doc could lie about behavior forever. Repro: ack a
`frob:doc` at default facet, rewrite only the body, `frob check` -> green.

Survey done first (required -- "cross-cutting... too large for the T-0403
sweep budget"): counted this repo's own `frob.lock` at the time of this
change -- 43 entries total, ALL `facet=sig`, ZERO existing `facet=body`
entries. Small, uniform footprint; no existing entry already relies on a
narrower assumption that a wider default would conflict with.

Landed: `frob.graph.lock._facets_for_ref` now always unions in `"body"`
alongside whatever facet(s) an ack would otherwise record (explicit
DESCRIBES facets, or the sig-only fallback) -- never narrows an explicit
request, only widens coverage. `acknowledge` already skips `body` for
kinds where it is meaningless (`_BODY_FACET_MEANINGLESS_KINDS`: class/
const/type have a constant body digest, T-0402/G5), so this cannot create
a body lock entry that could never observe drift.

Given the small, uniform survey result, landed this as the new DEFAULT
directly rather than behind an opt-in flag: gating it behind a flag
nobody would proactively flip would leave B2 open indefinitely for no
real safety gained, when the measured churn is 43 entries in a lock file
this size. Existing lock entries are unaffected until their next
`frob ack` (ordinary lock-format evolution, not a retroactive rewrite).

Updated `tests/test_graph_lock.py` (2 existing tests) for the new
entry-count expectations, and added a new regression test pinning the
exact B2 repro: ack at default facet, rewrite ONLY the body, confirm
DRIFT001-equivalent (`report.stale`) now fires on the `body` facet.

Anomaly found and NOT fixed here (filed instead, out of this ticket's
actual change): after closing this ticket's own work, a full `frob check`
(with or without `--ticket` override) shows COV002 firing again on several
symbols from the ALREADY-CLOSED T-0545/T-0552 (e.g. `stamp_coverage`,
`test_gate`, `_KNOWN_GATE_RULES`) despite each carrying a valid
`frob:ticket` directive and both tickets' closures still being part of the
diff vs `main`. This reproduced identically before any T-0556 code change
and is unrelated to `lock.py`/`test_graph_lock.py` -- it looks like a
COV002 grace-window hunk-matching artifact from running many tickets
sequentially in one worktree/branch (git diff hunk shape shifting as later
tickets' `tickets.md` operations land). Not Filed as T-draft-9557a879 (never refiled) rather
than debugged/fixed here, since it is outside T-0556's declared scope and
is a pre-existing accounting-gate defect in its own right, not a
consequence of the DRIFT001 facet fix.

### Changed
```
 CHANGELOG.md                |  19 +++
 frob.lock                   |   2 +-
 pyproject.toml              |   2 +-
 src/frob/gates/__init__.py  | 253 +++++++++++++++++++++++++++++++--
 src/frob/gates/_coverage.py | 125 ++++++++++++++++-
 tests/test_gates.py         | 249 ++++++++++++++++++++++++++++++++-
 tickets.md                  | 333 ++++++++++++++++++++++++++++++++++++++++++--
 uv.lock                     |   2 +-
 8 files changed, 961 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_graph_lock.py::TestAckDrift::test_ack_then_sig_edit_yields_stale` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_ack_then_body_only_rewrite_yields_stale` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_acknowledge_records_every_describes_facet` (pytest node id, verified passing when recorded)

## Done report

Findings addressed:

- REG005 docs/design/registry/check-coverage.yaml: FIXED. T-4387 added a
  `CHK-GATE-DOC014` row to `gate_rule_entries` (371 rows) but never bumped
  `gate_rule_total` (left at 370). Bumped it to 371. Confirmed by counting
  `- id:` rows under `gate_rule_entries:` (371) and by `git log -p` on the
  file showing T-4387's insertion with no total-field change alongside it.

- DRIFT001 src/frob/tickets/_leases.py: FIXED. T-4388 added the
  `exclude_from_reconcile` parameter to `read_all_leases`/
  `_live_leases_pruning_stale` (both docstrings already described it), but
  the acked doc section the `frob:doc` directive points at
  (docs/modules/tickets-lifecycle.md#cross-worktree-lease-side-channel-t-0473)
  never mentioned T-4172's terminal-lease reconciliation or T-4388's
  archive-time exclusion hatch at all -- a genuine contract gap, not just a
  digest bump. Added a new paragraph documenting both, then
  `frob ack src/frob/tickets/_leases.py::read_all_leases --facet doc`
  (accepted; sig+body facets re-acked, digests recorded in frob.lock).
  Widened ticket scope to add docs/modules/tickets-lifecycle.md (the doc
  target lives outside the ticket's originally-declared scope; the
  finding's own file, src/frob/tickets/_leases.py, was already in scope).

- TICK004 tickets.md: PRE-EXISTING RESIDUE, not caused by this batch.
  Called `_tick004_queue_rot` directly (full `frob check` would not
  complete inside the foreground budget under current fleet load -- see
  below): 40 queue-rot findings, all keyed off ticket `created` dates vs.
  priority-specific rot-day thresholds (a pure passage-of-time signal, not
  a code-shape regression). Sweep attribution already reports this as
  UNATTRIBUTED with no candidate commits. Not touched -- fixing rot is a
  per-ticket triage decision (work/reprioritize/drop), out of this
  ticket's scope, and the brief is explicit that TICK004/006 are fixed
  "via the frob ticket verbs, never by hand-editing tickets.md", which
  does not apply to a residue finding.

- TICK006 tickets.md: PRE-EXISTING RESIDUE, not caused by this batch.
  Called `_tick006_phantom_filing` directly: one finding, T-4041's Done
  report ("Filed: T-draft-858a1bad ...") citing a draft id that never
  resolved. T-4041 landed 2026-09-06, well before T-4388 (measured
  2026-09-10) -- the disclosed draft-loss shape T-4041's own Done report
  already calls out ("out-of-scope T-4172/archive-lease regression found
  while working T-4066"). Confirmed unattributed with no candidate
  commits.

Verification note: `uv run frob check --ticket T-4394` (plain, `--only
gates`, and `--only gates-fast`, `--json` and plain text, up to 585s
foreground) consistently reached the same last log line (REF003 dangling
doc refs) and then hung past the timeout with 12 lingering multiprocessing
children reaped by SIGTERM, every single attempt, at load average ~1.1 on
a 12-core host with 19GB free -- not a load/resource symptom. This looks
like a real stall in the checker itself (out of this ticket's scope:
src/frob/gates/_tickets_gate.py/`_tick004_queue_rot`/
`_tick006_phantom_filing` and the REG005/DRIFT001 detectors were instead
called directly via `python3 -c` against the loaded ticket queue/registry/
graph to reproduce and verify each finding individually, all matching
the ticket body's description). Filing a follow-up ticket for the
full-check hang is recommended but is itself out of T-4394's declared
scope.

Changed: docs/design/registry/check-coverage.yaml (gate_rule_total),
docs/modules/tickets-lifecycle.md (new paragraph, cross-worktree lease
side-channel section), frob.lock (ack digests).

Evidence: `frob ack` accepted the doc re-verification against
`src/frob/tickets/_leases.py::read_all_leases` (see frob.lock/ack audit
trail). REG005/TICK004/TICK006 reproduced directly via
`frob.gates._registry_exhaustiveness`/`frob.gates._tickets_gate` function
calls (see commands above); no test changes were needed since no public
symbol's behavior changed, only doc prose and a registry total.

Filed: none.

Gates: full `frob check --ticket T-4394` did not complete under current
fleet load (see verification note above) -- targeted, direct
reproduction of the DRIFT001/REG005/TICK004/TICK006 detectors stands in
as evidence pending a land-time check run, per the same posture T-4041's
own Done report used for the identical stall shape.

### Changed
```
 docs/design/registry/check-coverage.yaml |  2 +-
 docs/modules/tickets-lifecycle.md        | 25 +++++++++
 frob.lock                                | 22 +++++++-
 tickets/T-4394/done-report.md            | 89 ++++++++++++++++++++++++++++++++
 tickets/T-4394/ticket.md                 |  5 +-
 5 files changed, 139 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestTotalDrift::test_total_mismatch_fails` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_ack_then_sig_edit_yields_stale` (pytest node id, verified passing when recorded)

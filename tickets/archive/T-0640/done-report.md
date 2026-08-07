## Done report

Salvage/reconciliation pass (docs/guides/agent-playbook.md): the REL2xx
TIMEOUT obligation this ticket asked for is already fully implemented and
landed on main -- cdbd4337 (REL2xx TIMEOUT-obligation reliability family,
REL200 missing-timeout + REL201 unproven-timeout with proof-against-code
discharge per T-0331's provability constraint), 05264346 (REL2xx waiver
in_scope per rule-family), b13d2c66 (wired into `frob sys audit` via
`check_reliability_timeouts` in src/frob/app/sys_runner.py + cross-family
stale-waiver false-positive fix), hardened further by the T-0644 (REL21x
HEALTH) and T-0758 (REL201 dst-endpoint proof anchoring) follow-ups. The
ticket ledger record was simply never updated past queued: no state
transition, no evidence, no acceptance binding. This pass writes no new
feature code; it reconciles the record against what exists.

Verification, not assertion: all 10 recorded evidence tests (the full
tests/unit/strata/test_reliability.py REL2xx suite + the system-level
self-model parse/elaborate test) run green on current main, and both
acceptance criteria are bound to the specific tests that prove them
(missing-timeout fires + waiver stays flow-scoped; declared-but-unproven
timeout fails against code).

Scope was widened (reasons recorded per-glob) to design/frob.strata and
src/frob/app/sys_runner.py because the already-landed footprint touches
both -- leaving them out would credit this ticket for less than the work
being reconciled.

Deferred remainder made honest: the two REL200 waivers on
design/frob.strata's elaborator-synthesized in-process cache flows
(graph_cache__fill, graph_cache__inval_f_parse) previously cited T-0640
itself as their follow-up. Closing this ticket would have left them bound
to a done ticket (exactly what WAIVE006 exists to catch), so the
attr-forwarding surface they wait on is now filed as T-0845 and both
waivers' ticket refs re-pointed there in this pass.

### Changed
```
 design/frob.strata |   4 +-
 tickets.md         | 140 +++++++++++++++++++++++++++++++++++++++++++++++++++--
 2 files changed, 139 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_flow_without_timeout_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_discharged_and_exempt_flows_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_waiver_on_one_flow_keeps_sibling_flow_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestCrossFamilyWaiverScoping::test_timeout_entrypoint_ignores_health_family_and_health_entrypoint_ignores_timeout_family` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 1209 warning(s), 210 waived

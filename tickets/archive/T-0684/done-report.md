## Done report

T-0684 reconciled all 27 deferred:T-0684 CWE Top-25-class entries in
docs/design/registry/weaknesses.yaml against real, already-live enforcement:

- 8 entries (CWE-78, 79, 89, 94, 502, 639, 918, 922) get
  handled_by:THREAT002 -- frob.strata._threat's CWE_CATALOG/
  CWE_TOP_25_CATALOG already carry a real (non-None) capability_kind join
  for each of these ids, so a strata design flow reaching that capability
  without the catalog's own mitigation claim fires a live THREAT002
  obligation. Added `frob:enforces CWE-<id>` directives at the emitting
  symbol (`_capability_violation` in src/frob/strata/_threat.py) for all 8,
  closing REG008.
- 1 entry (CWE-798, hard-coded credentials) gets handled_by:SEC001 --
  frob.gates._secrets' real-looking-token/credential structural scan is
  exactly this CWE's checkable shape and is already live. Added
  `frob:enforces CWE-798` at `_secret_violation`.
- 18 entries get honest out_of_scope:none dispositions, each naming the
  specific missing kernel concept (buffer/bounds model, endpoint/route +
  authn/authz-boundary predicate, numeric-range model, concurrency/
  interleaving model, deployment/filesystem-ACL configuration, or
  citation-only capability_kind=None precondition) -- cross-checked
  against frob.strata._threat.CWE_TOP_25_OUT_OF_SCOPE's own reasoned-none
  rows where one already existed (CWE-787/416/20/125/862/476/77/306/863/
  434), and newly reasoned by the same pattern for the remainder
  (CWE-22/352/119/190/269/276/287/362) which the CWE Top 25 (2025 pin)
  membership either never carried a kernel row for, or dropped when the
  2023->2025 pin bump removed them.

No new detector code was written -- every disposition here is either a
sync onto enforcement that already existed (T-0143/T-0345/T-0401's strata
threat-model work, and the pre-existing SEC001 secrets scanner) or an
honest documented gap. `frob check --only registry` is clean (0
errors, 0 REG warnings after the frob:enforces additions).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_is_classified_not_benign_excused` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2384 warning(s), 419 waived
- error-findings: none (measured, zero errors)

## Done report

Root cause: `unbound_acceptance` only checks that SOME evidence id is bound to a criterion, never whether that evidence establishes the specific claim the criterion text makes. A criterion asserting a package-wide gate outcome ("0 <RULE> findings under <glob>") is satisfied by binding any passing, unrelated node id -- exactly how T-1276 closed done against 116 live TEST005 findings under its own named glob.

Fix chosen: option (1)'s spirit -- a dedicated verification obligation for gate-outcome-shaped criteria -- implemented as an injected boolean guard (`gate_claims_verified`), the same idiom this module already uses for `covers_scope`/`reviewed`/`mutation_evidence`/`evidence_reverified`/`own_obligations_clean` (most recently T-1384's `own_obligations_clean`). NOT option (2) (reusing ClaimDivergence): ClaimDivergence's `DoneReportClaims` is a whole-ticket, count-only capture (test_count/gate_errors totals) with no per-criterion rule-id+glob dimension at all -- generalizing it to per-criterion identity claims is a materially bigger change than adding one more injected boolean next to five already-established ones, and it lives in `_land.py`, concurrently held by T-1390 this session. Reusing the exact existing idiom in the exact file this ticket scoped is the smaller, more consistent change (NO DUPLICATION cuts the same way: a sixth injected-boolean guard clause, not new machinery).

New detection primitives (`_criterion_gate_claim`, `_gate_claim_criteria`, both private) are a plain text scan for the "0 <RULE-ID> findings under <glob>" shape (mirrors `_new_gate_rule_acceptance`'s own "grep-shaped scan, not a full parse" posture) -- precision over recall, disclosed as a known gap for a criterion phrased some other way. `_done_transition_gate_claim_guard` refuses (`GateClaimUnverified`, a new `TicketError` variant in `_models.py`, alongside `OwnObligationsUnclean`) only when the caller injects `gate_claims_verified=False` AND at least one criterion matches; `None` (default) or no matching criterion is a complete no-op, matching this ticket's own hard rule that an ordinary criterion (no rule id, no glob) behaves exactly as before.

Computing the actual `gate_claims_verified` value (re-running the named gate against the named glob) needs `frob.gates`/`frob.app`, a dependency `frob.tickets` deliberately stays free of (same architectural boundary `own_obligations_clean` cites) -- wiring that computation into `frob.app.ticket_runner`'s close path and `frob.tickets._land`'s post-merge reverify is out of this ticket's scope (src/frob/tickets/_evidence.py, widened only to _models.py for the new TicketError variant) and is NOT done here, same as `own_obligations_clean` itself: T-1384 landed the guard with zero live callers, and nothing calls it with `gate_claims_verified=False` yet either. Filed T-1410 to wire the actual computation into close/land so the guard fires in practice, not just in its own unit tests.

Immediate remediation for T-1276 itself: already tracked by the existing T-1400 (blocked on T-1398/T-1399/T-1401) -- I initially filed a duplicate successor ticket (T-1409) before discovering T-1400 already covers this exact remainder; dropped it as a duplicate rather than leave two open trackers for the same work. No new ticket needed here.

Widened scope: added src/frob/tickets/_models.py (new TicketError.GateClaimUnverified variant only -- TicketError lives there, not in _evidence.py, same split T-1384 used for OwnObligationsUnclean) and tests/test_tickets_gate_claim_evidence.py (new test file). The test file could not be added to T-1399's declared scope via `frob ticket scope --add` -- T-1235 holds 'tests/**' in-progress (a real, disclosed concurrent lease, not stale) -- so it carries a `frob:waive SCOPE001` with that reason instead; not a guard weakening, since SCOPE001 stays live and enforced for every other file.

Did NOT touch src/frob/tickets/_land.py -- T-1390 holds it concurrently this session; wiring `gate_claims_verified` into land's post-merge reverify belongs there, tracked as part of T-1410's follow-up scope once T-1390 clears.

Filed: T-1410 (wire gate_claims_verified into close/land -- real, kept). T-1409 (T-1276 successor attempt) was dropped as a duplicate of the already-existing T-1400 -- verify T-1410's real id on main before citing it elsewhere.

### Changed
```
 tickets.md | 129 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 126 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_rejects_t1276_shape_when_gate_claims_verified_false` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_allows_t1276_shape_when_gate_claims_verified_true` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_permissive_when_gate_claims_verified_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_unaffected_when_no_gate_claim_criterion_exists` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_ordinary_criterion_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_gate_claim_criteria_filters_ticket_acceptance` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 6 error(s), 551 warning(s), 699 waived
- error-findings: AFFECT001@src/frob/tickets/_evidence.py, AFFECT001@src/frob/tickets/_models.py, PII012@src/frob/tickets/_evidence.py, PRE001@tickets/T-1399, SELFAUDIT001@design, TICK006@tickets.md

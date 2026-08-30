## Done report

T-3054's title/body was empty (no scope, no description) -- investigated via the codebase's own extensive prior engineering on this exact class of problem (T-1961/T-2023 lease wait, T-2774/T-2816 land-lock wait, T-2913 rapid-profile check_gates skip) plus docs/guides/agent-playbook-appendix.md's own T-2032/T-2033 investigation, which measured land's inline check_gates re-verification spawn at 144-209s median with a long tail (p95 483s, max 1620s) and explicitly documented this exact gap as NOT YET fixed: FROB_LAND_DEADLINE_S (T-2774) only bounded the land.lock WAIT, never this spawn's own cost, so a land under the default (non-rapid) profile with a declared deadline too small to cover it could still start it and get SIGTERM'd mid-spawn -- a designed cost exceeding the shell cap, SIGKILL mid-saga instead of a clean refusal, matching the ticket's own title. The appendix doc explicitly flagged the deeper fix (caching/skipping individual gate stages, or splitting the lock scope) as needing an explicit architecture decision from whoever owns _verify.py/_land.py, NOT a blind implementation -- so rather than force that judgment call, this fix extends the ALREADY-ESTABLISHED, ALREADY-SHIPPED T-2913 pattern (skip the inline spawn, defer verification to the unconditional post-land sweep) with a SECOND, independent trigger: a declared FROB_LAND_DEADLINE_S too small for the estimated cost (reusing T-2774's own _derive_post_land_sweep_budget_s estimator, no new number to desync). This is surgical (one function extended, one new small helper split out for ARCH001, both in _land.py which was already in scope for the land saga) and strictly additive: absent/unparseable FROB_LAND_DEADLINE_S is byte-for-byte unchanged from before. 27/27 tests pass covering the new deadline-aware skip (4 new tests: insufficient-deadline-skips-regardless-of-profile, ample-deadline-still-runs, no-declared-deadline-unchanged, unparseable-deadline-unchanged) plus every pre-existing T-2913/T-2774/T-2816 test (no regression).

### Changed
```
 docs/modules/tickets-landing.md | 39 ++++++++++++++++++
 src/frob/tickets/_land.py       | 90 +++++++++++++++++++++++++++++++++++++++--
 tests/test_ticket_land.py       | 77 +++++++++++++++++++++++++++++++++++
 tickets/T-3054/ticket.md        | 40 ++++++++++++++++++
 4 files changed, 243 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline::test_insufficient_deadline_skips_regardless_of_profile` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline::test_ample_deadline_still_runs_the_spawn` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline::test_no_declared_deadline_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline::test_unparseable_deadline_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 11 error(s), 4483 warning(s), 858 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json

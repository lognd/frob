---
id: T-2938
title: Move ClaimDivergence re-verification onto the deferred post-land queue instead
  of scoping it inline
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/tickets/_land_verify.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/test_rapid_sweep.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2938: wire deferred post-land claim-divergence re-verification into the
    rapid sweep (_rapid_sweep.py), reusing _land_verify.py comparison helpers'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: 'T-2938: wire deferred post-land claim-divergence re-verification into the
    rapid sweep (_rapid_sweep.py), reusing _land_verify.py comparison helpers'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'T-2938: doc for the moved check + its unit test coverage'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2938: doc for the moved check + its unit test coverage'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_matching_claim_raises_nothing
- tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_divergent_claim_raises_quarantine_attributed_to_landing_ticket
- tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_stale_baseline_refuses_to_attribute
- tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_no_captured_claims_section_is_a_noop
- tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt
- tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid::test_non_rapid_profile_still_runs_inline_check_gates_spawn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b99dd0c2ff579a4df7bca012ba320f6e40ef840d
---
T-2913 removed the inline `frob check --ticket` spawn from the rapid land path
(measured 241.59s at 115% CPU, on EVERY land regardless of profile). That was
right and it stays removed. But it fed the ClaimDivergence check, which refuses
a land when a Done report's claimed gate error counts diverge from post-merge
reality -- and nothing restores that property. Claim re-verification exists ONLY
in `src/frob/tickets/_land_verify.py`, on the land path. The deferred sweep
detects NEW FINDINGS, which is a different property.

T-2924 proposed making the inline check cheap by scoping it to the merge delta.
That was investigated and REJECTED as unsound, with a reason worth preserving:
`--only` is a strict run-selector -- a family either runs in full or is entirely
absent from the output -- while `_parse_error_findings_from_json` (the T-0754
comparator) counts an error-severity finding from ANY ToolResult, gate or
lint/static tool alike. So any `--only` narrowing at land time silently drops
coverage for the omitted families from the very comparison the check exists to
make sound. `_shared_check_spawn_fn`'s own prior T-2053 investigation had
already flagged this. A safe inline version would need new infrastructure
(merging cached T-0602 gate results for un-rerun families into the compared
total), which is more than a scoping change.

DECISION (coordinator, superseding the inline-scoping approach): do not try to
make the check cheap enough to run inline. MOVE the claim-divergence comparison
onto the deferred post-land queue that already exists and already raises
quarantine.

Rationale. Claim divergence is a REPORT-HONESTY violation, not bad content
reaching main. The land publishes code that the agent's own pre-land check
already covered; what is unverified is whether the Done report's NUMBERS match
post-merge reality. Detecting that behind the land and raising quarantine is
proportionate, and it matches the publish-fast/verify-behind architecture the
rapid profile is built around. It also avoids putting a multi-minute check back
on the critical path, which is the entire point of T-2913.

This is not a licence to lose the property. A divergent claim must still be
DETECTED and ATTRIBUTED to the ticket that made it -- just after the land rather
than before it.

ACCEPTANCE

- Given a Done report whose claimed gate error counts diverge from post-merge
  reality, when the land completes under the rapid profile and the deferred
  queue drains, then the divergence is detected, raises quarantine, and is
  attributed to the landing ticket by id. Must-fire fixture required.
- Given a Done report whose claims match reality, when the same path runs, then
  no quarantine is raised and no new finding stream appears. Must-stay-quiet
  fixture required; re-measure repo-wide counts before and after.
- Given the non-rapid profile, when a land runs, then the existing inline
  ClaimDivergence refusal is UNCHANGED. Non-rapid must not regress.
- Given a stale verification baseline, when the deferred claim check would run,
  then it must refuse to attribute rather than report a confident wrong result
  -- reuse T-2929's existing staleness refusal rather than adding a second
  staleness policy.
- Land wall-clock under rapid must not regress from its post-T-2913 value.
  Measure and report before/after.

NOT IN SCOPE: re-scoping `_land_lock` itself (rejected under T-2937 as a
high-risk change to a core-locking file with a long incident history), and
building the T-0602 cache-merge infrastructure (that is T-2924's remaining idea,
left queued as the fallback if this deferred approach proves insufficient).
## Done report

Built the SOUND half of "is a frob:waive inert" -- deliberately not the
absence-based check the ticket's own filing text originally gestured at.

Research before writing any code (per the coordinator's explicit brief):
traced T-2493's own idea back through this repo's actual history and
found it had ALREADY been tried once, as T-1579's `_rule_has_live_finding`
escape -- "the rule fired somewhere this run, so the detector is healthy,
so a waiver of that rule matching nothing here is provably stale." That
shipped and deleted 55 LIVE waivers during a partially-degraded run that
found SOME instances of a rule while missing the exact sites the deleted
waivers covered. Reverted; locked by
tests/test_gates.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_with_live_finding_elsewhere_still_refuses.
T-1904 (successor) named the missing capability -- per-site
analysis-coverage proof -- and that substrate was later built
(T-1921/T-1943, frob.gates._coverage_sites) but deliberately shipped
wired to NOTHING, explicitly to avoid repeating the incident.

Given that, "0 findings for this waiver's site" (WAIVE004's own signal,
already implemented and correctly hardened with unconditional refusals
post-incident) can never be treated as inertness proof, in this ticket
or any future one, without the missing per-site coverage capability --
confirmed still absent for a general per-waiver verdict (the substrate
only instruments 5 gate families and stays unwired by design).

Root-caused the two REAL matching bugs this repo has actually found and
fixed (T-2314: gate:PERF emitted absolute paths so `_match_waiver`'s
file-equality silently never matched; T-2438: a hand-rolled C++ symref
spelling differed from the DSL's canonical qualname join) -- both were
found the SAME way: a violation persisted, UNSUPPRESSED, despite a
waiver that should have covered it. Presence, never absence. That is
the sound, general signal this ticket implements.

Changed:
- src/frob/app/ticket_runner/_waive_audit.py::CollisionSuspect (new
  model: file/line/rule/reason plus the colliding violation's own
  line/message)
- src/frob/app/ticket_runner/_waive_audit.py::find_collision_suspects
  (new pure function: for each waiver, flag it only when a
  GateReport.violations -- the KEPT/unsuppressed set -- entry of the
  same rule sits in the same repo-relative file; normalizes both sides'
  paths to catch T-2314's own absolute-vs-relative shape independent of
  whether _match_waiver's own comparison does)
- src/frob/app/ticket_runner/_waive_audit.py::_repo_relative (path
  normalization helper)
- docs/modules/app.md#waive-audit-t-2467 (documents the function, its
  disclosed blind spot, and the incident history)
- tests/unit/test_waive_audit_runner.py::TestCollisionSuspects (4 tests)

MANDATORY positive/negative controls, both satisfied:
- POSITIVE (must flag):
  test_active_unsuppressed_violation_in_same_rule_and_file_is_flagged --
  a waiver present, a real violation of the same rule/file left in the
  KEPT set (as if the waiver's shape never actually matched it) -> IS
  flagged.
- NEGATIVE #1 (must NOT flag): test_a_correctly_matching_live_waiver_is_
  not_flagged -- the waiver's rule/file has nothing in kept (its
  violation was correctly suppressed into waived); an unrelated kept
  violation in the same file proves this isn't a blanket file-level
  false match -> NOT flagged.
- NEGATIVE #2, the one that matters most (must NOT flag):
  test_a_quiet_hardened_site_with_zero_violations_anywhere_is_not_
  flagged -- a load-bearing waiver on a hardened guard with ZERO
  violations of its rule anywhere (the EXACT shape T-1579's escape
  misread as "provably dead") -> NOT flagged, by construction, since
  this function never reasons from absence at all.
- Bonus: test_absolute_violation_path_still_matches_repo_relative_waiver
  proves the path-normalization actually closes T-2314's own root
  cause rather than just restating the theory.

Disclosed blind spot, stated explicitly rather than hidden: a waiver
whose site has zero CURRENT violations anywhere is invisible to this
check -- indistinguishable from a genuinely inert waiver using only this
signal. Closing that gap needs the missing per-site coverage capability
this repo has twice now (T-1579, T-1904) found to be a materially
larger, multi-file undertaking, not something to approximate here.

Report-only, as required: find_collision_suspects is pure (takes data,
returns data), mutates nothing, is not called from `frob check` or
`frob ticket land`'s path, and is deliberately NOT wired to any CLI
subcommand by this ticket -- WIRE001 waived with an honest reason and a
real follow_up (T-2496, filed this ticket, scoped to the CLI
wiring only, itself required to stay report-only).

Filed: T-2496 "wire find_collision_suspects into a waive-audit
CLI subcommand" -- the CLI-wiring follow-up, out of this ticket's
single-file scope.

Gates: `frob check --ticket T-2493` clean on every touched file
(_waive_audit.py, docs/modules/app.md, tests/unit/
test_waive_audit_runner.py) -- ty/ruff/AFFECT001/WIRE002 all resolved.
`frob test --base main` selected 5 touched tests, exitstatus=0.

Session-pattern note for the coordinator: this is NOT a fourth instance
of "fix landed, mechanism still unusable for an adjacent reason" --
find_collision_suspects works exactly as designed and both controls
pass. The closer parallel is structural: like T-1904/T-1921/T-1943, the
sound version of this idea turned out to be materially SMALLER in scope
than the naive one (no per-site coverage substrate needed here, because
collision-based detection never needs to ask "was this site examined" --
presence of an unsuppressed violation already proves it was), at the
cost of a disclosed, permanent blind spot rather than a false sense of
completeness.

### Changed
```
 tickets/T-2493/ticket.md           | 22 +++++++++++++++++++++-
 tickets/T-2496/ticket.md | 27 +++++++++++++++++++++++++++
 2 files changed, 48 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_active_unsuppressed_violation_in_same_rule_and_file_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_a_correctly_matching_live_waiver_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_a_quiet_hardened_site_with_zero_violations_anywhere_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestCollisionSuspects::test_absolute_violation_path_still_matches_repo_relative_waiver` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, LANG004@src/frob/lang/_support.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2493, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

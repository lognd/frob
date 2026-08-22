## Done report

DOC006 unblocked first, as instructed: waived the `frob ticket doctor`
pointer above (illustrative hypothetical, never a real command) so this
ticket's body stopped carrying a hard DOC006 error on the shared floor.

Design decision: TICK012, a new read-time gate rule in
`frob.gates._tickets_gate` (dispatched from `tickets_gate()`, registered
in `_KNOWN_GATE_RULES`/`docs/design/registry/check-coverage.yaml`), not
a `mutate_scope`-adjacent write-time guard -- `mutate_scope`
(`src/frob/tickets/_scope.py`) and the ticket_runner write paths that
call it sit outside this ticket's declared scope, and this ticket's own
briefing named `src/frob/app/ticket_runner/` as actively held by
another agent, so a write-time guard there would have been both an
undeclared scope expansion and a lease collision. TICK012 fires one WARN
per IN_PROGRESS ticket whose live lease (`read_all_leases`) names a path
`scope_matches` no longer accepts against the ticket's CURRENT declared
scope -- closing the general case T-2547's `_effective_leakage_scope`
empty-scope short-circuit never covered, for every `read_all_leases`
consumer, not only CrossTicketLeakage.

Verified against the real repo, not only synthetic fixtures: a `frob
check` run on this worktree found a genuine live instance, T-2550
(in-progress, 3-4 of its lease's recorded paths no longer matched its
current declared scope) -- exactly the incident class this ticket exists
to surface.

Positive/negative controls (both directions, per BUG002):
- must-fire: `test_stale_superset_path_fires` -- confirmed genuinely
  FAILED_AT_PARENT via `frob ticket evidence --check-repro` against the
  test-only commit (before the TICK012 implementation existed), and
  designated as this ticket's repro test.
- must-not-fire (silent controls): `test_lease_matching_current_scope_
  is_silent` (exact-match lease), `test_queued_ticket_with_no_lease_is_
  silent` (no live lease at all), `test_dir_scope_still_covers_its_own_
  lease_paths` (a lease path still genuinely covered by a directory-
  shaped declared scope via `scope_matches`'s glob expansion, not a
  literal-string false positive).

Doc/registry wiring done in the same change: `docs/modules/tickets-
lifecycle.md`'s T-0162 decision-record section (AFFECT001's target for
`tickets_gate`) now names TICK012; `docs/design/registry/check-
coverage.yaml` got a `CHK-GATE-TICK012` entry plus its `gate_rule_total`
bump (327 -> 328), matched by `frob:enforces CHK-GATE-TICK012` on the
rule itself (REG010/REG005/REG008 all clean for this rule as a result).

Disclosed, filed, not silently dropped: `docs/modules/gates.md`'s
`frob:enumerates` rule-catalog list (DOCENUM001's target) still omits
TICK012 -- that file was held by another in-progress ticket's live lease
(T-2377) throughout this session, so widening T-2561's scope onto it
would have been a lease collision, not a legitimate expansion. Filed
T-2589 (`docs/modules/gates.md` scope) to add TICK012 (and the
pre-existing CYCLE001 gap found alongside it) once that lease frees up.
DOCENUM001 is therefore still red on `frob check` for this one rule,
disclosed here rather than waived or hidden.

Changed:
- `src/frob/gates/_tickets_gate.py::_tick012_lease_scope_drift` (new),
  wired into `tickets_gate()`
- `src/frob/gates/_waive.py::_KNOWN_GATE_RULES` (TICK012 added)
- `docs/modules/tickets-lifecycle.md` (T-0162 decision record, TICK012
  note)
- `docs/design/registry/check-coverage.yaml` (CHK-GATE-TICK012 entry,
  gate_rule_total bump)
- `tickets/T-2561/ticket.md` (DOC006 waive, this Done report)

Evidence: `tests/test_gates.py::TestTick012LeaseScopeDrift::
test_stale_superset_path_fires` (designated repro, FAILED_AT_PARENT
confirmed), `test_lease_matching_current_scope_is_silent`,
`test_queued_ticket_with_no_lease_is_silent`,
`test_dir_scope_still_covers_its_own_lease_paths`.

Filed: T-2589 (docs/modules/gates.md TICK012/CYCLE001
enumerates gap, blocked on T-2377's lease).

Gates: `frob check --ticket T-2561` clean of everything this ticket's
diff touches except the disclosed DOCENUM001 gap above (a real,
pre-existing, out-of-my-scope lease collision, not a waived-away
finding).

---
id: T-1705
title: close-time REL001 preflight is not rapid-aware and names a remedy the agent
  is forbidden to perform
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_profile.py
- tests/unit/test_close_rel001_bump.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_rapid_skips_the_check_and_records_debt
- tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_standard_still_runs_the_check
- tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_outstanding_bump_under_standard_names_land_as_the_remedy
- tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_unresolvable_profile_falls_back_to_running_the_check
designated_repro_test: null
threat: null
component: null
---
`frob ticket close`'s own-obligations preflight
(`_own_obligations_rel_bump_dirty`, `_close_cmd.py`) demands a REL001
version bump that a worktree-isolated agent structurally CANNOT satisfy:
`pyproject.toml` is land-owned and the T-0731 pre-commit hook refuses any
commit that touches its version line. The agent is told to do something
the tooling forbids it from doing.

Two separate defects behind that.

1. NOT PROFILE-AWARE. T-1575 specifies REL001 OFF under `rapid`, and
   `frob check`'s REL gate and the land path both honour that. This
   close-time preflight does not -- it calls `_required_release_bump`
   unconditionally. Under `rapid` it should not run at all. (T-1684
   already fixed a related half of this function: it compared the
   required bump against nothing, so an ALREADY-APPLIED bump never
   satisfied it. This is the remaining half.)

2. NO AGENT-REACHABLE REMEDY EVEN UNDER `standard`. The bump is applied
   by `_apply_release_bump_for_land` during land, which runs with the
   land's own internal commit channel. So the correct answer for an agent
   is "do not close by hand, let land close it" -- but `close`'s error
   message does not say that. It says the bump is outstanding, which
   reads as "go bump it", which the agent then cannot do. Two agents this
   session independently tried and were blocked; one worked around it by
   discovering that `frob ticket land` performs its own close internally.

   That workaround is the actual intended path and should be what the
   error names.

Fix:

- Skip the REL001 preflight entirely when `effective_profile(root)` is
  `rapid`, at the same seam every other rapid relaxation uses -- never an
  inline profile check sprinkled into unrelated logic -- and record it
  via `record_rapid_debt` like every other rapid relaxation, so the
  skipped check stays auditable.
- Under non-rapid profiles, when the bump is outstanding AND the caller
  is not the land path, the message must name the real remedy: the bump
  is applied by `frob ticket land`, which closes the ticket itself; a
  hand `close` is not the supported route for a ticket with a public-API
  change. Do not tell a caller to perform an action the hook forbids.

Regression coverage: under `rapid`, a ticket with a public-API change
closes without a bump and records the relaxation as debt; under
`standard`, the refusal message names `frob ticket land` as the remedy
rather than a bare "bump outstanding".

## Done report

Both defects fixed, exactly as scoped.

1. NOT PROFILE-AWARE: `_own_obligations_rel_bump_dirty`
   (src/frob/app/ticket_runner/_close_cmd.py) now checks
   `effective_profile(root)` first -- under `rapid`, the whole REL001
   preflight is skipped and the relaxation is recorded via
   `record_rapid_debt(root, ticket.id, "close-rel001-preflight-skipped")`,
   the same seam `frob.tickets._land._land_is_rapid` already uses for
   every other rapid relaxation. Fails closed: an unresolvable profile
   falls back to running the check (tested explicitly), never silently
   skips it.

2. NO AGENT-REACHABLE REMEDY: the outstanding-bump WARNING now names the
   real remedy explicitly -- "do NOT bump pyproject.toml by hand, that
   commit is land-owned and the T-0731 hook will refuse it; the
   supported remedy is `frob ticket land <id>`, which applies the bump
   and closes this ticket itself." Tested that the log message actually
   contains both the prohibition and the named remedy.

Regression coverage matches the ticket's own acceptance text: under
rapid, closes without a bump and records debt (tested); under standard,
the refusal message names `frob ticket land` (tested).

Not touched, disclosed rather than silently dropped: the generic
own-obligations refusal message in `frob.tickets._evidence`'s
`transition` (shared across COV001/SELFAUDIT001/REL001) still fires
alongside the specific, now-corrected REL001 WARNING this ticket owns --
`_evidence.py` is outside T-1705's declared scope.

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002.

### Changed
```
 tickets/T-1705/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_rapid_skips_the_check_and_records_debt` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_standard_still_runs_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_outstanding_bump_under_standard_names_land_as_the_remedy` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_unresolvable_profile_falls_back_to_running_the_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 931 warning(s), 731 waived
- error-findings: none (measured, zero errors)

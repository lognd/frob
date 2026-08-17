---
id: T-2268
title: 'Holding ticket: 14 pre-existing floor findings with no owning ticket (blocked
  quarantine clearance, fleet-wide land stall 2026-08-17)'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_skills_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Each listed finding is fixed or has its own owning ticket; none remains attributed
    solely to this holding ticket
  evidence: []
- text: The _skills_sync.py trio (COV001/DOC002/RENDER001) is addressed first -- regressions
    from a land hours old, not historical debt
  evidence: []
- text: Fixes land as separate subsystem-scoped commits; state the split
  evidence: []
- text: 'MUST-STILL-PASS: unscoped frob check with gate-summary present shows the
    floor down by the number fixed, no new identities'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# Tracking ticket: 14 pre-existing floor findings with no owning ticket, blocking quarantine clearance

## Why this ticket exists

`clear_quarantine` is ATOMIC over every recorded finding. On 2026-08-17 it
refused with 36 findings undisposed while quarantine was RAISED, which turns
off deferred landing repo-wide -- three lands retried for 45+ minutes with zero
completions and left staged residue in the shared root each time.

22 of the 36 already have owning tickets (COV003 x11 -> T-2256, COV004 x2 ->
T-2254, DOC011 x2 -> T-2237, and E501/F541/DRIFT001 x3/SELFAUDIT001/CLAUDE001
-> T-2260). The 14 below had none, so quarantine could not clear and the fleet
stayed blocked.

This ticket exists so those 14 are HONESTLY TRACKED rather than dismissed. They
are real findings, present in the measured unscoped floor. Disposing them to
this ticket asserts "tracked, not fixed" -- it does not assert they are
acceptable.

## The 14

    ARCH001    scripts/fleet_status.py
    ARCH001    src/frob/app/telemetry.py
    ARCH001    src/frob/app/ticket_runner/_land_cmd.py
    ARCH001    src/frob/app/ticket_runner/_new.py
    ARCH103    src/frob/app/ticket_runner/_land_cmd.py
    COV001     scripts/fleet_status.py
    COV001     src/frob/scaffold/_skills_sync.py
    COV002     src/frob/app/ticket_runner/_lifecycle.py
    COV002     src/frob/tickets/_land.py
    DOC002     src/frob/scaffold/_skills_sync.py
    DOC005     README.md
    DOC005     docs/modules/cli.md
    PERF004    scripts/fleet_status.py
    PERF004    src/frob/app/ticket_runner/_land_cmd.py
    REL001     pyproject.toml
    RENDER001  src/frob/scaffold/_skills_sync.py
    TEST010    tests/test_ticket_work_and_land_finish.py

Note three of these (COV001, DOC002, RENDER001 on `_skills_sync.py`) arrived
with T-2241's own land -- a brand-new subcommand landed without its doc edge,
export declaration, and render coverage. Those are the freshest and most
clearly actionable.

## Do NOT fix it this way

- **Do NOT dismiss these findings to clear quarantine.** A `--dismiss` asserts
  the finding is not a problem. These are real and the floor will keep
  reporting them; dismissing makes the quarantine lie rather than the floor
  shrink. That is why this ticket was filed instead.
- **Do NOT treat this ticket as a licence to leave them.** It is a holding pen
  with a named owner, not an acceptance. Split real work out of it as separate
  tickets rather than growing it.
- **Do NOT fix all 17 lines above in one change.** They span six unrelated
  subsystems. A single sweeping commit would be unreviewable and would collide
  with half the fleet's leases.
- **Do NOT resolve ARCH001 by raising the threshold.** The 60-line limit is the
  rule; the fix is extraction, and T-2214 landed a land-time gate specifically
  to stop these accumulating.

## Acceptance criteria

1. (MUST FAIL FIRST) Each of the listed findings is either fixed or has its own
   owning ticket; none remains attributed solely to this holding ticket. Fails
   today: all 14 identities point here and nowhere else.
2. The `_skills_sync.py` trio (COV001/DOC002/RENDER001) is addressed first --
   they are regressions from a land hours old, not historical debt.
3. Fixes land as separate, subsystem-scoped commits; state the split.
4. MUST-STILL-PASS CONTROL: an unscoped `frob check --json` (with
   `gate-summary` present -- a budget-truncated run reports a false
   improvement) shows the floor DOWN by the number fixed, with no new
   identities introduced.
5. When this ticket closes, no finding is left silently attributed to it.

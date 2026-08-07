---
id: T-1705
title: close-time REL001 preflight is not rapid-aware and names a remedy the agent
  is forbidden to perform
state: queued
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_profile.py
- tests/unit/test_close_rel001_bump.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
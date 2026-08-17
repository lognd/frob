---
id: T-2280
title: 'Land-time ''does not worsen'' gate covers ARCH001 alone, so every other error
  rule accumulates: floor grinds at -0.5/land while RENDER001 went 1 to 4'
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
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'A land introducing a NEW error-severity finding in a touched file is refused,
    naming rule/file/symbol (fixture: a bare print() producing a new RENDER001)'
  evidence: []
- text: 'MUST-STILL-PASS: clean land unaffected; pre-existing error in a touched file
    does not refuse; T-2214''s ARCH001 behaviour unchanged; unmeasurable worktree
    reports SKIPPED-UNMEASURED and still lands'
  evidence: []
- text: Participating rules derived from SEVERITY, not a hardcoded rule-name list,
    so a newly added ERROR gate is covered automatically
  evidence: []
- text: The refusal names what to fix and how to waive it in one message
  evidence: []
- text: State the added wall-clock on a land before and after; the land path is the
    fleet bottleneck
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# The land-time "does not worsen" gate covers ARCH001 alone, so every other rule accumulates one finding at a time

## Measured evidence (2026-08-17)

Unscoped `frob check --json`, coverage verified in every run (`gate-summary`
present, 25 gate families -- not a budget-truncated read):

    floor:  59  ->  53  ->  49 errors    across ~10 lands

Roughly -0.5 errors per land. The floor is not converging; it is grinding.

The reason is visible in the composition. Between the last two measurements,
while other classes were being actively repaired, these GREW:

    RENDER001      1 -> 4
    SELFAUDIT001   1 -> 3
    DOC005         2 -> 3
    ARCH103        2 -> 3

RENDER001 is the clearest case: T-2268 FIXED one RENDER001 (routing
`_skills_sync.run` through `Renderer.for_stream` instead of bare `print()`),
and the count still went to 4 -- new ones arrived in other lands faster than it
cleared.

## The gate exists, for exactly one rule

T-2214 landed `_assert_diff_does_not_worsen_long_functions_pre_land`
(`src/frob/app/ticket_runner/_land_cmd.py:3672`, wired at :3763). It refuses a
land whose diff pushes a function over ARCH001's threshold that was not already
over it at merge-base. That is precisely the right shape -- and it is the only
rule with it. Nothing stops a land introducing a new RENDER001, SELFAUDIT001,
DOC005, ARCH103, DRIFT001, or COV00x in the files it touches.

`git grep "_assert_diff_does_not_worsen" -- src/frob/app/ticket_runner/_land_cmd.py`
returns three hits, all for the long-functions check. No ticket generalizes it
(checked T-2081 dropped, T-2189/T-2201/T-2214/T-2220 all done and unrelated).

## Do NOT fix it this way

- **Do NOT gate on ALL findings.** There are 6,416 warnings and 1,320 notes.
  Refusing any land that adds one would stop the fleet dead. Gate
  ERROR-severity only, and say so explicitly.
- **Do NOT gate on the repo-wide count.** A land must not be refused because
  someone else's finding appeared, or because a pre-existing error happens to
  live in a file it touched. T-2214's shape is the correct one: compare the
  finding set for the TOUCHED files against the same files at merge-base, and
  refuse only what this diff newly introduces. Reuse that comparison, do not
  invent a second one.
- **Do NOT hard-fail when the comparison cannot be made.** A fresh worktree
  legitimately fails collection/native builds, and T-2255 just fixed a guard
  that went SILENT in exactly that case -- the lesson there was to surface the
  skip, not to block the land. Same rule here: if it cannot measure, say
  SKIPPED-UNMEASURED loudly and let the land proceed.
- **Do NOT require a waiver for every pre-existing finding in a touched file.**
  That would make any edit to an already-dirty file impossible and drive agents
  to waive in bulk, which is worse than the accumulation.

## Acceptance criteria

1. (MUST FAIL FIRST) A land whose diff introduces a NEW error-severity finding
   in a file it touches is refused, naming the rule, the file, and the symbol.
   Build the fixture from a real case: a bare `print()` added to a module,
   producing a new RENDER001 that does not exist at merge-base.
2. MUST-STILL-PASS CONTROLS, all four:
   - a land introducing no new error-severity findings still lands unchanged;
   - a PRE-EXISTING error in a touched file does not refuse the land;
   - T-2214's ARCH001 behaviour is unchanged (same refusals, same waiver
     honouring);
   - a worktree that cannot measure reports SKIPPED-UNMEASURED and still lands.
3. Which rules participate is stated explicitly and derived from severity, not
   a hardcoded rule-name list -- a new ERROR-severity gate must be covered
   automatically, or the same gap reopens on the next rule added.
4. The refusal names what to fix and how to waive it, in one message.
5. Measure the cost: state the added wall-clock on a land before and after. The
   land critical path is already the fleet's bottleneck (T-1684 moved work off
   it deliberately); a gate that adds minutes is not acceptable.

## Scope note

`src/frob/app/ticket_runner/_land_cmd.py` owns T-2214's gate and its wiring.
Verified unleased at filing. The finding-comparison primitive it needs already
exists there; if the right home turns out to be `src/frob/tickets/_land.py`
instead, say so with a measured reason rather than widening silently.

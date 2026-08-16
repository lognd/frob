---
id: T-2257
title: 'frob ticket new does not warn when another QUEUED ticket already scopes the
  same file: four tickets piled onto scripts/fleet_status.py and must now run serially'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Filing a ticket whose scope overlaps an existing queued/in-progress ticket
    emits a warning naming the other ticket(s) and overlapping path(s) (fails today:
    no such warning)'
  evidence: []
- text: Overlap computed on resolved paths so glob-vs-file is detected (src/frob/**
    vs src/frob/gates/_x.py)
  evidence: []
- text: 'MUST-STILL-PASS: a non-overlapping ticket files silently as today, and filing
    SUCCEEDS in both cases -- advisory, not a gate'
  evidence: []
- text: Terminal-state tickets (done/dropped/archived) excluded; state how determined
  evidence: []
- text: 'Verified against the real case: a fifth ticket scoped to scripts/fleet_status.py
    names T-2213, T-2229, T-2236, T-2249'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# `frob ticket new` does not warn when other QUEUED tickets already scope the same file, so filings silently pile up into a serial queue

## Measured evidence (2026-08-16)

Four queued tickets all declare `scripts/fleet_status.py`:

    T-2213   scripts/fleet_status.py
    T-2229   scripts/fleet_status.py, src/frob/gates/_tickets_gate.py
    T-2236   scripts/fleet_status.py, scripts/frob-telemetry-hook, docs/guides/coordinator-scripts.md
    T-2249   scripts/fleet_status.py

Because scope IS the lease here, these cannot be worked in parallel. Four
individually small fixes become four sequential agent-runs. A second, smaller
pileup exists on `docs/guides/coordinator-scripts.md` (T-2236 and T-2237).

None of these filings was warned about anything. `frob ticket new` prints
scope-CLOSURE warnings (doc/test edges not in scope) but says nothing about
another OPEN ticket already claiming the same path:

    git grep -nE "already scope|same file|other queued|scope overlap" \
      -- src/frob/app/ticket_runner/_new.py     -> no matches

## Why a rule is not the fix here

I already knew this. When filing T-2249 I wrote in its own scope note: "T-2213
and T-2229 are also queued against this same file. Dispatch all three as ONE
series." Then I filed T-2236 against the same file anyway, without re-checking.
The knowledge was written down, in the ticket, by the same person, minutes
earlier -- and it still did not fire at the moment of the next filing. That is
the definition of a rule that needs enforcement rather than repetition.

The adjacent check that DOES exist does not cover this: `fleet_status --ticket`
(T-2225) reports SCOPE COLLISION only against LIVE leases. A queued ticket
holds no lease, so four queued tickets on one file all report
`dispatchable: True` and collide only when the second one is dispatched.

## Do NOT fix it this way

- **Do NOT refuse the filing.** Two tickets legitimately touching one file is
  normal and often correct (a fix and its follow-on residue). This must be a
  WARNING that informs sequencing, never a block.
- **Do NOT auto-merge or auto-block the new ticket.** Whether these are one
  series or genuinely independent is a judgement call; presuming it would
  create false `blocked_by` edges, and `frob ticket block` is the audited path
  for that decision.
- **Do NOT compare scope entries as strings.** Scope entries are globs
  (`src/frob/**`); a new ticket scoped to `src/frob/gates/_x.py` collides with
  an existing `src/frob/**` and no text comparison of those two shows it.
  Expand and compare RESOLVED PATHS -- T-2225 already built exactly this
  (`_expand_scope_globs_to_paths`) for the live-lease case. Reuse it rather
  than writing a second expander. Standing user directive: token/grammar,
  never lexical.
- **Do NOT include terminal tickets.** A done/dropped/archived ticket's scope
  is history, not a claim. Only open states count.

## Acceptance criteria

1. (MUST FAIL FIRST) Filing a ticket whose scope overlaps an existing QUEUED or
   IN-PROGRESS ticket's scope emits a warning naming the other ticket(s) and
   the overlapping path(s). Fails today: no such warning exists.
2. The overlap is computed on resolved paths, so a glob-vs-file overlap is
   detected (`src/frob/**` vs `src/frob/gates/_x.py`).
3. MUST-STILL-PASS CONTROLS: a ticket with no overlap files silently as it does
   today, and the filing SUCCEEDS in both cases -- this is advisory output, not
   a gate. Existing scope-closure warnings are unaffected.
4. Terminal-state tickets (done/dropped/archived) are excluded; state how that
   is determined.
5. Verify against the real case: filing a fifth ticket scoped to
   `scripts/fleet_status.py` must name T-2213, T-2229, T-2236, T-2249.

## Scope note

`src/frob/app/ticket_runner/_new.py` owns the filing path and already emits
scope-closure warnings -- add alongside those. The path-expansion logic exists
in `scripts/fleet_status.py` from T-2225; if it cannot be imported (that script
is deliberately import-light and does not import frob), say so and propose
where the shared home should be rather than silently duplicating it.

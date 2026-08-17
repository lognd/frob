---
id: T-2312
title: Auto-filer skips DISPOSAL when it declines to file a duplicate, pinning quarantine
  and deadlocking every land fleet-wide
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given findings whose equivalent ticket already exists, when the auto-filer
    declines to duplicate, then it disposes them to that existing ticket and quarantine
    clears
  evidence: []
- text: given findings with no owning ticket at all, when the sweep runs, then quarantine
    still raises and still blocks (guard not weakened)
  evidence: []
- text: given quarantine is raised, when an operator reads fleet status or a land
    refusal, then the raised state and undisposed count are stated without needing
    frob verify status
  evidence: []
- text: given a quarantine store holding both absolute-path and relative-path finding
    identities, when an operator addresses one with --file-ticket, then a path-shape
    mismatch is reported as such rather than as a bare FindingsNotDisposed
  evidence: []
threat: null
component: verify
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17 evening: the whole 5-agent fleet was deadlocked for
~90 minutes. Zero lands completed. Root cause was a pinned verify
quarantine, which forces synchronous verification repo-wide and drives
every land past its shell-wrapper timeout.

THE THREE PINNED FINDINGS:

    [UNDISPOSED] E402:/home/logan/projects/frob/scripts/fleet_status.py: (commit=None, ticket=None)
    [UNDISPOSED] E501:/home/logan/projects/frob/scripts/fleet_status.py: (commit=None, ticket=None)
    [UNDISPOSED] F841:/home/logan/projects/frob/tests/test_ticket_land.py: (commit=None, ticket=None)

THE BUG: **T-2308 already existed and already named all three rule/file
pairs explicitly as UNATTRIBUTED.** The findings had a real owning ticket
the entire time. Nothing disposed them to it, so quarantine stayed raised.

The rapid sweep's auto-filer normally closes this loop -- earlier the SAME
day it raised quarantine at 06:28 and cleared it at 06:29 with
`cleared_reason: auto-filed by rapid sweep as T-2266`. That path works when
it files a NEW ticket.

The gap is the duplicate branch. An implementer working the fleet observed
the auto-filer declining with, verbatim:

    T-2308 already has this exact title and this exact scope

So when the auto-filer detects that an equivalent ticket already exists, it
skips filing -- and skips DISPOSING as well. Refusing to duplicate is
correct; abandoning the disposal is not. The findings are left undisposed
with no owner recorded, quarantine pins, and deferred landing switches off
fleet-wide. The better the dedup logic works, the more reliably the fleet
deadlocks.

NOTE THIS IS NOT THE T-2207 SHAPE, and T-2207's recovery verb cannot help:
`--retire-unidentifiable` matches `rule_id == "" and file == ""`. These
findings have BOTH populated; only `commit`/`ticket`/`line` are None. An
operator following the T-2207 playbook finds the documented escape hatch
silently inapplicable and concludes there is no CLI recovery path. There
is one -- `--file-ticket RULE:FILE:=T-2308` with an empty LINE -- but
nothing points at it.

MANUAL RECOVERY THAT WORKED (for the record):
    frob verify dispose \
      --file-ticket "E402:<abs-path>/scripts/fleet_status.py:=T-2308" \
      --file-ticket "E501:<abs-path>/scripts/fleet_status.py:=T-2308" \
      --file-ticket "F841:<abs-path>/tests/test_ticket_land.py:=T-2308" \
      --reason "..." --actor coordinator
Note the ABSOLUTE paths: the records store absolute paths, and a
relative-path identity will not match.

REQUIRED FIX: when the auto-filer declines to file because an equivalent
ticket exists, it must dispose the findings to THAT existing ticket, with
the same effect as if it had just filed it. A refusal to duplicate must
never leave a finding ownerless.

POSITIVE CONTROLS: (1) must-now-pass -- findings whose equivalent ticket
already exists are disposed to it and quarantine clears; (2)
must-still-pass -- findings with no owning ticket still raise quarantine
and still block (this is the guard's real job, do not weaken it);
(3) the duplicate-detection itself still refuses to create a second ticket.

SURFACING: per the standing "automatic over commands" directive, the
deadlock was invisible -- five agents reported "running" while nothing
landed for 90 minutes. Whatever an operator already reads (fleet_status,
land refusal text) should say "quarantine RAISED, N undisposed, deferred
landing OFF" rather than requiring someone to think to run
`frob verify status`.

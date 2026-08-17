---
id: T-2312
title: Auto-filer skips DISPOSAL when it declines to file a duplicate, pinning quarantine
  and deadlocking every land fleet-wide
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_rapid_sweep.py
- tests/unit/verify/test_quarantine.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/verify/_quarantine.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
- tests/unit/verify/test_quarantine.py
- tests/unit/test_land_cmd_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: T-2312 repro/positive-control tests
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: T-2312 repro/positive-control tests
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: The two source files this fix actually edits. Both were lease-blocked when
    T-2312 was implemented (T-2303 held _rapid_sweep.py as a queued tracker, T-2310
    held verify/**); T-2303 has since been narrowed to ['design'] and T-2310 has landed,
    so the real scope can now be declared.
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: The two source files this fix actually edits. Both were lease-blocked when
    T-2312 was implemented (T-2303 held _rapid_sweep.py as a queued tracker, T-2310
    held verify/**); T-2303 has since been narrowed to ['design'] and T-2310 has landed,
    so the real scope can now be declared.
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_non_duplicate_filing_failure_still_leaves_quarantine_raised
- tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_path_shape_mismatch_is_diagnosed_not_a_bare_refusal
- tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_notice_names_undisposed_count_and_dispose_command
designated_repro_test: tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping
acceptance:
- text: given findings whose equivalent ticket already exists, when the auto-filer
    declines to duplicate, then it disposes them to that existing ticket and quarantine
    clears
  evidence:
  - tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping
- text: given findings with no owning ticket at all, when the sweep runs, then quarantine
    still raises and still blocks (guard not weakened)
  evidence:
  - tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_non_duplicate_filing_failure_still_leaves_quarantine_raised
- text: given quarantine is raised, when an operator reads fleet status or a land
    refusal, then the raised state and undisposed count are stated without needing
    frob verify status
  evidence:
  - tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_notice_names_undisposed_count_and_dispose_command
- text: given a quarantine store holding both absolute-path and relative-path finding
    identities, when an operator addresses one with --file-ticket, then a path-shape
    mismatch is reported as such rather than as a bare FindingsNotDisposed
  evidence:
  - tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_path_shape_mismatch_is_diagnosed_not_a_bare_refusal
threat: null
component: verify
anchor: false
anchor_reason: null
land_commit: b592fdd93a23630ad7c5041204c7dcc3d6ca3a7e
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
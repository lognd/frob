---
id: T-3943
title: 'F-173: check/done-report/close hardcode main as diff base, burying 8 real
  findings under 431 false ones'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'filed scope named _query.py, which carries neither the hardcoded main default
    nor the base_ref plumbing -- I picked it without checking. Measured: the main
    default and base_ref both live in _close_cmd.py, with the config surface in app/config.py;
    those are the two the consumer''s report names (close has no override at all,
    done-report''s --base-ref governs only the Changed section)'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'filed scope named _query.py, which carries neither the hardcoded main default
    nor the base_ref plumbing -- I picked it without checking. Measured: the main
    default and base_ref both live in _close_cmd.py, with the config surface in app/config.py;
    those are the two the consumer''s report names (close has no override at all,
    done-report''s --base-ref governs only the Changed section)'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/app/config.py
  reason: 'filed scope named _query.py, which carries neither the hardcoded main default
    nor the base_ref plumbing -- I picked it without checking. Measured: the main
    default and base_ref both live in _close_cmd.py, with the config surface in app/config.py;
    those are the two the consumer''s report names (close has no override at all,
    done-report''s --base-ref governs only the Changed section)'
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-173, 2026-09-06.

MEASURED BY THEM, with a clean before/after that makes the mechanism
unambiguous. T-0166 worked on branch sub-17-rust, which frob ticket start
ITSELF warned was 250+ commits behind main's tip:

    frob check --ticket T-0166                 -> gate:SCOPE 61 errors,
                                                  gate:COV  311 errors
    frob check --ticket T-0166 --base sub-17-rust -> gate:SCOPE 0 errors,
                                                  gate:COV  8 (the real,
                                                  pre-existing T-0162 ones)

439 findings collapsed to 8. Every one of the 431 was noise: the diff was taken
against main, so every symbol in the whole sub-17-rust history -- not the
ticket's actual 3-file touched set -- was reported as "changed with no
frob:ticket edge".

THE DEFECT IS A HARDCODED DIFF BASE. The ticket knows which branch it started
on; the gate ignores that and assumes main. Note frob ticket start already
detects and WARNS that the branch is far behind main, so the information needed
to pick the right base is not merely available, it has already been computed and
shown to the user at that point.

WHY THIS IS WORSE THAN A BAD DEFAULT. This is a signal-destroying failure, and
it destroys the signal in the most damaging possible direction: it does not hide
real findings, it BURIES them in false ones. An agent facing a 439-error gate
summary has exactly two options -- spend the session triaging noise, or learn
that frob's findings are not to be trusted. The consumer's own words are "the
next agent isn't staring at a 439-error gate-summary wondering what they broke."
Every other ticket in this queue exists to prevent that lesson being taught.

RELATED WORK ALREADY LANDED: T-3787 added support for landing onto a non-main
target branch. This is the same family -- main hardcoded where a branch-aware
value belongs -- reached from the gate side rather than the land side. Check
whether T-3787 established a canonical "what is this ticket's base branch"
accessor; if it did, this should consume it rather than deriving a second answer,
and if it did not, that accessor is the actual deliverable here.

THE SECOND HALF, WHICH IS NOT OPTIONAL. The consumer reports the override is
missing from the paths where it matters most:
  - frob ticket close: no base override AT ALL.
  - frob ticket done-report: has --base-ref, but it only affects the auto-filled
    Changed section -- NOT the gate-state warnings it captures.
That second one deserves special attention: a flag that appears to control the
base and silently governs only part of the output is worse than no flag, because
a user who passes it reasonably believes the gate state was recomputed against
it. Fix the auto-detection AND make that flag either govern both or say plainly
that it does not.

PREFER AUTO-DETECTION OVER A NEW FLAG. A flag requires the user to already know
about this trap; the whole point is that they do not. Derive the base from the
ticket's start branch and keep an explicit override for the genuine exception.

MUST-FIRE FIXTURE: a ticket started on a branch far behind main reports only its
own touched set, not the branch's whole history.
MUST-STAY-QUIET: a ticket started on main is byte-identical to today -- no
regression for the case that currently works.
THIRD FIXTURE: done-report's captured gate state honours the same base its
Changed section does.

ACCEPTANCE
- Diff base derives from the ticket's start branch, not a hardcoded main.
- close and done-report agree with check on what the base is.
- The done-report --base-ref partial-application is resolved, not documented around.
- All three fixtures committed.
---
id: T-4126
title: the sweep filer re-files findings already disposed to an earlier sweep ticket;
  a consumer measured four consecutive sweep tickets dropped for the same reason
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a finding identity already disposed to an earlier sweep ticket, when
    a later sweep run executes, then no new ticket is filed for it
  evidence: []
- text: given a genuinely new finding identity, when a sweep run executes, then it
    is still filed
  evidence: []
- text: given one finding carried through both the filing and disposal paths, when
    its identity is computed on each side, then the two are byte-identical
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE SWEEP FILER RE-FILES AN IDENTITY THAT HAS ALREADY BEEN DISPOSED TO AN EARLIER
SWEEP TICKET, so the same parked finding class is filed, triaged and dropped
again and again. Reported as logand.app-v2 F-312. Their measurement is the part
that makes this worth fixing rather than tolerating:

    FOUR CONSECUTIVE SWEEP TICKETS DROPPED FOR THE SAME REASON.
    The newest was filed for a parked evidence-resolution class already swept by
    an earlier ticket, and was dropped exactly as its three predecessors were.

Their proposed rule is one sentence and is correct: the sweep filer should
recognise an identity already disposed to a sweep ticket, and skip it.

WHY A FOUR-IN-A-ROW DROP RATE IS A DEFECT AND NOT HOUSEKEEPING. Each of those
tickets consumed a filing, a triage and a drop, and each one is indistinguishable
at filing time from a real finding -- so the operator must read it to learn it is
noise. A filer whose output is reliably dropped is training its readers to drop
its output unread, and the first genuine finding it produces will be dropped with
the rest. That is the wrong-incentive class applied to the queue itself: the
cheapest correct response to this filer degrades the reader's handling of every
future ticket it files.

THE MECHANISM TO LOOK FOR IS AN IDENTITY MISMATCH, NOT A MISSING CHECK. A
deduplicating check almost certainly already exists -- the sweep filer would be
filing far more than four duplicates otherwise. The likely defect is that the
identity it computes for a finding does not match the identity recorded on
disposal, so the lookup misses and the finding reads as new. This repo has
measured that exact failure twice: an absolute-versus-relative path shape
silently voided identity matching across three separate subsystems, and a stale
baseline reported five of six pre-existing identities as new. Check the identity
computation on BOTH sides before concluding no check exists.

FIRST, MEASURE THE POPULATION IN THIS REPO. The consumer sees four; we may see
more or none. Count how many sweep-filed tickets in this queue were dropped, and
how many of those name a finding class that an earlier sweep ticket had already
disposed of. Report that number before designing anything. If our own drop rate
is comparable, the fixture can be built from our history; if it is zero while
theirs is four, that difference is itself the finding and needs explaining --
most likely a configuration or profile difference, which would change the fix.

DISTINGUISH THIS FROM THE ALREADY-ARCHIVED BYTE-IDENTICAL-DUPLICATE TICKET. That
one concerned a post-land sweep filing two tickets with identical content in one
run. This is a different verb, a different window, and a different comparison:
a finding disposed of in an EARLIER, separate run being filed again later. A fix
for one does not cover the other; confirm the archived fix's mechanism before
assuming it applies.

DO NOT FIX THIS BY SUPPRESSING THE FILER OR RAISING A THRESHOLD. A filer that
files less is not a filer that files correctly, and a threshold hides the genuine
first occurrence along with the repeats. The disposal record is the right source
of truth; make the lookup work.

MUST-FIRE FIXTURE:   a finding identity already disposed to an earlier sweep
                     ticket is not filed again by a later sweep run.
MUST-STAY-QUIET:     a genuinely new finding identity is still filed, including
                     one that merely resembles a disposed identity.
THIRD FIXTURE:       the identity computed at filing time is byte-identical to
                     the one recorded at disposal, for a finding carried through
                     both paths -- the specific mismatch this ticket suspects.

ACCEPTANCE
- The drop rate of sweep-filed tickets in this repo measured and reported before
  any design.
- The identity computation compared on both the filing and disposal sides, with
  the result stated either way.
- The relationship to the archived byte-identical-duplicate fix confirmed or
  refuted.
- No threshold or suppression used as the fix.
- All three fixtures committed.

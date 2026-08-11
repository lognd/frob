---
id: T-2049
title: A raised quarantine silently forces synchronous verification on every land
  and is surfaced nowhere an operator looks -- two unused imports cost an hour of
  fleet land throughput
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_cmd_quarantine.py
- docs/guides/coordinator-scripts.md
- tickets/T-2126/**
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: scripts/fleet_status.py
  reason: acceptance criteria touch fleet_status.py (surface quarantine) and _land_cmd.py's
    quarantine-notice log line, plus their existing test files
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: acceptance criteria touch fleet_status.py (surface quarantine) and _land_cmd.py's
    quarantine-notice log line, plus their existing test files
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: acceptance criteria touch fleet_status.py (surface quarantine) and _land_cmd.py's
    quarantine-notice log line, plus their existing test files
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_land_cmd_quarantine.py
  reason: acceptance criteria touch fleet_status.py (surface quarantine) and _land_cmd.py's
    quarantine-notice log line, plus their existing test files
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: new quarantine_state() public symbol in fleet_status.py needs its own frob:doc
    anchor here, matching every other fleet_status.py symbol's existing anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2126/**
  reason: T-2049's own acceptance criterion 4 investigation filed T-2126 as a follow-up
    from inside this worktree; its ticket.md ships with this branch
  actor: logan
  at: '2026-08-11'
- op: add
  glob: rapid-debt.jsonl
  reason: frob ticket close's own REL001 rapid-profile debt-recording auto-appends
    this file; routine bookkeeping like tickets.md, not part of the actual fix
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: quarantine_state()/QUARANTINE need their own frob:doc anchor content here,
    matching every other fleet_status.py symbol's existing anchor pattern
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_reports_raised_with_undisposed_count
- tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_reports_clear_when_store_says_cleared
- tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_reports_clear_when_no_file
- tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_unreadable_store_is_unknown_never_clear
- tests/unit/test_coordinator_scripts.py::TestQuarantineState::test_non_dict_record_is_unknown
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine::test_prints_raised_with_undisposed_count_and_consequence
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine::test_prints_clear
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMainQuarantine::test_prints_unknown_as_unsafe
- tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_notice_names_undisposed_count_and_dispose_command
- tests/unit/test_land_cmd_quarantine.py::TestQuarantineUndisposedSummary::test_no_quarantine_ever_raised_is_unknown_not_a_crash
- tests/unit/test_land_cmd_quarantine.py::TestQuarantineUndisposedSummary::test_corrupt_store_is_unknown
- tests/unit/test_land_cmd_quarantine.py::TestQuarantineUndisposedSummary::test_raised_record_counts_undisposed_findings
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Problem

A raised verify quarantine silently converts every land in the repo onto the
fully-synchronous verification path (T-1693), multiplying land wall-clock
past the 540s foreground cap the tooling permits. The whole fleet then cannot
publish finished work. Nothing surfaces this where an operator or agent is
actually looking; the only signal is one ERROR line buried in a land's own
several-hundred-line output.

## Measured evidence (2026-08-10)

The quarantine was raised by exactly two findings:

    [UNDISPOSED] F401 tests/test_gates_fmt_directives.py
    [UNDISPOSED] F401 tests/unit/test_tickets_evidence_only_scope.py

Two unused imports. While they sat undisposed, every land printed:

    ERROR: ticket land: T-XXXX quarantine is raised (or its store could not
    be read) -- deferred landing is OFF, forcing fully-synchronous
    verification for this land regardless of profile (T-1693)

and then ran long. Four separate coordinator land attempts died at the
540-580s shell cap without reaching `LAND-PROOF` (T-2032 x2, T-2033 x2), plus
agent attempts on T-2011, T-2027 and T-2033. Several tickets sat finished and
unpublishable for over an hour. After the two imports were fixed
(`f28ab6590`, 49 tests still pass) and the findings disposed, deferred
landing resumed and four lands ran concurrently without issue.

Cost: roughly an hour of fleet-wide land throughput, for two dead imports.

## Why the existing output is not enough

The ERROR line was printed on EVERY affected land, in full, and was read past
every time -- by the coordinator, across at least four attempts, while
actively investigating why lands were slow. It sits among dozens of other
WARNING/ERROR lines (profile ratchet warnings, `duplicate node id`,
SUPPRESS001 correlation failures) that are routine and ignorable. A signal
that appears only inside the output of the very command it is degrading, and
that looks like the surrounding noise, is not a signal.

Note also the message conflates two states -- "quarantine is raised (or its
store could not be read)" -- so it cannot be told apart from an unreadable
store without a separate `is_quarantined` call. That conflation is
deliberate and correct for safety (cannot-verify must never read as
not-raised), but it further reduces the line's information value at a glance.

## Proposed fix

Surface quarantine state where people already look, rather than adding
another line to a place they do not:

1. `scripts/fleet_status.py` is the pre-dispatch check ("is it safe to
   dispatch"). It reports ROOT / LEASES / WORKTREES and says nothing about
   quarantine. Add quarantine state, with the undisposed finding count and
   the consequence spelled out ("deferred landing OFF -- every land runs
   synchronous verification"). This is the single highest-value placement:
   it is the command run BEFORE dispatching a wave.
2. `frob ticket land` should report the expected consequence UP FRONT, before
   doing the slow work -- not as one ERROR among many mid-run. Naming the
   cost ("this land will run fully-synchronous verification and take
   substantially longer; N finding(s) undisposed; clear with `frob verify
   dispose`") gives the operator a decision point while it still matters.

## Do NOT fix it this way

- Do NOT auto-clear or auto-dispose the quarantine to keep lands fast. The
  quarantine exists to stop unverified work compounding; dismissing findings
  without fixing them is exactly the false-green this system is built to
  prevent.
- Do NOT make the land skip synchronous verification when quarantine is
  raised. That inverts the safety property deliberately.
- Do NOT just reword the existing ERROR line. It was already accurate,
  already an ERROR, and already ignored four times. Rewording is the
  documentation-shaped non-fix.
- Do NOT add a new command an operator must remember to run. The failure was
  not knowing to look; a command requires knowing to run it.

## Acceptance criteria

1. A test that `fleet_status.py` reports a raised quarantine, with the
   undisposed count, when the store says raised. THIS TEST MUST FAIL BEFORE
   THE FIX -- watch it fail and record the output.
2. A test that it reports clear when the store is clear, and that an
   UNREADABLE store is reported as unknown/unsafe, never as clear.
3. A test that `frob ticket land` emits its quarantine consequence notice
   BEFORE the verification work begins, not after.
4. Report whether any other state that silently changes land cost (verify
   queue depth, watermark age) belongs in `fleet_status.py` by the same
   argument. Measure before proposing; do not add fields speculatively.
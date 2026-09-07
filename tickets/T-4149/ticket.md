---
id: T-4149
title: decide and document the no-[[test.runner]]-declared fallback policy
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: a consumer hit this on a clean worktree and it refused their entire test
    verb over a language their diff never touched, which settles the priority this
    ticket was parked on. Adds the all-or-nothing framing, and the prior question
    of whether selection should have picked those tests at all -- if the resolver
    over-selects, that is the real cause and it changes the fallback design
  actor: logan
  at: '2026-09-07'
  old_length: 475
  new_length: 3714
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3887's open question: what happens when a project declares no [[test.runner]] and has no resolvable environment for project_tool_argv/pytest spawns. Options: refuse the affected gates with a clear message, or fall back to frob's own interpreter WITH an explicit, unmissable capability statement that the result is measured in frob's environment (never a silent fallback). Decide, document in docs/modules/process.md and docs/modules/testing.md, and add a MUST-FIRE fixture.
A CONSUMER HAS NOW HIT THIS AND IT BLOCKS THEIR WHOLE TEST VERB, WHICH SETTLES
THE PRIORITY QUESTION THIS TICKET WAS PARKED ON. Reported from logand.app-v2
(their T-0394):

    ERROR: run_selected: language 'bash' has selected tests but no runner --
    add a [[test.runner]] entry with language = 'bash' to frob.toml
    ERROR: frob test: NoRunner: A language has selected tests but no runner

Reproduced on a CLEAN worktree off their main, and -- the important part -- the
failure is UNRELATED TO THEIR DIFF. Their touched set was a lock file, a
Dockerfile, a requirements lock, a python test and a spec document. No bash file
was touched at all. The verb still refused repo-wide, and they worked around it by
running the touched-set test file directly, outside frob.

WHY THAT MATTERS MORE THAN THE MISSING CONFIG ENTRY. The remedy the message names
is real and easy -- declare a runner for that language. But the failure is
ALL-OR-NOTHING across languages: one language with selected tests and no runner
refuses the entire run, including the python tests that DO have a runner and that
the ticket actually needed. A caller who cannot run any tests because of a
language their change never touched will stop using the verb, which is exactly
what happened here.

THREE THINGS THIS TICKET MUST NOW DECIDE, rather than the one it was filed with:

  1. WHAT THE DEFAULT IS when a language has selected tests and no declared
     runner. Refusing the whole run is the current answer and it is the worst
     available one. Running the languages that CAN run, and reporting the others
     as UNMEASURED by name, preserves both the work and the honesty. Do not
     silently skip them -- unmeasured must be visible, which is the posture this
     queue has demanded of every other gate.
  2. WHETHER SELECTION SHOULD HAVE PICKED THOSE TESTS AT ALL. Their diff touched
     no bash. If the touched-set resolver selected bash tests anyway, that is a
     separate defect upstream of this one and possibly the real cause -- a
     resolver over-selecting is why an undeclared runner became reachable.
     MEASURE THIS BEFORE DESIGNING THE FALLBACK; if selection is wrong, the
     fallback question changes shape.
  3. WHETHER THE SCAFFOLD SHOULD DECLARE RUNNERS for the languages it generates.
     A scaffolded project that cannot run its own test verb is the day-one-noise
     class, already filed separately, and this would be another instance.

MUST-FIRE FIXTURE:   a repository with one runnerless language and one declared
                     runner runs the declared language's tests and reports the
                     other as unmeasured, naming it.
MUST-STAY-QUIET:     a repository whose every selected language has a runner
                     behaves exactly as today.
THIRD FIXTURE:       a diff touching no files of a runnerless language does not
                     select that language's tests at all.

ACCEPTANCE
- The all-or-nothing refusal replaced with per-language outcomes, unmeasured
  reported by name rather than skipped.
- The over-selection question measured and answered before the fallback is
  designed.
- The scaffold question decided or explicitly deferred with a reason.
- All three fixtures committed.

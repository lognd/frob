---
id: T-4319
title: Lease held by a dead holder is invisible to every routine check
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/test_gates_tick009_tick010.py
- tests/gates_suite/test_fix_engine.py
- tests/gates_suite/test_tick.py
- tests/test_gates_tickets_hygiene.py
- tests/test_tick012_gate.py
- tests/test_tick013_gate.py
- tests/test_tickets_collision.py
- tests/test_tickets_migration.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'src/frob/gates/_tickets_gate.py is a bundled multi-rule
  ledger-hygiene module (TICK001-014) whose own module-level LARGE001 waiver already
  documents this: each _tickN_* helper carries its own frob:doc/frob:tests targets.
  Scoping this ticket to the whole file (required, since the fix lives in the shared
  tickets_gate() entrypoint and _tick010_stale_lease_report) pulls in every OTHER
  pre-existing rule''s doc/test targets via SCOPE002''s closure check; this is the
  file''s own chronic breadth, not new breadth from this change.'
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_tick009_tick010.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/gates_suite/test_tick.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_gates_tickets_hygiene.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_tick012_gate.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_tick013_gate.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_tickets_migration.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: 'T-4319: widening TICK010 (whole-file scope) triggers SCOPE002''s exhaustive
    frob:doc/frob:tests coverage requirement over every OTHER pre-existing _tickN_*
    function this shared multi-rule file already carries directives for; adding them
    here (most demoted to evidence-only next) is a mechanical land requirement of
    touching this file at all, not new work content.'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/gates.md
  reason: 'T-4319: reverting an over-broad closure widening -- these pre-existing
    frob:doc/dependency edges belong to OTHER pre-existing _tickN_* functions this
    ticket does not touch; docs/modules/gates.md alone cascades into 700+ unrelated
    closure warnings (a shared project-wide catalog doc), which is chronic-breadth
    territory (TICK009), not a real dependency of this change. Using scope-ack instead.'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-4319: reverting an over-broad closure widening -- these pre-existing
    frob:doc/dependency edges belong to OTHER pre-existing _tickN_* functions this
    ticket does not touch; docs/modules/gates.md alone cascades into 700+ unrelated
    closure warnings (a shared project-wide catalog doc), which is chronic-breadth
    territory (TICK009), not a real dependency of this change. Using scope-ack instead.'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-lifecycle.md
  reason: 'T-4319: reverting an over-broad closure widening -- these pre-existing
    frob:doc/dependency edges belong to OTHER pre-existing _tickN_* functions this
    ticket does not touch; docs/modules/gates.md alone cascades into 700+ unrelated
    closure warnings (a shared project-wide catalog doc), which is chronic-breadth
    territory (TICK009), not a real dependency of this change. Using scope-ack instead.'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/gates/_mutation_evidence.py
  reason: 'T-4319: reverting an over-broad closure widening -- these pre-existing
    frob:doc/dependency edges belong to OTHER pre-existing _tickN_* functions this
    ticket does not touch; docs/modules/gates.md alone cascades into 700+ unrelated
    closure warnings (a shared project-wide catalog doc), which is chronic-breadth
    territory (TICK009), not a real dependency of this change. Using scope-ack instead.'
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_holder_dead_lease_reports_as_error_with_remedy
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_live_holder_lease_is_silent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THREE TICKETS SAT LEASED BY DEAD AGENTS TODAY AND NOTHING SURFACED IT. THE
DETECTOR THAT WOULD HAVE CAUGHT THEM IS CORRECT AND EFFECTIVELY UNREACHABLE.

WHAT HAPPENED, MEASURED. Three tickets were found in-progress with no owning agent
alive: one whose worktree held nothing but its start-transition commit and had
been idle roughly five hours, one with no worktree at all, and one holding real
uncommitted source edits with no activity for hours. Each was holding a lease. One
of them had already refused a legitimate scope change on an unrelated ticket. All
three were found by hand, by looking; nothing announced them.

THE DETECTION ALREADY EXISTS AND IS WELL BUILT. There is a helper that judges a
lease orphaned by three signals -- path gone, ticket gone, or holder dead past a
time horizon with no live process in the worktree. Its read-only posture is
DELIBERATE and correct: automatically releasing a merely-slow agent's lease would
let two worktrees edit the same scope at once, which is a worse failure than a
stuck lease. Do not change that posture. The problem is not the judgement.

THE PROBLEM IS THAT NOTHING ROUTINE ASKS IT. Its only consumer is the queue's
in-flight display, a command that does not complete on this repository -- so in
practice the judgement is never rendered. Meanwhile the gate-level rule that does
run on every check covers a strictly narrower case: it fires only when a lease's
recorded worktree PATH no longer exists on disk. The dominant real case today was
the opposite shape -- the worktree was present and intact, and the HOLDER was
dead. That case runs through the gate silently.

CLOSE THE GAP BY WIDENING WHAT THE ROUTINE CHECK ASKS, not by building a new
detector. The judgement helper already answers the holder-dead question; the gate
should consult it rather than re-deriving a narrower test of its own. Reusing one
judgement in both places is the whole point -- two copies of a liveness rule is a
desync waiting to happen.

REPORT IT AS SOMETHING A READER WILL SEE. A single warning among several thousand
is not surfacing. Decide deliberately what severity a lease held by a
provably-dead holder past the horizon deserves, and record the reasoning. A stuck
lease actively blocks other work, which argues for more than a warning; against
that, a slow-but-live agent must never be misjudged, so the liveness signal has to
be strong before it escalates. Say which way you went and why.

STATE THE REMEDY IN THE MESSAGE. Reclamation is an explicit operator action by
design, so any finding should name the exact command and the ticket it applies to,
the way the existing narrow rule already does.

VERIFY BY FORCING THE CONDITION, not by observing a healthy tree: construct a lease
whose recorded holder pid does not exist and whose worktree is present, and assert
the routine check reports it. Then construct a live-holder lease and assert it does
NOT. A liveness check verified only against healthy state is exactly the kind of
diagnostic this project has repeatedly found silent at the moment it was needed.
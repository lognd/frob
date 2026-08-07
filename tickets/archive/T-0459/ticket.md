---
id: T-0459
title: 'render enforcement gate: fail frob check on bare print/click.echo/sys.stdout.write
  outside frob.render (so the T-0448 output layer cannot be bypassed and rot)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/render/
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0459 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_gates.py::TestRenderLintGate::test_bare_print_fires
- tests/test_gates.py::TestRenderLintGate::test_render_package_exempt
- tests/test_gates.py::TestRenderLintGate::test_stderr_directed_print_is_silent
designated_repro_test: null
threat: null
component: null
---
Enforces INV-RENDER-SOLE-STDOUT (docs/modules/render.md#renderer): a command
runner produces human-facing stdout ONLY through frob.render.Renderer. User
refinement 2026-07-20: the "only" must be DEFENSIBLE THROUGH STRATA, not just
a grep gate -- expand strata's capability may-analysis to cover it.

Design (two mutually-reinforcing enforcements of the same invariant):
1. frob check GATE (fast, syntactic): fail on any bare `print(...)`,
   `click.echo(...)`, `sys.stdout.write(...)`, or equivalent stdout write in
   src/frob/ OUTSIDE src/frob/render/ (and outside the sanctioned `--json`
   channel, which uses its own writer). Waivable per-line with a reason for
   the rare legitimate exception. This catches regressions at check time.
2. STRATA PROOF (sound, effect-level): model a `terminal`/stdout-write
   CAPABILITY in the strata may-analysis (T-0339 sound-capability epic). A
   command-runner node may NOT hold the stdout-write capability directly;
   only frob.render may. The may-analysis then PROVES (fail-closed on
   runtime dispatch) that no command runner reaches stdout except through
   frob.render -- turning "only frob.render prints" from an assertion into a
   proven effect, exactly like the exec/net/fs capabilities strata already
   tracks. EXPAND the strata may-capability vocabulary to add this
   terminal/stdout-write capability if it is not already modeled (the user
   explicitly authorized expanding strata "may" capabilities for this).
- The gate is the cheap always-on guard; the strata proof is the sound
  invariant. Both bind to INV-RENDER-SOLE-STDOUT so the render.md claim stops
  being bare prose.
- Acceptance: a bare `print` added to any command runner fails `frob check`
  (gate) AND fails the strata may-analysis (a runner node acquiring the
  stdout capability is unprovable/denied); frob.render itself holds the
  capability and passes; the invariant is anchored, not asserted.
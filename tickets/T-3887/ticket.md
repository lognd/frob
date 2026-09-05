---
id: T-3887
title: several gates execute the target project's code in frob's own interpreter,
  so they cannot measure any non-frob project
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Three stpone findings (F-012, F-017, F-018) are one structural defect: SEVERAL
GATES EXECUTE THE TARGET PROJECT'S CODE IN FROB'S OWN INTERPRETER AND
ENVIRONMENT, rather than the project's. frob is installed as a global uv tool,
so the project's packages are not importable from it and its own dependency set
is not the project's.

THE INSTANCES, as reported:

  F-012  FLAGCOV001 imports the project's parser from frob's interpreter.
         With `[[docblocks.commands]] parser = "stpone.flash.cli:build_parser"`:
             WARNING: flagcov001: could not resolve
             'stpone.flash.cli:build_parser': No module named 'stpone'
         and the gate stays UNRESOLVED. Their verdict: "the gate cannot measure
         any non-frob project."

  F-017  `frob coverage --full` spawns a bare `pytest` from frob's own
         environment.

  F-018  coverage refresh assumes pytest-xdist is installed -- in frob's
         environment, not necessarily the project's.

THE CORRECT PATTERN ALREADY EXISTS IN FROB. F-012's own expectation names it:
"the way the pytest collection already runs inside `uv run`". So this is not a
capability to invent; it is an established convention applied to some call sites
and not others -- the same shape as the tail-me result-block contract and the
DOC004-checks-docs-but-not-remedy-strings gap found today.

WHY THIS IS MORE THAN FRICTION. It is a PORTABILITY defect of the kind this repo
has a standing rule about (a detector that hardcodes `src/frob/` passes
vacuously off-repo). Here the failure is louder in one case and silent in
others:
  - FLAGCOV001 goes UNRESOLVED, which is at least visible -- though "unresolved"
    reads to a consumer as "frob could not check this" rather than "frob checked
    it in the wrong interpreter".
  - A bare `pytest` spawn is worse: if frob's environment happens to HAVE
    pytest, it runs and measures THE WRONG THING -- the project's tests under
    frob's dependency versions. A result produced that way is not a false zero,
    it is a false measurement, which is harder to notice.
  - Assuming xdist is installed compounds it: absent, the run silently loses
    parallelism or fails for a reason that names neither the project nor frob.

WHAT TO BUILD
  1. ENUMERATE FIRST. Find every site that imports, execs, or spawns something
     belonging to the TARGET project: parser=/config=/forwarded= resolution,
     coverage's pytest spawn, coverage refresh, and anything else. Report the
     list with file:line before changing any of them. That enumeration is the
     durable artifact; fixing three named sites leaves the fourth.
  2. Route all of them through the project's own interpreter, using the
     existing `uv run` / `[[test.runner]]` environment convention rather than a
     new mechanism. If a site genuinely cannot be routed that way, say why.
  3. TOOL PRESENCE MUST BE LOUD, per the standing rule that a missing tool is a
     typed error naming the tool and its install command -- never a silent
     degrade. That applies to xdist here (F-018) and to pytest itself. Absent
     must never become "ran without parallelism" or "ran in frob's env instead".

DECIDE AND STATE: what happens when a project declares no `[[test.runner]]` and
has no resolvable environment. Options are to refuse the affected gates with a
clear message, or to fall back to frob's interpreter WITH AN EXPLICIT
capability statement that the result is measured in frob's environment. The
owner's standing doctrine -- no situation where someone thinks frob has
capabilities it does not -- points at the first, or at the second only if the
statement is unmissable. Do not fall back silently.

DO NOT special-case frob's own repo. In this repo the project environment and
frob's environment coincide, which is exactly why this went unnoticed: every
gate works here and fails off-repo. Any fix must be verified against a
non-frob project, not against this one. If that cannot be done in-tree, say so
and describe the fixture that would.

MUST-FIRE FIXTURES:
  - a project whose package is not importable from frob's interpreter still has
    its parser resolved (via the project environment), not reported UNRESOLVED
  - a project environment missing pytest produces a loud typed error naming
    pytest, not a silent skip or a frob-env run
MUST-STAY-QUIET:
  - frob's own repo behaves exactly as before (the environments coincide, so
    nothing should change here)

ACCEPTANCE
- The full enumeration of project-code execution sites reported with file:line.
- Each routed through the project environment, or a stated reason it cannot be.
- Missing-tool paths loud and typed.
- The no-runner-declared policy decided and stated.
- Fixtures committed, with the off-repo verification described.

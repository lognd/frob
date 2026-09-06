---
id: T-3931
title: 'a freshly scaffolded untouched project is not gate-clean: eight findings the
  user did not cause on day one'
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
body_changes:
- mode: set
  reason: 'DOC006 failed CI on ubuntu and macOS against this ticket''s own prose:
    a quoted consumer symref (file-colon-symbol form) and a proposed config section
    in double-bracket TOML form both parse as live pointers into THIS repo, where
    neither resolves. Rewritten as prose so the gate is satisfied by fixing the cause
    rather than waiving a correct finding'
  actor: logan
  at: '2026-09-06'
  old_length: 4969
  new_length: 5514
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A FRESHLY SCAFFOLDED, UNTOUCHED PROJECT IS NOT GATE-CLEAN. Reported by a new
downstream consumer (kicad-libsync) on frob 0.530.0, under the heading "gate
noise that is not the project's fault". Every item below is something the
consumer had to work around before doing any work of their own.

THE DAY-ONE FINDINGS, on the scaffold as generated:

  ROOT001  fires on `.github/` and `invariants/` EVEN THOUGH the scaffold's own
           frob.toml already carries [[refs.entrypoint]] rows for
           `.github/workflows/*.yml` and `invariants/.gitkeep`. So a
           scaffold-provided config does not satisfy a scaffold-provided gate.
           Worked around with two frob:external-reader declarations.
  REF001   fires on EVERY `tickets/T-*/ticket.md` the moment `frob ticket new`
           creates one (ledger v2), and again on `done-report.md` the moment
           `frob ticket done-report` writes it. FROB'S OWN LEDGER ARTIFACTS
           SHOULD NEVER BE REF FINDINGS. Worked around by adding an entrypoint
           glob, then widening it.
  COV001   fires on the PYPROJECT constant inside the scaffold-provided
           scripts/bump_version.py in THEIR repo. Waived inline.
           (Named in prose rather than as a file-colon-symbol pointer: that
           form is a live symref into THIS repo, where the symbol does not
           exist, so writing it verbatim made DOC006 fail CI on ubuntu and
           macOS. Quote a consumer's symbol as prose, never as a pointer.)
  MILE003  fires for every ticket because the scaffold's frob.toml has no
           [tickets].default_milestone, and "a fresh repo has no way to know it
           must set one until the first frob check".
  WIRE001  fires on every public symbol whose consumer is the NEXT ticket in a
           bottom-up ticket tree, so a first-ticket module needs three lines of
           directive per symbol (frob:doc + frob:tests + frob:waive WIRE001).
           They propose a wire.pending config section (named in prose, not in
           double-bracket TOML form -- as a literal section header it reads as a
           live config pointer and DOC006 correctly refuses it, since no such
           key exists) or a ticket-level follow_up instead of
           per-symbol waives -- which is the same ask as T-3855's tier-3
           framework-wired declaration, reached from a different direction.
  frob-suggest blocked a `sed` on docs/*.md as a "hand-rename of an import
           line" with no import involved -- an eighth instance of the
           lexical-hook class.
  NESTED WORKTREES: with implementer agents in `.claude/worktrees/agent-*/`,
           the main checkout's `frob check` ty stage SCANS THOSE WORKTREES and
           reports unresolved imports for files that exist only on their
           branches. They excluded `.claude/**` in three separate places
           (pyproject [tool.ruff] extend-exclude, [tool.ty.src] exclude, and
           frob.toml [graph]). FROB SHOULD SKIP NESTED WORKTREES ITSELF -- it
           creates them, so it knows where they are.

  AND THE COVERAGE FAILURE, WITH ITS ROOT CAUSE ALREADY DIAGNOSED BY THEM:
           `frob coverage --full` runs `pytest --cov=... -n 7`, the python-tool
           scaffold's dev group has no pytest-xdist, pytest exits 4 (usage
           error), frob reports "suite was RED", and `coverage xml` then fails
           with "No data to report".
           ROOT CAUSE: frob invokes a BARE `pytest`, which resolves to
           `~/.local/bin/pytest` -- a global shim without pytest-cov or xdist --
           instead of `.venv/bin/pytest`. `uv run pytest` with identical args
           exits 0.
           THIS IS T-3887 CONFIRMED FROM A THIRD REPOSITORY, with the mechanism
           and the workaround (`PATH=.venv/bin:$PATH`) both named. Their
           proposed fix is exactly the one already on that ticket: frob coverage
           should honour the [[test.runner]] command prefix the way `frob test`
           already does. Attach this evidence there; it is the clearest
           statement of the bug anyone has produced.

WHY THIS IS ALPHA-CRITICAL RATHER THAN A BACKLOG ITEM. A scaffold exists to
produce a working, conformant starting point. If `frob scaffold new` followed
immediately by `frob check` is not clean, then the tool's own first impression
is a wall of findings the user did not cause and cannot interpret -- and the
only available lesson is that frob's findings are noise to be waived. That is
the exact habit every other ticket in this queue is trying to prevent.

THE ACCEPTANCE TEST IS SIMPLE AND SHOULD BE AUTOMATED: scaffold each project
type into a temp dir, run `frob check`, and assert ZERO findings. Then
`frob ticket new`, `frob ticket done-report`, and assert zero again -- the
ledger findings only appear once a ticket exists, which is why a scaffold-only
check would miss half of these. That test belongs in frob's own suite, because
every item here is a frob defect that frob's own repo cannot surface.

DO NOT FIX THESE BY SHIPPING MORE WAIVERS IN THE SCAFFOLD. A scaffold that
starts with pre-written waivers teaches the same wrong lesson. Each item should
be fixed at its source: the gate should not fire, or the scaffold should not
generate the thing that trips it.

RELATED, FILE SEPARATELY IF NOT ALREADY: the hyphenated-package-name defect
from the same consumer is filed as its own critical ticket -- it is a broken
generated project rather than gate noise, and should not be bundled here.

---
id: T-0448
title: 'EPIC: unified CLI output layer -- every command/subcommand/subsubcommand renders
  through one TTY-aware formatter (pretty colors for human TTY, standardized plain/no-color/no-ansi
  for pipes+agents)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- src/frob/app/
- docs/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_render.py::TestResolveColor::test_no_color_flag_wins_over_everything
- tests/system/test_cli_render_golden.py::TestDoctorGolden::test_doctor_plain_mode_has_no_ansi
- tests/unit/test_render.py::TestRenderIntegration::test_renderer_end_to_end_report
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: go through EVERY command, subcommand, and
subsubcommand and ensure a single standardized output format, with pretty
colors when stdout is a human TTY and standardized plain/no-color/no-ansi
output otherwise (pipes, files, agents). "I want a pretty terminal when I
run these personally; an agent running them wants no colors but the same
standardized structure."

Design (one output layer, every command routes through it):
- A single frob.render (or frob.app.output) module: the ONLY place that
  writes user-facing stdout. TTY/color detection done once
  (sys.stdout.isatty(); honor NO_COLOR, FROB_NO_COLOR, --no-color,
  --color=always|never|auto, TERM=dumb, CLICOLOR_FORCE). No raw ANSI escape
  anywhere else in the codebase.
- Standardized element vocabulary shared by all commands: heading, subhead,
  key/value row, status pill (ok/warn/error/skip), table, tree, count
  summary, path, ticket-id, count deltas, progress (TTY-only, erased on
  completion -- T-0419). Each element has BOTH a colored-TTY rendering and a
  deterministic PLAIN rendering; the plain rendering is the canonical
  machine-stable form (stable columns, no ansi, no cursor control, no
  spinner residue) so `frob ... | tee` and agent captures are clean/greppable.
- Semantic color only (good/warn/critical/muted/accent), never decorative;
  one palette across every command; accent separate from severity;
  colorblind-safe.
- Enforcement so it cannot rot: a gate/test that every command runner writes
  through the output layer (no bare print/click.echo/sys.stdout.write outside
  frob.render), mirroring the module-logger discipline. A golden-output test
  per command in BOTH modes (color-forced and plain-forced) so a format
  regression fails CI.
- --json stays the separate structured channel (unchanged); this epic is the
  HUMAN/plain text channel only.

Existing tickets are INSTANCES and should become children (parent T-0448):
T-0419 (frob check live task-list + progress bars, TTY-only, clears on
completion), T-0420 (frob check gates line -> named per-family stages + gate
summary, consistent coloring), T-0421 (frob check per-language tooling:
skipped-unchanged vs hidden-language-absent). This epic generalizes their
contract to EVERY command (graph, ticket, vet, sys, deploy, release, map,
outline, xref, dup, arch, docs, exports, bind, perf, mutate, stats, serve,
doctor, scaffold, ...) and every subcommand/subsubcommand. File one leaf
ticket per command group under this parent so the sweep is accountable and
none is missed.
---
id: T-4687
title: 'CLI surface: 52 verbs and 49 ticket subverbs down to a dozen verbs; aliases,
  read-only analysis and field-setters folded'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-2994
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: story tier; all files are declared by its seven
  leaves T-4688..T-4694, which are the write-lease holders'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2994
  reason: '2026-09-19: CLI verb reduction is a direct instance of the debloat doctrine
    -- four grouping verbs added names and removed none; owner approved cutting the
    surface'
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 3648
  new_length: 4265
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DECISION (2026-09-19): "start removing subverbs and the read-only analysis.
Delete the duplicates." The CLI surface is to shrink to roughly a dozen verbs.

MEASURED 2026-09-19 (planner, re-measured; coordinator's figures were close but
the exact counts are these):
- `frob --help` usage line lists 51 top-level verbs (coordinator said 52).
- `frob ticket --help` lists 54 subverbs (coordinator said 49).
- .frob/telemetry.jsonl: 34388 rows. kind=cli 2970, kind=tool 30698,
  kind=dispatch 470, kind=ticket 140, kind=gate_rule_counts 110.
  31418 rows (91%) carry an EMPTY `subcommand` field -- every kind=tool row.
  So the verb tail CANNOT be ranked from telemetry today; that is leaf 1's job.
- Of the 51 top-level verbs, only 9 ever appear in a kind=cli row:
  ticket 2165, verify 613, check 168, xref 16, ack 3, claude 2, clean 1,
  natives 1, serve 1. 42 top-level verbs have never been recorded.

WHY THE SURFACE GREW: four "grouping" tickets (T-1238 explore, T-1567 quality,
T-1568 design, T-1569 ops) each added an intent-named GROUP verb while keeping
every member's standalone top-level form "working unchanged". They added four
names and removed zero. `frob explore xref` and `frob xref` are the same
ArgumentParser object (`_cli_parsers/_explore.py::_mirror_subparser` writes the
flat parser straight into the group's `choices`). That is the duplication this
story deletes.

SHAPE OF THE TARGET SURFACE (about a dozen verbs):
  check (absorbs every gate stage via --only), test, ticket, explore (absorbs
  every read-only analysis leaf), graph, verify, ack, format, agent, worktree,
  vet, release, doctor, clean, serve, scaffold, sys, registry, refactor, fleet.

NAME CHOICE FOR LEAF 4, measured by citation count over .claude/ docs/ scripts/
src/ tests/: "frob explore" 95 citations, "frob show" 0. The verb is `explore`.

DEPRECATION POLICY (all leaves): use the EXISTING frob:deprecated machinery
(src/frob/gates/_debt_deprecated.py, _deprecated_baseline.py,
src/frob/app/deprecated_runner.py) and the `fmt` precedent
(src/frob/app/fmt_runner.py: "DEPRECATED alias for frob format --directives
(T-3906, sunset 2026-12-01)"). Do NOT invent a second shim mechanism. Every
removed name keeps a shim for ONE minor version that prints the surviving
spelling on stderr and, after the sunset date, exits non-zero.

PARSER FILE MAP (measured; this is why the leaves are ordered the way they are).
Every top-level verb is registered by one of:
  _cli_parsers/_core.py     scaffold cycle outline map xref parse dup arch docs
                            exports bind agent worktree whereis pool status
  _cli_parsers/_misc.py     check profile test vet perf release mutate stats
                            serve sys deploy doctor clean fmt format claude
                            natives coverage sync-skills
  _cli_parsers/_reporting.py gitlog graph ack debt deprecated pool profile
                            registry fleet status
  _cli_parsers/_explore.py  explore, docs-search
  _cli_parsers/_quality.py  quality
  _cli_parsers/_design.py   design
  _cli_parsers/_ops.py      ops
  _cli_parsers/_status.py   status
  _cli_parsers/_verify.py   verify, verify status
  _cli_parsers/_check.py    check's flag population
  _cli_parsers/_ticket/**   ticket + its 54 subverbs
_core.py, _misc.py, _reporting.py and src/frob/__main__.py are touched by
several leaves, so those leaves are CHAINED by blocked_by rather than pretended
disjoint -- a frob scope is a write lease and cannot be shared.

OUT OF SCOPE, REPORT ONLY: ~/.claude/refs/frob.md is the owner's file. No leaf
edits it; leaf 7 lists the needed edits in its Done report.

LEAVES (filed 2026-09-19):
  T-4689  telemetry records verb+subverb            2 pts  blocked_by []
  T-4690  delete aliases and duplicates + shim mod  3 pts  blocked_by []
  T-4692  gate stages -> frob check --only          3 pts  blocked_by [T-4690]
  T-4695  read-only analysis -> frob explore        3 pts  blocked_by [T-4690, T-4692]
  T-4696  ticket field setters -> ticket set        2 pts  blocked_by [T-4690]
  T-4698  ticket subverb tail verdicts              3 pts  blocked_by [T-4690, T-4696]
  T-4702  regenerate docs/commands + refs drift     2 pts  blocked_by [T-4690, T-4692, T-4695, T-4696, T-4698]

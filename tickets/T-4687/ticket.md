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
sprint: v0.533.0
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
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.534.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 3648
  new_length: 4265
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 4265
  new_length: 6316
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 6316
  new_length: 6316
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 6316
  new_length: 6316
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 6316
  new_length: 6316
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 6316
  new_length: 6316
- mode: set
  reason: '2026-09-19 coordinator review: explore survives (no delete-then-rebuild);
    pool/profile/debt/deprecated/parse reclassified out of the check --only fold;
    exports split check/scaffold; story acceptance numbers; T-4689-before-hooks ordering'
  actor: logan
  at: '2026-09-19'
  old_length: 6316
  new_length: 6316
- mode: set
  reason: 'DOC006: planned CLI forms written as prose so unrelated lands are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 6316
  new_length: 6340
- mode: set
  reason: 'DOC006: planned CLI forms written as prose so unrelated lands are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 6340
  new_length: 6340
- mode: append
  reason: 'owner 2026-09-20: decide which subverbs stay, which become automatic, which
    move to a daemon; telemetry evidence attached'
  actor: logan
  at: '2026-09-20'
  old_length: 6330
  new_length: 8280
designated_repro_test: null
acceptance:
- text: Given frob --help after all seven leaves land, when the top-level verb count
    is re-measured with the same command that produced the 2026-09-19 baseline of
    51, then it reports 12 or fewer verbs excluding live deprecation shims, and the
    Done report states both numbers (surface, and surface plus live shims)
  evidence: []
- text: Given frob ticket --help after all seven leaves land, when the subverb count
    is re-measured with the same command that produced the 2026-09-19 baseline of
    54, then it reports 25 or fewer subverbs excluding live deprecation shims
  evidence: []
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
names and removed zero. frob explore xref (planned) and `frob xref` are the same
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

ACCEPTANCE NUMBERS (coordinator, owner-approved, 2026-09-19). The story is not
done on vibes; it is done on counts.
  BASELINE, measured 2026-09-19 before any leaf landed:
    top-level verbs in `frob --help`      51
    subverbs in `frob ticket --help`      54
  TARGET, measured the same way after all seven leaves land:
    top-level verbs in `frob --help`      12 or fewer
    subverbs in `frob ticket --help`      25 or fewer
  Deprecation shims do NOT count toward either target while they are live: a
  shim is a name on its way out, and counting it would make the story
  un-closable until the sunset date. Count them separately and report both
  numbers (surface, and surface + live shims) at close.
  The counting command is the same one that produced the baseline:
    frob --help | sed -n '1,4p' | tr -d ' \n' | sed 's/.*{//;s/}.*//' | tr ',' '\n' | grep -c .
  Re-run it verbatim at close so the before/after are commensurable.

AMENDMENTS APPLIED 2026-09-19 after coordinator review:
  - T-4690 KEEPS `explore` as the surviving verb (it deletes explore's
    standalone mirrors outline/map/xref/docs-search and the quality/design/ops
    groups). T-4695 no longer rebuilds explore; it only adds leaves to it. This
    removes a delete-then-rebuild cycle on the same verb.
  - T-4692 no longer folds `pool`, `profile`, `debt`, `deprecated` or `parse`
    into `check --only`. `pool`/`profile` MUTATE state (T-4663 used `frob pool
    snapshot` this sprint) and become frob check pool|profile <op> (planned) subverbs;
    `debt`/`deprecated` are read-only listings and move to T-4695 under
    `explore`; `parse` is a tool-output adapter and moves to T-4698's verdict
    table (measured: zero consumers outside its own code, test and doc page).
  - OWNER DECISION on `exports`: the check half folds into frob check --only
    exports (planned); the generate half moves under `scaffold`.
  - T-4689 lands BEFORE the hooks story's telemetry-logging leaf
    (T-5098, scope `.claude/hooks/*`); both edit
    .claude/hooks/tool-call-telemetry.py.


EVIDENCE (telemetry.jsonl, 30 days to 2026-09-20): 108 ticket subverbs registered, 46 command shapes ever used, 21 shapes account for 99% of calls. Top: verify 1637, ticket sprint 790, new 522, work 480, land 402, show 382, body 310, promote 254, scope 219, check 195, evidence 110, set-parent 103, milestone 95, merge-driver 94. Used once or never in 30 days: 60+ subverbs. DECISIONS to encode here (owner directive: automatic over commands): (a) transition verbs that are only ever called by another verb become internal: promote (called by new/land), sweep and sweep-async (called by start/land), reverify, reconcile, requeue, evidence (written by check/close), done-report (written by close), merge-driver (git-invoked), plan (implicit in start). (b) setters collapse into one 'frob ticket set ID field=value' with the same validation: sprint milestone tier priority kind component label anchor set-parent runs-last runs-last-parallel-safe body. (c) queries collapse into 'frob ticket ls' with filters (list doable board epic contention wave flow sprint show debt deprecated) and 'frob ticket show'. (d) read-only views that are expensive because they mine git or spawn checks move behind a daemon: 'frob serve' already exists as the MCP host; extend it with a background worker that owns the parse-artifact cache, the ledger index, lease registry, done-transition mining (flow) and the T-2006 re-verify, refreshed on ledger commits via a post-commit trigger, so doable/flow/doctor/xref answer from memory in under 1 s and the CLI falls back to in-process when no daemon is running. The daemon is the fix for the cross-invocation cache gap the 2026-09-20 perf audit named (T-5135, T-draft-d098cf91). (e) keep human-facing verbs: new work land close fail drop block unblock show ls set brief attach archive restore reopen. Target: about 15 ticket subverbs, every removed one an alias for one release with a deprecation line, then gone.
---
id: T-draft-3a073b48
title: 'Fold the read-only analysis surface into one verb: explore map/outline/xref/docs-search/gitlog/stats
  and the graph queries'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4690
- T-4692
parent: T-4687
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_explore.py
- src/frob/app/explore_runner.py
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- src/frob/app/gitlog_runner.py
- src/frob/app/stats_runner.py
- src/frob/app/graph_runner.py
- tests/unit/test_explore_verb.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a fixture with one known definition site and two known use sites, when
    frob explore xref runs on that symbol, then all three paths appear in the output
  evidence: []
- text: Given the deprecated top-level frob xref before its sunset date, when it runs,
    then it prints the frob explore xref spelling on stderr and still returns the
    same results
  evidence: []
- text: Given frob --help after this ticket, then map, outline, xref, docs-search,
    gitlog and stats are absent from the top-level usage line and present under frob
    explore --help
  evidence: []
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 3. Parent story T-4687. blocked_by T-4689 and T-4690 -- it shares
_core.py/_misc.py/_reporting.py/_explore.py/__main__.py with both, and a frob
scope is a write lease that cannot be shared.

OWNER DECISION: "start removing subverbs and the read-only analysis."

FOLD the read-only analysis surface into ONE verb with these subverbs:
  map, outline, xref, docs-search, gitlog, stats,
  and `graph query` / `graph why` / `graph affects`
Delete the top-level duplicate of each, with a T-4689 shim for one minor
version.

NAME: `explore`, not `show`. MEASURED by `git grep -c` over .claude/ docs/
scripts/ src/ tests/: "frob explore" 95 citations, "frob show" 0. The name is
chosen by existing citations, not taste.

THIS IS NOT A REVIVAL OF THE T-1238 GROUP. T-4689 deletes the old `explore`,
which was a pure alias mirror (`_mirror_subparser` aliased the flat parsers into
a group and kept both spellings). The `explore` this ticket builds is the ONLY
spelling: after this ticket `frob xref` is a shim, not a peer.

`graph`'s non-read-only halves (cache build, drift explanation with a write
side) STAY on `frob graph`. Only the pure queries move. State in the Done
report which graph subverbs moved and which did not, with the reason.

POSITIVE CONTROL (acceptance): a test that runs `frob explore xref <symbol>` on
a fixture with a KNOWN definition site plus two known use sites, and asserts all
three paths appear; plus a test asserting the deprecated top-level `frob xref`
prints the `frob explore xref` spelling on stderr and still works before the
sunset date. `frob xref` has 16 recorded kind=cli invocations, so its shim is
the one with a real live consumer -- do not skip it.

FILES (declared scope):
  src/frob/_cli_parsers/_explore.py, _core.py, _misc.py, _reporting.py
  src/frob/__main__.py
  src/frob/app/explore_runner.py, map_runner.py, outline_runner.py,
  docs_runner.py, gitlog_runner.py, stats_runner.py, graph_runner.py
  tests/unit/test_explore_verb.py (new)

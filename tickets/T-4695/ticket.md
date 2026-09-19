---
id: T-4695
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
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 1987
  new_length: 1987
- mode: set
  reason: '2026-09-19 coordinator review: explore survives; pool/profile/debt/deprecated/parse
    reclassified out of the check --only fold; exports split check/scaffold; ordering
    vs hooks story'
  actor: logan
  at: '2026-09-19'
  old_length: 1987
  new_length: 3223
- mode: set
  reason: 'DOC006: planned CLI forms written as prose so unrelated lands are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 3223
  new_length: 3255
designated_repro_test: null
acceptance:
- text: Given a fixture repo with a KNOWN conventional-commit history, when frob explore
    gitlog runs on it, then the expected type/granularity rollup appears -- a no-crash
    assertion does not satisfy this criterion
  evidence: []
- text: Given the deprecated top-level frob gitlog before its sunset date, when it
    runs, then it prints the frob explore gitlog spelling on stderr and returns output
    identical to the new spelling; the same holds for stats, debt and deprecated
  evidence: []
- text: Given frob --help after this ticket, then gitlog, stats, debt and deprecated
    are absent from the top-level usage line and present under frob explore --help,
    and graph query/why/affects are reachable through frob explore while frob graph
    keeps its cache-building and write-side subverbs
  evidence: []
acceptance_amendments:
- op: replace
  index: 1
  old_text: Given a fixture with one known definition site and two known use sites,
    when frob explore xref runs on that symbol, then all three paths appear in the
    output
  new_text: Given a fixture repo with a KNOWN conventional-commit history, when frob
    explore gitlog runs on it, then the expected type/granularity rollup appears --
    a no-crash assertion does not satisfy this criterion
  reason: '2026-09-19 coordinator review: map/outline/xref/docs-search are T-4690
    work now; this ticket moves gitlog, stats, the graph queries, debt and deprecated,
    so the positive control must be one of those'
  actor: logan
  at: '2026-09-19'
- op: replace
  index: 2
  old_text: Given the deprecated top-level frob xref before its sunset date, when
    it runs, then it prints the frob explore xref spelling on stderr and still returns
    the same results
  new_text: Given the deprecated top-level frob gitlog before its sunset date, when
    it runs, then it prints the frob explore gitlog spelling on stderr and returns
    output identical to the new spelling; the same holds for stats, debt and deprecated
  reason: '2026-09-19 coordinator review: the shims this ticket owns are gitlog/stats/debt/deprecated,
    not xref (T-4690 owns that one)'
  actor: logan
  at: '2026-09-19'
- op: replace
  index: 3
  old_text: Given frob --help after this ticket, then map, outline, xref, docs-search,
    gitlog and stats are absent from the top-level usage line and present under frob
    explore --help
  new_text: Given frob --help after this ticket, then gitlog, stats, debt and deprecated
    are absent from the top-level usage line and present under frob explore --help,
    and graph query/why/affects are reachable through frob explore while frob graph
    keeps its cache-building and write-side subverbs
  reason: '2026-09-19 coordinator review: this ticket adds leaves to the surviving
    explore verb; map/outline/xref/docs-search were already folded by T-4690'
  actor: logan
  at: '2026-09-19'
threat: null
component: cli
labels:
- cli-debloat
- points-3
anchor: false
anchor_reason: null
land_commit: null
---
POINTS: 3. Parent story T-4687. blocked_by T-4690 and T-4692 -- it shares
_core.py/_misc.py/_reporting.py/_explore.py/__main__.py with both, and a frob
scope is a write lease that cannot be shared.

OWNER DECISION: "start removing subverbs and the read-only analysis."

AMENDED 2026-09-19 (coordinator review): this ticket no longer creates `explore`
and no longer moves map/outline/xref/docs-search. T-4690 keeps `explore` as the
surviving verb and deletes their standalone mirrors, so those four leaves are
ALREADY under `explore` when this ticket starts. This ticket only ADDS to it.

MOVE UNDER frob explore (planned), deleting each top-level spelling with a T-4690 shim:
  gitlog                          -> frob explore gitlog
  stats                           -> frob explore stats
  graph query|why|affects         -> frob explore graph-query|graph-why|
                                     graph-affects (or a nested `explore graph`
                                     subgroup -- pick one and say which)
  debt      (moved here from T-4692) -> frob explore debt
  deprecated (moved here from T-4692) -> frob explore deprecated
`debt` and `deprecated` are read-only listings ("list outstanding frob:debt
entries", "list outstanding frob:deprecated entries"), which is why they belong
here and not behind frob check --only (planned).

NAME: `explore`, not `show`. MEASURED by `git grep -c` over .claude/ docs/
scripts/ src/ tests/: "frob explore" 95 citations, "frob show" 0. The name is
chosen by existing citations, not taste.

`graph`'s non-read-only halves (cache build, and any drift explanation with a
write side) STAY on `frob graph`. Only the pure queries move. State in the Done
report which graph subverbs moved and which did not, with the reason.

TOP-LEVEL `debt`/`deprecated` VS `frob ticket debt`/`frob ticket deprecated`:
these are four names for two concepts. T-4698 renders the verdict on the
`ticket` side; coordinate so the two tickets do not both decide, and record the
agreed outcome in whichever closes second.

POSITIVE CONTROL (acceptance): a test that runs frob explore gitlog (planned) on a
fixture repo with a KNOWN conventional-commit history and asserts the expected
type/granularity rollup appears; plus a test asserting the deprecated top-level
`frob gitlog` prints the frob explore gitlog (planned) spelling on stderr and returns
the identical output before the sunset date. "Runs without crashing" does not
close this ticket.

FILES (declared scope):
  src/frob/_cli_parsers/_explore.py, _core.py, _misc.py, _reporting.py
  src/frob/__main__.py
  src/frob/app/explore_runner.py, gitlog_runner.py, stats_runner.py,
  graph_runner.py, debt_runner.py, deprecated_runner.py
  tests/unit/test_explore_verb.py (new)
NOTE: map_runner.py and outline_runner.py are no longer needed here (T-4690
handles those mirrors); debt_runner.py and deprecated_runner.py are new arrivals
from T-4692. Reconcile the ledger scope with `frob ticket scope T-4695 --add/
--remove` before starting.

TITLE DRIFT: this ticket's title still lists map/outline/xref/docs-search. After
this amendment it covers gitlog, stats, the graph queries, debt and deprecated.
`frob ticket` has no title setter; this paragraph is the correction of record.

---
id: T-1344
title: 'Agentic-development throughput: the land path is the bottleneck, not the work'
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- docs/guides/agent-playbook.md
- src/frob/tickets/_land_git_ops.py
- src/frob/gates/__init__.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: given N concurrent agents finishing work, when each lands, then no agent is
    refused for DirtyMain and no agent touches another agent uncommitted state
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: given an unchanged file set, when frob check re-runs, then gate results are
    served from a content-digest cache rather than recomputed
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Filed 2026-07-31 from direct observation of a 7-agent parallel drive (T-1334/1336/1337/1338/1340/1327/1276/1293/1294/1296).

THE EVIDENCE: across four completed tickets that day, every agent got its ENGINEERING right on the first pass. Effectively all of the lost wall-clock was in the LAND PATH:

- T-1336: DirtyMain refusal from a sibling's in-flight land, plus one land attempt killed by an undersized timeout wrapper.
- T-1337: committed ANOTHER agent's uncommitted tickets.md churn to main, twice, purely to clear DirtyMain. Inert metadata this time; the shape is dangerous.
- T-1338: land killed mid-Tier-A-autofix left a GARBLED source file; the obvious "git checkout -- <file>" recovery then silently destroyed an uncommitted new test. Caught only because a pytest count looked wrong.
- Coordinator: "frob ticket new" exceeded a 120s timeout under 4 concurrent agents (single-file ledger lock).

So the leverage is not in how agents do the work -- it is in serialization, cache-coldness, and non-atomic recovery. Leaves cover: merge queue, digest-memoized gates, sibling-lease disclosure in brief, transactional land auto-fix, ledger write contention.

ALSO NOTE (separate but related): the coordinator was hand-writing 40-line dispatch prompts duplicating what "frob ticket brief" already emits. Underused capability, not a tool gap -- addressed by convention plus the brief leaf.

CONSTRAINT DISCOVERED: memory is no longer the limit on agent count (.wslconfig now gives 23 GB + 24 GB swap). CPU is: 12 cores, load ~11 at only 4 agents, and land must finish inside a 540s wrapper. Practical ceiling ~7 concurrent agents. Every item below raises that ceiling by making the land path cheaper.

T-1058 (worktree cut from stale origin/main -- a documented silent-revert cause) is ARCHIVED, not resolved in the active ledger; the playbook still carries a manual "git merge main first" step as the mitigation. Re-decide it under this epic if the merge queue does not subsume it.

## Done report

CORRECTED per coordinator feedback mid-investigation. Original draft
attributed the land-path cost primarily to lock contention (based on the
coordinator's initial "9-19 concurrent processes" figure, which turned
out to be a raw `ps` count of every wrapper/subprocess per land, not real
concurrency). Re-measured concurrency from .frob/telemetry.jsonl interval
overlap directly (not ps): of 812 successful lands, 83.1% (n=675) had NO
other land in flight at all. The solo-only bucket alone reproduces the
same wide spread as the aggregate (median 80.4s, p75 263.9s, p90 424.2s,
p95 483.0s, max 1620.9s) -- proof that queueing is not the dominant
driver, since a solo land waits ~0s on the lock by definition.

VERDICT: COST dominates, not contention. Root cause, confirmed by reading
the code and directly timing the mechanism: land()'s post-merge
re-verification (`_check_gates_summary_fn`, src/frob/app/ticket_runner/
_verify.py, wired at _land_cmd.py:3355) spawns a fresh, synchronous
`python -m frob check --ticket <id> --json` against the just-merged tree,
INSIDE the land lock, on every single land -- and per the playbook's own
section 6c, --ticket narrows almost nothing, so this is effectively a
full unscoped gate sweep. Timed live in this investigation: 208.7s total
(sys=34.6s, archgate=29.6s, perf=30.9s, coverage=19.0s, refs=15.3s,
dead_symbols=11.7s, pii_structural=11.0s, docblocks=7.5s, clones=7.0s,
test=6.3s, tickets=5.5s, plus ~15 smaller stages). That number sits
almost exactly between this ticket's own measured median (95.4s) and p75
(322.6s) -- strong direct evidence this one spawn is the single largest
line item in a typical land.

Lock queueing (_land_lock, src/frob/tickets/_land.py:277-385, T-0577,
one process-wide flock wrapping the entire precheck-through-commit body)
is real but SECONDARY: it explains the heavier tail seen in the ~16.8% of
lands that do overlap (concurrency=2's p95 is 539.0s vs the solo
bucket's 483.0s), not the median or the bulk of the spread.

The T-2032/T-2033 silent deaths (four lands that died at 540-580s with no
LAND-PROOF line) are still explained -- by cost first now, not contention
first: _LAND_LOCK_TIMEOUT_S=600.0 (_land.py:148) exceeds the playbook's
mandated 540-580s shell wrapper, so a land whose own work (merge +
Tier-A + the ~209s re-verification spawn + tests + commit) runs long
enough on its own merits gets killed by the outer wrapper before any
internal timeout or lock-wait message can print.

Wrote the corrected finding (measured numbers, code citations, the
direct 208.7s timing, and a ranked three-point proposal targeting the
re-verification spawn's cost first, lock-narrowing second) into
docs/guides/agent-playbook.md section 13. No code change was safely
implementable inside this ticket's own scope (the mechanism lives in
src/frob/app/ticket_runner/_verify.py and src/frob/tickets/_land.py,
neither in scope, and _land_git_ops.py is explicitly owned by other
agents this session) -- per the brief, landing the design and disclosing
what needs a decision is the complete deliverable here.

DISCLOSED CUT: acceptance criteria [0] (merge-queue/DirtyMain behavior)
and [1] (digest-keyed gate cache reuse) describe the FULL fix, not this
investigation's own deliverable -- neither is implemented. The evidence
bound to them (the CLI-dispatch integration test, docs-only-ticket
precedent per playbook section 5) proves only that the playbook doc is
wired into the CLI test surface, not that the acceptance behavior
exists. This ticket is not being closed to "done"; it stays in-progress
carrying the design finding for a decision on the ranked proposal.

### Changed
```
 docs/guides/agent-playbook.md | 132 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1344/done-report.md |  59 +++++++++++++++++++
 tickets/T-1344/ticket.md      |  12 +++-
 3 files changed, 200 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, CLAUDE001@.claude/hooks/sync-claude-config.py, DOC005@README.md, DOC005@docs/modules/cli.md, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, F401@/home/logan/projects/frob/.claude/worktrees/t1344-land-throughput/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1344-land-throughput/tests/unit/test_tickets_evidence_only_scope.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-1344, SELFAUDIT001@design

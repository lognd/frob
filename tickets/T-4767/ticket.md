---
id: T-4767
title: 'Source narrative C4: app/ticket_runner + app/ + lang/ -- 21 files, 48 runs,
  1060 lines'
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: high
parent: T-4691
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/app/__init__.py
- src/frob/app/_config_external.py
- src/frob/app/_daemon_proxy.py
- src/frob/app/config.py
- src/frob/app/parse_runner.py
- src/frob/app/pyfmt_runner.py
- src/frob/lang/__init__.py
- src/frob/lang/_models.py
- src/frob/lang/_nodes.py
- src/frob/lang/_support.py
- src/frob/lang/_walk_strata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_new.py
  reason: leased by in-progress T-4805, deferred per BRIEF.md concurrency rule
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: leased by in-progress T-4660, deferred per BRIEF.md concurrency rule
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/telemetry/_state.py
  reason: leased by in-progress T-4689 (src/frob/app/telemetry/**), deferred per BRIEF.md
    concurrency rule
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: 'given the 21 files in this cluster, when the sweep is done, then zero comment
    runs longer than 12 consecutive # lines remain in them (the DOCARCH002 default
    cap)'
  evidence: []
- text: given every block that cited a ticket, when the sweep is done, then that narrative
    is readable in that ticket body -- moved, never deleted (T-2994 constraint 1)
  evidence: []
- text: given every block that cited NO ticket, when the sweep is done, then its narrative
    is in this cluster ticket body
  evidence: []
- text: given the whole diff, when git diff -w is taken over non-comment lines, then
    it is empty -- comments only, no behaviour change
  evidence: []
- text: given each batch of frob narrative move calls, when the batch finishes, then
    frob ticket list exits 0 (T-2994 constraint 3, the DuplicateId hazard)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CLUSTER leaf of T-4691 (C4). Scope-disjoint from every other cluster leaf;
not blocked by the gate (T-4693) or tool (T-4697) leaves -- `frob narrative move
<file> <line>` already works per-block and hand migration is sanctioned. Take
this leaf now; if T-4697's bulk mode lands first, use it.

MEASURED 2026-09-19 over src/frob/**/*.py (scratchpad/measure.py):
  21 files, 48 comment runs of 15+ consecutive `#` lines, 1060 lines.

PER-FILE:
    7 runs   163 lines  src/frob/app/ticket_runner/_rapid_sweep.py
    7 runs   143 lines  src/frob/lang/_support.py
    5 runs   114 lines  src/frob/app/ticket_runner/__init__.py
    5 runs    92 lines  src/frob/app/ticket_runner/_new.py
    3 runs    90 lines  src/frob/app/ticket_runner/_verify.py
    3 runs   140 lines  src/frob/app/ticket_runner/_waive_audit.py
    3 runs    55 lines  src/frob/app/config.py
    2 runs    34 lines  src/frob/app/ticket_runner/_ledger_mirror.py
    1 runs    18 lines  src/frob/app/ticket_runner/_close_cmd.py
    1 runs    18 lines  src/frob/app/ticket_runner/_lifecycle.py
    1 runs    15 lines  src/frob/app/ticket_runner/_query.py
    1 runs    16 lines  src/frob/app/__init__.py
    1 runs    18 lines  src/frob/app/_config_external.py
    1 runs    17 lines  src/frob/app/_daemon_proxy.py
    1 runs    16 lines  src/frob/app/parse_runner.py
    1 runs    16 lines  src/frob/app/pyfmt_runner.py
    1 runs    16 lines  src/frob/app/telemetry/_state.py
    1 runs    24 lines  src/frob/lang/__init__.py
    1 runs    24 lines  src/frob/lang/_models.py
    1 runs    15 lines  src/frob/lang/_nodes.py
    1 runs    16 lines  src/frob/lang/_walk_strata.py

WHAT TO DO, per T-2994's doctrine (code carries UTILITY, tickets carry NARRATIVE):
- For each over-long run, SPLIT it. The part that tells a reader about to modify
  or reuse this code something they need (an invariant, a platform quirk, why the
  obvious approach fails) STAYS. The part that tells the story of how we got here
  (which ticket superseded which, what a prior attempt got wrong, cross-references
  to landed work) MOVES into the ticket the block already cites.
- Use `frob narrative move <file> <line> --reason "..."`, with `--keep-file` for
  the lines that stay. `--dry-run` first.
- A block citing NO ticket: its narrative goes into THIS cluster ticket's body.
  Never delete it and never invent a ticket for it.

T-2994 CONSTRAINTS, all binding on this leaf:
1. MOVE, NEVER DELETE. This is institutional memory -- agents have avoided
   repeating landed mistakes purely because such a note existed. A migration that
   loses narrative is strictly worse than the bloat it removes.
2. THE SPLIT IS A JUDGEMENT, NOT A REGEX. T-2994's own example: in the
   `_socketd.py` T-2961 block, "a CLASS statement referencing a missing base at
   module scope raises AttributeError at IMPORT time, unlike the fcntl pattern
   used for FUNCTIONS" is load-bearing and STAYS; the T-2918/T-2934/T-2952/T-2953
   cross-references and historical framing MOVE. Both kinds live in one block.
3. ARCHIVED-TICKET WRITE HAZARD. Most cited tickets are archived, and
   `frob ticket body` on a done ticket has previously written the ACTIVE path and
   produced a DuplicateId that downed every ledger load repo-wide. Prove the
   archived-write path on ONE ticket, verified, before any batch. Run
   `frob ticket list` (must exit 0) after EVERY batch, not just at the end.
4. IDEMPOTENCY. Re-running a move must not duplicate content into the ticket.

NO BEHAVIOUR CHANGE. This leaf touches comments only. Not one token of executable
code changes. Close with `--no-behavior-change`; `git diff -w` on the non-comment
lines must be empty, and that is the cheapest proof the reviewer has.

THRESHOLD NOTE: the titles and counts above use the 15+ line measurement. The
DOCARCH002 gate (T-4693) caps at 12 by default, so sweep at >12, not >=15, or the
cluster will still show findings when the gate lands.

FILES EXCLUDED FROM EVERY CLUSTER (22 files, ~95 runs, ~2,288 lines) because they
are leased by in-progress tickets as of 2026-09-19 18:05 -- taking them would
collide with a live lease and be refused at land:
  src/frob/__main__.py  -- leased by T-4546
  src/frob/_cli_parsers/_root.py  -- leased by T-4546
  src/frob/app/sys_runner.py  -- leased by T-4112
  src/frob/app/ticket_runner/_land_cmd.py  -- leased by T-draft-f5ac9ec0
  src/frob/gates/__init__.py  -- leased by T-3962
  src/frob/gates/_coverage.py  -- leased by T-3997
  src/frob/gates/_docblocks_refs.py  -- leased by T-4254
  src/frob/gates/_pii_structural/__init__.py  -- leased by T-4073
  src/frob/gates/_sys.py  -- leased by T-4212
  src/frob/gates/_tickets_gate.py  -- leased by T-3899
  src/frob/gates/_waive.py  -- leased by T-4212
  src/frob/graph/callgraph.py  -- leased by T-3962
  src/frob/process/_guard.py  -- leased by T-3802
  src/frob/strata/_effects.py  -- leased by T-4669
  src/frob/strata/_waive.py  -- leased by T-4112
  src/frob/tickets/_doable.py  -- leased by T-4379
  src/frob/tickets/_evidence.py  -- leased by T-4684
  src/frob/tickets/_leases.py  -- leased by T-4659
  src/frob/tickets/_new_renumber.py  -- leased by T-4658
  src/frob/tickets/_renumber_v2.py  -- leased by T-4658
  src/frob/tickets/_scope.py  -- leased by T-3412
  src/frob/verify/_quarantine.py  -- leased by T-3082
These are follow-up work once those leases release; they are deliberately not
dropped, just deferred.

---
id: T-4691
title: 'Source narrative: 447 comment blocks of 15+ lines (10.7k lines) migrate to
  tickets, NARR001 covers untagged comment runs'
state: queued
kind: docs
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
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2994 (DOCARCH001/NARR001 doctrine epic): code and docs carry UTILITY,
tickets carry NARRATIVE. T-4623..T-4632 cover DOCSTRING narrative in tests. This
story covers COMMENT-BLOCK narrative in src/frob/**.

MEASURED 2026-09-19 18:20 by the planner over src/frob/**/*.py (553 files), script
in scratchpad/measure.py + gap.py, not estimates:

| shape                                        | count | lines  |
|----------------------------------------------|-------|--------|
| comment runs of 15+ consecutive `#` lines    |   447 | 10,718 |
| ...of those reading as change narrative      |   442 |      - |
| comment runs of 8-14 lines                   | 1,228 | 12,179 |
| docstrings of 15+ lines                      | 1,732 | 50,560 |

447 runs across 185 files. Top files: tickets/_land.py 19 runs/478 lines,
app/ticket_runner/_land_cmd.py 16/341, gates/_waive.py 14/481, gates/__init__.py
12/243, tickets/_models.py 12/210, gates/_bug_repro.py 11/273, graph/dsl.py
11/251, tickets/_leases.py 9/202, gates/_wire.py 8/197, tickets/_evidence.py 8/181.

TOOLING AS MEASURED (this corrects the framing the story was requested under):

1. DOCARCH001 does NOT cover `#` comment runs. `src/frob/gates/_docstring_archaeology.py`
   line 155-185 (`docarch001_violations`) iterates `parsed.danger_ok.symbols` and
   tests `sym.doc_text` only -- docstrings, nothing else. No new DOCARCH id is
   needed and none should be added.
2. The comment-run rule ALREADY EXISTS: NARR001,
   `src/frob/gates/_narrative_blocks.py` (T-2993/T-3014), WARN tier, catalogued at
   docs/modules/gates.md:135 and documented at docs/commands/narrative.md#narr001-the-detector.
3. NARR001's COVERAGE GAP is the real gate work, and it is measured:
   `_iter_blocks` (_narrative_blocks.py:52-60) only opens a block on a
   `# T-####:` LEAD line (`_TICKET_LEAD_RE`, line 48), and
   `NARR001_THRESHOLD_LINES = 12` is a module constant (line 45), not frob.toml
   config. Against the 447 measured runs:
     - NARR001 fires on        91 blocks /  2,071 lines
     - NARR001 does NOT fire on 376 blocks /  8,774 lines
   The 376 are 15+ line runs that read as narrative (T-id cited mid-block, or
   "previously"/"used to"/"superseded"/"folded into" wording) but do not OPEN
   with a `# T-####:` line. 82% of the measured bloat is invisible to the gate.
4. `frob narrative move <file> <line>` is single-block and positional: one block,
   one invocation, no directory/file-sweep, no `--apply`. There is no bulk mode.

CONSTRAINTS INHERITED FROM T-2994 (all still binding):
- MOVE, NEVER DELETE. This is institutional memory.
- THE SPLIT IS A JUDGEMENT, NOT A REGEX. One block often holds both kinds
  (T-2994's `_socketd.py`/T-2961 example); the load-bearing sentence STAYS.
- ARCHIVED-TICKET WRITE HAZARD. `frob ticket body` on a done ticket has
  previously written the ACTIVE path and downed the ledger repo-wide. Prove the
  archived-write path on ONE ticket before any batch; `frob ticket list` must
  exit 0 after every batch.
- IDEMPOTENCY. Running a migration twice must not duplicate ticket content.
- IT MUST NOT REGROW. Gate first-class, shipped WARN, burned down, then ERROR.

LEAF SHAPE: one GATE leaf (NARR001 coverage + frob.toml config), one TOOL leaf
(bulk `frob narrative`), and 8 scope-disjoint cluster leaves covering 164 files /
352 runs / 8,430 lines. Clusters are NOT blocked by the gate or tool leaves --
`frob narrative move` already works per-block and hand migration is sanctioned.

22 files (95 runs, ~2,288 lines) are EXCLUDED from every cluster because they are
leased by in-progress tickets; they are listed in the cluster bodies and are
follow-up work once those leases release.

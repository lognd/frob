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
milestone: 0.534.0
flavour: user_story
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'story tier: an umbrella over 11 leaves; all code scope
  lives on the leaves'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: 'owner decision: docstring half automated via the same Tier-A fix; record
    the three new leaves and the relocate-vs-condense division'
  actor: logan
  at: '2026-09-19'
  old_length: 3686
  new_length: 6151
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


AMENDMENT 2026-09-19 -- THE DOCSTRING HALF IS NOW IN SCOPE, AND AUTOMATED.

The story originally covered COMMENT-BLOCK narrative only, and left the docstring
half (1,055 docstrings over 20 lines, 38,964 lines) as an open question for the
ERROR-promotion leaf to decide. Owner decision: AUTOMATE IT, NO SEPARATE VERB.
The docstring migration is the same `frob check --fix` Tier-A fix, not a new
command. Three leaves added:

- T-4807 (blocked_by T-4694) -- the docstring half of the Tier-A fix. Keep
  paragraph 1 as the docstring; route the remainder by the same rule as comment
  runs: to the cited ticket's body when a T-#### is cited, else to
  docs/modules/<module>.md under a heading named for the symbol, leaving a
  `frob:doc` pointer on the symbol. Idempotent. REFUSES when the target ticket
  does not exist. Acceptance includes byte-for-byte identical COV/TEST findings
  after -- docstrings feed COV002 and frob:doc edges feed DRIFT001/COV001, so a
  sweep that shifts the finding set has moved the enforcement surface, not prose.
  Split out of T-4694 because it adds a second destination type and would have
  taken that leaf past three points.
- T-4808 -- a docs/modules size lint: a per-symbol section over N lines is a
  finding, N config in <!-- frob:waive DOC006 reason="illustrative future frob.toml section this ticket proposes -- does not exist until the DOCARCH002 leaf lands" -->[gates.docs] beside comment_run_max and docstring_max.
  This is the DESTINATION-SIDE half of the same ratchet: without it, relocating
  38,964 lines into docs/modules is a relocation rather than a reduction, and
  prose escapes one cap by moving under the other. N chosen from the measured
  distribution of today's section lengths, recorded in the ticket.
- T-4810 (blocked_by T-4807) -- run the fix repo-wide in a coordinator-declared
  quiet window as ONE cross-ticket land. Acceptance is the count: 1,055 -> N,
  re-measured, not the exit code. Agents review diffs per package.

DIVISION OF LABOUR, recorded because it is what makes 38,964 lines tractable:
the fix RELOCATES prose mechanically; agents CONDENSE the relocated prose when
they review the diff. Agents do not hand-author the moves. T-4808's lint is what
turns "condense in review" from an intention into a gate finding when it does not
happen.

T-4772 (ERROR promotion) is now also blocked by T-4807, T-4808 and T-4810. Its
original acceptance asked for a decision on the docstring half "on the record" --
this amendment IS that decision, and the leaf's job there is now to confirm the
burn-down happened rather than to choose a policy.

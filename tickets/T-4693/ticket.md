---
id: T-4693
title: 'DOCARCH002: structural comment lint -- content-blind length cap, T-#### citations
  must be directives, ratcheted (baseline 507 runs/1055 docstrings/2303 citations)'
state: in-progress
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4691
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docarch_structural.py
- tests/gates/test_docarch_structural.py
- docs/modules/gates.md
- frob.toml
- frob-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob-ratchet.lock.json
  reason: T-4693 DOCARCH002 ratchet baseline snapshot
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: given a 20-line comment run of pure algorithm explanation citing no ticket,
    when DOCARCH002 check 1 runs, then it is flagged (content-blind)
  evidence: []
- text: 'given a 5-line comment run, a 20-line frob: directive block, and a 20-line
    module license header, when DOCARCH002 check 1 runs, then none of the three is
    flagged (exempt by syntax, not by wording)'
  evidence: []
- text: given a 25-line docstring and a 15-line docstring, when DOCARCH002 check 1
    runs with default docstring_max=20, then the 25-line one is flagged and the 15-line
    one is not
  evidence: []
- text: given frob.toml [gates.docs] comment_run_max = 30, when DOCARCH002 runs over
    the 20-line fixture, then it is quiet -- proving the config path, not just the
    default
  evidence: []
- text: given a frob:ticket T-1234 directive, a single-line '# see T-1234' pointer,
    and a '# T-1234:' line followed by 3 prose lines, when DOCARCH002 check 2 runs,
    then only the third is flagged and its remedy names frob narrative move
  evidence: []
- text: given DOCARCH002 ships WARN with today's counts baselined into frob pool,
    when one new over-cap comment run is added, then frob check fails on the increase
    immediately
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
GATE leaf of T-4691. Owner directive 2026-09-19 18:30: file this as a STRUCTURAL
comment lint, NOT a narrative-keyword heuristic (standing directive: token/grammar,
never lexical). The keyword discriminator NARR001 and DOCARCH001 both use is the
wrong instrument here; length and directive-shape are decidable from the token
stream, wording is not.

WHY A NEW ID AND NOT DOCARCH001. Measured, cite-checked:
- `src/frob/gates/_docstring_archaeology.py:155-185` (`docarch001_violations`)
  iterates `parsed.danger_ok.symbols` and tests `sym.doc_text` only. DOCARCH001 is
  docstrings-only and content-keyed (`_is_archaeology`, line 90). It cannot host a
  content-blind comment-run cap without changing what DOCARCH001 means.
- NARR001 (`src/frob/gates/_narrative_blocks.py`, T-2993/T-3014) is the existing
  comment-run rule, but it is also the wrong host: `_iter_blocks` (line 52) only
  OPENS a block on a `# T-####:` lead line (`_TICKET_LEAD_RE`, line 48) and
  `NARR001_THRESHOLD_LINES = 12` (line 45) is a module constant, not config.
So: DOCARCH002, a new rule family with three checks. NARR001 stays as-is; this
ticket must state in docs/modules/gates.md how DOCARCH002 and NARR001 divide the
surface (NARR001 = ticket-led blocks flagged for `narrative move`; DOCARCH002
check 1 = content-blind length cap over ALL comment runs and docstrings).

THREE CHECKS, ONE RULE FAMILY (DOCARCH002):

(1) LENGTH CAP, CONTENT-BLIND.
    Any run of consecutive `#` comment lines longer than N (frob.toml
    [gates.docs] comment_run_max, default 12) is a finding. Any docstring longer
    than M lines ([gates.docs] docstring_max, default 20) is a finding.
    No wording test anywhere in this check.
    EXEMPT BY SYNTAX, NOT BY WORDING: a shebang/coding line, a license header
    block (the leading comment run before the first token of the module), and a
    `# frob:` / `# noqa` / `# type:` / `# ruff:` / `# mypy:` directive run.
    Exemption is decided from the token's own shape, never from what it says.
    REMEDY TEXT: "move history to the ticket (`frob narrative move`) or
    explanation to docs/modules with a `frob:doc` pointer".

(2) TICKET CITATIONS ARE DIRECTIVES.
    A `T-####` appearing in a comment must be one of: a `frob:ticket` /
    `frob:todo` directive, or a single-line `# see T-####` pointer. Two or more
    comment lines under a `T-####` citation is a finding whose remedy is
    `frob narrative move`.

(3) RATCHET THEN ERROR.
    Ships WARN and baselines today's measured count into the ratchet pool
    (`frob pool`). Any INCREASE fails immediately -- that is the "it must not
    regrow" constraint T-2994 lists, and it is what makes this a fix rather than
    a sweep. Promotion to ERROR is a separate follow-up leaf blocked by the eight
    cluster leaves.

MEASURED BASELINE for the ratchet pool, 2026-09-19 over src/frob/**/*.py (553
files); scratchpad/struct.py is the script:
| check                                         | count | lines  |
|-----------------------------------------------|-------|--------|
| (1) comment runs >12, directive runs excluded |   507 | 10,973 |
| (1) docstrings >20 lines                      | 1,055 | 38,964 |
| (2) T-#### citation with 2+ lines under it    | 2,303 | 18,795 |
| directive runs >12 correctly exempted         |    97 |      - |
The 97 exempted directive runs are the positive control for "exempt by syntax":
they must NOT appear in the baseline. If a run of the pool lands at 604 for check
1 instead of 507, the syntax exemption is not firing.

POSITIVE CONTROLS (fixtures; every one of these is an acceptance criterion):
- a 20-line comment run of pure algorithm explanation, citing no ticket, IS
  flagged by check 1 -- content-blind means content-blind.
- a 5-line comment run is NOT flagged.
- a 20-line `# frob:` directive block is NOT flagged.
- a 20-line license header at the top of the module is NOT flagged.
- a 25-line docstring IS flagged; a 15-line docstring is NOT.
- a `# frob:ticket T-1234` line is NOT flagged by check 2.
- a `# see T-1234` single-line pointer is NOT flagged by check 2.
- a `# T-1234: ...` followed by 3 lines of prose IS flagged by check 2.
- thresholds respond to frob.toml: setting comment_run_max = 30 makes the 20-line
  fixture quiet, proving the config path and not just the default.

NON-GOALS: no wording/keyword list anywhere in DOCARCH002. No change to
DOCARCH001 or NARR001 behaviour. The `--fix` auto-fix for check 2 is a separate
leaf; this leaf only emits the finding and the remedy string.

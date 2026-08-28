---
id: T-3189
title: 'Enforce the placement rule: ticket narratives belong in tickets, not code
  comments or module docs'
state: dropped
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_comment_placement.py
- tests/gates/test_comment_placement.py
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_comment_placement.py
  reason: new placement gate, its fixtures, and the convention statement
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/gates/test_comment_placement.py
  reason: new placement gate, its fixtures, and the convention statement
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: new placement gate, its fixtures, and the convention statement
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: cedfabc3260e9d4ac02c75b4f5c64e0913b22d71
---
OWNER DIRECTIVE 2026-08-27: "TICKET NARRATIVES GO IN TICKETS. modules need to be
debloated as well; they should have the details needed for an operator or a
developer."

THE PLACEMENT RULE to enforce:
  - TICKET     -- why we did it, what was measured, what was rejected, history.
  - docs/      -- what an operator or developer needs: how to run it, what the
                  rules mean, what the failure modes are. NO ticket archaeology.
  - CODE       -- only what a reader of THAT LINE needs in order not to misread
                  it. Not a ticket body.

MEASURED 2026-08-27, both surfaces violate this, in DIFFERENT shapes.

CODE (`src/`, 290,150 lines):
  ticket-citing contiguous comment blocks, by length --
    <=3 lines carrying a frob: DSL directive   2891   (legitimate, leave alone)
    <=3 lines prose                             623
    4-10 lines                                 2630
    11-25 lines                                 574
    26+ lines                                   96
  Total in 4+ line blocks: 28,273 lines, about 9.7% of src.
  Longest: 130 lines at src/frob/vet/_capability_typescript_bindtable.py:18
  (a file of 593 lines total). Others over 100:
    src/frob/gates/_waive.py:1461 (107)
    src/frob/gates/_waive.py:2217 (70)

  These are ticket bodies living in .py files. The 130-line block recounts why
  lexical needle-matching failed for TypeScript, tabulates six import forms, and
  explains a scope-shadowing rule. Good content -- wrong home.

DOCS (`docs/`, 71,689 lines, 152 files):
  6,283 ticket-id mentions across 143 of 152 files.
  Worst: docs/modules/gates.md (884 lines carry a ticket id, file is 7,169).
  Shape here is provenance parentheticals wedged into operator reference tables:
    | DUP003 | clones | (T-0399) `[dup].enforce=true` but frob-core is not ...
    | SYS003 | sys | (error, T-2407) tier-2 code binding ...
  The TABLE is exactly right for an operator. The ticket id tells them nothing
  they can act on. Strip provenance, keep behaviour.

WHY THIS IS NOT COSMETIC. A free-floating `# T-0377: <40 lines>` block is
invisible to every drift gate -- DRIFT/DOC enforce docstring and docs/ anchor
consistency, not arbitrary comment prose. So this narrative can describe
behaviour the code stopped having and NOTHING fires. Intent recorded in prose is
not enforcement; that failure mode was observed four separate times in one
session. Here it is institutionalised across 28k lines.

BUILD THE GATE. Two rules, both needing must-fire AND must-stay-quiet fixtures:
  1. Refuse a contiguous comment block over N lines that cites a ticket id.
     Choose N from the measured distribution and JUSTIFY it; do not pick 50
     because this ticket's title says so. Start at ERROR only if the burn-down
     is achievable, otherwise WARN with a promotion ticket (the repo's usual
     ladder).
  2. Refuse ticket ids in docs/modules/** outside a designated provenance
     section.

MUST STAY QUIET (each needs a fixture -- a guard shipped without one is how
three misfiring rules reached this repo):
  - `frob:` DSL directives of every verb, at any length. These are the
    enforcement surface, not narrative.
  - changelog.d/, CHANGELOG.md, docs/decisions/, and tickets/** -- provenance
    is the POINT in those.
  - A short attribution like `# T-1234: keep the sort stable` where the id is
    genuinely the shortest way to say why a line exists.

MIGRATION IS PART OF THIS, NOT A FOLLOW-UP. A gate that fires 96 times on day
one and gets waived away is worse than no gate -- this repo already carries 2,192
`frob:waive` directives against 93 `frob:debt`, a 23.6:1 ratio that is getting
worse, and a noisy new rule feeds exactly that. Move the narrative into the
CITED TICKET's body before or with the gate. If the cited ticket is archived,
say what you did instead.

ACCEPTANCE
- The placement rule stated in docs/ as the project's convention.
- Both gate rules implemented with must-fire and must-stay-quiet fixtures each.
- The 96 very-long code blocks migrated into their cited tickets, or an explicit
  count of any that could not be, with reasons.
- Before/after counts for both surfaces, measured the same way as above.
- No net loss of knowledge: every migrated block is reachable from the code site
  by a short pointer to the ticket id.

## Drop reason
- 2026-08-28: duplicate of the T-2994 placement-rule epic tree, filed independently of it; reconciled per coordinator instruction. T-2987 (waiver-reason cap) and T-2988 (docstring standard) already cover two of T-3189's angles under T-2994; T-3022 covers the docs-narrative bulk migration (was also duplicated as T-3023, dropped separately). The one genuinely missing piece -- the ENFORCEMENT GATE itself -- is filed as T-3218 (parented under T-2994), carrying forward both T-3189's measurements (28,273 lines in 4+ line ticket-citing code comment blocks, 96 blocks 26+ lines, worst 130 at src/frob/vet/_capability_typescript_bindtable.py:18; 6,283 ticket-id mentions across 143/152 docs files, worst docs/modules/gates.md at 884) and T-2987's finding that frob:waive reason prose is itself narrative bloat and should NOT be blanket-exempt the way T-3189 originally proposed for all frob: directives -- T-3218 narrows the exemption to frob:ticket/frob:tests/frob:doc only, per T-2987.

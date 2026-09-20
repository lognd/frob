---
id: T-4808
title: 'docs/modules size lint: a per-symbol section over N lines is a finding, so
  relocated prose cannot pile up at the destination'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: T-4691
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
- docs/modules/docstrings.md
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: correct a forward reference written before the sweep leaf had an id
  actor: logan
  at: '2026-09-19'
  old_length: 2467
  new_length: 2700
- mode: append
  reason: correct a forward reference written before the sweep leaf had an id
  actor: logan
  at: '2026-09-19'
  old_length: 2700
  new_length: 2933
- mode: append
  reason: correct a forward reference written before the sweep leaf had an id
  actor: logan
  at: '2026-09-19'
  old_length: 2933
  new_length: 3166
- mode: append
  reason: correct a forward reference written before the sweep leaf had an id
  actor: logan
  at: '2026-09-19'
  old_length: 3166
  new_length: 3399
- mode: append
  reason: correct a forward reference written before the sweep leaf had an id
  actor: logan
  at: '2026-09-19'
  old_length: 3399
  new_length: 3632
- mode: append
  reason: correct a forward reference written before the sweep leaf had an id
  actor: logan
  at: '2026-09-19'
  old_length: 3632
  new_length: 3865
designated_repro_test: null
acceptance:
- text: given a fixture docs/modules/x.md with a section of N+5 lines and one of N-5
    lines, when the lint runs, then only the first is flagged
  evidence: []
- text: given frob.toml [gates.docs] raises N, when the lint runs over the same fixture,
    then the first section is quiet -- proving the config path, not just the default
  evidence: []
- text: given todays docs/modules content, when this leaf closes, then the measured
    distribution of section lengths is recorded in the ticket and N is chosen from
    it, not from intuition
  evidence: []
- text: given the lint ships, when a new over-cap section is added, then frob check
    fails on the increase (baselined into frob pool, same posture as DOCARCH002)
  evidence: []
- text: given docs/modules/docstrings.md, when this lands, then it states that the
    Tier-A fix RELOCATES and agents CONDENSE in review rather than authoring moves
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner's decision alongside the docstring automation: the relocated prose must not
simply pile up at the destination. T-4807's fix moves up to 38,964 lines of
docstring remainder into `docs/modules/*.md`. Without a cap there, T-2994's
cleanup is a RELOCATION rather than a reduction -- the same bloat, one directory
over, now unread because nothing gates it.

THIS IS THE DESTINATION-SIDE HALF OF THE SAME RATCHET. DOCARCH002 (T-4693) caps
the source side (comment runs > 12, docstrings > 20). This leaf caps the docs
side, so prose cannot escape one cap by moving under the other.

THE RULE: a per-symbol section in `docs/modules/*.md` running longer than N lines
is a finding. N is config in `frob.toml [gates.docs]` alongside
`comment_run_max` and `docstring_max`, same table, same precedent. Structural,
not lexical: the section boundary is a heading in the parsed markdown, and the
measure is its line count. No wording test -- same standing directive
(token/grammar, never lexical) that shaped T-4693.

REMEDY TEXT must point at CONDENSATION, not at another move. The failure mode
this lint exists to catch is prose being shuffled a third time instead of edited
down.

MEASURE THE BASELINE BEFORE CHOOSING N. `docs/modules/` already has content that
predates any of this; T-2994 measured docs .md at 30,959 lines citing a T-id, 44%
of all 69,736 doc lines. Pick N from the measured distribution of today's section
lengths, not from intuition, and record that distribution in this ticket. A cap
that flags 80% of existing sections on day one is a cap nobody can adopt; a cap
above the largest relocated section catches nothing. Baseline into `frob pool`
and fail on increase, exactly as T-4693 does.

CONDENSATION IS A REVIEW STEP, NOT AN AUTHORING STEP (owner's note, recorded here
because this lint is the thing that makes it enforceable): the Tier-A fix
RELOCATES prose mechanically; agents CONDENSE the relocated prose when they review
the diff -- they do not hand-author the moves. This lint is what turns "condense
in review" from a good intention into a gate finding when it does not happen.
Document that division in `docs/modules/docstrings.md` so the next agent reads it
before running the repo-wide sweep (T-4808).

POSITIVE CONTROL: a fixture `docs/modules/x.md` with one section of N+5 lines and
one of N-5 lines -- the first is flagged, the second is not; raising N in
frob.toml silences the first, proving the config path and not just the default.


CORRECTION to the last paragraph above: the repo-wide sweep leaf is T-4810, not
T-4808 (T-4808 is this ticket). The ids were assigned in the same planning pass
and the forward reference was written before the sweep leaf was filed.


CORRECTION to the last paragraph above: the repo-wide sweep leaf is T-4810, not
T-4808 (T-4808 is this ticket). The ids were assigned in the same planning pass
and the forward reference was written before the sweep leaf was filed.


CORRECTION to the last paragraph above: the repo-wide sweep leaf is T-4810, not
T-4808 (T-4808 is this ticket). The ids were assigned in the same planning pass
and the forward reference was written before the sweep leaf was filed.


CORRECTION to the last paragraph above: the repo-wide sweep leaf is T-4810, not
T-4808 (T-4808 is this ticket). The ids were assigned in the same planning pass
and the forward reference was written before the sweep leaf was filed.


CORRECTION to the last paragraph above: the repo-wide sweep leaf is T-4810, not
T-4808 (T-4808 is this ticket). The ids were assigned in the same planning pass
and the forward reference was written before the sweep leaf was filed.


CORRECTION to the last paragraph above: the repo-wide sweep leaf is T-4810, not
T-4808 (T-4808 is this ticket). The ids were assigned in the same planning pass
and the forward reference was written before the sweep leaf was filed.

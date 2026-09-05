---
id: T-3853
title: 'enforce the V-model from the get-go: scaffold both arms plus design/vmodel.strata,
  generate rather than hand-author, promote VMOD001 to error'
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
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
OWNER QUESTION 2026-09-05: "How do we actually enforce vmod from the get-go? I
kind of like what ../logand.app-v2 did with its docs/; is that kind-of
enforced?"

ANSWER, MEASURED. Yes, it is enforced -- but only because that repo BUILT the
enforceable artifact by hand, and only at WARN. A repo that merely adopts the
docs layout gets nothing.

WHAT logand.app-v2 ACTUALLY HAS (read-only inspection, 2026-09-05):

    docs/spec/L1-requirements.md              docs/spec/L1-customer-tests.md
    docs/spec/L2-requirement-specification.md docs/spec/L2-customer-test-plan.md
    docs/spec/L3-system-specification.md      docs/spec/L3-system-integration-test-plan.md
    docs/spec/L4-system-design.md             docs/spec/L4-subsystem-integration-test-plans.md
    (L5 = implementation/unit)

    design/vmodel.strata      <- the declarations VMOD001 actually reads
    scripts/vmodel_gen.py     <- a GENERATOR they had to write themselves
    tests/unit/test_vmodel_gen.py

The docs layout alone is inert. `design/vmodel.strata` is the enforceable
artifact: `vmodel_node`/`vmodel_edge` statements that VMOD001 aggregates across
every .strata file and runs `vmodel_check` against for structural closure.
That they ALSO wrote `vmodel_gen.py` is the tell -- hand-authoring the graph
alongside the docs was not sustainable, so they generated it.

TWO REASONS IT IS NOT ENFORCED "FROM THE GET-GO" TODAY:

1. VMOD001 IS OPT-IN BY EXISTENCE. From src/frob/gates/_vmodel.py's own
   docstring: "a repo with no design dir, or a design dir with zero vmodel
   declarations, sees NOTHING from this gate". That posture was right when
   nothing could author a graph. It means a fresh repo is silent by default and
   stays silent until someone hand-builds what logand.app-v2 built.

2. IT IS WARN-ONLY. Same docstring: "every VMOD001 finding is WARN, not ERROR
   (owner's explicit instruction, T-3042's ticket body)", with the reasoning
   that shipping at ERROR against a repo with zero requirements would be waived
   en masse. The owner has now reversed that instruction. Verified the
   mechanism: _vmodel.py hardcodes Severity.WARN at lines 220/233, but
   `_apply_severity_overrides(kept, cfg.root)` runs over all kept violations at
   gates/__init__.py:8696, so frob.toml's `[gates.severity]` DOES reach it.
   Promotion works; see T-3844.

WHAT TO BUILD -- scaffold the enforceable artifact, not just the docs.

  a. The scaffold ships the L1-L5 spec skeleton (both arms of the V: each
     specification level paired with its verification level) with the docs as
     stubs, not prose.
  b. The scaffold ships a `design/vmodel.strata` declaring the corresponding
     vmodel_node/vmodel_edge set, so VMOD001 has a graph to check on day one.
  c. GENERATION, NOT HAND-AUTHORING. logand.app-v2 wrote vmodel_gen.py because
     keeping declarations in step with docs by hand does not hold. Decide
     whether frob should own that generation as a verb (`frob vmodel sync`, or
     an extension of an existing verb) rather than leaving every consumer repo
     to write its own script. Read scripts/vmodel_gen.py first (READ-ONLY --
     ../logand.app-v2 is not ours to modify) and report what it does; if the
     answer is "each repo's mapping is too bespoke to generalize", say that and
     ship a documented template instead. Do not assume either way.
  d. VMOD001 promoted to error for scaffolded repos. This is now safe FOR
     SCAFFOLDED REPOS because (a)+(b) mean the graph exists and closes from the
     first commit -- the "waived en masse" objection was about bolting the gate
     onto a repo with zero requirements, which is a different situation.

THE PREREQUISITE, AND IT IS WHY THE PLANNING CARVE-OUT MATTERS. A design-first
repo NAMES ARTIFACTS BEFORE THEY EXIST -- that is what design-first means. L1
requirements reference a component nobody has written yet. Today that fires
DOC006 (unresolvable pointer) and SYS101 (declared-never-observed capability),
so a correctly-authored day-one V-model repo is RED IMMEDIATELY on rules that
are working exactly as designed. See T-3829, T-3821, T-3317, and the logand.app-v2
F-016/F-024 family.

So the planned-artifact marker is not a concession to sloppiness -- it is a
PRECONDITION for enforcing the V-model from day one. Without it, "enforce vmod
from the get-go" and "keep the pointer gates strict" cannot both hold, and the
repo learns to waive. Sequence this ticket AFTER a planned marker exists, or
carry the marker as part of it and say so.

SCOPE NOTE: this is scaffold + gate posture. It does NOT include building frob
its own V-model graph -- frob has none today ("frob has no V-model graph of its
own yet"), and whether frob should eat this particular dogfood is a separate
decision worth its own ticket.

MUST-FIRE FIXTURES:
  - a scaffolded repo whose vmodel graph does NOT close fails VMOD001 as an error
  - a spec level with no paired verification level is flagged
MUST-STAY-QUIET FIXTURES:
  - a freshly scaffolded repo, untouched, passes clean (this is the one that
    decides whether the feature is usable at all -- a scaffold that is red on
    creation gets deleted, not adopted)
  - a repo that opts OUT (no design dir) still sees nothing from VMOD001

ACCEPTANCE
- Scaffold ships both arms of the V plus design/vmodel.strata.
- The generation-vs-template decision made, after reading logand.app-v2's
  generator, with reasoning.
- VMOD001 promoted to error for scaffolded repos, with the day-one-clean
  fixture proving it.
- The planned-marker dependency stated and sequenced, not discovered later.

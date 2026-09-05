---
id: T-3902
title: SCOPE002=error makes docs/modules/gates.md unaddable to any ticket scope (3143-warning
  closure explosion)
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: four independent sightings today (FA, FI, FE, consumer); records the ratchet
    interaction that made it blocking and the three agent workarounds it caused
  actor: logan
  at: '2026-09-05'
  old_length: 2990
  new_length: 6051
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
Found while working T-3315 (frob ticket sweep refuses on a done ticket).
frob.toml:690 sets `SCOPE002 = "error"` (promoted from the rule's own
documented WARN default, src/frob/gates/__init__.py::_scope002_violation's
docstring still says "WARN turn-on"). SCOPE002 (T-0998) fires per SYMBOL
declared in a ticket's scope whose own frob:doc/frob:tests/private-helper
edges point outside that scope -- so it fires for EVERY symbol in a
file, not just the ones a given diff actually touches.

`src/frob/app/ticket_runner/_lifecycle.py` (a large, multi-command
module: plan/start/requeue/sweep/reconcile/attach/block) has one function,
`_warn_scope_breadth_on_start`, whose `frob:doc` anchor points at
`docs/modules/gates.md` -- the repo's own giant shared gates design doc.
Adding `docs/modules/gates.md` to ANY ticket's scope (to close that one
edge) pulls in that doc's own closure requirements: MEASURED during
T-3315, `frob ticket scope T-3315 --add docs/modules/gates.md` alone
produced 3143 additional scope-closure warnings (`consider --add ...`)
naming dozens of unrelated gates/*.py source files, each themselves
pulling in more docs/tests transitively.

Net effect: SCOPE002=error + `_lifecycle.py` (or any other file whose
frob:doc anchor touches docs/modules/gates.md) makes that file
effectively unscopable without an unbounded scope-widening cascade -- a
ticket doing a genuinely small, single-function fix cannot reach a clean
`frob check --ticket` without either (a) widening scope to an
unreasonable fraction of the whole gates subsystem, or (b) leaving
SCOPE002 as an unresolved error and accepting a red ticket-scoped check.

T-3315 worked around this by reverting to a minimal, sane scope
(`_verify.py` + `_lifecycle.py` + its own test file) and leaving the
`_warn_scope_breadth_on_start` -> `docs/modules/gates.md` SCOPE002 finding
unresolved rather than chasing the cascade -- filed here instead of
silently widening or silently ignoring it.

## Plan
- Confirm whether SCOPE002's promotion to error (frob.toml:690) was
  measured clean against a representative sample of tickets BEFORE
  promotion, per the T-0756 promotion playbook
  (docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756) -- this
  finding suggests it was not measured against a large multi-purpose
  module referencing the shared gates design doc.
- Consider: (a) demoting SCOPE002 back to warn until closure-cascade
  cases like this one are addressed, (b) capping SCOPE002's own closure
  walk so a single doc target this large/shared is exempted (a doc this
  broadly cited is closer to "always in scope" than "needs an explicit
  add" -- similar to how the ledger/tickets/<id>/ shard are already
  always-in-scope exemptions elsewhere in this codebase), or (c) leaving
  error severity but adding a documented, first-class escape hatch (a
  `frob ticket scope --scope002-ack` parallel to `scope_breadth_ack`)
  for exactly this "the doc is too broadly shared to close" shape.



FOUR INDEPENDENT SIGHTINGS, 2026-09-05. Three from frob's own agents, one from a
consumer. This is now the best-corroborated open defect in the queue.

  Series FA (this ticket's filing)  adding ONE shared doc to a ticket's scope
      produced 3143 additional closure warnings; src/frob/app/_lifecycle.py is
      effectively UNSCOPABLE because of its doc edge into the shared
      docs/modules/gates.md.
  Series FI (T-3903)  dropped version_coupling_gate's frob:doc edge into
      docs/guides/release.md rather than widen scope: that doc's other anchors
      pulled in scripts/artifact_smoke.py, scripts/verify_release_ci_status.py
      and src/frob/doctor.py. MEASURED: error count went 5 -> 12 when tried.
      It waived the resulting COV001 against an existing precedent instead.
  Series FE (T-3857/T-3884/T-3886)  reported the same shape hitting all three
      of its tickets: "SCOPE002's doc-anchor closure explodes to hundreds of
      unrelated files whenever a hub doc enters a ticket's scope"
      (docs/guides/release.md, design/frob.strata,
      docs/modules/tickets-verify-sweep.md named).
  logand.app-v2 F-101 (the SECOND finding they numbered F-101 -- their file has
      two, the other is about `frob ticket block --by`; cite by title, not
      number)  declaring a shared L5 doc in scope pulls ~15 unrelated files in
      through the doc-closure rule.

THE PATTERN IS CONSISTENT ACROSS ALL FOUR: a HUB DOC -- one that many symbols
anchor into -- makes scope closure transitive across everything else that
touches it. The cost is not proportional to the change; it is proportional to
how popular the doc is.

THIS INTERACTS DIRECTLY WITH TODAY'S SEVERITY RATCHET, and that interaction is
why it now blocks work rather than merely warning. T-3844 promoted SCOPE002 to
"error" (verified at frob.toml:690) because it measured ZERO at rest. It
measures zero at rest and fires during a scope CHANGE -- the category-(b)
"condition has never arisen" case recorded against the ratchet. So the
promotion converted a noisy warning into a blocking error precisely for the
operation people perform most often when doing real work.

CONSEQUENCE ALREADY OBSERVED, worth stating because it is the real damage: THREE
SEPARATE AGENTS WORKED AROUND IT RATHER THAN THROUGH IT. FI dropped a legitimate
doc edge; FE accepted the fan-in as documented debt; FA left findings
unresolved. Each choice was locally correct and each one degraded the doc-edge
graph slightly. A rule that is routinely worked around is training people to
weaken the thing it protects.

WHEN FIXING, ANSWER THIS FIRST: is transitive doc closure the intended
semantics, or an over-application? Scope exists to say which files a ticket may
WRITE. A doc anchor is a READ relationship -- "this symbol is described there"
-- and it is not obvious that needing to read a doc should require a write
lease on everything else described in it. That framing may collapse the whole
problem, and it is the same evidence-coverage-versus-write-lease conflation
recorded in F-060 and F-085.

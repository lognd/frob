---
id: T-3411
title: 'Owner decision needed: collapse the last 2 CYCLE001 SCCs (frob.graph<->.lock,
  frob.app.telemetry)'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/__init__.py
- src/frob/graph/lock.py
- src/frob/app/telemetry/__init__.py
- src/frob/app/telemetry/_footguns.py
- src/frob/app/telemetry/_usage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 in CI run 33298117154: the backticked proposed module path frob.app.telemetry._state
    was read as a symbol pointer; reworded to prose so the live-repo DOC004/DOC006
    test stays zero'
  actor: logan
  at: '2026-08-30'
  old_length: 3823
  new_length: 3840
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3350 fixed CYCLE001's own detector bug (import-time vs deferred edges
were conflated) and mechanically collapsed 4 of the 6 small real cycles
correct counting exposed. Two remain, and both are a genuine mutual
dependency an earlier, deliberate design choice already worked around via
import ORDERING rather than avoided -- collapsing either means overriding
that prior choice, not a mechanical import-line rewrite. Per the repo
owner's explicit standing instruction ("if that decision is not obvious,
stop and tell me rather than guessing; I would rather own that call than
have it made implicitly"), both are reported here rather than guessed at.

1. `frob.graph` <-> `frob.graph.lock` (2 nodes): `lock.py` needs
   `resolve()` (frob/graph/__init__.py:791), which `frob.graph.__init__`
   defines directly and keeps WITH its build-graph pipeline
   (`load_graph`/`edges_from`/`edges_to`) under an EXISTING
   ARCH102/LARGE001 cohesion waiver at the top of that file ("one
   build-graph pipeline plus its three query accessors, coupled by the
   shared GraphSnapshot model"). `frob.graph.lock` is imported back into
   `__init__.py` at the BOTTOM of the file (T-0362, `# frob.graph.lock
   imports resolve back from this package, so it must be imported only
   after resolve is defined above`), a documented, deliberate ordering
   workaround for exactly this mutual dependency.

   Candidate fixes an owner could pick between:
   a. Move `resolve` (and its two callers inside lock.py) into
      `frob.graph._models` (already imported by both files, holds
      GraphSnapshot/SymbolRecord/GraphError) or a new leaf module, and
      re-export it from `__init__.py` for its own public surface. This
      narrows the ARCH102/LARGE001 waiver's stated boundary (resolve
      would no longer live with edges_from/edges_to) -- reasonable, but
      contradicts that waiver's own cohesion argument until it is
      re-worded.
   b. Have `lock.py` re-derive what it needs from `GraphSnapshot`
      directly instead of calling the shared `resolve()` -- avoids
      moving code, but risks exactly the kind of accidental logic
      duplication (T-0402's ambiguous-match resolution rules) this
      repo's NO-DUPLICATION principle exists to prevent.
   c. Leave the waiver and T-0362 ordering workaround as-is (status quo
      -- this is a real but tiny, easily-explained SCC, and the ordering
      trick works).

2. `frob.app.telemetry` <-> `frob.app.telemetry._footguns` <->
   `frob.app.telemetry._usage` (3 nodes): both submodules need
   `is_disabled`/`_telemetry_path` (`_footguns` also needs
   `_home_config_state_hash`/`_external_path_arg_hash`), all four
   defined directly in `frob/app/telemetry/__init__.py`. `__init__.py`
   imports `_footguns`/`_usage` at the BOTTOM of the file, after those
   four are defined (T-2694, `# imported at the BOTTOM, after every
   event-recording name above is defined`), the same deliberate
   ordering-workaround shape as (1).

   Candidate fixes:
   a. Extract the four functions (is_disabled ~5 lines, _telemetry_path
      ~2 lines, both trivial; _home_config_state_hash and
      _external_path_arg_hash are larger, with their own private helpers
      like _walk_home_claude_entries) into a new leaf module
      (a `_state` leaf under the telemetry package?) both `__init__.py` and the two
      submodules import from -- collapses the SCC cleanly but is a
      bigger move than (1)'s.
   b. Leave the T-2694 ordering workaround as-is (status quo).

Either way, once a direction is picked for both, remove the
`frob:debt CYCLE001` block at src/frob/__init__.py (currently pointed at
this ticket's id via `ticket=`) -- T-3350's own investigation already
narrowed it down to exactly these two SCCs, so no further re-measurement
should be needed before landing whichever fix is chosen.

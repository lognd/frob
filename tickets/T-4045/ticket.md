---
id: T-4045
title: 'F-245: the vitest collect cache is never refreshed (error path skips the write;
  an empty result caches as legitimate), forcing ~15 tickets onto cmd: evidence'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_ts.py
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
Consumer logand.app-v2 F-245, 2026-09-06, MEASURED by their T-0213:

  ".frob/vitest-collect.json is never rebuilt by `frob test`, `frob test
   --collect` or `frob check`. The python-only collector paths refresh; the
   vitest cache stays stale or empty, so every vitest-backed ticket in this repo
   (about 15 so far) binds `cmd:` evidence and then trips COV003."

FIFTEEN TICKETS FORCED ONTO cmd: EVIDENCE, THEN PENALISED FOR IT. That is the
cost. They cannot bind real node ids because the cache the binder consults is
empty or stale, so they fall back to `--evidence-cmd` -- and COV003 then fires on
the result. Note this compounds with T-4000 (a cmd: entry recording an
empty-output no-op as genuine evidence) and T-4017 (close calling a cmd:-bound
criterion unbound when the command contains a comma): the fallback channel they
were pushed into is itself the least reliable one.

I READ THE COLLECTOR RATHER THAN GUESSING. `collect_ts_tests` in
src/frob/testing/_collect_ts.py:205 DOES write the cache -- `_store_cache` at
:230 -- so this is not a missing write. There are two paths that reach the end of
a run without a fresh write, and I did NOT determine which one they hit:

  CANDIDATE 1 -- AN ERROR SKIPS THE WRITE ENTIRELY. At :223-224:
        listed = _run_vitest_list(project_dir)
        if listed.is_err:
            return Err(listed.danger_err)
    An early return before `_store_cache`. If vitest listing fails for ANY
    project, nothing is written and whatever the cache already held survives --
    "stays stale", exactly as reported.

  CANDIDATE 2 -- AN EMPTY RESULT IS CACHED AS A LEGITIMATE ONE. If
    `_find_vitest_projects(root)` discovers no projects, the loop body never
    runs, `frozen` is the empty frozenset, and `_store_cache` writes it. Every
    subsequent call then takes the `cached is not None` branch at :217 and
    returns a CACHE HIT OF ZERO NODE IDS. That is a silent zero in its textbook
    form: "no vitest projects found" and "this project has no tests" are stored
    identically and are indistinguishable to every consumer thereafter.
    Their phrase "stays ... empty" fits this exactly.

DETERMINE WHICH BEFORE FIXING -- the remedies differ. Candidate 1 needs the write
to happen (or the error to be surfaced) on the failure path; candidate 2 needs
zero-discovered-projects to be distinguishable from zero-tests, which is
T-3985's subject-count primitive applied to a collector. Both may be true.

THE CONSUMER'S OWN PROPOSED FIX -- "the vitest runner in frob.toml needs a
collect step that writes that file" -- is worth checking against candidate 2: if
project discovery is the failing step, a configured collect step fixes it; if it
is candidate 1, a collect step that errors silently reproduces the same problem
one layer out.

RELATED, AND DISTINCT -- DO NOT MERGE:
  - T-4016 (the TS walker emits no symbol for describe()/it()) is the root cause
    of F-172/F-219/F-225. That is about the SYMBOL side of the binding edge.
    This ticket is about the COLLECTED-ID side. Both must work for a vitest
    binding to resolve; fixing either alone leaves TS evidence unusable.
  - I earlier recorded a cache hypothesis on T-4003 and then SUPERSEDED it when
    T-4016 was found. This finding does not revive that hypothesis -- T-4003's
    symptom is explained by the walker. It does show a genuine and separate
    cache defect. Two different caches-adjacent problems; keep them apart.

MUST-FIRE FIXTURE: a repo with a real vitest project has .frob/vitest-collect.json
written with its node ids after a collection run.
MUST-STAY-QUIET: a repo with no TS at all does not error and does not warn about
a missing node toolchain.
THIRD FIXTURE: zero-discovered-projects is distinguishable from
zero-tests-in-a-discovered-project, in the cache and in what callers see.
FOURTH FIXTURE: a vitest listing failure surfaces as an error rather than
silently leaving a stale cache in place.

ACCEPTANCE
- Which candidate (or both) is responsible, established by measurement.
- The empty/absent distinction made explicit, cross-referenced to T-3985.
- All four fixtures committed.
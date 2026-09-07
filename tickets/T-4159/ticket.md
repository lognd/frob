---
id: T-4159
title: 'the gate cache is measurably corrupt in this checkout and a consumer reports
  it serving a stale finding across clean runs: correctness surface, not a performance
  cache'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
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
acceptance:
- text: given a file whose content changed after a finding was cached for it, when
    the gate runs, then the new result is produced rather than the cached one
  evidence: []
- text: given an unchanged file, when the gate runs, then it is still served from
    cache
  evidence: []
- text: given a corrupted cache database, when the tool opens it, then it is detected
    and rebuilt rather than read, and the run says so
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THIS REPOSITORY'S GATE CACHE IS MEASURABLY CORRUPT, and a consumer independently
reports the cache serving a stale finding that only a manual database deletion
cleared. Those may be one defect or two; this ticket exists to determine which
before either is "fixed".

WHAT I MEASURED HERE, 2026-09-07, on a copy taken to avoid the live lock:

    PRAGMA integrity_check  ->  *** in database main ***
                                Freelist: size is 2 but should be 5

That is a real structural inconsistency, not lock contention. It corroborates
something I had been observing all session and deliberately refusing to call
corruption without this check: five separate ticket-filing runs emitted

    cache: store_file_data(tests/test_dup_prefilter.py) hit a stale/corrupt
    connection, reopening ... and retrying (attempt 1/3): database disk image
    is malformed

always on the same file, always auto-retrying, always followed by
"build_graph: cache lock never released: database is locked". I could not run the
integrity check earlier because live agents held the database; the copy-then-check
approach is what finally answered it.

THE CONSUMER REPORT (logand.app-v2 F-359): after fixing a tree-sitter parse trap,
`frob check` kept reporting the SAME parse finding across several runs although
the file parsed clean under the same grammar. Only deleting the cache databases
cleared it. Their diagnosis: the cache key must include the file's content hash,
or a tree hash must invalidate parse artifacts. Their closing line is the right
severity judgement -- A STALE PARSE FINDING IS WORSE THAN NO CACHE.

DO NOT ASSUME THESE ARE THE SAME BUG. They are two candidate mechanisms with
different fixes, and treating them as one is how the wrong thing gets fixed:
  (a) STRUCTURAL CORRUPTION -- a damaged database returning wrong rows. My
      measurement is evidence this occurs here. It would explain arbitrary stale
      results, but it does not explain a stale result being REPRODUCIBLE across
      several clean runs, which is what they describe.
  (b) A KEYING DEFECT -- the cache key not covering file content, so a fixed file
      still hits the entry recorded for the broken one. That WOULD reproduce
      exactly as they describe, on a perfectly healthy database.
Their symptom fits (b) better than (a). My measurement is (a). Establish both
independently rather than letting one explain the other away.

WHY THIS MATTERS MORE THAN A PERFORMANCE CACHE USUALLY WOULD. A gate cache that
can serve a stale FINDING is not a performance optimisation, it is a correctness
surface: it can report a violation that no longer exists, and by the same
mechanism it can withhold one that now does. The second direction is the
dangerous one and nobody would notice it -- this is the silent-zero shape with a
persistence layer attached. Whatever else is done, the cache must be unable to
answer a question about a file whose content it has not seen.

WHAT TO DO
  1. Determine what the cache key actually covers today, and report it. If file
     content is not part of it, that is the finding and (b) is confirmed.
  2. Add an integrity check the tool runs on its own behalf. A corrupt cache
     should be detected and rebuilt automatically, not diagnosed by hand by
     whoever happens to notice. The auto-retry already present proves the code
     can see the symptom; it currently retries and gives up rather than
     rebuilding.
  3. Decide what happens when the cache cannot be trusted. Rebuilding silently is
     acceptable; SERVING A POSSIBLY-STALE ANSWER IS NOT. Prefer a slow correct
     run over a fast wrong one, and say which was chosen in the output.
  4. Investigate why the corruption arises at all. This repo runs many concurrent
     checks against one cache and has measured up to seven at once; concurrent
     writers are the obvious suspect and the repeated single-file symptom is a
     clue worth following.

OPERATIONAL NOTE, NOT PART OF THE FIX: this checkout's cache should be rebuilt.
I have NOT done it, because agents are live and the database is shared -- deleting
it under a running check is exactly the kind of shared-root action that has broken
this fleet before. Do it in a quiet window, and record whether the corruption
returns afterwards, because a corruption that comes back is a much more
interesting finding than one that does not.

MUST-FIRE FIXTURE:   a file whose content changed after a finding was cached
                     produces the NEW result, not the cached one.
MUST-STAY-QUIET:     an unchanged file is still served from cache -- the fix must
                     not disable caching to achieve correctness.
THIRD FIXTURE:       a deliberately corrupted cache database is detected and
                     rebuilt rather than read, and the run reports that it did so.

ACCEPTANCE
- The cache key's actual coverage measured and reported.
- Structural corruption and stale-keying established independently.
- A corrupt or untrustworthy cache is rebuilt rather than served.
- The concurrency question investigated, with findings recorded either way.
- All three fixtures committed.

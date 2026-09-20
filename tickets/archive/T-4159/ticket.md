---
id: T-4159
title: 'the gate cache is measurably corrupt in this checkout and a consumer reports
  it serving a stale finding across clean runs: correctness surface, not a performance
  cache'
state: done
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
scope:
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/cache.py
  reason: 'T-4159: the gate cache implementation this ticket investigates for corruption/keying'
  actor: logan
  at: '2026-09-09'
body_changes:
- mode: set
  reason: 'records the quiet-window rebuild and the measurement that narrows the cause:
    of five databases under the frob state directory only cache.db was corrupt, which
    argues against a storage fault and points at the concurrent store_file_data write
    path named in every warning. Notes the rebuild is automatic and cheap, and that
    recurrence under load is the signal that confirms the writer-coordination defect'
  actor: logan
  at: '2026-09-07'
  old_length: 5139
  new_length: 7354
evidence:
- tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_integrity_check_reports_corrupt
- tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption
- tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_healthy_cache_never_triggers_a_rebuild
- tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_corrupt_cache_self_heals
designated_repro_test: null
acceptance:
- text: given a file whose content changed after a finding was cached for it, when
    the gate runs, then the new result is produced rather than the cached one
  evidence:
  - tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption
- text: given an unchanged file, when the gate runs, then it is still served from
    cache
  evidence:
  - tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_healthy_cache_never_triggers_a_rebuild
- text: given a corrupted cache database, when the tool opens it, then it is detected
    and rebuilt rather than read, and the run says so
  evidence:
  - tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_integrity_check_reports_corrupt
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

REBUILT IN A QUIET WINDOW, 2026-09-07, AND THE RESULT NARROWS THE CAUSE.
Conditions: zero lands in flight, zero agents, zero concurrent checks, load 4.3.
A forensic copy of the corrupt database is preserved before deletion.

THE DECISIVE MEASUREMENT IS WHICH DATABASES WERE AFFECTED. Before deleting
anything I ran an integrity check over EVERY database under the frob state
directory:

    .frob/cache.db              CORRUPT  (Freelist: size is 2 but should be 5)
    .frob/gate-cache.db         ok
    .frob/parse-artifacts.db    ok
    .frob/dup.db                ok
    .frob/hotgraph_sketches.db  ok

ONE OF FIVE. That argues strongly AGAINST a general disk, filesystem or WSL
storage fault -- those would not spare four neighbouring databases, one of them
249MB. It points at something specific to this database's access pattern.

AND THE ACCESS PATTERN IS THE ONE THING THAT STANDS OUT. Every corruption warning
observed this session named the same function: `store_file_data`, the write path
this database receives from every concurrent `frob check`. This session measured
up to SEVEN concurrent checks against it. The other four databases are written by
narrower paths.

So the concurrency hypothesis in the section above is now the leading one, and the
investigation has a specific target rather than a general one: how
`store_file_data`'s writers coordinate, and whether the journal mode, busy timeout
and connection lifecycle are correct for N concurrent writer processes rather than
N threads.

AFTER DELETION, a rebuild happened automatically on the next verb that needed the
graph, produced a 10.7MB database (down from 23.3MB), and that rebuild passes
integrity_check. So recovery is cheap and needs no special tooling -- which makes
the automatic detect-and-rebuild proposed above cheaper than it might have looked.

WATCH FOR RECURRENCE, and treat it as the real signal. A corruption that does not
come back was a one-off event worth noting and closing. A corruption that returns
under concurrent load confirms the writer-coordination defect and is the finding
that matters. Re-run the same five-database integrity sweep after the next heavy
fleet session and record the result here either way.
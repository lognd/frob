---
id: T-3895
title: the native and pure-Python parser backends disagree on the same C file, so
  gate results depend on which machine ran them
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/**
- tests/test_lang.py
- tests/fixtures/lang/**
- docs/modules/lang.md
- docs/guides/install.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/**
  reason: PARSE002 divergence lives in frob.lang's parse/PARSE002 path; differential
    test and fixtures land alongside it, T-0133 parity statement in docs/modules/lang.md
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_lang.py
  reason: PARSE002 divergence lives in frob.lang's parse/PARSE002 path; differential
    test and fixtures land alongside it, T-0133 parity statement in docs/modules/lang.md
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/fixtures/lang/**
  reason: PARSE002 divergence lives in frob.lang's parse/PARSE002 path; differential
    test and fixtures land alongside it, T-0133 parity statement in docs/modules/lang.md
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/lang.md
  reason: PARSE002 divergence lives in frob.lang's parse/PARSE002 path; differential
    test and fixtures land alongside it, T-0133 parity statement in docs/modules/lang.md
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/install.md
  reason: T-0133 honest-degrade parity statement lives here
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as stpone FROBLEMS F-021. Two parser backends produce DIFFERENT parse
results for the same file, so a repo's gate outcome depends on which machine ran
it.

MEASURED BY THE REPORTER:

    with native extensions (their local tool):
        src/stpalpha/hal/setup.c parses fully; a PARSE002 waiver on that file
        reports WAIVE004 "matches 0 findings"
    without natives (CI, `uv tool install "frob @ git+..."`):
        PARSE002 fires on the same file

Their conclusion is exact: "One waiver cannot satisfy both without a spurious
warning on one side."

THE WAIVER COMPLAINT IS THE SYMPTOM. The defect is that ONE FILE HAS TWO PARSE
RESULTS. Everything downstream of the parse -- findings, waivers, the symbol
graph, coverage attribution, doc anchors -- inherits that divergence. A waiver
that is live on one backend and dead on the other is just the first place it
became visible.

WHY THIS IS RELEASE-RELEVANT RIGHT NOW, and why it should be settled before the
alpha rather than after. T-3845 makes `frob-core`/`strata-core` DEFAULT
dependencies instead of an optional extra. That flips which backend most users
get. Today the population splits by who bothered to install the natives;
afterwards nearly everyone lands on the native path. If the two backends
disagree, that packaging change silently changes gate RESULTS for every existing
consumer -- a behaviour change smuggled inside a dependency change, which is
exactly the kind of thing a release note cannot repair after the fact.

IT ALSO WEAKENS THE T-0133 GUARANTEE. The documented posture is that the natives
degrade HONESTLY: a clear Err, never a crash, when absent. That promise is about
availability. It does not cover CORRECTNESS divergence -- "the pure-Python path
gives a different answer" is not honest degradation, it is two implementations
of one contract disagreeing. Whichever way this is fixed, the honest-degrade
docs should say which properties are guaranteed identical across backends and
which are not.

FIRST QUESTION, AND IT DECIDES EVERYTHING: WHICH ONE IS RIGHT? The report says
native parses the C file fully and pure-Python raises PARSE002. That is
suggestive but not conclusive -- a backend that parses "fully" might be
accepting something it should reject. Get the file (or a reduced repro of it)
and determine which result is correct against the language, not against
convenience. Do not assume the native path is authoritative just because it is
the faster one or the one that stays quiet.

WHAT TO BUILD, in order:
  1. A DIFFERENTIAL TEST. Parse a corpus with both backends and assert the
     results agree. This is the durable artifact and it is worth more than the
     single fix: without it, the next divergence is found by another consumer
     repo the same way this one was. Include C, C++, Rust, TypeScript and
     Python -- anything with two paths.
  2. The specific setup.c divergence root-caused and fixed on whichever side is
     wrong.
  3. A statement in the docs of what parity is guaranteed.

DO NOT fix this by downgrading WAIVE004 to info, which is the reporter's own
fallback suggestion. It would silence the messenger while leaving the two
backends disagreeing, and WAIVE004 has separate problems already (T-3888: it
reports live waivers as matching zero because it is evaluated before the
consuming gate runs). Fixing the parse divergence removes this instance of the
warning legitimately.

MEASURE THE BLAST RADIUS: how many files in a mixed corpus parse differently
between backends? If the answer is "one C file", this is a narrow bug. If it is
a class, the differential test is urgent and the alpha should carry a documented
caveat. That number should be reported before the fix is designed.

MUST-FIRE FIXTURE:   a file that both backends can parse produces identical
                     symbol/finding output from each
MUST-STAY-QUIET:     a file only one backend supports is reported as such
                     explicitly, not as a silent difference in findings

ACCEPTANCE
- Which backend is correct, decided against the language spec with the repro.
- The differential test landed and running over a multi-language corpus.
- The divergence count reported.
- The T-0133 honest-degrade docs updated to state what parity is guaranteed.
- Cross-referenced on T-3845 so the cores-by-default change is not landed
  believing it is purely a packaging change.

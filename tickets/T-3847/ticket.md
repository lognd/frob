---
id: T-3847
title: 'evidence verification buckets only python and rust: cpp/kotlin/ts ids are
  silently never verified, and catch2 is unsupported'
state: in-progress
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
- src/frob/app/ticket_runner/_verify.py
- src/frob/testing/_collect.py
- src/frob/testing/__init__.py
- tests/unit/test_verify_language_buckets.py
- src/frob/app/ticket_runner/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: wire cpp/kotlin/ts collectors into evidence verification buckets (registry-derived),
    make an unbucketed evidence id a loud typed UNMEASURED refusal naming the id and
    languages tried
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/testing/_collect.py
  reason: wire cpp/kotlin/ts collectors into evidence verification buckets (registry-derived),
    make an unbucketed evidence id a loud typed UNMEASURED refusal naming the id and
    languages tried
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/testing/__init__.py
  reason: wire cpp/kotlin/ts collectors into evidence verification buckets (registry-derived),
    make an unbucketed evidence id a loud typed UNMEASURED refusal naming the id and
    languages tried
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_verify_language_buckets.py
  reason: wire cpp/kotlin/ts collectors into evidence verification buckets (registry-derived),
    make an unbucketed evidence id a loud typed UNMEASURED refusal naming the id and
    languages tried
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: export new _verify_unbucketed_ids helper alongside sibling _verify_* re-exports,
    same pattern as _verify_one_bucket_passing
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-09-05: "ensure all tests are bindable -- not just vitest,
but all the testing frameworks across the languages we support (like both catch2
and gtest for c++, cargo test, and so forth)."

This started from logand.app-v2's F-039 ("evidence and close never validate
against vitest/TypeScript node ids at all"). That report is correct but
understates the problem: it is not a vitest gap, it is a PYTHON-AND-RUST-ONLY
verification path wearing a ten-language costume.

MEASURED 2026-09-05.

LANGUAGES WITH GRAMMAR WALKERS (src/frob/lang/_extract.py):
    bash, c, cpp, csharp, java, kotlin, python, rust, tsx, typescript

TEST COLLECTORS THAT EXIST (src/frob/testing/):
    _collect.py         python
    _collect_rust.py    cargo test
    _collect_cpp.py     ctest, gtest
    _collect_kotlin.py  junit
    _collect_ts.py      vitest

EVIDENCE VERIFICATION BUCKETS (src/frob/app/ticket_runner/_verify.py:2109):

    buckets = {
        "python": tuple(n for n in node_ids if matches_collected(n, python_collected)),
        "rust":   tuple(n for n in node_ids if matches_collected(n, rust_collected)),
    }
    for language, items in buckets.items():
        if items:
            outcomes.update(_verify_one_bucket_passing(root, language, items, runners))

TWO buckets. A node id from cpp, kotlin, typescript or anything else matches
NEITHER, so it lands in no bucket, `_verify_one_bucket_passing` is never called
for it, and it contributes NO entry to `outcomes`.

THAT IS THE DEFECT, AND ITS SHAPE IS THE FAMILIAR ONE. An id that was never
verified is indistinguishable from one that verified clean, because both are
simply absent from the failing set. The collectors for cpp/kotlin/ts were
BUILT and are not WIRED to verification -- catalogued, not enforced.

THE SECOND, WIDER HOLE: `_check_evidence_resolution`
(src/frob/tickets/_evidence.py:1344) accepts anything when `collected is None`:

    if collected is None:
        _log.warning("tickets: %s evidence %s recorded UNRESOLVED -- no
                      collector supplied, existence against the current test
                      suite was not checked ...")
        return Ok(None)

It is honest -- it always logs -- but it cannot reject. Every `frob ticket new`
run in this repo today emitted that warning. For a language with no collector,
this is the ONLY path, so any string at all binds as evidence.

FRAMEWORKS NOT SUPPORTED EVEN WHERE THE LANGUAGE IS. Measured by grepping the
collectors for framework names; counts are mentions, zero means absent:
    catch2      0   <- the owner named this one explicitly
    doctest     0
    jest        0
    nextest     0
    xunit/nunit 0   (csharp has a walker, no collector at all)
    go test     0   (no go walker either -- out of scope, note it)
Present: vitest 48, ctest 46, cargo test 24, junit 23, gtest 10.

THE WORK

1. WIRE THE EXISTING COLLECTORS INTO VERIFICATION. Make the bucket set derive
   from the registered collectors rather than being a hand-written two-entry
   dict. This is the highest-value step and it is mostly plumbing: cpp, kotlin
   and ts collectors already exist.

2. MAKE AN UNBUCKETED ID LOUD. An evidence id matching no collector must be a
   typed refusal naming the id and the languages that were tried -- never a
   silent absence from `outcomes`. This is the part that must not be skipped
   even if step 1 is partial: a known-unverifiable id is acceptable, an
   invisibly-unverified one is not.

3. ADD CATCH2, and decide about doctest/jest/nextest explicitly. catch2 is
   named in the directive. For each of the others, say whether it is in or out
   and why -- an enumerated "out, because X" is a fine answer; silence is not.

4. DECIDE THE `collected is None` POLICY. Options: keep warn-only for languages
   with no collector (status quo, honest but unenforcing); refuse unless the
   ticket declares an explicit no-collector escape; or make it an error once
   every supported language has a collector. State the choice. Do NOT make it a
   hard refusal in the same change that lands step 1 without measuring how many
   existing tickets it would invalidate -- measure first, then decide.

FRAMEWORK ID SHAPES DIFFER, AND THAT IS THE HARD PART, NOT THE PLUMBING. pytest
uses `path::Class::method`; gtest uses `Suite.Case`; ctest uses a bare test
name; cargo test uses `module::path::test_name`; vitest uses a file plus a
describe/it string that may contain spaces and quotes; junit uses a FQCN plus
method. `matches_collected` and `_symref_to_nodeid` (src/frob/nodeid.py) encode
pytest's spelling. Do not force the others through it -- resolve per collector,
and say how an ambiguous id (one that could belong to two frameworks) is
disambiguated. Guessing wrong here binds evidence to the wrong test, which is
worse than not binding it.

MUST-FIRE FIXTURES:
  - an evidence id that exists in NO collector is refused, naming the id
  - a gtest id that does not exist is refused
  - a catch2 id that does not exist is refused
  - a vitest id that does not exist is refused
MUST-STAY-QUIET FIXTURES:
  - a real id in each supported framework binds and verifies
  - existing pytest and cargo-test binding is unchanged (no regression)

ACCEPTANCE
- The bucket set derived from registered collectors, not hand-written.
- Unbucketed ids loud, with the fixture proving it.
- catch2 supported; doctest/jest/nextest each explicitly in or out with reason.
- The `collected is None` policy decided, after measuring how many current
  tickets a stricter rule would invalidate.
- A support matrix published in the done report: language x framework x
  (collects? verifies?). That matrix is the durable artifact -- it is what tells
  the next person what is actually bindable.

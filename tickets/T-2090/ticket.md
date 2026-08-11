---
id: T-2090
title: Evidence collection discards the missing_natives it already computed, so a
  fresh worktree reports UnknownEvidence and advises deleting the cache instead of
  building natives
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_collect.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a worktree whose declared natives are unbuilt, when frob ticket evidence
    is given a valid node id, then it either builds the missing natives and resolves
    the id, or fails naming the missing native and its build_cmd -- this test MUST
    fail against current main
  evidence: []
- text: given natives are present and the node id genuinely does not exist in the
    tree, when evidence binding fails, then the message says the test is absent and
    does NOT advise deleting the collection cache
  evidence: []
- text: given natives are already built, when frob ticket evidence runs, then no native
    rebuild is triggered -- the build happens only when missing_natives is non-empty
  evidence: []
threat: null
component: testing
anchor: false
anchor_reason: null
---
## Measured evidence (my own session, verbatim)

Binding evidence for T-2084 in a fresh worktree:

    $ frob ticket evidence T-2084 <two valid node ids> --path <worktree>
    ERROR: collect_python_tests: pytest --collect-only exited 2 in
      /home/logan/projects/frob/.claude/worktrees/t2084-state-color
    ERROR: ticket evidence: pytest collection failed: CollectFailed

The real cause was that a fresh worktree has no built natives. Nothing in
that output says so. The remedy was `uv run frob natives build`, which is
not mentioned.

Worse, the sibling failure on the same path actively misdirects:

    ERROR: ticket evidence failed: UnknownEvidence: Evidence id does not
      resolve to a collected test (the collection cache self-refreshes on
      the next `frob test` / `frob check` run; if it still does not
      resolve, delete .frob/pytest-collect.json ... or fix the id)

I followed that advice, deleted `.frob/pytest-collect.json`, and it did not
help, because the cache was never the problem. Two wasted cycles on a
one-command fix.

## Root cause, read from source

1. `_maybe_autorebuild_natives` ALREADY EXISTS (`src/frob/gates/__init__.py:7381`)
   and already does exactly the right thing. Its callers are:
     - `src/frob/app/ticket_runner/_land_cmd.py:323` (via
       `_worktree_natives_verifiably_healthy`)
     - `src/frob/gates/__init__.py:7518` (inside `run_gates`)
   It is NOT called on the evidence/collection path.

2. `collect_python_tests` (`src/frob/testing/_collect.py:444`) ALREADY
   COMPUTES the answer and carries it in its own result:

       natives = _load_natives_or_empty(root)
       missing = _missing_natives(natives)
       ...
       return Ok(CollectedTests(node_ids=cached, missing_natives=missing))

   `src/frob/testing/_models.py:103` states the intent outright:
   "`missing_natives` lets COV003 name the real remedy (build the native)".

3. COV003 does exactly that (`src/frob/gates/__init__.py:2020-2023`),
   formatting `f"{spec.name} (run: {spec.build_cmd})"`.

So the information is computed, carried, and already used correctly by one
consumer -- and then DISCARDED at the point where an agent actually hits the
wall. This is the same shape as T-1669's `allocator_lock`: a correct
primitive wired into too few call sites.

## Cost, and why a brief is not the fix

Every agent brief in this session tells agents to build natives first, and
the playbook covers it. Agents still hit it, and so did I, an hour after
writing the memory about it. A rule that must be remembered before the tool
will work is not enforcement. Per the standing audit rule: if a written rule
was not followed, the rule is not the fix.

## DO NOT FIX IT THIS WAY

- **Do not just reword the error string.** A better sentence still costs the
  agent a full round trip. The information is already in hand at the moment
  of failure; act on it.
- **Do not make every `frob ticket evidence` call build natives
  unconditionally.** A native build is slow, and land cost is already the
  fleet's throughput ceiling (~210s inside the land lock). Build only when
  `missing_natives` is non-empty, i.e. only when it is known to be the cause.
- **Do not silently swallow a genuine absent-test case into a natives
  rebuild.** After a rebuild, if the id still does not resolve, the correct
  answer is "this test does not exist in this tree" -- which must be said
  distinctly from "collection failed". I hit BOTH cases in one session and
  they were indistinguishable in the output; that is what made the diagnosis
  take three attempts.
- **Do not delete or weaken the cache-invalidation advice** for the case
  where it IS the cache; just stop offering it when `missing_natives` says
  otherwise.

## The general rule

A diagnostic must name the remedy it already knows. This repo has the
precedent written down and enforced elsewhere: T-1664, "Semantic checks must
report UNRESOLVED, never silently pass when they cannot" -- same principle,
different surface. Here the check does not silently pass, but it reports the
wrong reason, which costs the same debugging session.

---
id: T-1982
title: Land-time ty check passes explicit paths, bypassing the tests/fixtures exclude,
  so detector fixtures can refuse a land
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`pyproject.toml` excludes `tests/fixtures/**` from type checking, but the
land-time `ty check` invocation passes EXPLICIT PATHS, and an explicit
path overrides the config exclude. So fixture files -- which are
deliberately malformed, duplicated, or otherwise non-conforming BY
DESIGN, because they exist to be detected -- get type-checked anyway and
can refuse a land.

MEASURED, 2026-08-10, while landing T-1957: the new fixture
`tests/fixtures/dup_type_name/src/{mod_a,mod_b}.py` (a deliberate
type-name-only clone pair, the whole point of the fixture) was
type-checked at land time despite the exclude. The agent confirmed the
same exposure applies to the PRE-EXISTING sibling fixture
`tests/fixtures/dup_region/`, so this is not specific to the new files.

It was worked around by making the fixture self-contained rather than by
touching the exclude config -- a good local call, since editing the
exclude to satisfy a checker invocation that ignores excludes would not
have worked anyway. But the workaround does not generalize: every future
fixture under `tests/fixtures/` inherits the same trap, and a fixture
that CANNOT be made type-clean (one whose entire purpose is to be
ill-typed) has no workaround at all.

WHY IT MATTERS: fixtures are how detectors are regression-tested here.
T-1957 exists precisely because a detector gap needed a corpus. If
adding a corpus can refuse a land, the cost of testing a detector goes
up exactly when we most want it down -- and the failure appears at LAND
time, after all the work, not at authoring time.

DO NOT FIX IT THIS WAY:
- Do NOT add per-file `# type: ignore`-style suppressions across
  fixtures. A suppression must target any consumer's checker, not just
  the one this repo runs, and blanketing fixtures with them hides real
  problems in non-fixture code if a path is ever mis-globbed.
- Do NOT delete or weaken the `tests/fixtures/**` exclude. It is correct;
  the defect is that the land-time invocation bypasses it.
- Do NOT special-case the two known fixture directories by name. The next
  fixture will not be in the list, which is the same
  exemption-by-enumeration trap that leaves guards silently narrow.

FIX DIRECTION: make the land-time checker invocation honor the project's
configured excludes -- either by not passing explicit paths that fall
inside an excluded glob, or by filtering the explicit path list against
the exclude set before invoking. One place, applies to every fixture that
will ever exist.

ACCEPTANCE: first test must FAIL before the fix -- add a deliberately
ill-typed file under `tests/fixtures/`, run the land-time check path, and
assert it is NOT type-checked. Then assert a genuinely ill-typed file
OUTSIDE `tests/fixtures/` is still caught (the exclude must not widen),
and confirm `tests/fixtures/dup_region/` and
`tests/fixtures/dup_type_name/` are both covered.

---
id: T-3884
title: 'nothing installs the built frob wheel and runs it before publish: CI proves
  the source tree, not the artifact'
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
OWNER DIRECTIVE 2026-09-05: "Hold the alpha until we're sure we have a working
build." This ticket is what "sure" requires, and it is a gap, not a formality.

THE GAP, MEASURED 2026-09-05 against .github/workflows/release.yml.

The workflow DOES smoke-test the native wheels, and does it well:

    line 111  # Acceptance: "a built wheel installs into a clean venv on each
              #  target platform and the natives import successfully"
              #  -- verified HERE, on the real runner that just built it
    line 114  - name: Install the just-built wheels into a clean venv and import them
    line 118       uv venv /tmp/native-check-venv
    line 119       uv pip install --python .../bin/python \
                       frob-core/dist/*.whl strata-core/dist/*.whl
    line 121       .../python -c "import frob_core, strata_core; ..."

THERE IS NO EQUIVALENT FOR FROB'S OWN WHEEL. Nothing installs the built `frob`
artifact into a clean environment and runs it. The pure-Python wheel is built
(`uv build`), uploaded, and published without ever being executed.

WHY THAT IS THE WHOLE PROBLEM. CI proves the SOURCE TREE passes its tests. It
does not prove the PUBLISHED ARTIFACT works, and those differ in exactly the
ways that bite: dependency resolution against the real index rather than the
lockfile, packaging metadata, entry points, extras, and files that exist in the
repo but were never included in the wheel.

WE ALREADY HAVE A LIVE INSTANCE OF THAT DIFFERENCE. T-3857: `frob serve` is
broken against mcp 2.x because the `serve` extra pins `mcp>=1.28.1` unbounded.
This checkout resolves 1.28.1, so every gate is green and `frob serve` works
locally -- while a fresh resolve gets mcp 2.x and a failing import. A green
repo and a broken published extra, from one source tree. No amount of CI on the
source tree can see it; only installing the artifact can.

WHAT TO BUILD -- an artifact smoke stage in release.yml, after build and BEFORE
publish, gating the publish:
  1. Create a clean venv. Install the built frob wheel FROM dist, not from the
     source tree, and not with `uv sync`. Resolve dependencies from the index
     the way a user would.
  2. Run a real command, not just an import: `frob --version` AND at least one
     verb that exercises the dependency surface (`frob doctor` is the natural
     candidate -- it exists precisely to report native-extension and
     environment health).
  3. Install `frob[serve]` in its own clean venv and start the serve adapter far
     enough to prove the mcp import resolves. This is the exact failure T-3857
     describes; a smoke test that would not have caught it is not worth adding.
  4. Do the same for `frob[native]` (or whatever the extra set becomes once
     T-3845 makes the cores default) and confirm the natives import through
     FROB's own code path, not just directly.
  5. Fail the workflow if any of it fails. This gate must block publish, not
     warn -- an advisory smoke test is a green light nobody read.

DO IT ON EVERY TARGET PLATFORM the build matrix covers, for the same reason the
native check does: the platform that built a wheel is the honest place to prove
it installs. A linux-only smoke test would not have caught a Windows-only
packaging fault.

DECIDE AND STATE: whether the smoke venv should install from a LOCAL dist
directory or from a real index (TestPyPI). Local dist is simpler and catches
metadata/entry-point faults. It does NOT catch a dependency that fails to
resolve from the index, which is precisely the T-3857 shape -- so local dist
alone would have missed the live example. Prefer resolving dependencies from the
index while installing the local wheel; say how you achieve that, or why not.

DO NOT let this become a full test-suite run against the installed artifact.
That is slow and duplicates CI. The bar is: does the thing we are about to
publish install, start, and report healthy.

MUST-FIRE FIXTURES:
  - a wheel whose extra pins a dependency that cannot resolve fails the stage
    (T-3857's exact shape -- construct it deliberately)
  - a wheel missing a file it needs at runtime fails the stage
MUST-STAY-QUIET:
  - a healthy build passes and publishes as before

ACCEPTANCE
- The smoke stage exists, runs on every matrix target, and BLOCKS publish.
- `frob --version`, `frob doctor`, and the serve-extra import all exercised.
- The local-dist-vs-index decision stated with reasoning.
- Both fixtures committed.
- Cross-referenced from the release runbook so the next person cutting a
  release knows this gate is what "we have a working build" means here.

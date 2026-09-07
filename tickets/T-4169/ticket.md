---
id: T-4169
title: 'the documented typani lint command cannot run here: our floor permits a version
  with no lint module, and the lock pinned exactly that version'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given this repository's own environment, when the documented typani lint command
    is run, then it executes successfully
  evidence: []
- text: given the lock refresh, when it completes, then no unrelated dependency has
    been upgraded
  evidence: []
- text: given a declared floor permitting a version that lacks a required submodule,
    when the check runs, then it is detected by importing the required surface rather
    than by comparing version strings
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE HOUSE RULES REQUIRE A LINT COMMAND THAT CANNOT RUN IN THIS REPOSITORY.
Reported from logand.app-v2 (T-0324): the instructed
`uv run python -m typani.lint <file>` fails with "No module named typani.lint".
Their agent skipped it and substituted other checks. Measured here, the same
command fails in frob's own environment for the same reason.

TRACED, WITH EVERY LINK CHECKED:

    frob pyproject declares        typani>=0.0.3
    frob uv.lock pins              typani 0.0.3
    installed package contains     __init__, dispatch, error_set, option,
                                   result, singleton, sum, unit, unreachable
                                   -- and NO lint module
    typani's own tree ships        src/typani/lint/{__init__,__main__,
                                   _report,_rules}.py at version 0.2.2
    published on PyPI              0.2.2 is the latest, and 0.2.0, 0.2.1,
                                   0.1.0 are all available

So the module exists, is packaged by its own project, and IS PUBLISHED. Nothing
upstream is missing. Our floor is simply five releases stale, and the lock
resolved to the floor exactly.

WHY A FLOOR THIS LOW IS ITSELF THE DEFECT. `>=0.0.3` expresses no requirement at
all beyond "some typani". It cannot express the fact that we depend on a
CAPABILITY -- the lint module -- that did not exist at that version. A dependency
declaration that permits a version lacking the feature you rely on is a claim
that is true of the package name and false of the package. The lock then
faithfully pinned the oldest thing allowed, which is the resolver behaving
correctly against a wrong specification.

THE INSTRUCTION AND THE ENVIRONMENT HAVE DISAGREED SILENTLY FOR SOME TIME. Every
agent told to run this lint has hit the failure and worked around it
independently -- the consumer's agent substituted other checks and moved on, and
nothing recorded the gap until it was reported. That is the "catalogued is not
enforced" shape applied to a workflow instruction rather than to code: the rule
is written down, nothing verifies it is runnable, and each reader discovers it
alone.

WHAT TO DO
  1. Raise the floor to the version that actually provides the lint module, and
     refresh the lock. Determine which release first shipped it rather than
     assuming it was the latest -- the tree carries it at 0.2.2 but 0.1.0 or
     0.2.0 may already have had it, and the honest floor is the earliest version
     that satisfies the dependency.
  2. Verify by RUNNING the command afterwards, not by reading the version. The
     failure mode here was a package present but a submodule absent, which a
     version check cannot see.
  3. Consider whether this dependency should be checked at all. A repo whose
     documented workflow requires a submodule of a dependency has a runnable
     precondition; something should assert it once rather than letting each agent
     discover it. If frob has a suitable existing surface for that, use it; if
     not, say so rather than inventing one here.
  4. Report whether any OTHER declared dependency floor is low enough to permit a
     version lacking a capability we depend on. This one was found by accident;
     the same shape elsewhere would be equally invisible.

MUST-FIRE FIXTURE:   the documented lint command runs successfully in this
                     repository's own environment.
MUST-STAY-QUIET:     no unrelated dependency is upgraded as a side effect of
                     refreshing the lock.
THIRD FIXTURE:       a declared floor that permits a version lacking a required
                     submodule is detectable -- by a test that imports the
                     required surface, not by comparing version strings.

ACCEPTANCE
- The floor raised to the earliest release that actually provides the module, not
  simply to the newest.
- The command verified by running it.
- Other floors audited for the same shape, with findings reported either way.
- All three fixtures committed.

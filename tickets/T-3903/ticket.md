---
id: T-3903
title: VERSION001 reads only the native extra's pins, so T-3845's new default-dependency
  pins are unguarded going into a required bump
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
- src/frob/gates/_version_coupling.py
- tests/unit/gates/test_version_coupling.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_version_coupling.py
  reason: 'T-3903: extend VERSION001 to match by package name repo-wide across pyproject;
    add fixtures; pyproject.toml scoped read-only for the bump-path audit finding'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/gates/test_version_coupling.py
  reason: 'T-3903: extend VERSION001 to match by package name repo-wide across pyproject;
    add fixtures; pyproject.toml scoped read-only for the bump-path audit finding'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: pyproject.toml
  reason: 'T-3903: extend VERSION001 to match by package name repo-wide across pyproject;
    add fixtures; pyproject.toml scoped read-only for the bump-path audit finding'
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/release.md
  reason: 'closure: version_coupling_gate frob:doc target'
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: docs/guides/release.md
  reason: not editing this doc; closure demands unrelated scripts/doctor.py out of
    scope for this pin-matching fix
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
VERSION001 guards the `frob[native]` EXTRA's pins. T-3845 (landed today,
85012d5ae) added a SECOND pin site that the gate does not read, and the next
action on the release path is a version bump that would skew it.

MEASURED 2026-09-05, after T-3845 landed:

    pyproject.toml:76   "frob-core==0.530.0",        <- [project].dependencies
    pyproject.toml:77   "strata-core==0.530.0",      <- NEW, added by T-3845
    pyproject.toml:100  native = ["frob-core==0.530.0", "strata-core==0.530.0"]

    src/frob/gates/_version_coupling.py:155
      """VERSION001: frob's own version, its `frob[native]` EXTRA's exact pins
         on frob-core/strata-core, and those two crates' own pyproject.toml
         version fields must all match exactly ..."""

The gate reads frob's `[project].version`, the `native` extra, and the two
crates' own pyprojects. It says "extra" throughout and nowhere reads
`[project].dependencies`. So the two pins at lines 76-77 are UNGUARDED.

WHY THIS IS URGENT RATHER THAN THEORETICAL: `frob release check` currently says
"since 0.530.0: major change -> need >= 0.531.0 (current 0.530.0): BUMP
REQUIRED". The bump is the LAST step before the cut, and the alpha is held
pending it. If the bump updates frob's version and the extra but not the default
dependencies, the published artifact is frob 0.531.0 hard-depending on
frob-core==0.530.0 -- a package that cannot resolve, from a repo where every
gate is green.

That is the exact failure typani reported as their T-026, arriving here by the
same route: "typani's bump script updated four version strings but not the
`native = [...]` pin; caught by eye before dispatch". They caught theirs by eye.
This one is caught by their note, not by our gate, which is the point.

NOTE THE IRONY WORTH RECORDING: VERSION001's own module docstring argues that
`==` on all three, cut together, "is the only shape a gate can mechanically
enforce rather than merely recommend". The reasoning is right; the gate's
coverage simply did not follow the pins when a new pin site appeared.

WHAT TO DO
  1. Extend VERSION001 to read EVERY pin naming frob-core/strata-core anywhere
     in root pyproject.toml -- `[project].dependencies`, every extra under
     `[project.optional-dependencies]`, and any dependency-group table -- not
     just the `native` extra by name. Enumerating the sites by name is what
     failed; enumerate by PACKAGE NAME across the document instead.
  2. Verify the BUMP path writes all of them. The gate catching skew after the
     fact is necessary but not sufficient: `bump_patch_version` /
     `rewrite_pyproject_version` (src/frob/release/__init__.py:345, :409)
     rewrite the `version = "..."` line. Confirm whether anything rewrites the
     pins, and if nothing does, that is the deeper defect -- the gate would then
     fire on every release and require a manual edit, which is a chore that will
     eventually be skipped.
  3. TAKE typani's GENERALISATION SERIOUSLY, from their T-026: "a REL-family
     rule that checks every `<pkg>==<version>` pin naming a sibling
     distribution in the same repo equals the repo version would generalise
     VERSION001 to consumers." That is the correct shape -- VERSION001 is
     currently hardcoded to two package names in one repo, which is the
     portability defect class this repo has a standing rule about. Decide
     whether to generalise now or file it; do not silently leave it
     frob-specific without saying so.

DO NOT simply add lines 76-77 to a hardcoded list of places to check. That is
the same mistake one level down: the next pin site added will be missed the same
way. Match by package name across the whole document.

MUST-FIRE FIXTURES:
  - a `[project].dependencies` pin skewed from frob's version fires VERSION001
  - a loose pin (`>=`) in `[project].dependencies` fires, as it already does for
    the extra
  - a pin in a NEWLY ADDED extra (not named `native`) fires
MUST-STAY-QUIET:
  - today's matched state (all four pins at the same version) is clean

ACCEPTANCE
- VERSION001 matches by package name across the whole root pyproject, not by
  table name.
- The bump path confirmed to rewrite every pin it must, or the gap named.
- The generalisation-to-consumers question answered, not left implicit.
- All fixtures committed.
- Cross-referenced to T-3845, which created the second pin site, and to typani
  T-026, which is the same defect in a sibling repo.

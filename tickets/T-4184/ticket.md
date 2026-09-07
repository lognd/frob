---
id: T-4184
title: 'automatic per-land dev-version bumping as core functionality: a version that
  never moves cannot identify a build, and four consumer reports in one day were version
  skew'
state: queued
kind: feature
origin: human
created: '2026-09-07'
priority: high
blocked_by:
- T-4270
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
- text: given two lands in sequence, when each completes, then the project version
    differs between them with no manual step in either
  evidence: []
- text: given the toggle set off, when a land completes, then the version is untouched
    and behaviour matches today
  evidence: []
- text: given a major-version increment with the toggle still on, when the release
    runs, then it either refuses or requires the configured acknowledgement
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
AUTOMATIC PER-LAND DEV-VERSION BUMPING, AS CORE FROB FUNCTIONALITY FOR EVERY
CONSUMER. Owner request, and it closes a problem measured four times in one day.

THE PROBLEM IT SOLVES. This repository's version string has been unchanged across
hundreds of commits, so two builds reporting the same version can accept and
reject completely different code. Four consumer reports in one day turned out to
be version skew rather than live defects, and the only thing that finally settled
two of them was asking the reporter to grep their installed site-packages for the
name of an internal function. A version that does not move cannot identify a
build, and the reporter, the maintainer and the tool are all blind in the same
way.

THE SPEC, as the owner stated it:
  - The bump happens PER LAND, ATOMICALLY, and NO AGENT THINKS ABOUT IT. It is
    not a step anyone can forget, skip, or be asked to remember.
  - It must be TOGGLEABLE, because a release must be able to turn it off.
  - AT THE FIRST MAJOR-VERSION INCREMENT, frob should either suggest turning it
    off or REQUIRE AN EXPLICIT ACKNOWLEDGEMENT IN CONFIGURATION to keep it on.
  - It is CORE FUNCTIONALITY FOR ANY DOWNSTREAM USER, not a frob-only convenience.

USE PEP 440's DEV SEGMENT. Python already has the fourth component this needs:

    0.530.0       <  0.531.0.dev1     a dev build of the next release
    0.531.0.dev4  <  0.531.0.dev5     the counter advances
    0.531.0.dev4  <  0.531.0          and it vanishes at the stable release

Verified with the packaging library, which is already a declared dependency here.

DO NOT USE A SEMVER-STYLE HYPHEN SUFFIX. It looks like the same idea and is not:
packaging parses a hyphen-number suffix as a POST-release, which sorts AFTER the
stable version rather than before it -- the exact inverse of the intent. Two
conventions that disagree silently is the worst available outcome. Build metadata
after a plus sign is also unusable as release identity, because the index rejects
local versions.

THERE IS A BLOCKER IN OUR OWN CODE AND IT MUST BE FIXED FIRST. The release module
parses versions with a hand-rolled regular expression matching three numeric
groups, start-anchored with no end anchor. Measured: a dev-suffixed version
matches it and yields only the three numbers, so THE DEV SEGMENT IS SILENTLY
DISCARDED. Every comparison would treat a dev build as identical to the stable
release, and the counter would do nothing for the problem it exists to solve.
Replace that parser with the packaging library already on the dependency list --
this is the same hand-rolled-versus-standard-parser shape this queue keeps
filing, and here it would defeat the feature outright.

THE OWNERSHIP MECHANISM ALREADY EXISTS, WHICH MAKES THIS SMALLER THAN IT LOOKS.
The land already owns this exact line: T-1805 records that pyproject is PARTIALLY
land-owned -- specifically its version line -- while every other field remains
legitimate ticket territory, and two sibling files are wholly land-owned and
refused outright for any worktree commit that touches them. So "the land writes
the version, an agent never does" is established, documented behaviour. This
feature extends it rather than introducing it.

DESIGN POINTS TO DECIDE, NOT ASSUME
  1. Where the toggle lives, and its default for a NEW project. A scaffolded
     project should get a sensible default and a comment explaining the
     major-version interaction, or downstream users will meet this only when it
     surprises them.
  2. What the major-version behaviour actually is. "Suggest turning it off" and
     "require an acknowledgement to keep it on" are different strengths; the owner
     named both. Pick one, and make the acknowledgement a configuration value
     rather than a prose reason -- this repo has recorded four times in one
     session that an intention stated in prose is not enforcement.
  3. How this interacts with REL001. That rule demands a bump when the PUBLIC API
     changes and is about release semantics; the dev counter is about build
     identity. They are orthogonal and must not fight -- confirm that a dev-suffixed
     version neither satisfies nor spuriously violates REL001, with a fixture each
     way.
  4. Whether the counter resets. On bumping to the next stable, the dev counter
     should start over; state that explicitly.

ONE COST TO WEIGH HONESTLY: a per-land bump touches the manifest on every land,
and this drive has spent significant time on contention over that exact file. The
land already writes that line, so the additional contention should be nil -- but
confirm it rather than assuming, because the failure mode is fleet-wide.

MUST-FIRE FIXTURE:   two lands in sequence produce two distinguishable versions,
                     with no manual step in either.
MUST-STAY-QUIET:     with the toggle off, the version is untouched by a land and
                     behaves exactly as today.
THIRD FIXTURE:       a major-version increment with the toggle still on either
                     refuses or requires the configured acknowledgement, per the
                     decision above.

ACCEPTANCE
- The version parser uses the standard library-grade parser, not a hand-rolled
  regex, and dev segments survive every comparison.
- The bump is applied by the land, atomically, with no agent-facing step.
- A configuration toggle exists, is documented, and is set sensibly by the
  scaffold for a new project.
- The major-version transition behaviour is implemented as decided and cannot be
  satisfied by prose.
- REL001 interaction proven both ways.
- All three fixtures committed.

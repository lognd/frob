---
id: T-4259
title: move the two rust kernel crates from the repository root into a single crates
  directory
state: queued
kind: feature
origin: human
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
- frob.toml
- Makefile
- .github/workflows/ci.yml
- .github/workflows/release.yml
- frob-core/**
- strata-core/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the repository root, when the move is complete, then both rust crates
    live under one crates directory and no crate directory remains at the root
  evidence: []
- text: given the relocated crates, when both natives are built from source and imported,
    then both extension modules import and both crate test suites pass
  evidence: []
- text: given the gate configuration's documentation anchor and native test routing,
    when the gates run after the move, then they resolve rather than reporting an
    unrouted item
  evidence: []
- text: given the release workflow, when it builds wheels and source distributions
    for both crates, then every working directory and artifact path resolves at the
    new location
  evidence: []
- text: given the ticket history, when the move lands, then no historical ticket or
    done report has been rewritten to say the crates were always in their new home
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MOVE THE TWO RUST CRATES OUT OF THE REPOSITORY ROOT AND UNDER A SINGLE CRATES
DIRECTORY. Owner request. Today the frob kernel crate and the strata kernel
crate each sit as their own top-level directory beside the Python package, the
docs, and the tests, which makes the root read as though native code were a
peer of the application rather than a component of it. Grouping them under one
crates directory is the conventional Rust workspace layout and makes the root
legible.

THIS IS A PURE RELOCATION. No crate content changes, no module renames, no
version changes. If the work starts to look like anything else, stop and say so.

WHAT MAKES THIS BIGGER THAN A DIRECTORY RENAME. The two crate locations are
named in build configuration, in gate configuration, and in both CI workflows,
and several of those references are load-bearing in ways a search-and-replace
will not tell you about.

  The project manifest declares each crate as a path source and pins each as a
  hard equality default dependency. The pins and the path sources must stay
  consistent with each other through the move, and the manifest's own comments
  record a publish-ordering contract that must not be disturbed.

  The gate configuration names one crate's type stub as a documentation anchor,
  names both toolchain files, and routes native test items by matching a working
  directory against the leading segment of a symbol reference. That routing
  fails loudly on an unrouted item, so a half-updated configuration will not
  silently pass; expect it to be the first thing that breaks, and treat that as
  the mechanism working.

  The integration workflow caches both build output directories keyed on a hash
  of both lock files, and runs the crate test suites by changing directory into
  each crate.

  The release workflow builds, checks, and uploads wheels and source
  distributions for both crates using per-crate working directories and artifact
  paths. THIS IS THE PATH AN IMMINENT PUBLISH DEPENDS ON. Getting it wrong does
  not fail a test; it fails a release, or worse, publishes something wrong.

  The Makefile's native-build recipe is a prerequisite of most other recipes and
  reinstalls both natives from source. Note independently that this recipe being
  in a Makefile at all contradicts the standing rule that workflows belong in
  frob subcommands; do NOT fix that here, but file it if no ticket covers it.

THE TICKET HISTORY MUST NOT BE REWRITTEN. Several hundred files under the ticket
tree mention the old locations. Those are historical records of what was true
when they were written, and rewriting them would falsify the record. Restrict
the change to configuration, source, tests, documentation, and workflows.
Documentation prose describing where the crates live SHOULD be updated; a done
report describing a past change SHOULD NOT.

VERIFY BY BUILDING, NOT BY GREPPING. A clean search proves only that no literal
text remains. Prove the move by building both natives from source, importing
both extension modules, running both crate test suites, and running the gate
suite far enough to show the anchor and routing configuration still resolves.
Confirm the lock files are consistent afterwards.

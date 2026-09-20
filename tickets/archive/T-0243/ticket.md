---
id: T-0243
title: cache.db not invalidated across frob/parser upgrades
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/**
- tests/**
- docs/modules/graph.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense fingerprint-package incident history into T-0243 body
  actor: logan
  at: '2026-09-19'
  old_length: 401
  new_length: 2626
evidence:
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (medium): a stale cache served 2830 symbols where a fresh parse of identical sources gave 3007 -- cache survived a frob upgrade with changed parser behavior. Include the frob version + grammar/parser fingerprint in the cache key so any upgrade invalidates cleanly. Regression: bump a fake version constant in test, assert cold rebuild.

<!-- narrative-moved:src/frob/graph/cache.py:74:T-0243 -->
frob:ticket T-0243
Packages whose behavior changes the shape of the parsed graph: the frob
distribution itself (extraction/digest logic) plus every tree-sitter
grammar/runtime package it parses source with. Bumping any of these can
silently change symbol/edge output for identical source bytes -- see the
T-0243 malmberg pilot incident (2830 vs 3007 symbols from a stale cache
after a frob upgrade).
frob:ticket T-0402
G6: "frob-strata" was missing here -- a frob-strata native-extension
upgrade that changed `.strata` parse output would NOT invalidate the
cache, exactly the T-0243 incident this mechanism exists to prevent,
reintroduced for `.strata`.
frob:ticket T-0433
G6 (full fix): the tree-sitter grammar packages are now DERIVED from
`frob.lang.GRAMMAR_FINGERPRINT_PACKAGES` -- the module that actually owns
grammar loading -- instead of hand-copied here. "frob" (this
distribution's own extraction/digest logic) and "frob-strata" (the one
non-tree-sitter grammar) are not `frob.lang` grammar packages, so they
stay listed here explicitly; every tree-sitter-loaded language's
fingerprint surface now updates automatically if `frob.lang` ever adds or
drops a package to that set, with no second hand-copied tuple to forget.
frob:ticket T-3433
PORT001-IDENT reviewed and DECIDED as a legitimate self-reference, not a
portability bug: this cache belongs to frob's OWN analyzer, not to
whatever repo it happens to be scanning. The fingerprint's job is "would
a version bump of a package that determines parse OUTPUT silently make
this cache stale" -- and the packages that determine THIS cache's parse
output are always frob's own extraction/digest code and frob-strata's
native `.strata` grammar, regardless of which repo is under analysis. A
consumer repo's own dependencies play no part in how frob.graph parses
that repo's source, so there is nothing to "resolve from the scanned
repo's own declared dependencies" here -- unlike PORT001-PATH's silent-
pass/false-fire class, retargeting this to be config-driven would not
fix a real cross-repo bug, only replace two names that are correct for
every host repo with a lookup that could return the wrong ones.
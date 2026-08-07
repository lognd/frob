---
id: T-0988
title: 'frob fmt: perform the deferred repo-wide recompaction once the DSL continuation-parse
  bug is fixed'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
blocked_by:
- T-0987
- T-0994
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/**
- tests/**
- frob-core/src/**
- strata-core/src/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/**
  reason: 'T-0988: repo-wide mechanical frob fmt recompaction touches every file with
    a frob: directive comment across src/, tests/, and native crates by the ticket''s
    own repo-wide nature; declared scope narrowed to the fixed module only, extending
    to cover the actual sweep'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/**
  reason: 'T-0988: repo-wide mechanical frob fmt recompaction touches every file with
    a frob: directive comment across src/, tests/, and native crates by the ticket''s
    own repo-wide nature; declared scope narrowed to the fixed module only, extending
    to cover the actual sweep'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob-core/src/**
  reason: 'T-0988: repo-wide mechanical frob fmt recompaction touches every file with
    a frob: directive comment across src/, tests/, and native crates by the ticket''s
    own repo-wide nature; declared scope narrowed to the fixed module only, extending
    to cover the actual sweep'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: strata-core/src/**
  reason: 'T-0988: repo-wide mechanical frob fmt recompaction touches every file with
    a frob: directive comment across src/, tests/, and native crates by the ticket''s
    own repo-wide nature; declared scope narrowed to the fixed module only, extending
    to cover the actual sweep'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1
- tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_matches_a_real_token
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_transition_allows_when_covers_scope_true
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_requires_reason
designated_repro_test: null
threat: null
component: null
---
## Description

T-0985 fixed `_fmt_directives.py`'s `# noqa: E501` escape-hatch handling
(directive lines ending in a `# noqa`/`# noqa: CODE` pragma are now left
byte-identical instead of force-wrapped), but deliberately did NOT run
the one-time repo-wide recompaction that would make `frob fmt` idempotent-
at-zero on a fresh `frob fmt .` -- roughly 260 files still have `frob:`
directive comments in a non-minimal (but individually within-limit)
wrapped form, left over from an older/looser wrapping convention.

Attempting the repo-wide recompaction during T-0985 surfaced a real,
separate bug (filed as T-0987): rewrapping shifts word-wrap
boundaries, and in ~a dozen files this happens to place a `frob:`-shaped
prose token at the start of a continuation line, which
`frob.graph.dsl.parse_directives` then misparses as a bogus new
directive. Doing the recompaction before that bug is fixed cascades into
90 DSL gate errors and dozens of new test failures (registry
reconciliation exhaustiveness gates, doc-anchor coverage, several ticket-
land/CLI tests) -- see T-0985's Done report for the exact repro and file
list.

## Plan

1. Land T-0987 (or whatever the DSL continuation-parsing fix
   becomes) first.
2. Re-run the repo-wide recompaction: `frob fmt .` from a clean worktree.
3. Verify the diff is purely whitespace/wrapping (no token-content change)
   the same way T-0985 did: for every changed `.py` file, strip comment
   markers + collapse whitespace on both old and new content and assert
   equality (T-0985's Done report includes the exact script).
4. Run the FULL test suite (not just the fmt-directive unit tests) and
   confirm zero new failures beyond this repo's pre-existing baseline
   (T-0985 hit 5 baseline-failing tests unrelated to fmt; see its Done
   report for which ones and why they're pre-existing).
5. Confirm `frob fmt --check .` reports 0 files after the recompaction is
   committed -- idempotent-at-zero, the actual acceptance bar for
   T-0985/this ticket combined.

## Acceptance

- `frob fmt --check .` on a fresh checkout after landing reports 0 files.
- Full test suite green (modulo the same pre-existing baseline failures
  T-0985 documented, if still unfixed at that point).
- No new `MalformedDirective`s anywhere in the repo relative to the
  pre-recompaction baseline.
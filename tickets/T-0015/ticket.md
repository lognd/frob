---
id: T-0015
title: 'gob-mdtest: markdown corpus runner with firing and non-firing controls'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0005
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- crates/gob-mdtest/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a corpus file with a fire block lacking a clean block for the same rule,
    when run, then the corpus fails naming the rule
  evidence: []
- text: Given a block expecting RULE at line 3 and the runner reports it at line 4,
    when run, then the failure shows both
  evidence: []
threat: null
component: gob-mdtest
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-mdtest per build-test-ci.md section 2 and audit L18. A test harness that walks tests/mdtest/**/*.md in a consuming crate, parses fenced blocks with an info string (language plus options such as rule=ID, expect=fire|clean, config=...), runs a caller-supplied closure (text, options) -> Vec<Finding>, and asserts the expected finding ids and line numbers given by inline markers (a comment containing error: RULE or the finding count); failures print a diff. Every rule corpus must contain at least one fire and one clean case for the rule or the harness fails the corpus with the rule id (positive-control doctrine). Expose a macro mdtest!(dir, runner) that registers each file as a libtest case name for nextest. Document the corpus format in the crate docs.
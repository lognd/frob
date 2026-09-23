---
id: T-5421
title: 'docenum: comment-dsl-directives.md COMMENT_TYPES enumeration omits css/scss/html/javascript/vue'
state: done
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 1
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/extending/comment-dsl-directives.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '1'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/test_docenum_gate.py::TestCommentDslDirectivesDocMatchesCommentTypes::test_enumerates_directive_members_match_comment_types
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-3c4622ad
branch: t-draft-3c4622ad
---
CI run 35863437945 (ubuntu+macos, dev 08b02016db); re-verified failing on current dev tip: tests/test_docenum_gate.py::TestCommentDslDirectivesDocMatchesCommentTypes::test_enumerates_directive_members_match_comment_types fails -- doc claims 12 members but frob.lang._extract.COMMENT_TYPES's real keys are 17 (T-5300/T-5303 added css/html/javascript/scss/vue without updating this doc's frob:enumerates directive). Add the 5 missing languages to the members= list.
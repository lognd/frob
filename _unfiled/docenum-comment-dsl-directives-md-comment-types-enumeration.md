+++
id = "01M35RZY9D272J8WXP7NXZG2N3"
title = "docenum: comment-dsl-directives.md COMMENT_TYPES enumeration omits css/scss/html/javascript/vue"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5421"]
labels = ["milestone:v0.534.0"]
scope = ["docs/guides/extending/comment-dsl-directives.md"]
+++

CI run 35863437945 (ubuntu+macos, dev 08b02016db); re-verified failing on current dev tip: tests/test_docenum_gate.py::TestCommentDslDirectivesDocMatchesCommentTypes::test_enumerates_directive_members_match_comment_types fails -- doc claims 12 members but frob.lang._extract.COMMENT_TYPES's real keys are 17 (T-5300/T-5303 added css/html/javascript/scss/vue without updating this doc's frob:enumerates directive). Add the 5 missing languages to the members= list.

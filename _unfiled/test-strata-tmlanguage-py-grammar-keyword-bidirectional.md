+++
id = "01M336K75BJZ4SSW0QM9317B51"
title = "test_strata_tmlanguage.py grammar/keyword bidirectional coverage drifted"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5291"]
labels = ["milestone:0.534.0"]
scope = ["tests/unit/test_strata_tmlanguage.py", "strata-core"]
+++

gh run 35717833933; re-verified on dev tip 3acf8c6b30: test_construct_keywords_match_parser_bidirectionally and test_clause_keywords_covered_by_grammar both fail -- tmLanguage grammar and parser keyword sets have drifted apart.

+++
id = "01M30M6G31SMTZTHQKSZCA43E3"
title = "LEXCHECK001 new backlog item: _docarch_structural.py::scan_citation_shape decides from re.search without a symref"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5217"]
scope = ["src/frob/gates/_docarch_structural.py", "src/frob/gates/_lexical_selfcheck.py"]
+++

Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469 fails: src/frob/gates/_docarch_structural.py:264 scan_citation_shape decides from re.search/match/fullmatch/findall/finditer and builds a symref-less Violation (LEXCHECK001). This must be either fixed at the root (give the Violation a real symref) or added to _KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG with a stated class-(b) reason per this test's own T-2469 precedent -- do not skip/delete the test.

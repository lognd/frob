## Done report

19 constants annotated with frob:doc edges (docs anchors added or
verified in docs/modules/{app,logging,testing,vet,dup,lang}.md and
docs/strata/{kernel,policy,evidence}.md), 2 honestly underscored as
internal (scripts/bump_version.py _PYPROJECT; strata/_claims.py
_GROWTH_HORIZON_MONTHS -- zero external references, grep-verified by
reviewer). COV001 21 -> 0 on a fresh cache; no new rule codes; ruff and
format clean on all 14 touched files; frob test --base main green.
Evidence ids are the T-0087 CONST-extraction regression tests that
created these obligations; verification itself is gate-based (COV001
count). Reviewer flagged a PRE-EXISTING doc-anchor slug mismatch class
(frob:doc targets are not slug-validated by any gate) -- follow-up
filed as T-0127.

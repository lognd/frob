## Done report

Investigated: both `_LazyStdoutHandler.stream` and `_LazyStderrHandler.stream`
already carry a `frob:doc docs/modules/logging.md#public-api` anchor
(pre-existing in src/frob/logging/handler.py, landed by a prior change to
this file after this ticket was filed) -- a fresh `frob check --only
gates-fast --ticket T-1394` shows zero COV001 findings for handler.py; the
anchor target (`## Public API` -> #public-api) resolves cleanly too, so
DOC002 is clean as well.

Tried adding docs/modules/logging.md to the ticket's own scope to close the
resulting SCOPE002 nudge (the doc anchor's target file is out of scope) but
reverted it: that file is frob logging's single monolithic public-API doc,
already describing 15+ other unrelated symbols across logger.py/
formatter.py/filter.py/color.py/quiet.py -- pulling it in balloons the
scope far past two property anchors, the exact tension T-1010's Done report
already hit and waived rather than chase. SCOPE002 is WARN-tier/a nudge, not
a hard block (docs/modules/gates.md#scope002-t-0998), so leaving the
narrower scope and the resulting nudge is correct rather than expanding.

No code change was needed; this ticket's remaining work was verifying the
prior fix actually closed COV001 and documenting why SCOPE002's nudge is
left unaddressed.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 144 warning(s), 745 waived
- error-findings: none (measured, zero errors)

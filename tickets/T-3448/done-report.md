## Done report

The ticket's diagnosis (attachment glob tickets/*/attachments/** too broad) was falsified by direct measurement: git check-attr text confirms the -text attachment glob already resolves ONLY for tickets/*/attachments/** and tickets/attachments/** paths (text: unset) and NOT for an unrelated root-level file (text: auto) -- the glob was never the bug. The real root cause: T-2611 later added a repo-wide '* text=auto eol=lf' pin (for measurement tools reading working-tree bytes directly), which suppresses checkout-time CRLF injection for EVERY tracked file regardless of attribute coverage. This made the old negative-control assertion (checkout and assert literal CRLF bytes present) permanently false for ALL files, not just attachments, so it could no longer distinguish 'covered by the attachment rule' from 'covered by the repo-wide default eol=lf pin' -- a real, deterministic failure (reproduces locally), not a CI-only environment artifact. Fixed by rewriting the negative control to assert the resolved git attribute directly via 'git check-attr text', which is immune to the eol pin and actually proves what the test claims: an unrelated file resolves to the repo-wide default (text: auto), never to the attachment rule's override (text: unset). No .gitattributes or src/frob/tickets/_archive.py change was needed since the underlying attribute coverage was already correct; only the test's verification method was wrong.

### Changed
```
 tests/unit/test_gitattributes_merge.py | 29 ++++++++++++++++++++++-------
 tickets/T-3448/ticket.md               |  6 +++++-
 2 files changed, 27 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v2_nested_attachment_survives_checkout_unconverted` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v1_flat_attachment_still_covered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 12 error(s), 4018 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3448, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json

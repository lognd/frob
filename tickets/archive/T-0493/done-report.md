## Done report

Root cause: `_done_report_section_lines`/`replace_done_report_section`
(src/frob/tickets/_models.py) both located the section's END boundary by
stopping at the NEXT `## ` heading, including another `## Done report`
heading. If a stray, empty `## Done report` heading ever preceded a real,
substantive one (hand-typed as a placeholder, or left over from an earlier
corrupted write), the FIRST (empty) heading's own section boundary was the
SECOND heading's line -- meaning `has_substantive_done_report` only ever
examined the empty first section (0 lines of content between the two
headings), permanently rejecting a genuinely-done ticket as
`MissingEvidence`. `replace_done_report_section` had the mirror bug on the
write side: it only ever replaced the first, empty section, leaving the
real second heading + its content stuck as `after`, untouched, on every
subsequent `frob ticket done-report` call -- the exact "stray empty heading
before the rendered one" this ticket describes, and the reason manually
deleting the leading blank heading was the only workaround.

Fix: added `_done_report_section_end`, the single home for this boundary
scan, used by both functions -- it now SKIPS OVER a repeated `## Done
report` heading (treating it as still part of the same section) and only
stops at a genuinely different `## ` heading or EOF. This makes both
functions treat a run of one-or-more Done-report headings as one section:
`has_substantive_done_report` now sees the real content past a stray empty
heading, and `replace_done_report_section` collapses the whole run into the
one freshly-composed section on the very next write -- self-healing a
stray duplicate instead of leaving it stuck forever.

Regression test: TestReplaceDoneReportSection.test_stray_empty_heading_
before_real_one_collapses_to_one reproduces the exact corrupted shape (an
empty heading immediately followed by a real, substantive one) and asserts
a single `replace_done_report_section` call collapses it to exactly one
heading with the new content.

### Changed
```
 src/frob/app/ticket_runner.py      | 25 ++++++++--
 src/frob/tickets/_models.py        | 56 +++++++++++++++++-----
 src/frob/tickets/_store.py         | 98 ++++++++++++++++++++++++++++++--------
 tests/test_tickets.py              | 32 +++++++++++++
 tests/test_tickets_evidence_cli.py | 43 +++++++++++++++++
 tests/unit/test_ticket_store.py    | 14 ++++++
 tickets.md                         | 93 ++++++++++++++++++++++++++++++++++--
 7 files changed, 321 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestReplaceDoneReportSection::test_stray_empty_heading_before_real_one_collapses_to_one` (pytest node id, verified passing when recorded)

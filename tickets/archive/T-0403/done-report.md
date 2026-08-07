## Done report

Audit docs/audits/gates-accounting.md worked finding-by-finding, verify-first / counterexample-first.
Two findings fixed with real code + tests (B14, B15). One finding (B13) dispositioned as
correct-by-design per the audit's own note -- no fix, no follow-up needed. The remaining
11 findings (B1-B12 except B13) are genuine, HIGH/MEDIUM/LOW, but each requires a
cross-cutting design change (severity promotion campaigns, digest-facet redesign, new
collectors, waiver-model changes) too large for this ticket's budget -- filed as
follow-up tickets under this ticket's parent, each carrying the finding text, repro, and
a RIGHT-WAY fix direction, per the dispatch's explicit "file a follow-up rather than
rushing" instruction.

Disposition table:
- B1  (HIGH)   TEST001 vacuous-test credit, TEST002/005 non-blocking -- FOLLOW-UP (too large): T-draft-45d2f71f
- B2  (HIGH)   DRIFT001 default sig facet blind to behavior       -- FOLLOW-UP (too large): T-draft-b3811054
- B3  (HIGH)   native TS/C/C++ frob:tests need no execution        -- FOLLOW-UP (too large, overlaps T-0404#1): T-draft-772cc4a3
- B4  (MEDIUM) TEST005 skips symbols absent from coverage.xml      -- FOLLOW-UP: T-draft-da68edb5
- B5  (MEDIUM) coverage/baseline/prework chain gitignored, untrusted -- FOLLOW-UP: T-draft-30bed097
- B6  (MEDIUM) name-only convention match credits wrong symbol      -- FOLLOW-UP: T-draft-35fbff4e
- B7  (MEDIUM) parametrized no-op tests inflate case counts         -- FOLLOW-UP: T-draft-612af618
- B8  (MEDIUM) COV002/SCOPE001/bare-TODO fail open on empty diff    -- FOLLOW-UP: T-draft-64eacee1
- B9  (MEDIUM) SCOPE001/PRE001 disabled with no active ticket       -- FOLLOW-UP: T-draft-1374d550
- B10 (MEDIUM) COV002 satisfied by ANY open ticket's broad scope    -- FOLLOW-UP: T-draft-15c96f2d
- B11 (MEDIUM) file-level waiver blanket-suppresses whole file      -- FOLLOW-UP: T-draft-7ee4ed63
- B12 (MEDIUM) INV001 evidence is existence not proof               -- FOLLOW-UP: T-draft-1bbab126
- B13 (LOW)    WAIVE002 doesn't flag a waiver on a real-but-non-firing rule -- VERIFIED CORRECT BY DESIGN
              per the audit's own note ("which is correct-by-design"); no fix, no ticket.
- B14 (LOW)    REL001 changelog check passes on ANY substring occurrence of the version --
              FIXED: _changelog_mentions now requires the version, bounded against
              adjacent digits/dots, to appear on a markdown HEADING line
              (gates/__init__.py:_changelog_mentions). Verified the OLD behavior first:
              a CHANGELOG.md with only "## [1.2.34] ... bumped past 1.2.3" used to satisfy
              _changelog_mentions(root, "1.2.3") via bare substring match -- now returns
              False; a real "## [1.2.3]" heading still returns True.
- B15 (LOW)    TEST006 staleness misses newly ADDED files (stamped_hashes.get(path) is None
              -> silently skipped, not flagged) -- FIXED: _test006_stale now treats a
              present-in-snapshot, absent-from-stamp source file as stale, scoped to the
              same _SOURCE_EXTS set the coverage stamper itself hashes (so doc/.strata
              files the graph also tracks, but the stamper never did, are not
              misreported).

Section (A)/(D) framing and (C) soundness notes in the audit were read but are not
independently-actionable findings -- no disposition row needed for them.

### Changed
```
 src/frob/gates/__init__.py | 54 ++++++++++++++++++++++++++++++++++++++++++----
 tests/test_gates.py        | 53 +++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 11 +++++++---
 3 files changed, 111 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_test006_stale_on_new_file_not_in_stamp` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_changelog_mentions_rejects_substring_in_prose` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_changelog_mentions_accepts_real_heading_entry` (pytest node id, verified passing when recorded)

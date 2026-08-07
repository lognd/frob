## Done report

FINAL (round 2, after coordinator feedback): completed the full
gate-by-gate catalog. `known_gate_rule_ids()` returns 118 rule ids;
this sweep additionally found 7 real, currently-firing rule ids the
frozenset itself OMITS (PARSE001, TICK005, REG011, PII011, PII012,
SYSWAIVE002, THREAT006 -- itself H3 below), for 125 distinct rule ids
total. Every one of the 125 now carries an explicit verdict in
docs/audits/gates-vacuous.md's "Catalog coverage" table -- swept total
== catalog total, zero unread, per the acceptance criterion's own bar.

Round 1 (18 examined vectors) covered COV/TODO/SCOPE/PRE/TEST/TICK001-002/
COMPLIANCE005/REG001-010/DEC/FUZZ/PARSE-partial/SEC/SEC110/the lang parse
entrypoint/2 strata comment-flagged sites. Round 2 (this pass) closed the
remaining ~60 rule ids/dispatch sites: INV001-006, DEBT001-003,
DEPR001-004, DSL001, WAIVE001-007, REL001, DOC001-005, DUP001-002 (native
path), FUZZ (confirmed), PERF001-007, SYS001-004, TICK003-004/006-008,
FMT001, PII010-012, ARCH001/101-103, REF001-003, REG011, WALK001
(confirmed), EXCL001, SEC-CVE-FINGERPRINT-001, RENDER001, LANG001-003,
DEAD001, PROTO001-003, PARSE001's own dispatch, SYSWAIVE002, THREAT006,
plus the `_KNOWN_GATE_RULES`-completeness cross-check itself.

Findings by severity (final): 3 HIGH, 4 MEDIUM, 3 LOW (disclosed/
already-tracked, no new ticket).

HIGH:
- H1 (round 1): SCOPE001 vacuously passes when `ticket.scope` is empty.
- H2 (round 1): partial (salvaged) tree-sitter parses silently drop
  symbols; `partial_parse_files()` has zero gate consumers.
- H3 (round 2, NEW): `_KNOWN_GATE_RULES` omits 7 real, currently-firing
  rule ids (PARSE001, TICK005, REG011, PII011, PII012, SYSWAIVE002,
  THREAT006) -- the exact DEAD001-class listing-omission T-0753 already
  fixed once, recurred 6+ more times since. Breaks WAIVE002 validity for
  those 7 ids AND strata/registry `caught_by`/`handled_by` resolution
  credit for controls that actually ARE enforced by them.

MEDIUM:
- M1 (round 1): lang/** tree-sitter ingestion has no file-size cap or
  parse timeout -- untrusted-file trust-boundary gap.
- M2 (round 1, broadened round 2): registry/design-dir-backed gates
  (COMPLIANCE005, REG001-011, DEC001-002, and -- newly identified this
  round -- SYS001-004 and DOC001/DOC003) all share the same "missing
  backing dir/file/glob-match == no claim" posture that cannot
  distinguish never-adopted from deleted. SYS*/DOC001/DOC003 instances
  folded into the existing fix ticket's scope rather than re-filed (one
  "adopted-then-vanished" detector should cover all six).
- M3 (round 2, NEW): `dup_gate` silently no-ops (log-only WARNING, no
  Violation) when `frob-core` native is unavailable, even with
  `[dup].enforce=true` -- the exact class T-0552/TEST013 already fixed
  for the coverage gate's own native fallback, never applied to DUP.
- M4 (round 2, NEW): RENDER001, PII010/SEC110 (via `pii_structural_gate`),
  and SEC-CVE-FINGERPRINT-001 each run their own private
  `ast.parse`/file-read outside `frob.lang.parse_file`'s PARSE001-tracked
  pipeline, silently skipping an unparseable/undecodable file with only a
  DEBUG log line -- exactly the class T-0558/PARSE001 was built to make
  loud, recurring in three independent code paths that never route
  through it.

LOW (disclosed/already-tracked, no new ticket): L1 secrets_gate's
line-wrap gap (already fully disclosed in-code, T-0151); L2 DEAD001's
Python-only scope (already disclosed, already has a follow-up ticket
per its own docstring -- T-0422's Done report); L3 ARCH101-103's missing
`frob:enforces CHK-GATE-*` cross-link (already disclosed as a pending
land obligation, same T-0788 precedent).

Draft tickets filed: 7 fix+gate pairs total (14 tickets) -- 4 pairs from
round 1 (H1, H2, M1, M2/COMPLIANCE005), 3 more pairs round 2 (H3, M3, M4).

docs/index.md's audit-index entry updated to reflect the final, complete
sweep (125/125, zero unswept) and the full finding list.

Disclosed cut: none remaining -- round 1's disclosed gap (the other half
of the catalog) is now closed. LANG002's inherent completeness boundary
(cannot flag a wholly unenumerated file extension) and L1-L3 above are
the only residual, explicitly-accepted non-defects.

### Changed
```
 docs/audits/gates-vacuous.md | 429 +++++++++++++++++++++++++++++++++++++++++++
 docs/index.md                |   1 +
 tickets.md                   | 381 +++++++++++++++++++++++++++++++++++++-
 3 files changed, 810 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

## Done report

Enumerated the repo's real surface mechanically before comparing to
docs/, per the ticket's required method (code enumeration first, diff
against docs second, not a prose read-through):

- CLI verb tree: `frob --help`'s 43-verb list, cross-checked against
  `docs/commands/*.md` + `docs/modules/*.md`. All 43 have at least one
  dedicated doc section describing their own behavior, except `frob
  coverage` (T-1516/T-1525), which is named in a verb table and one
  passing aside but has no section of its own.
- Env vars: every `FROB_*` string-literal constant assigned in
  src/frob/**/*.py (15 real vars, after filtering out non-env-var
  `_RE`/regex-named constants that share the prefix), cross-checked
  against every doc file, matching either the literal string or the
  Python constant name that carries it (several vars are referenced by
  constant name, not literal string, and that is adequate documentation
  -- confirmed for FROB_PARSE_ARTIFACT_CACHE, see the audit doc's "Not
  gaps" section). One genuinely undocumented anywhere: T-0806's
  FROB_WORKER_STDOUT_LOG_LEVEL.
- Gate rule ids: every `"XXXX###"`-shaped string literal under
  src/frob/gates/ (275 distinct ids), cross-checked against
  docs/modules/gates.md's own "Rule catalog" table, which frames itself
  as the exhaustive index. 122 real, already-fired ids are missing from
  that table (each documented elsewhere in a per-family doc, so not an
  undocumented-BEHAVIOR gap -- a discoverability/completeness gap in the
  one file claiming to be the catalog).

Full findings, method, and the complete missing-id list:
docs/audits/docs-completeness-2026-08-06.md (indexed from docs/index.md
alongside the repo's other audit docs).

Fixed inline (small, unambiguous, within this ticket's budget):
- Added a dedicated paragraph to docs/modules/gates.md documenting
  FROB_WORKER_STDOUT_LOG_LEVEL/T-0806, next to the existing T-1436
  process-pool-cap note (the natural neighboring section).

NOT fixed, filed instead (disclosed cut -- backfilling either
accurately requires reading each gate/CLI implementation in detail,
disproportionate to complete inside this sweep without risking
inaccurate doc content):
- T-1681: backfill ~122 missing rows into docs/modules/
  gates.md's rule-catalog table (full id list carried in the ticket
  body).
- T-1682: add a dedicated `frob coverage` doc section.
Both draft ids renumber at land; verify the real ids on main before
citing them elsewhere.

Per this ticket's own instruction: doc gaps are recorded, not
detector-gap-classified here -- T-1611 (next in series) does that
classification, consuming docs/audits/docs-completeness-2026-08-06.md
as its input, including the one concrete, already-confirmed detector
observation this sweep surfaced in passing: docs/modules/gates.md has
no mechanical self-check that its own rule-catalog table stays
exhaustive against the gate modules it claims to index (noted in the
filed ticket's body for T-1611's classification, not resolved here).

Gates: `frob check --ticket T-1610` clean after `frob ticket sweep
T-1610` refresh. Deletion-filter check
(`git diff main --diff-filter=D --stat`) shows only FROBLEMS.md,
T-1612's own authorized deletion -- nothing new deleted by this ticket.

### Changed
```
 FROBLEMS.md                                 |  26 -----
 docs/audits/docs-completeness-2026-08-06.md | 126 +++++++++++++++++++++
 docs/index.md                               |   1 +
 docs/modules/gates.md                       |  15 +++
 tickets.md                                  | 166 +++++++++++++++++++++++++++-
 5 files changed, 305 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 2779 warning(s), 711 waived
- error-findings: none (measured, zero errors)

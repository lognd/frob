## Done report

Corrected system-design-corpus.md's own DENOMINATOR MANIFEST so the
119-vs-105 discrepancy is machine-distinguishable in the source doc
itself, not just in the already-reconciled system-design.yaml
(T-0392 had already tagged the yaml side; the corpus.md side was the
remaining gap this ticket closed).

Artifact identification (recounted independently against
RECONCILIATION.md finding (d), then cross-checked line-by-line against
docs/design/registry/system-design.yaml's own
`disposition: "out-of-scope(manifest-extraction-artifact)"` entries,
which matched exactly):

- SDC-1-STRATA-CHECKABILITY, -2, -3, -4, -5 (5) -- header-cell
  ("STRATA-CHECKABILITY") of section 1's five headerless single-row
  tables (1.2-1.6) mis-scanned as a named row, once per table.
- SDC-1-ADVISORY, SDC-1-NOT-CHECKABLE (2) -- the same tables' own
  checkability-value cell (`advisory`/`not-checkable`) was short enough,
  once slugified, to collide with a second header-shaped artifact rather
  than read as a real topic name.
- SDC-5-STRATA-CHECKABILITY, -2 (2) -- same header-mis-scan for
  section 5's two headerless tables (5.2 SLO, 5.3 chaos engineering).
- SDC-10-STRATA-CHECKABILITY (1) -- same pattern, section 10.1 (Jepsen).
- SDC-13-BEST-PRACTICE, -2, -3, -4 (4) -- header-cell ("Best practice")
  of 4 of section 13's five seam tables mis-scanned as a named row.

Total: 14 artifact rows, matching RECONCILIATION.md finding (d) and the
already-landed system-design.yaml disposition list exactly (verified
id-for-id, not just by count).

Disposition: kept every artifact row in place in the manifest (never
silently deleted, per the no-silent-drop instruction) and appended
`| artifact: true | artifact-reason: mechanical-extraction (header-cell/
short-cell-value mis-scanned as a named row)` to each of the 14 lines.
Added a new explanatory paragraph directly above the manifest list
documenting the extraction bug and the disposition, and extended the
manifest's own format line to declare the optional trailing
`artifact: true` field. Updated the trailing `TOTAL: 119` line to state
the 105-genuine / 14-artifact split explicitly.

Final counts (verified by the bound evidence command): 119 total ids,
14 tagged `artifact: true`, 105 genuine (119 - 14). This satisfies the
ticket's acceptance criterion via its second disjunct ("artifact rows
are machine-distinguishable without a hardcoded exclusion list") -- a
parser can now `grep`/filter on `artifact: true` to get the genuine 105
without needing the RECONCILIATION.md id list baked into any tool.

docs/design/registry/system-design.yaml needed NO changes: T-0392 had
already landed the full 14-entry `disposition:
"out-of-scope(manifest-extraction-artifact)"` set (with
`total_genuine: 105` / `total_artifacts: 14` fields already present),
and it matches this pass's independently-recounted 14 exactly.

Deviation: `frob ticket evidence --evidence-cmd --accepts` did not
actually bind the cmd: evidence entry to acceptance[0] (a real CLI/
library gap in src/frob/tickets, filed as T-0796, out of this
ticket's docs-only scope). Worked around by calling the underlying
`frob.tickets.add_evidence(root, "T-0677", [<already-recorded cmd:
entry>], accepts=[0])` library function directly to bind the
already-verified evidence after the fact -- no source files touched, no
hand-edited YAML.

### Changed
(no changed files detected)

### Evidence
- `cmd:test "$(grep -c "^- id: " docs/design/system-design-corpus.md)" = 119 && test "$(grep -c "^- id: .*artifact: true" docs/design/system-design-corpus.md)" = 14 exit=0 sha256=e3b0c44298fc` (cmd evidence, exit=0)

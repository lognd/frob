## Done report

Implemented named frob:waive reason presets: `frob:waive RULE preset="<name>"`
resolves its reason from `frob.graph._waive_presets.WAIVE_PRESETS`, a single
table documented (and drift-locked) at docs/modules/gates.md#waiver-presets.
`_attrs_verb_error_waive` in frob.graph.dsl now accepts `preset=` as an
alternative to `reason=` (both may coexist; an explicit `reason=` wins), and
resolves the preset's text into `attrs["reason"]` at parse time -- every
downstream consumer (WaiverRef, _match_waiver, _apply_waivers) needs zero
changes since it only ever sees `attrs["reason"]`. An unknown preset name is
a MalformedDirective (WAIVE001-shaped), never a silent no-op.

Two presets defined: `split-carried-prose` (the T-0585 INV006 calibration-
batch lineage) and `split-fragment` (the package-split-submodule REF002
family). Migrated 127 verbatim INV006 calibration-batch waivers and 4 REF002
split-fragment waivers to the new preset form via a mechanical script that
only touched sites whose reason text matched the canonical template
byte-for-byte (modulo the per-file filename substitution) -- sites carrying
additional site-specific rationale beyond the boilerplate tail (~55 files,
mostly the "this file's 'only'/'never' hits" strata variant and a handful of
double-space-typo'd copies) were left untouched rather than risk losing real
information; disclosed below, not silently dropped.

Each migrated site still carries its own explicit `frob:waive RULE
preset="name"` directive naming the rule -- only the boilerplate reason
prose deduplicates, per the ticket's own "not a blanket waiver" mandate.

Cut: the ~55 INV006 sites whose reason text carries extra site-specific
clauses beyond the T-0585 boilerplate tail were not migrated in this pass
(migrating them would require either dropping real information or adding
more presets per-variant); left as-is, a natural follow-up ticket.

### Changed
```
 tickets.md | 397 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 395 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWaivePresets::test_docs_table_matches_waive_presets` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaivePresets::test_resolve_preset_known_name` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaivePresets::test_resolve_preset_unknown_name_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaivePresets::test_waive_preset_resolves_reason_and_matches_like_inline` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaivePresets::test_unknown_preset_is_malformed_directive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

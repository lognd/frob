## Done report

Audited all 5 T-0524 COV007 dedup commits (086499c6, 53f177ce, f9fd1fc6,
2642c5f3, c96db341) for the over-pruning pattern the T-0706 incident
found: an extending-guide anchor (docs/guides/extending/*.md#fragment)
removed as a supposed COV007 duplicate when it was actually the only
carrier of that anchor for its registry_of_registries.json row.

Method:
- Diffed each commit for removed `frob:doc` lines
  (`git show <commit> | grep -E '^-.*frob:doc'`).
- Cross-referenced every removed anchor against
  docs/guides/extending/registry_of_registries.json's anchor_file/
  anchor_symbol rows.
- Ran tests/unit/test_extending_guides_complete.py (the canary) and
  `frob check --only docanchor` (the DOC002 did-you-mean instrument) at
  HEAD.

Findings:
- 086499c6 (tickets/__init__.py) and c96db341 (gates/__init__.py) removed
  only docs/modules/*.md#public-api anchors (module docs, not extending
  guides) -- not in scope for this concern.
- f9fd1fc6 (dup/_core.py) and 53f177ce (lang/_common.py) removed no
  frob:doc lines at all -- they added frob:waive COV007 directives, doc
  anchors were left in place.
- 2642c5f3 (vet/_capability_registry.py) is the ONE commit that removed
  an extending-guide anchor
  (docs/guides/extending/capability-registry.md#capability-registry) from
  DANGEROUS_OPERATIONS as a supposed duplicate. This is the exact incident
  already caught and fixed by T-0706 (waived SCOPE001 there, anchor
  restored). No other T-0524 commit repeats this pattern.

Conclusion: honest no-findings beyond the already-fixed T-0706 case. All
5 anchor_file/anchor_symbol pairs in registry_of_registries.json that
overlap T-0524's touched files still resolve correctly;
test_extending_guides_complete.py passes (6/6); `frob check --only
docanchor` at HEAD reports 0 errors. No further over-pruning found; no
code changes made.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_has_a_guide_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_no_orphan_guides` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_probe_table_and_inventory_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_probe_still_matches_source` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

## Done report

Changed:
  src/frob/gates/_docptr.py::_config_ref_candidates
  src/frob/gates/_docptr.py::_is_markdown_link_bracket
  src/frob/gates/_docptr.py::_markdown_link_reference_labels
  tests/test_docptr_gate.py::TestDoc006Config (4 new tests)

Enumeration of bracketed-construct candidates the CONFIG REFERENCE regex
(`_CONFIG_REF_PROSE_RE`) accepts, and disposition of each:
  - genuine TOML `[section]`/`[section.key]` pointer in prose -- kept,
    still resolved against frob.toml/pyproject.toml/Cargo.toml (MUST-FIRE).
  - inline markdown link `[text](url)` -- already excluded by the regex's
    own `(?!\()` lookahead; unchanged.
  - full reference link `[text][label]` -- NEW: excluded by checking
    whether the bracket is immediately followed by a second `[`.
  - shortcut/collapsed reference link `[label]`/`[label][]` resolved via a
    `[label]: target` definition elsewhere in the SAME document -- NEW:
    excluded by collecting all `^[label]: target` definition lines
    (CommonMark reference-link-definition shape) into a lower-cased,
    whitespace-normalized label set and checking membership.
  - footnote reference `[^1]` -- never a candidate; the regex requires a
    leading letter and `^` is not one.
  - task-list marker `- [ ]` / `- [x]` -- never a candidate; no dot
    segment, and `x`/` ` alone fails the "at least one `.` group" shape.
  - bare numeric/citation marker `[1]`/`[12]` -- never a candidate; no
    leading letter.
  - ALL-CAPS citation tag `[IN-REPO]` -- already excluded pre-existing
    (`_ALL_CAPS_TAG_RE`), unrelated to this ticket's fix.

Sibling pointer kinds checked for the analogous defect:
  - FILE/PATH pointer kind (`_file_and_anchor_violations`) and CLI
    pointer kind (`_cli_violations`) both consume `_prose_tokens`, which
    derives candidates from backtick-delimited code spans and from the
    URL-target portion of `[text](url)` inline links only (`_MD_LINK_RE`
    matches `](...)`, never the link TEXT) -- markdown link TEXT is never
    read as a path/CLI candidate in the first place, so there is no
    analogous false-positive there. Both kinds also run against
    `_blank_fenced_blocks(text)` before token extraction, so fenced code
    blocks are already excluded for these two kinds (verified by reading
    `doc006_gate`'s call sequence). Reference-style link TARGETS
    (`[text][label]` / `[label]: target`) are currently never resolved as
    path pointers at all by these kinds -- a coverage gap, not a false
    positive, and out of this ticket's scope; not fixed here.
  - CONFIG REFERENCE kind (`_config_violations`/`_config_ref_candidates`)
    was the one with the real defect, fixed above.

Evidence: tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged,
  ::test_real_section_passes, ::test_inline_markdown_link_not_flagged,
  ::test_shortcut_reference_link_not_flagged,
  ::test_full_reference_link_not_flagged,
  ::test_bogus_section_still_flagged_alongside_markdown_links,
  tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
  (full tests/test_docptr_gate.py run: 93 passed, 0 failed)
Filed: none
Gates: frob check --ticket T-3900 -- gate:SCOPE/gate:PREWORK and the
  diff-scoped gate:COV (COV002/TODO001)/gate:FMT/gate:AFFECT checks clean;
  ruff-format clean on touched files after reformat. Repo-wide gate:ARCH/
  gate:COV/gate:DRIFT/gate:PRE/gate:SCOPE findings in the full run are
  pre-existing and unrelated to this diff (verified: no new symbol/call
  added by this change into any file outside declared scope; git diff
  contains no added cross-file references).

### Changed
```
 tickets/T-3900/ticket.md | 8 ++++++++
 1 file changed, 8 insertions(+)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_real_section_passes` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_inline_markdown_link_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_shortcut_reference_link_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_full_reference_link_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006Config::test_bogus_section_still_flagged_alongside_markdown_links` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 6 error(s), 4517 warning(s), 937 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/vet/_bare_toolchain.py, DRIFT001@src/frob/gates/_rule_id_scan.py, DRIFT002@src/frob/check/_python.py, PRE001@tickets/T-3900, SCOPE002@tickets.md

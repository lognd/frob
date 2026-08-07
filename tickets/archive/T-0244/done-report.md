## Done report

Did both (b) and (a), not just (b)-then-spike-(a): (b) is the real fix,
(a) is wired in fully rather than left as a spike, since it was cheap once
(b)'s region-detection existed.

Mechanism (`src/frob/vet/_capability.py`, python host files only for this
pass -- the ticket's own reported shape):
- `_embedded_code_regions(path)`: walks a python file's tree-sitter parse
  for `string` nodes; a node's content counts as an embedded-code region
  when it is >= 200 bytes (`_EMBEDDED_CODE_MIN_LEN`) AND contains at least
  one of a small HTML/JS signal-token set (`_EMBEDDED_CODE_SIGNALS`:
  `<script`, `<html`, `<!doctype`, `<body`, `<div`, `document.`,
  `window.`, `addeventlistener`, `innerhtml`), case-insensitive.
- `_embedded_capabilities(path)`: for every region found, ALWAYS adds the
  new `embedded_code` capability kind (fail-closed declaration per
  docs/design/structural-linter-adversarial-hardening.md rule 3 -- the
  region is declared even when the re-scan below finds nothing), PLUS
  runs the existing typescript needle table (`_matched_capabilities`)
  over the region's own text so specific sub-capabilities
  (`eval`/`html_render`/`fetch_url`/...) surface too when the embedded
  content matches a JS/TS registry needle. Wired into
  `scan_file_capabilities` for python files, after the existing lexical
  and T-0328 binding passes.
- `_embedded_operations(path)`: the `scan_file_operations` sibling --
  names the specific typescript `DANGEROUS_OPERATIONS` entry that fired
  inside an embedded region (library/rationale/safer_alternative), not
  just the bare kind. Wired into `scan_file_operations` for python files.
- Registry (`src/frob/vet/_capability_registry.py`): added `embedded_code`
  to `CAPABILITY_KINDS` (T-0158's single-source enum) plus 5
  `MatrixExcuse` rows (one per LANGUAGES entry: python/typescript/rust/
  c-cpp/kotlin) explaining the kind is emitted structurally by the region
  detector above, not from a per-language needle -- keeps
  `unexcused_empty_cells()` (the T-0158 exhaustiveness gate) satisfied for
  every (kind, language) cell.

Fail-closed confirmed by test: `test_embedded_code_declared_even_when_
content_opaque_to_needles` -- a large embedded plain-HTML region (no
script, no JS needle match at all) still declares `embedded_code`; the
region is never silently passed just because the best-effort re-scan came
back empty. `test_embedded_code_region_below_size_threshold_not_detected`
confirms the heuristic requires BOTH the size floor and a signal token,
not either alone (a short string merely mentioning `<script>` in prose
does not fire).

VET002 (observed capability not in declaration) now naturally covers this
class end to end: a dependency embedding an HTML/JS payload as a python
string literal will show `embedded_code` (and any specific sub-
capabilities the re-scan resolves) in its observed set, requiring a
`[vet.allow]` declaration or waiver like any other observed capability --
no separate gate needed.

Docs: `docs/modules/vet.md` -- new `embedded_code` row in the "Capability
taxonomy" table, plus a new "Embedded-code declaration, not full re-parse"
paragraph in "Honest limits" stating plainly that detection is a
heuristic (not a real HTML/JS parse), scoped to python hosts only for
this pass, and that TS/rust/C-C++/kotlin hosts embedding HTML/JS strings
are a documented gap, not attempted here.

Changed:
- src/frob/vet/_capability.py::_embedded_code_regions
- src/frob/vet/_capability.py::_looks_like_embedded_code
- src/frob/vet/_capability.py::_string_content_bytes
- src/frob/vet/_capability.py::_embedded_capabilities
- src/frob/vet/_capability.py::_embedded_operations
- src/frob/vet/_capability.py::scan_file_capabilities (wired in)
- src/frob/vet/_capability.py::scan_file_operations (wired in)
- src/frob/vet/_capability_registry.py::CAPABILITY_KINDS (+embedded_code)
- src/frob/vet/_capability_registry.py::CAPABILITY_MATRIX_EXCUSES
  (+5 embedded_code excuse rows, one per LANGUAGES entry)
- docs/modules/vet.md (taxonomy table row + Honest limits paragraph)

Evidence (fresh `pytest --collect-only -q -o addopts=""`, all 4 node ids
confirmed collected, `tests/test_vet.py::TestEmbeddedCodeCapability: 4
tests collected`), recorded via `frob ticket evidence T-0244`:
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_html_script_string_detected
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_code_region_below_size_threshold_not_detected
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_code_declared_even_when_content_opaque_to_needles
- tests/test_vet.py::TestEmbeddedCodeCapability::test_embedded_code_regions_scanned_via_operations

`uv run pytest tests/test_vet.py tests/test_capability_registry.py -q`:
all passed (272 tests). `uv run frob test --base main`: python
touched-set selected (51 node ids incl. the 4 new ones), exit=0,
13.03s. `uv run ruff check` / `uv run ruff format --check` on
`src/frob/vet/_capability.py src/frob/vet/_capability_registry.py
tests/test_vet.py`: clean under both `uv run ruff` and PATH `ruff`.
`uv run ty check src/frob/vet/_capability.py
src/frob/vet/_capability_registry.py`: All checks passed.

Gates: `uv run frob check --delta --ticket T-0244` (after re-stamping the
baseline post-edit, per playbook section 6): `0/54 new  0 errors, 0
warnings, 25 waived` -- clean delta, no new violations of any kind.
REL001 disclosure: `frob check`'s full (non-delta) run shows a
pre-existing REL001 (public API changed since 0.21.0, bump to >= 0.22.0)
-- present in the baseline BEFORE this ticket's changes (confirmed via
`--stamp-baseline`'s 54-kept count being identical before and after), not
caused by this ticket; not fixed here (out of this ticket's scope --
version bumps are a release-flow concern, not this ticket's). No
strictness check was weakened: `embedded_code` is a strictly ADDITIVE new
observed-capability kind (more can now fire, VET002 gets stricter for
affected packages, never looser), and the matrix exhaustiveness gate
(`unexcused_empty_cells`) was kept satisfied, not bypassed, by adding
real excuse rows rather than exempting the kind.

Filed: none -- no out-of-scope work found.
